---
layout: "simple"
title: "Building a Qt Client Against LibreAgent"
description: "LibreAgent::ClientQt — connecting, discovering readers and cards, issuing an operation, and reading its three error axes"
weight: 64
---

`LibreAgent::ClientQt` is the library a Qt or KDE application links to talk to
the card agent. Nineteen public headers live under
`client/qt/include/LibreSCRS/AgentClient/`, and they are the only group in
LibreAgent's public surface outside the `Agent::` namespace.

The test of whether this page is enough: someone who has read only this should
be able to issue one operation and handle its outcome without opening
LibreAgent's source.

## Linking

```cmake
find_package(LibreAgent 5.0 CONFIG REQUIRED COMPONENTS ClientQt)

target_link_libraries(my_app PRIVATE LibreAgent::ClientQt)
```

The component list matters: asking for the package without one makes it probe
every component it can find and run each one's `find_dependency()`. Building
the library needs `-DLIBREAGENT_BUILD_CLIENT_QT=ON`, which is **off by
default** — see
[Building from source](/developer-guide/building-from-source/).

Your application links Qt6 and this library. It does **not** link
LibreMiddleware, and it needs no PC/SC stack: every card operation happens in
the agent.

## The three objects

```
sharedAgentClient()  ──▶ AgentClient          connection + discovery
                              │
                              ├─▶ AgentReader   one reader
                              │        │
                              │        └─▶ AgentCard  one inserted card
                              │                 │
                              └─────────────────┴─▶ AgentOperation  one request
```

`AgentClient` owns the transport, tracks whether the agent is reachable, and
maintains the reader and card registries from the agent's discovery snapshot
plus live add and remove notifications. The transport — D-Bus on Linux — is an
internal detail; nothing transport-specific appears on this surface.

Prefer the process-wide accessor over constructing your own:

```cpp
#include <LibreSCRS/AgentClient/SharedAgentClient.h>

auto client = LibreSCRS::AgentClient::sharedAgentClient();
```

Every caller gets the same instance, so a process establishes one connection
rather than one per consumer, and its internal availability watch keeps
liveness current — a long-lived shared client *sees* an on-demand agent appear
after a cold start.

One caveat the header states outright: this relies on there being exactly one
copy of the library in the process, which the default shared build gives you.
Statically duplicating it across plugin boundaries would mint one "shared"
client per copy, which is a known Qt static-state failure mode.

### The constructor already did the work

```cpp
LibreSCRS::AgentClient::AgentClient client;
if (client.isAvailable()) {
    for (auto* reader : client.readers()) { /* ... */ }   // valid on this line
}
```

Construction runs a **bounded** synchronous probe of availability and, if the
agent is reachable, populates the initial registry before returning. Live
subscriptions are armed there too, so later appear/vanish and registry changes
arrive as `availabilityChanged`, `readersChanged` and `cardChanged` with no
polling.

`readers()` returns readers in **deterministic id-sorted order**, never hash
iteration order. If you render a roster, that ordering is the shared primitive
to use, so two surfaces in the same application do not disagree about the order
of the same readers.

### Two kinds of "no agent"

```cpp
client.isAvailable();      // reachable right now
client.agentInstalled();   // installed: reachable now, or startable on demand
```

They answer different questions, and a user-facing empty state needs both. "The
agent is not installed — here is how to install it" and "no card operation has
started the agent yet" call for different words and different buttons.
`agentInstalled()` is also a bounded probe and never hangs.

### Feature discovery

```cpp
if (client.hasFeature(QStringLiteral("batch-sign"))) { /* offer it */ }
```

`features()` is empty before the agent is reachable, and against an agent that
predates the discovery surface — that is not an error. `agentVersion()` is a
**display datum only**: an About box, a support report. It is a free-form
string the agent chooses; never parse it to decide what the agent can do. That
is what `hasFeature()` is for.

## Issuing an operation

Every card operation is minted by an `AgentCard` method (or by
`AgentClient::certificateDer()`), returns immediately, and is never null:

```cpp
#include <LibreSCRS/AgentClient/AgentCard.h>
#include <LibreSCRS/AgentClient/AgentOperation.h>

using namespace LibreSCRS::AgentClient;

AgentCard* card = client->card(cardId);
if (!card) { return; }

AgentOperation* op = card->readIdentity();

QObject::connect(op, &AgentOperation::groupReady, this,
                 [](const FieldGroup& group) {
                     // progressive delivery: render as fields arrive
                 });

QObject::connect(op, &AgentOperation::finished, this, [op, this] {
    if (op->status() != OperationStatus::Ok) {
        showFailure(op);            // see "three error axes" below
        return;
    }
    render(op->identityResult());   // settled before finished() fired
});
```

The available operations:

| Call | On | Typed result |
|---|---|---|
| `readIdentity()` | `AgentCard` | `identityResult()` |
| `getPhoto()` | `AgentCard` | `takePhotos()` |
| `readCertificates()` | `AgentCard` | `certificatesResult()` |
| `readTokenInfo()` | `AgentCard` | token metadata |
| `sign(certId, document, options)` | `AgentCard` | signature artifact |
| `signBatch(certId, docs, options)` | `AgentCard` | per-document rows |
| `listCredentials()` | `AgentCard` | `credentialsResult()` |
| `managePin(pinId, verb, options)` | `AgentCard` | credential outcome |
| `activateSigningKey()` | `AgentCard` | credential outcome |
| `certificateDer(readerId, certId)` | `AgentClient` | `certificateDerResult()` |

Each operation is QObject-parented to the object that minted it, so it never
outlives its card or client. Delete it earlier if you are done with it.

### Four guarantees worth relying on

These are the parts that are easy to get wrong by hand, and the reason to use
this library rather than speak the wire yourself.

1. **`finished()` fires exactly once, ever** — including when the terminal
   outcome was already known at minting time. A call the agent refuses at
   entry, or an operation that completed before the object finished
   constructing, has its terminal *queued* to the event loop rather than
   emitted from inside the constructor. So a consumer that connects to
   `finished()` on the very next line, having had no earlier chance, still
   observes it.
2. **Everything is settled before `finished()` fires.** `status()`,
   `errorCode()`, `callError()` and the typed result getter are all valid
   inside a directly connected slot, read synchronously, with no further
   synchronisation.
3. **Signals arrive on the thread the minting object lives on.** Never from a
   foreign thread, so a direct connection on that thread cannot race the polled
   state.
4. **A lost result is loud.** Where the agent retains a payload, a raced or
   lost one-shot result signal is recovered from it. Where it cannot be
   recovered, the operation surfaces a communication error rather than
   masquerading as a silent empty success.

The last one is the most valuable and the least visible: a hand-written client
that misses a one-shot result signal reports success with no data, and the bug
looks like a card that returned nothing.

### Forward compatibility

`OperationStatus` and `OperationPhase` are wire-frozen and append-only, and the
client is built to survive a newer agent:

- an unrecognised terminal **status** is treated as an error rather than
  surfaced as an unnamed enumerator;
- an unrecognised **phase** leaves the last known-good phase in place —
  `progress()` still advances on such a report, the phase simply does not
  regress to something meaningless;
- an unrecognised numeric `ErrorCode` passes through verbatim.

### Cancellation

```cpp
op->cancel();   // fire-and-forget
```

The terminal outcome still arrives through `finished()`, normally with a
cancelled status. It is never delivered synchronously from `cancel()`.

## The three error axes

This is the part to read twice. A failed operation reports on up to three
orthogonal axes, and using only one of them loses information you will want.

```cpp
op->errorCode();   // ErrorCode                 — the agent answered, with a failure
op->callError();   // CallError                 — no wire-level answer ever arrived
op->syncError();   // std::optional<SyncError>  — which named refusal it was
```

**`errorCode()` and `callError()` are mutually exclusive.** When the agent
answered — even with a failure — the answer is an `ErrorCode` and `callError()`
stays `None`. When the client never got that far, `errorCode()` stays `None`
and the reason is a `CallError`:

```cpp
enum class CallError : std::uint8_t {
    None, AgentUnavailable, Timeout, AccessDenied,
    InvalidArguments, TransportFailure, ProtocolError,
};
```

`CallError` is **local**: it is never itself carried on the wire.
`AgentUnavailable` means no agent is reachable at all — which is a very
different message to a user than a card that refused a PIN.

The **third** axis is the refusal's own name, and it exists because several
distinct names collapse onto one bucket of the other two. `UnknownCredential`
and `InvalidRequest` both report `CallError::InvalidArguments`, and a client
whose recovery differs between them — re-list stale ids, versus surface a
persistent failure — cannot tell them apart from the bucket. The name never
changes what the other two report; it says which of the several names sharing
their bucket this actually was.

`syncError()` is disengaged when no name from that vocabulary was in play. The
discriminator is *who named it*, not what went wrong: a local framing fault is
reported on the other two axes, and reading a name there would attribute it to
the card, which is a different failure with a different recovery.

One warning from the header is worth carrying: an engaged
`SyncError::CommunicationError` does **not** prove the peer named that error.
`sync-error` is a text-token vocabulary with no room to carry an unrecognised
token forward, so a name from a newer agent degrades to that value at decode
time on both transports. Read it as "named, but not usefully" — never as a
positive identification.

For a user-facing message, `messageKey()` carries the agent's own i18n key for
the terminal outcome. It is empty on a recovered terminal, where you map
`errorCode()` instead.

## Timeouts are yours to enforce

```cpp
inline constexpr int kHandshakeTimeoutMs   = 1000;   // cheap synchronous round-trips
// ... kDefaultCallTimeoutMs, kLongOperationTimeoutMs
```

Plain `int` milliseconds, because every Qt timer and socket API these feed
takes `int` msec.

The enforcement rule is not uniform, and assuming it is will cost you a hang.
The transports apply the handshake and default-call budgets internally to their
synchronous round-trips. `kLongOperationTimeoutMs` is a **caller-enforced
advisory budget**: the library has no internal watchdog and never auto-fails a
stalled operation. A client that wants stall detection runs its own timer
against that constant and calls `cancel()` when it expires.

Nothing on the wire carries a timeout. The agent's own per-operation watchdog
is a separate, server-side budget the client merely observes.

## Two shared readers, and why they are here

Two headers in this library exist to stop the same code being written three
incompatible ways.

### `SecurityChecks.h`

A card plugin reports what it verified as ordinary identity fields, and a
field's value is deliberately an open string — so no closed vocabulary
describes the *shape* those fields make between them. Left to each consumer,
that shape gets re-invented per consumer: three mutually incompatible readings
of the same group were live in this project at once, and **every one of them
had a passing test**, because each test measured a reader against its own
author's idea of the wire.

The shape is owned here instead. Both desktop clients build this library, so a
check separated here is separated the same way in all of them.

What it deliberately does *not* do: translate or judge. `status`, `category`
and `reason` come back as the producer's own tokens, and
`SecurityCheckEntry::reason` is a **key**, not a sentence. Turning a token into
words needs a catalogue in the reader's language, and those live in the GUI
hosts.

### `SealedPayload.h`

The single audited reader for the small, fully-buffered payloads the agent
hands over as file descriptors. Every place that turns such a descriptor into
bytes goes through `readBoundedPayload()` rather than re-spelling stat and read
per call site, so the byte cap and the descriptor-shape checks cannot be
applied at one call site and forgotten at another.

Its 8 MiB ceiling is honest about what it is: a **new** invariant introduced by
that reader, not a restatement of a bound enforced somewhere upstream. The
agent pushes a photo field's raw bytes into the descriptor with no length check
of its own, and the socket wire's 1 MiB frame ceiling bounds the CBOR body, not
the descriptor beside it.

## Related pages

- [Core architecture](/developer-guide/agent-architecture/)
- [Card operations](/developer-guide/agent-operations/)
- [The wire protocol](/developer-guide/agent-wire-protocol/)
- [Building from source](/developer-guide/building-from-source/)
