---
layout: "simple"
title: "LibreAgent: Core Architecture"
description: "AgentCore, the identity value types, and the four backend interfaces a platform host implements"
weight: 60
---

LibreAgent is the platform-neutral core of the LibreSCRS card agent, published
as a library in its own right from 5.0. This page covers the seventeen public
headers that make up the core itself: `include/LibreSCRS/Agent/*.h` and the
`backend/`, `config/` and `crypto/` subtrees.

Who this is for: someone writing a **platform host** — a process that owns a
transport and a policy gate and lets the neutral core drive the card. If you are
writing a *client* of a running agent, you want
[Building a Qt client](/developer-guide/agent-client-qt/) instead.

## The shape

```
        platform host (LibreLinux, LibreDarwin)
        owns: transport · authorizer · prompter · capability resolver
                            │  injected by reference
                            ▼
                        AgentCore
        owns: presence model · caches · key tracker · prompt gate
              config · signing engine · rate limiter · lease manager
              operation scheduler
```

`AgentCore` is a **constructor-injected owning aggregate**. There is no
`instance()`, no lazily-created global: a host constructs one once its four
borrowed collaborators exist, and holds it in place. The type is neither
copyable nor movable, because its owned members guard mutexes and worker
threads.

```cpp
#include <LibreSCRS/Agent/AgentCore.h>

// resolver, transport, authorizer and prompter are owned by the host and must
// outlive the core.
LibreSCRS::Agent::AgentCore core{
    resolver, transport, authorizer, prompter,
    configFile,          // std::filesystem::path
    cacheRoot,           // std::filesystem::path
    resolveReaderCard,   // std::function<std::optional<ReaderCard>(const std::string&)>
    resolveCardKey};     // Pkcs11Broker::ResolveCardKeySeam
```

Everything the core owns is reached through a reference accessor —
`core.presenceModel()`, `core.credentialCache()`, `core.objectRegistry()` — so a
backend re-sources from the aggregate rather than caching its own copies.

### Why the ownership split is not incidental

Members are declared in a deliberate internal dependency order, so construction
runs dependency-first and destruction runs strictly **borrower before
borrowee**. That is the invariant a card agent needs most, and it is the one
that is easiest to break by moving a declaration.

A related invariant is worth stating on its own, because it explains a type you
would otherwise find puzzling. A private-key or read operation runs on a
per-reader worker that can block in a call nobody can cancel: the consent
prompt, a held-session acquire, an on-card terminal operation. If the host is
torn down while that worker is parked, the worker outlives the aggregate that
owned its collaborators.

`CryptoWorkerContext` is the answer. It bundles everything such a worker may
touch on unblock — the prompter, the prompt gate, the credential caches, the
lease manager, the shutdown token — into one shared object. Every worker
closure that can outlive the aggregate value-captures **that whole context**,
so on unblock it touches only memory it co-owns. One capture instead of four,
and a future worker path is safe by construction rather than by review.

## Identity: three opaque tokens

`Agent/Identity.h` defines three value types the core passes around and never
parses:

| Type | What it names | Minted by |
|---|---|---|
| `CallerToken` | one connected client | the backend, from the transport |
| `ObjectId` | one reader, or one card insertion | `PresenceModel` |
| `OperationId` | one in-flight operation | `OperationManager::publish` |

Each wraps a value with equality and a total order and offers nothing else.
`CallerToken` replaces what used to be a raw bus name in five separate places —
the authorization subject, the PKCS#11 caller, the lease key, the rate-limiter
key and the disconnect table — so a backend that identifies clients differently
changes one mapping instead of five.

`ObjectId` is explicitly **never a card fingerprint**; `0` is reserved for
"none". The backend owns the mapping from `ObjectId` to a wire path, and no
core component reconstructs a path.

Why a token rather than a process id: a `pid_t` is reused. A transport-minted
token is reuse-immune for the connection's lifetime, which is what makes it
safe as an authorization subject — the host resolves it to a process subject at
check time, pinned by pidfd or start time.

## The four backend interfaces

A host implements these. They are the entire platform surface.

### `AgentTransport` — the client membrane and its dispatch thread

```cpp
class AgentTransport {
public:
    virtual void publishReader(const ReaderState&) = 0;
    virtual void publishCard(const CardState&) = 0;
    virtual void withdraw(ObjectId) = 0;
    virtual void updateProperties(ObjectId reader, const PropertyDelta&) = 0;

    virtual void post(std::function<void()>) = 0;
    virtual void postAfter(std::chrono::microseconds, std::function<void()>) = 0;

    virtual void onClientDisconnect(std::function<void(CallerToken)>) = 0;
};
```

Three concerns that look separable — publishing objects, posting onto the event
loop, and noticing that a client went away — are one interface on purpose. On
each platform they are one cohesive transport-and-threading model: D-Bus
`ObjectManager` plus sd-event plus `NameOwnerChanged` on Linux, an XPC endpoint
plus dispatch plus connection invalidation on macOS. Splitting them would ask a
host to implement three views of one object.

`onClientDisconnect` is **additive**: every registered handler fires, in
registration order, on each disconnect. Production registers two — the
operation manager's auto-cancel, then the PKCS#11 broker's lease revoke — and
that order is part of the contract.

### `Authorizer` — the policy gate, with three outcomes

```cpp
enum class AuthorizationOutcome : std::uint8_t { Granted, Denied, Undecided };

class Authorizer {
public:
    virtual AuthorizationOutcome authorize(std::string_view actionId,
                                           const CallerToken& caller) = 0;
};
```

Three states, not two, and this is the single most important detail on the
page. A client told "not authorized" when the authority never answered has been
told something untrue about a security decision. `Undecided` means **nothing
was decided and nothing was done** — an unreachable policy service is not a
denial, and a timeout waiting for a human to answer a prompt is not a denial
either.

The action ids are constants in the same header, so the strings cannot drift
between the host's action-selection path and its `Authorizer` implementation:

| Constant | Action | Posture |
|---|---|---|
| `kActionConfigure` | change signing settings | default-allow |
| `kActionConfigureTrust` | change trust and timestamping settings | authenticate |
| `kActionSign` | produce a signature | default-allow, PIN is the consent |
| `kActionPkcs11Login` | establish a PKCS#11 lease | default-allow, PIN is the consent |
| `kActionCredentialsManage` | change or unblock a PIN | default-allow, PIN is the consent |

Default-allow is not laxness: for these actions the PIN the user is about to
type *is* the proof of human presence, and a second dialog in front of it would
train people to click through both. The action exists so a site policy can
restrict which clients may ask, and the rate limiter caps abuse under the
default. Trust settings are the exception because they change what a signature
is checked against.

Two implementations ship in the header: `AllowAllAuthorizer` for tests and for
the explicit no-policy mode, and a degraded fallback used when the platform
authorization service is unreachable at startup — which fails **closed** on the
trust-elevation action while keeping the default-allow decision for the
operational ones.

### `PrompterClientBase` — collecting secrets, without seeing the transport

```cpp
class PrompterClientBase {
public:
    virtual PromptResult requestPin(const PromptOptions&) = 0;
    virtual PromptResult requestCan(const PromptOptions&) = 0;
    virtual PromptResult requestMrz(const PromptOptions&) = 0;
    virtual void cancel(const std::string& promptId) noexcept;              // no-op default
    virtual PinChangePromptResult requestPinChange(const PromptOptions&);   // fails closed
};
```

A secret comes back as a cleansing `Secure::String`, never as a file
descriptor, so the core never sees the transport that carried it.

Two rules govern how this interface grows, and both are load-bearing:

- Growth happens by **appending** a virtual with a safe default —
  `requestPinChange` is one, and its default returns `PromptStatus::Error` so a
  host that has not wired multi-secret prompting fails closed rather than
  silently.
- Growth **never** happens by overloading an existing name. C++ name lookup
  hides an inherited overload set as soon as a derived class declares any
  member of that name, so every implementer would trip
  `-Woverloaded-virtual` — which a host repository builds with `-Werror`.

`cancel` takes a prompt id rather than dismissing "the prompt". The prompt gate
is keyed by card, so more than one dialog can be on screen at once, and an
unaddressed dismissal would close whichever is topmost — very often another
card's.

### `CapabilityResolver`

Owned by the process entry point and borrowed by the core; it answers what a
card in a reader can do. It is documented with the rest of the presence
machinery on
[Presence and caching](/developer-guide/agent-presence-and-cache/).

## Logging

`Agent/backend/Logging.h` is a Qt-free facade in namespace
`LibreSCRS::Agent::log`:

```cpp
namespace LibreSCRS::Agent::log {
    enum class Level : std::uint8_t { Info, Warn, Error };
    using LogSink = std::function<void(Level, std::string_view line)>;

    void init(LogSink sink, std::string category = "rs.librescrs.agent");
    void resetForTest() noexcept;

    void info(std::string_view);      // also warn, error
    template <class... Args> void infof(std::format_string<Args...>, Args&&...);
}
```

This is the one sanctioned process-global in LibreAgent, and it is sanctioned
rather than tolerated: threading a logger reference down to a `catch` block
inside a poll thread would cost the whole surface and buy nothing.
`init` is wired once during single-threaded startup, and `resetForTest()` is
the obligation that comes with a global — a test that injects a sink restores
the built-in one so the next case in the same binary is unaffected. An empty
sink also restores it.

LibreMiddleware carries the same shape under `LibreSCRS::log` since 5.0, down
to the journald priority prefix, so one diagnostic grep reads the host layer
and the middleware alike.

## Feature tokens

`Agent/FeatureTokens.h` holds the agent's optional-capability vocabulary — the
list served verbatim on both wires and read back by clients through
`AgentClient::hasFeature()`. It is `std::`-only by design, reachable from a
build with the core switched off entirely.

The rule attached to it is the interesting part: **only a token whose serving
surface exists may appear in the array.** A task that lands a new surface moves
its token out of the planned list and into the served one in the *same commit*
that lands the surface. A capability is never advertised before it exists,
because a client that asks for one and gets a failure has no way to tell "not
supported here" from "broken".

## Crypto mechanisms

`Agent/crypto/Mechanism.h` names the mechanism a key operation requests, with
its parameters as a closed-but-extensible variant:

```cpp
enum class Mechanism : std::uint8_t {
    RsaPkcs1Sign, RsaPssSign, EcdsaSign,          // private key, lease-gated
    RsaPkcs1Decrypt, RsaOaepDecrypt, EcdhDerive,
    RsaPkcs1Encrypt, RsaOaepEncrypt,              // public key, no consent
};
```

Two of these are wired today (`RsaPkcs1Sign`, `RsaPkcs1Decrypt`, both with
empty parameters); the rest are designed-additive. Freezing the shape now means
EC and RSA-PSS arrive as an enum value plus a parameter arm, and never as a
widened seam signature. Note that `RsaPssSign` is deliberately *not* on the
empty-parameter arm — PSS needs the hash, MGF and salt-length triple, and
pretending otherwise now would force exactly the signature change this design
avoids.

## Related pages

- [Card operations](/developer-guide/agent-operations/)
- [Presence and caching](/developer-guide/agent-presence-and-cache/)
- [The wire protocol](/developer-guide/agent-wire-protocol/)
- [Building a Qt client](/developer-guide/agent-client-qt/)
- [Architecture overview](/developer-guide/architecture/)
