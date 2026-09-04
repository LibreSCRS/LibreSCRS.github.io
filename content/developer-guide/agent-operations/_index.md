---
layout: "simple"
title: "LibreAgent: Card Operations"
description: "The operation catalogue, the per-reader worker and session holder, the prompt gate and the rate limiter"
weight: 61
---

`include/LibreSCRS/Agent/operations/` is the largest group in LibreAgent's
public surface: **41 headers** at the head of the 5.0 cycle. It holds the card
operations themselves, the flows they delegate to, the seams those flows call
through, and the machinery that schedules and gates all of it.

This page is about that machinery. If you want the client's side of one of
these calls, see
[Building a Qt client](/developer-guide/agent-client-qt/).

## Nine operation classes

Every operation a client can ask for is one class deriving from
`OperationBase`, and each is a thin adaptor over a flow that does the work:

| Operation | What it does |
|---|---|
| `ReadIdentityOperation` | reads the document's identity data |
| `GetPhotoOperation` | reads the portrait; a cache miss runs the identity flow |
| `ReadCertificatesOperation` | reads the card's certificates |
| `ReadTokenInfoOperation` | reads token metadata — sibling of the identity read, exactly as `CardPlugin::readTokenInfo` is a sibling of `readCard` |
| `SignOperation` | one AdES signature |
| `SignBatchOperation` | many documents under one set of batch-wide parameters |
| `ListCredentialsOperation` | lists the card's PIN credentials and their state |
| `ManagePinOperation` | changes, unblocks or activates one PIN credential |
| `ActivateSigningKeyOperation` | verifies the signing PIN and activates the on-card key |

Each carries a nested `Deps` struct: everything the operation needs, supplied
by `OperationManager` at enqueue time. No operation reaches for a collaborator
it was not given.

The pattern is worth naming. The operation class holds no logic — it maps a
request onto a flow, emits typed results as they arrive, and finishes with a
mapped status. The flow beneath it (`SignFlow`, `IdentityReadFlow`,
`CredentialListFlow`, `PinChangeFlow`, `KeyActivationFlow`, `CertReadFlow`,
`TokenInfoReadFlow`, `RawCryptoFlow`, `BatchSignFlow`) is where orchestration
lives, and the flow calls the card only through injected seams — which is what
makes the whole layer testable without a card, a reader, or a bus.

## Two shared verdict vocabularies

`FlowOutcome.h` declares the two enums the flows and seams share:

```cpp
enum class FlowOutcome { Ok, Cancelled, Error };

enum class SeamStatus {
    Ok, AuthFailed, ParseError, UnsupportedCard, CommunicationError, Cancelled,
};
```

Five flows had been returning the same three-way verdict and two seams the same
six-way one, each with its own copy, identical down to enumerator order. The
reason to declare them once is not the lines saved: it is that a new enumerator
now reaches every `switch` **at compile time**. `-Wswitch` names the ones that
do not handle it, in a build that fails, instead of leaving each flow's private
copy to be found by whoever remembers.

Two distinctions the vocabulary makes deliberately:

- `Cancelled` is **not** an error. The caller or the session holder stopped the
  work, and nothing about the card is known to be wrong. Reporting a
  cancellation as a failure is the defect this separation exists to prevent.
- `SeamStatus` is wider than `FlowOutcome` because a seam is where the card's
  own refusals surface, and the flow above it has to tell them apart before
  deciding whether to retry, re-authenticate, or give up. `AuthFailed` and
  `CommunicationError` lead to different next steps; collapsing them would make
  that choice guesswork.

A flow whose verdicts are genuinely its own keeps its own enum. Several do, and
they are not these.

## One worker per reader, one session per worker

`OperationManager` owns a worker thread and a queue per reader. Each worker
owns one `CardSessionHolder`.

```
reader A ──▶ worker A ──▶ CardSessionHolder A ──▶ one open CardSession
reader B ──▶ worker B ──▶ CardSessionHolder B ──▶ one open CardSession
```

The holder opens one session lazily, reuses it across `acquire()` calls, and
resolves the candidate plugin list once per held session. That reuse is not an
optimisation — it is what lets a **PACE secure channel survive** from one
operation to the next. Reopening per operation would re-run the whole channel
establishment, and with it the credential prompt.

A reader that sits idle is proactively closed after an idle interval, so a
stale PACE channel and its PC/SC handle are not held forever; the next
`acquire()` transparently reopens. The holder is touched **only** on its worker
thread: `enqueue` stamps the pointer into the operation's `Deps` under the
worker mutex, and the worker dereferences it inside `doWork()`.

Three injected seams keep this testable with no PC/SC daemon and no wall clock:

```cpp
using SessionFactory   = std::function<std::expected<std::shared_ptr<CardSession>, OpenError>(const std::string& reader)>;
using CandidateResolver = std::function<CandidateList(std::span<const std::uint8_t> atr, CardSession&)>;
// plus a steady Clock, supplied at construction
```

### Backlog cap

```cpp
inline constexpr std::size_t kMaxQueuedOpsPerReader = 32;
struct QueueFull : std::runtime_error { /* ... */ };
```

Each operation owns auxiliary threads, so an unbounded queue is an unbounded
thread count. The cap turns a flooding client into a named refusal the backend
maps to a rate-limited wire error, rather than into memory pressure.

`OperationManager` is backend-neutral: it holds no transport type at all.
Adaptor construction and wire mapping live in the platform backend.

## Which card is this? — `CardTypeArbitration`

A card routinely matches more than one driver: a family driver plus one or both
generic PKI drivers, or — on a card no family driver claims — the two generic
ones alone. `CardTypeArbitration` picks the card-type string for a held
session's candidate list, so that every surface reporting a card type reports
the same one.

## The prompt gate

`PromptSerializer` admits **at most one live prompt per card**, and the "per
card" is the whole point.

The agent runs one worker per reader, so two readers can drive two credential
prompts concurrently — and they are meant to. This gate was originally
agent-wide, and that is what went wrong in practice. The per-operation watchdog
arms on entry to authentication, *before* a worker queues at the gate, so an
unanswered dialog on one reader did not merely delay the others: once the
watchdog budget elapsed, their operations died with a timeout and their pages
went with them. One card waiting for a CAN cost the user every other card in
the machine.

Keying the slot by card fixes exactly that. Two different cards prompt
concurrently. Two operations on the same card still serialise, which is the
case that genuinely needs it — one card cannot answer two dialogs at once, and
a second dialog for the same card is always a bug or a race.

`PromptIdMinter` gives each prompt an id so a cancellation can name the dialog
it means; see the `cancel` contract on
[the prompter interface](/developer-guide/agent-architecture/).

## The rate limiter

```cpp
static constexpr std::size_t kMaxPerWindow = 5;
static constexpr auto kWindow      = std::chrono::seconds{60};
static constexpr auto kBaseBackoff = std::chrono::seconds{2};
static constexpr auto kMaxBackoff  = std::chrono::seconds{60};
```

Under a default-allow authorization posture with the PIN as the consent gate,
an unbounded caller could drive reflexive-PIN phishing: raise prompt after
prompt until the user types the PIN out of habit. The limiter caps attempts per
caller and converts a flood into a hard error rather than into yet another
dialog.

One limiter instance covers both the signing entry and the credential-mutation
entries, so a flood spread across the two is bounded as **one** per-caller
budget rather than two. It is keyed by the caller token — reuse-immune for the
connection's lifetime, the same handle the authorizer uses — and takes its
clock by constructor injection, so tests drive time deterministically instead
of sleeping. A caller that stays under the limit decays its backoff back to
zero.

## The signing engine snapshot

`SigningEngineProvider` owns the signing engine the in-process sign path
consumes, and hands it out as a pair:

```cpp
struct EngineSnapshot {
    std::shared_ptr<LibreSCRS::Signing::SigningService> engine;
    std::string boundTsaUrl;   // empty when no TSA is configured (B-B only)
};
```

Both fields are captured under one lock, so an in-flight signature consumes a
**consistent** pair: the timestamp-authority URL bound to the engine is the one
that engine will actually contact, not whatever the live configuration store
happens to hold after a concurrent reconfigure. Handing out the engine and then
reading the URL separately is a metadata time-of-check-to-time-of-use bug, and
this is the shape that prevents it.

`engine` is null when the trust configuration could not be built; the signer
seam maps a null engine to a signing-engine error rather than dereferencing it.

## PIN-as-consent in the raw crypto path

`RawCryptoFlow` is the path a PKCS#11 client's sign or decrypt takes. Its
terminal operation takes the collected PIN as a pointer, and the two cases are
a contract rather than a convenience:

- **non-null** — the operation must verify the PIN on-card *before* the sign or
  decipher, holding the card across both, so that a PIN-always key keeps its
  verified state for the immediately following operation. A rejection surfaces
  as an authentication failure. This is the first operation of a lease, or the
  first after a prior failure.
- **null** — the PIN is already verified for this held channel.

Sign and decrypt share one signature: the routed candidates and the certificate
id select the key, and the bytes are the input or the ciphertext.

## Related pages

- [Core architecture](/developer-guide/agent-architecture/)
- [Presence and caching](/developer-guide/agent-presence-and-cache/)
- [The wire protocol](/developer-guide/agent-wire-protocol/)
- [Building a Qt client](/developer-guide/agent-client-qt/)
