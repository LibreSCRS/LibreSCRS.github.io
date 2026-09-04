---
layout: "simple"
title: "LibreAgent: The Wire Protocol"
description: "The transport-neutral socket wire, the two error axes, the PKCS#11 broker and its leases, and the country-signing anchor import"
weight: 63
---

Twenty-seven public headers cover the agent's outward-facing contract:
`Agent/wire/` (10), `Agent/pkcs11/` (12), `Agent/trust/` (1) and
`Agent/util/` (4).

## Why the wire links nothing of ours

`LibreAgent::Wire` depends on **no first-party library**: no Qt, no
LibreMiddleware, no OpenSSL. That is not minimalism for its own sake. It is
what lets the same protocol serve a D-Bus transport on Linux and a plain socket
transport on macOS without either host dragging a desktop stack, a card engine
or a crypto library behind it — and it is what lets the wire library be built
from a configuration with the agent core switched off entirely.

The formal definition is `wire/librescrs-agent.cddl` in the LibreAgent
repository, installed alongside the library. It is the authority on message
shapes; the C++ in `wire/Messages.h` is a typed model over it, and a guard test
pins the two together. Read the CDDL rather than reconstructing shapes from
this page.

## Framing

```
[uint32 bodyLen LE][uint32 fdCount LE][ CBOR body (RFC 8949) ]
                                       + fdCount descriptors via SCM_RIGHTS
```

```cpp
inline constexpr std::uint32_t kProtocolVersion  = 1;
inline constexpr std::size_t   kFrameHeaderBytes = 8;
inline constexpr std::size_t   kMaxFrameBytes    = 1u << 20;   // 1 MiB
inline constexpr std::size_t   kMaxFrameFds      = 16;
```

Large artifacts — a signed document, a portrait, a signing input — never travel
in the body. They ride as file descriptors over `SCM_RIGHTS` and are referenced
from the CBOR body by index, so message bodies stay small and the frame cap can
be tight.

The **fd count in the header** is the part worth understanding. Without it, a
streaming reader cannot robustly attribute descriptors received mid-stream to
the frame they belong to; ancillary data does not announce which frame it goes
with. Carrying the count in the fixed header lets a reader take exactly that
many, which is the same approach D-Bus takes with its own fd field.

Two details that are security posture rather than plumbing:

- The frame cap rejects an oversized frame **before allocating** for it. The
  peer on the other end may be a PKCS#11 module loaded into a browser, which is
  untrusted input by definition.
- The socket is `SOCK_CLOEXEC`, and `FD_CLOEXEC` is set on each received
  descriptor with an explicit `fcntl` after `recvmsg` — because
  `MSG_CMSG_CLOEXEC` is Linux-only and absent on macOS, and a leaked descriptor
  in a child process is exactly the kind of thing a portable-looking flag
  silently fails to prevent.

The fd ceiling of 16 is not arbitrary either: a batch signature relays one
descriptor per document, so it has to cover the batch maximum with room to
spare, and it mirrors the reference D-Bus daemon's default so the socket
transport gets the same per-message budget the D-Bus surface relies on.

## Two error axes, and why they are separate

This is the part most likely to trip a client author, because the two look
interchangeable and are not.

### `ErrorCode` — asynchronous, numeric, frozen

Carried on the operation-finished signal. Clients branch on the numeric value.

```cpp
enum class ErrorCode : std::uint32_t {
    None = 0, CardRemoved = 1, CredentialWrong = 2, CredentialBlocked = 3,
    CommunicationError = 4, ParseError = 5, UnsupportedCard = 6, AuthFailed = 7,
    // ... appended only
};
```

**Wire-frozen and append-only.** Existing entries are never renumbered and
never removed; the integers are a published contract. A new code takes the next
free value.

The header names its own mirrors, and the reason it does is worth repeating:
the integers are re-declared by hand in the Linux host's CBOR schema and in the
macOS Swift host's type mirror, and both must move in lockstep with any append.
This repository's guard test pins every integer and the current maximum, so an
append trips CI until the pin is added — which is the reminder to update the
mirrors.

The Swift mirror is deliberately **fail-closed with no automatic guard**: an
unmirrored code is treated as a hard error rather than quietly ignored, so a
forgotten append surfaces as a visible macOS failure instead of a wrong branch.

A consumer that reaches the taxonomy through this project's Qt client library
re-declares nothing — `LibreSCRS::AgentClient::ErrorCode` is a `using` alias
for this same enum, not a copy — so there is nothing on that side that can fall
out of step. That is why the KDE client holds no mirror of its own. The Qt
client also passes an unrecognised numeric value through verbatim rather than
rejecting it, so a newer agent talking to an older client degrades rather than
failing.

### `SyncError` — synchronous, named, reorderable

Carried by synchronous methods: as the `name` field of the socket's error info,
and as the tail of the D-Bus error name.

```cpp
enum class SyncError : std::uint8_t {
    UnknownCard, KeyNotFound, NotAuthorized, /* ... */
};
```

The underlying integers here are **not** wire-significant: the wire carries the
*name*. So this enum may be reordered freely without breaking a peer, unlike
`ErrorCode`. What must stay in lockstep is the **set of names**, and the
conversion in both directions lives in the same header.

Why carry this axis at all, when the Qt client also classifies errors into
coarse buckets: several distinct names collapse onto one bucket — `NotAuthorized`
and `UserNotLoggedIn` both become "access denied" — so the bucket alone cannot
tell a caller which refusal it actually received. A client that wants to say
something useful reads the name.

### Decode failures are a third thing

`WireError` names why a request could not be modelled from its CBOR —
`NotDecodable`, `NotAMap`, `MissingField`, `WrongType`, `NoTag`,
`UnknownMessage`, `BadEnum`, `BadConfigKey` — as distinct from the byte-level
decode failure the CBOR reader reports. All of them fail closed. The agent is a
server: it parses inbound requests strictly, as untrusted input, and builds
outbound replies from trusted core results.

## The PKCS#11 broker

`Agent/pkcs11/` implements the surface a PKCS#11 module talks to: certificate
DER, public key, login, logout, raw sign and decrypt.

### Leases

```cpp
struct LeaseKey { CallerToken caller; ObjectId card; };

struct LeaseConfig {
    std::chrono::seconds idleTimeout{std::chrono::minutes(10)};  // primary bound
    std::chrono::seconds maxLifetime{std::chrono::hours(8)};     // hard cap; 0 = none
};
```

A lease is scoped to a **(caller, card)** pair, both opaque tokens the backend
minted — the manager only compares them, never parses them. A successful login
grants or refreshes one; a raw sign or decrypt calls `touch()`, which bumps the
idle clock and returns whether the lease is still alive. A false result maps to
"user not logged in".

Two bounds rather than one: an idle timeout is the primary limit, and a hard
maximum lifetime exists so that a client which keeps a lease warm forever still
has to re-authorise eventually.

The clock is injected, so lease-expiry tests are deterministic rather than
sleeping. The manager is thread-safe under a single internal mutex, because
card-removal signals arrive on a monitor thread while calls arrive on the bus
thread.

### Async handoff

Every card-touching method is asynchronous. The broker does the cheap
validation — authorization, rate limit, card resolution, lease gate —
**synchronously on the dispatch thread**, and on failure fulfils the reply
inline. Only once validation passes is the actual card I/O enqueued onto the
per-reader worker, with a continuation that captures the reply and the lease key
and does the post-processing (revoke the lease on an authentication failure,
audit) when the card is done.

The dispatch thread is therefore released the moment work is enqueued. The bus
loop is never parked on an in-flight card operation, which is the property that
keeps one slow card from stalling every other client.

## Country-signing anchor import

`Agent/trust/CscaAnchorImport.h` turns signed ICAO country-signing master lists
into the agent's trust anchors — and decides whether to believe them. Its header
comment states the problem more clearly than a summary can, so the shape of it:

**There is a decision to make, because the first list has nothing to check it
against.** A master list is signed by a key chaining to a country's authority,
and the list is what supplies the anchors that authority would be checked
against. Verifying a list against anchors carried *inside that same list* proves
internal consistency and says nothing whatsoever about authenticity. It must
never be presented as a check.

**What happens instead**: the first list is trusted on import and its signer
recorded. Every later list must be signed by a key already recorded, or by a
signer whose certificate chains to an anchor the previous import carried — which
is how a publisher's lawful key rotation is followed without a person comparing
fingerprints out of band. Anything else is refused, both fingerprints are
reported, and the stored anchors are left alone. A lawful rotation and an attack
look identical from here, so accepting one silently would accept the other.

**A file is not a list.** What the ICAO Public Key Directory serves is an LDIF
directory export carrying dozens of master lists, each published and signed by a
different country. The unit a person hands in is a *file*; the unit that gets
verified is a *list*. Everything is stated per list: each verified against its
own signer, each signer with its own record, the rotation and replay rules
applied to each, and the installed anchors the **union** of those that survived.

Reading the file happens in the agent rather than in the client that passed it —
a client that decided what counts as a master list would be deciding what the
agent may be asked to believe, and the client is not the trust boundary.

**Partial outcomes are the ordinary case, not an edge.** Twenty-eight countries
publish on their own schedules, so a collection with two stale lists and
twenty-six current ones is what a reader downloads on an ordinary Tuesday. An
import takes what verifies and reports the rest: nothing is installed that was
not verified, one publisher's stale list does not deny a person the others, and
the refusals are carried out as records rather than swallowed — so a surface can
say what happened instead of showing an unexplained smaller number. An import
that admits no list at all is a refusal like any other, and leaves the store
untouched.

## Utilities with a reason

`Agent/util/` holds four small headers, each of which exists to stop something
being reimplemented differently in two places:

- `HexEncode.h` — the single agent-internal hex encoder behind the certificate
  serial (colon-separated, upper case), key-id and fingerprint presentation
  (upper, no separator), and the certificate id (lower, no separator).
- `Sha256Hex.h` — lowercase-hex SHA-256, used to derive a certificate's id from
  its DER.
- `CallerLabel.h` — platform-neutral shaping of the "Requested by …" line in
  the consent prompt.
- `DisplayText.h` — is this byte sequence safe to render as a label? True only
  for well-formed UTF-8, multi-byte included, with no C0 controls and no DEL.
  It rejects structurally invalid sequences, overlong encodings, UTF-16
  surrogates and beyond-Unicode code points — which is the set a card can hand
  you and a dialog should not paint.

## Related pages

- [Core architecture](/developer-guide/agent-architecture/)
- [Card operations](/developer-guide/agent-operations/)
- [Building a Qt client](/developer-guide/agent-client-qt/)
- [Trust, certificates and secure values](/developer-guide/trust-and-certificates/)
