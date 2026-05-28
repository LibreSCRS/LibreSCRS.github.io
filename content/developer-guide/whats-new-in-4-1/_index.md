---
layout: "simple"
title: "What's new in LibreSCRS 4.1"
description: "Public API additions in the 4.1 cycle — cross-plugin secure channels, PKCS#11 session injection, multi-PIN dispatch, and migration notes from 4.0"
weight: 10
---

LibreSCRS 4.1 extends the 4.0 consumer surface with three coordinated additions: a protocol-agnostic secure-messaging layer under `LibreSCRS::SecureChannel`, an in-process PKCS#11 session-sharing path that lets a host reuse a single `CardSession` across display and signing, and multi-PIN PKCS#11 dispatch that keeps each card to a single probe. The 4.0 consumer baseline remains stable — host applications that consume `LibreSCRS::Plugin`, `LibreSCRS::Signing`, and `LibreSCRS::Trust` build and run unchanged. Only plugin authors that previously installed a `TransmitFilter` on `PCSCConnection` to drive PACE or BAC themselves need to migrate; the new `CardSession` API hides the protocol behind a single activation call.

## `LibreSCRS::SecureChannel` — protocol-agnostic secure messaging

The new `LibreSCRS::SecureChannel` namespace introduces `ISecureChannel`, the abstract seam between a `CardSession` and any concrete channel. The 4.1 cycle ships three implementations — `PaceChannel` (PACE-GM with `SessionKeys` derived per BSI TR-03110), `BacChannel` (ICAO 9303 BAC with 3DES session keys), and `PlainChannel` (no secure messaging, for contact cards that do not require it). Channels are session-scoped, manage their own zeroising `SessionKeys`, and are not instantiated directly by plugins; the `CardSession` API owns at most one active channel at a time and routes APDUs through it. See [Secure Channels](../secure-channels/) for the full type catalogue, the channel lifecycle states, and the error model.

## `CardSession` secure-messaging activation

`LibreSCRS::SmartCard::CardSession` gains two activation entry points. `activateChannelFor` opens a plain channel for non-PACE cards — it begins a PC/SC transaction, SELECTs the AID, and installs a `PlainChannel`, returning an `ActiveChannelHolder` RAII guard whose destruction ends the transaction. `activateChannelWithSm` accepts an `SmProtocolRequest` variant describing either PACE or BAC, and dispatches to the matching concrete channel; on a credentials cache miss it invokes the optional `CredentialProvider`. Hosts that have collected the secret out-of-band — for example a PKCS#11 module that received "CAN:PIN" through `C_Login` — can pre-populate the cache with `setPaceSecret(PaceSecretKind, ...)` or `setBacInput(...)` to suppress duplicate UI prompts. See [CardSession Secure-Messaging API](../card-session-sm/).

## PKCS#11 session injection and multi-PIN dispatch

> **Superseded in 4.2.** The attach C ABI described below
> (`AttachHook.h`, `SessionAttachment`) was **removed** in LibreSCRS 4.2 and
> replaced by automatic in-process session sharing via the `SessionPresence`
> registry. This section documents the 4.1 surface for historical reference;
> on 4.2+ see [In-Process Session Sharing](../pkcs11-session-injection/) and
> [What's new in 4.2](../whats-new-in-4-2/).

The `librescrs-pkcs11.so` module can now be loaded in-process and share the host application's already-open `CardSession` rather than opening a second PC/SC handle on the same reader. The C ABI in `LibreSCRS/Pkcs11/AttachHook.h` exposes `librescrs_pkcs11_attach_session`, taking a versioned token whose `magic` field equals `LIBRESCRS_PKCS11_ATTACH_MAGIC_V1`. C++ callers use the `LibreSCRS::Pkcs11::SessionAttachment::attach` RAII wrapper, which retains the module via `RTLD_NOLOAD` and detaches on scope exit. Multi-PIN dispatch reuses the same session across slots, and the backing `LibreSCRS::SmartCard::CardMap` cache ensures each card is probed exactly once even when multiple readers are populated. See [PKCS#11 Session Injection](../pkcs11-session-injection/).

## Migration from 4.0

- **Host applications (display-only):** no changes required. The 4.0 `MonitorService` + `CardPluginService` + `CardSession::open` flow is unchanged.
- **Host applications embedding `librescrs-pkcs11.so`:** add a `SessionAttachment::attach` call after `C_Initialize` to share the existing `CardSession`; without this the module still works in standalone mode for non-PACE cards.
- **Plugin authors implementing PACE or BAC:** migrate from installing a `TransmitFilter` directly on `PCSCConnection` to calling `CardSession::activateChannelWithSm`. The new API hides protocol details behind `ISecureChannel` and removes the need to manage session-key lifetimes by hand.
- **Credential collection:** the existing `LibreSCRS::Auth::CredentialProvider` continues to work. Hosts with pre-collected credentials can adopt `CardSession::setPaceSecret` to skip the prompt.

## ABI stability note (historical)

In the 4.1 cycle the C ABI in `AttachHook.h` was versioned by magic cookie. **This C ABI was removed in 4.2** in favour of automatic in-process session sharing — see [In-Process Session Sharing](../pkcs11-session-injection/). The note below describes the 4.1 design only.

The v1 token shape — `LibrescrsPkcs11AttachTokenV1` with `LIBRESCRS_PKCS11_ATTACH_MAGIC_V1` — was the 4.1 attach contract; 4.2 replaced it outright rather than shipping a v2 token.

## References

- [Architecture overview](../architecture/)
- [Secure Channels](../secure-channels/)
- [CardSession Secure-Messaging API](../card-session-sm/)
- [PKCS#11 Session Injection](../pkcs11-session-injection/)
- LibreMiddleware repository (LGPL-2.1)
- LibreCelik repository (GPL-3.0)
