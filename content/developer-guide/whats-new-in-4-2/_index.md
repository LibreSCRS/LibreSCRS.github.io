---
layout: "simple"
title: "What's new in LibreSCRS 4.2"
description: "Public API changes in the 4.2 cycle — reader-list snapshot API, Qt-free CardData accessors, the new in-process session-sharing model, and migration notes from 4.1"
weight: 5
---

LibreSCRS 4.2 is the second feature release of the 4.x cycle. It adds a
Qt-free reader-list snapshot API and card-data convenience accessors,
**replaces** the 4.1 PKCS#11 attach C ABI with an automatic in-process
session-sharing model, completes the cross-reader Secure-Messaging
coordination, and sweeps RAII / exception-safety / API-surface hygiene. The
ABI is additive relative to 4.1.0 (no breakage inside the visibility gate);
test-only seams are no longer exported to SDK consumers.

Display-only hosts that consume `LibreSCRS::Plugin`, `LibreSCRS::Signing`,
and `LibreSCRS::Trust` build and run unchanged. The one breaking change is
the removal of the 4.1 PKCS#11 attach C ABI — see
[Migration](#migration-from-41).

## Reader-list snapshot API

`LibreSCRS::SmartCard::MonitorService` gains
`subscribeReaderList(ReaderListCallback)` / `unsubscribeReaderList(...)`,
which deliver the full post-change reader-list snapshot per change (plus a
bootstrap fire for late joiners). Consumers no longer fold per-reader
`ReaderAdded` / `ReaderRemoved` events into a local `std::set` to recover
membership. The API is Qt-free and additive to the existing per-event
`subscribe` stream. See [Reader-List Snapshot API](../monitor-reader-list/).

## Qt-free CardData accessors

`LibreSCRS::Plugin::textValue(data, groupKey, fieldKey)` and
`textValueAt(data, groupIndex, fieldKey)` collapse the
`findGroup → groupAt → field-loop` dance over `CardData` into one
`std::optional<std::string>` call. GUI adapters (LibreCelik now; LibreMac /
LibreKDE next) become thin `QString` wrappers on top. See
[CardData Convenience Accessors](../card-data-access/).

## In-process session sharing replaces the attach C ABI

The 4.1 PKCS#11 attach C ABI — `AttachHook.h`
(`librescrs_pkcs11_attach_session` / `_detach_session`, the
`LibrescrsPkcs11AttachTokenV1` token) and the C++ wrapper
`LibreSCRS::Pkcs11::SessionAttachment` — **is removed**. In 4.2,
`CardSession` inherits `std::enable_shared_from_this`; owning the session
through a `std::shared_ptr<CardSession>` auto-registers it in a process-local
`SessionPresence` registry (a `weak_ptr` cleared by RAII). The in-process
opensc-pkcs11 provider consults that registry and **defers** — refusing to
open a parallel PC/SC handle — when a live PACE/BAC secure-messaging channel
already exists on the reader, so an in-process signing consumer reuses the
host's live SM instead of running a conflicting second handshake. There is no
explicit attach/detach call any more. See
[In-Process Session Sharing](../pkcs11-session-injection/).

## Concurrency hardening

The 4.2 cycle hardens the `MonitorService` / internal `Monitor` concurrency
surface with deterministic, hardware-free regression tests:

- **Bootstrap-fire race** — `subscribeReaderList` registered after a
  per-event `subscribe` could deliver an empty snapshot before the poll
  thread's first enumeration; now gated on an `initialPollComplete` latch so
  registration order no longer affects correctness.
- **Subscription lifecycle + coalescer** — closed a TOCTOU that orphaned the
  internal poll subscription (leaking a poll thread + open PC/SC context);
  `unsubscribe(Drain)` releases the dispatch lock before joining the poll
  thread; the coalescer suppresses a stale `CardInserted`/`CardRemoved` for a
  reader removed during the flush window.
- **CardSession re-entrancy guard** — calling a `CardSession` method on the
  thread that holds an `ActiveChannelHolder` previously self-deadlocked;
  `activateChannelWithSm` / `activateChannelFor` now return
  `ChannelActivationError::ReentrantAccess` instead of blocking.

## Cards and plugins

- **AET SafeSign QSCD (Infineon)** — the PKCS#15 plugin unlocks AET SafeSign
  QSCD cards via a software-attestation PUT DATA exchange, so read and
  signing now work on these cards.
- **Foreign-passport rejection over SM** — the PKCS#15 applet probe runs
  SM-wrapped and distinguishes a present applet (`0x9000`) from an absent one
  (`0x6A82`), so foreign ICAO passports on a live SM channel are declined
  cleanly instead of being mis-bound.

## Packaging and hygiene

- **Bundled-license completeness** — LibreCelik ships a manifest-driven,
  fail-closed bundle-license check: every bundled shared library must map to
  a documented license (covering the Linux `.so` and macOS `.dylib`
  layouts), enforced in CI on every push.
- **RAII / exception-safety / API hygiene** — new RAII wrappers for OpenSSL,
  OpenSC, PC/SC context, and `dlopen` handles; a noexcept-allocation-contract
  sweep; a minimal public API surface with CMake-enforced policy; test-only
  injection seams gated behind `LIBRESCRS_INTERNAL_BUILD` and no longer in
  the SDK-visible export set.

## Migration from 4.1

- **Display-only hosts:** no changes required.
- **Hosts embedding `librescrs-pkcs11.so` in-process:** remove all
  `SessionAttachment` / `AttachHook` plumbing. Own the live session as a
  `std::shared_ptr<CardSession>` and hand it to the in-process consumer (e.g.
  `SigningService::sign`); SM reuse now happens automatically via
  `SessionPresence`. See [In-Process Session Sharing](../pkcs11-session-injection/#migration-from-41).
- **Reader monitoring:** replace any hand-rolled `std::set` fold over
  per-reader events with `subscribeReaderList`.
- **GUI / card-data adapters:** delegate field lookups to
  `LibreSCRS::Plugin::textValue` / `textValueAt`.

## References

- [Reader-List Snapshot API](../monitor-reader-list/)
- [CardData Convenience Accessors](../card-data-access/)
- [In-Process Session Sharing](../pkcs11-session-injection/)
- [Architecture overview](../architecture/)
- [What's new in 4.1](../whats-new-in-4-1/)
