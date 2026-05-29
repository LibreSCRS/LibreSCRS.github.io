---
title: "LibreSCRS 4.2.0 — reader-list snapshot API and in-process session sharing"
date: 2026-05-28
summary: "LibreMiddleware 4.2.0 + LibreCelik 4.2.0: a Qt-free reader-list snapshot API, CardData convenience accessors, automatic in-process session sharing replacing the 4.1 attach C ABI, AET SafeSign QSCD support, and a fail-closed bundled-license check."
draft: false
---

LibreSCRS 4.2.0 is the second feature release of the 4.x cycle.
**LibreMiddleware 4.2.0** and **LibreCelik 4.2.0** carry GPG-signed git
tags and cosign-signed release artifacts. The ABI is additive relative to
4.1.0; display-only consumers of `LibreSCRS::Plugin`, `LibreSCRS::Signing`,
and `LibreSCRS::Trust` build and run unchanged.

## Highlights

- **Reader-list snapshot API** — `MonitorService::subscribeReaderList`
  delivers the full post-change reader list as one Qt-free snapshot (plus a
  bootstrap fire for late joiners), so consumers no longer fold per-reader
  events into a local set.
- **Qt-free CardData accessors** — `LibreSCRS::Plugin::textValue` /
  `textValueAt` collapse the `findGroup → groupAt → field-loop` dance into a
  single `std::optional<std::string>` call; GUI adapters become thin
  wrappers.
- **In-process session sharing replaces the attach C ABI** — the 4.1
  `AttachHook` / `SessionAttachment` PKCS#11 attach C ABI is **removed**.
  Owning a `CardSession` as a `std::shared_ptr` now automatically lets an
  in-process signing path reuse the host's live Secure-Messaging session
  with no explicit attach call.
- **AET SafeSign QSCD (Infineon)** — read and signing now work on AET
  SafeSign QSCD cards via a software-attestation unlock.
- **Concurrency hardening** — fixed several reader-monitor concurrency
  races, with deterministic, hardware-free regression tests.
- **Fail-closed bundled-license check** — LibreCelik enforces, in CI on
  every push, that every bundled shared library maps to a documented
  license across the Linux `.so` and macOS `.dylib` layouts.

See [What's new in 4.2](/developer-guide/whats-new-in-4-2/) for the full API
changes and migration notes from 4.1.

## Upgrading

- Display-only hosts: no changes required.
- Hosts that embedded `librescrs-pkcs11.so` in-process: remove the
  `SessionAttachment` / `AttachHook` plumbing and own the live session as a
  `std::shared_ptr<CardSession>` — see
  [In-Process Session Sharing](/developer-guide/pkcs11-session-injection/).

## Downloads

- [LibreMiddleware 4.2.0 release](https://github.com/LibreSCRS/LibreMiddleware/releases/tag/4.2.0)
- [LibreCelik 4.2.0 release](https://github.com/LibreSCRS/LibreCelik/releases/tag/4.2.0)

All artifacts ship with `.sigstore.json` cosign signatures; verify
with `cosign verify-blob --bundle <name>.sigstore.json <name>`.
