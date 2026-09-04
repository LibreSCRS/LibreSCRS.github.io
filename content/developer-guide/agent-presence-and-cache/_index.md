---
layout: "simple"
title: "LibreAgent: Presence and Caching"
description: "How the agent knows which card is in which reader, what it remembers between operations, and what it deliberately does not"
weight: 62
---

Eighteen public headers cover the two questions this page answers: **which card
is where** (`Agent/presence/`, 6 headers) and **what is remembered between
operations** (`Agent/cache/`, 7 headers, plus the 5 value types in
`Agent/value/` those caches store).

## Presence

```
LM monitor poll thread
        │  reader added / card inserted / card removed
        ▼
   PresenceModel  ──mints──▶  ObjectId
        │                       │
        ├──▶ ObjectRegistry ────┴──▶ AgentTransport (publishes)
        └──▶ CardKeyTracker ────────▶ cache invalidation on removal
```

### `PresenceModel`

A pure mapping from reader and card presence onto registry objects. No D-Bus, no
PC/SC, no Qt — it is driven by four calls (`onReaderAdded`, `onReaderRemoved`,
`onCardInserted`, `onCardRemoved`) and answers two (`readerIdFor`,
`cardIdFor`).

It mints the `ObjectId`s, from a single monotonic per-process counter with `0`
reserved for "none". One header comment on this type is a security requirement
rather than a design note, and it is the reason the counter exists at all:

> the stable per-card fingerprint must never appear in an object path — it is
> consent-gated, and path-leaking it would let any peer correlate cards across
> insertions by simple introspection.

An opaque per-process counter carries no such information. A fingerprint in a
path would be readable by anything allowed to list objects, and would tie one
card's insertions together across time.

### `ObjectRegistry`

Holds the published reader and card objects and notifies four observers —
reader added, card added, removed, and a typed `PropertyDelta` when an existing
reader's card-presence fields flip. The backend materialises those into wire
objects, because it owns the `ObjectId`-to-path mapping and all the interface
naming; unit tests inspect the registry contents directly instead.

The delta on change carries **only** the presence change, so the backend emits
a minimal properties-changed signal rather than republishing an object.

### `CardKeyTracker`

Maps a reader name to the currently inserted card's per-insertion `ObjectId`,
and fires a callback with that id when the card or its reader goes away, so the
caches keyed under it are actually dropped.

The choice of key is the substance here. The product contract is "the CAN is
entered once per card **insertion**" — cleared on removal, prompted again on
re-insertion — and a per-insertion id matches that one-to-one. An ATR
fingerprint would not: it is non-unique across cards from the same batch, so it
would cross-link distinct cards' secrets, and it survives a removal, so it
would carry a secret across the very event that is supposed to clear it.

### `CapabilityResolver`

Maps a card to non-secret facts, in two phases. `resolvePlugin(atr)` is a fast
ATR-only hint that covers plugins declaring a non-empty ATR table.
`resolveCandidates(atr, session)` runs on the per-reader worker's
**already-open** held session and covers plugins that identify only by AID
probe — an ePassport, for instance.

The reason for two phases rather than one: probing by AID needs a live session,
and opening a transient session off the worker thread would fight the worker
for the reader. Doing the fallback on the held session means no transient
session is ever opened.

## Caching

Three caches, and telling them apart matters more than any single one of them.

| Cache | Holds | Dropped when |
|---|---|---|
| `CredentialCache` | the CAN / MRZ pre-read **secrets** | card removal, full scrub |
| `CardReadCache` | the identity snapshot (including the portrait) and the enumerated certificates | card removal, idle expiry, mutation |
| `CredentialSnapshotCache` | the credential **records** a listing produced — labels, lifecycle state, retry counters | card removal, mutation, idle expiry, full scrub |

`CredentialCache` and `CredentialSnapshotCache` are deliberately distinct
types with confusingly similar names, so it is worth being explicit: the
snapshot cache holds **no secret at all** — no PIN, no CAN. They also
invalidate under different rules. Any credential mutation that reaches the card
drops the snapshot, because the retry counters and state it enumerated may have
moved; it must **not** evict a still-valid pre-read secret, because nothing
about that secret changed.

### What every cache does on the way out

Two properties are uniform across all three, and both are about what is left
behind rather than what is served:

- **Scrub on drop.** Every field buffer is cleansed before an entry is
  dropped — on overwrite, expiry, invalidation or clear — so no card-derived
  data lingers in freed heap. Certificates are public, and are scrubbed anyway,
  uniformly.
- **Never persisted.** These are in-memory caches for one process lifetime.

### Residency

`CardReadCache` follows active use: a sliding idle window refreshed on every
successful read, and an idle entry erased and zeroized once it elapses. The
production configuration passes a sentinel that **disables** idle expiry for the
identity and certificate halves, because an eID's identity data cannot go stale
while the card is seated — any change to it is a physical re-issue, which means
a card removal, which already invalidates the entry. The short default window
exists for the expiry unit tests.

Both read caches are thread-safe through an internal mutex, and their `get`
accessors are `const` while still self-cleaning an expired entry — a mutable
map and an injected clock, so that expiry tests do not sleep.

### Invalidation is declared once, not mirrored

Two small headers exist for one reason each, and the reason is the same:

```cpp
// cache/CardRemovalCaches.h
inline void invalidateCardRemovalCaches(CredentialCache&, CardReadCache&,
                                        CredentialSnapshotCache&,
                                        const std::string& cardPath);

// cache/FullScrubCaches.h
inline void clearFullScrubCaches(CredentialCache&, CredentialSnapshotCache&);
```

Each is the **single source of truth** for which caches die on a given event —
card removal for the first, a full lifecycle scrub (system sleep, fast user
switch away) for the second — and each is shared by the production hook and by
its regression test. That sharing is the whole point: dropping a cache from the
list breaks production and the test *together*, instead of leaving a test that
still passes against a hook that has quietly stopped clearing something.

What deliberately stays outside these helpers: the PKCS#11 lease revocation and
the per-reader session invalidation. Those need the operation manager and the
broker, not just the caches, and folding them in would give the helper a reason
to reach for collaborators it has no business knowing.

### Versioning the credential snapshot

Every stored snapshot is stamped with a strictly increasing, agent-wide,
never-reused version — not even reset across an invalidate followed by a fresh
listing. It is internal freshness bookkeeping today: it never crosses the wire,
and no client-visible comparison uses it. Its guarantees are pinned by a test
anyway, so that a future wire exposure can rely on them; version `0` is
reserved for a snapshot that never passed through the cache.

## The MRZ choice sink

One type inside `CredentialCache` is worth reading on its own, because it
solves a problem that has no obvious shape: what to do when the user answers a
different question from the one that was asked.

The prompter may offer an alternative credential kind. A user asked for a CAN
can answer with an MRZ instead. That payload is useless to the activation
attempt in flight — the card asked for a CAN — so it is parked in a
`MrzChoiceSink` and the walk unwinds as a *cancellation*. The flow one level up
consults the sink **before** honouring that cancellation, and renegotiates the
read as an MRZ read instead.

Consumption is one-shot consume-and-scrub: `take()` moves the payload out under
the mutex and disarms the sink, so a second `take()` yields nothing. That is
what the flow's "re-run the read exactly once" contract rests on. `reset()`
scrubs a payload nobody consumed, called at run exit so that a sink filled on
an error path never outlives the run while holding secret bytes.

## Error taxonomy

`Agent/value/ErrorTaxonomy.h` maps middleware-side failures onto the wire's
frozen error codes, and one of its three overloads carries an extra rule:

```cpp
struct CredentialFinish {
    Operations::OperationStatus status = Operations::OperationStatus::Error;
    ErrorCode code = ErrorCode::CommunicationError;
};
CredentialFinish errorCodeFor(CredentialOutcome) noexcept;
```

A credential outcome fixes the finish **status** as well as the code, because
a user cancellation finishes as `Cancelled` with **no** error code —
cancellation is a status, never an error — while every genuine failure finishes
as an error whose integer carries the coarse class. The finer distinctions
(retries left, blocked, key activation versus verification) ride the result
payload, not that integer.

The defaults fail closed: an unassigned pair reads as an error with a generic
transport code, never as a spurious success.

## Related pages

- [Core architecture](/developer-guide/agent-architecture/)
- [Card operations](/developer-guide/agent-operations/)
- [The wire protocol](/developer-guide/agent-wire-protocol/)
