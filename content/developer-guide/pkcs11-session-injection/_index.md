---
layout: "simple"
title: "In-Process Session Sharing"
description: "Sharing a live CardSession between display and the in-process PKCS#11 sign path via the SessionPresence registry — reworked in LibreSCRS 4.2.0"
weight: 60
---

This page is for host applications (LibreCelik, third-party signing tools,
browser-style integrators) that drive the PKCS#11 sign path **in-process**
and want the module to reuse the host's live `CardSession` instead of
opening a second PC/SC handle to the same reader. Opening a parallel handle
would tear down any PACE/BAC secure-messaging (SM) state the host
established, so LibreSCRS coordinates the two through a process-local
registry.

## What changed in 4.2

> **The 4.1 attach C ABI was removed.** The `extern "C"`
> `AttachHook.h` surface (`librescrs_pkcs11_attach_session` /
> `_detach_session`, the `LibrescrsPkcs11AttachTokenV1` token, the
> `LIBRESCRS_PKCS11_ATTACH_*` codes) and the C++ wrapper
> `LibreSCRS::Pkcs11::SessionAttachment` **no longer exist**. There is no
> explicit attach/detach call in 4.2. If you have 4.1 code that calls
> `SessionAttachment::attach(...)`, see [Migration](#migration-from-41)
> below.

In 4.2 the coordination is **automatic**. `CardSession` inherits
`std::enable_shared_from_this`, so the moment you own a session through a
`std::shared_ptr<CardSession>` it registers a `weak_ptr` in an internal,
process-local `SessionPresence` registry. The in-process opensc-pkcs11
provider consults that registry: when a live SM channel already exists on a
reader, the provider **defers** — it refuses to open a parallel PC/SC handle
rather than tearing down the host's session-scoped SM tunnel. Your in-process
sign call therefore reuses the host's authenticated session and its live
Secure Messaging.

Registration is RAII: when the owning `shared_ptr` drops, the `weak_ptr`
clears itself, so there is nothing to deregister by hand.

## Host responsibility: own the session as a `shared_ptr`

The entire host-side contract is "hold the session in a
`std::shared_ptr<CardSession>` and hand that pointer to the in-process
consumer." `LibreSCRS::Signing::SigningService::sign(...)` already takes the
session by `std::shared_ptr` value, so the common case needs no extra code.

```cpp
#include <LibreSCRS/SmartCard/CardSession.h>
#include <LibreSCRS/Signing/SigningService.h>

namespace ls = LibreSCRS::SmartCard;

void run_signing(const std::string& readerName)
{
    auto opened = ls::CardSession::open(readerName);
    if (!opened) { return; }

    // Owning the session through shared_ptr auto-registers it in the
    // process-local SessionPresence registry (weak_ptr, RAII).
    auto session = std::make_shared<ls::CardSession>(std::move(*opened));

    // ... activate any PACE/BAC channel the card needs (see Card-Session SM) ...

    // In-process signing reuses `session` and its live SM. The opensc-pkcs11
    // provider sees the live presence and defers instead of opening a second
    // PC/SC handle to `readerName`.
    signingService.sign(request, session, token);

    // Dropping `session` at scope exit clears its registry weak_ptr.
}
```

This mirrors what LibreCelik does:
`std::make_shared<LibreSCRS::SmartCard::CardSession>(std::move(*opened))`
in `src/librecelik.cpp`, with the same `shared_ptr` flowing into the signing
wizard and `SigningService::sign()`.

### Value-stored sessions

`SessionPresence` auto-registration relies on `shared_from_this()`, which is
only valid when the session is owned by a `std::shared_ptr`. A session held
**by value** (for example the SwiftUI host's `BridgeSession`, which stores
the `CardSession` inline) short-circuits registration as a documented no-op —
`shared_from_this()` would otherwise throw `std::bad_weak_ptr`. Such hosts
keep a single PC/SC handle anyway, so there is no parallel-handle conflict to
coordinate.

## CardMap and multi-PIN dispatch

PKCS#11 multi-PIN dispatch is backed by `LibreSCRS::SmartCard::CardMap`
(`include/LibreSCRS/SmartCard/CardMap.h`), a thread-safe process-local
cache keyed by the tuple `(reader, atrHex, serial)` that maps to a
`CardMapEntry` carrying the resolved PKCS#15 path, the working SELECT FILE
P2 byte (`0x0C` by default, `0x00` for cards that require it), and the
PIN labels discovered in the AODF. The cache lets each card's PKCS#15
layout be probed once and reused across slot enumeration, so a
multi-credential card surfaces one slot per PIN without re-running EF.DIR
fallback on every entry point.

| Method | Purpose |
|---|---|
| `get(key)` | Look up the cached entry; returns `std::nullopt` if absent. |
| `put(key, entry)` | Install or overwrite the entry. |
| `invalidate(key)` | Drop the entry for one card (e.g. on `cardRemoved`). |
| `invalidateAll()` | Drop every entry, typically at `C_Finalize` time. |

All public methods are `noexcept` and internally synchronised. Host
applications generally do not touch `CardMap` directly — it is consumed by
the PKCS#11 module — but the type is public so PKCS#11 providers built on
LibreMiddleware can integrate with the same cache instead of running a
parallel one.

## Migration from 4.1

| 4.1 (removed) | 4.2 (replacement) |
|---|---|
| `librescrs_pkcs11_attach_session(reader, token)` C call | none — own the session as `std::shared_ptr<CardSession>` |
| `LibreSCRS::Pkcs11::SessionAttachment::attach(modulePath, reader, session)` | none — auto-registration via `enable_shared_from_this` |
| Explicit `detach()` / destructor teardown before `C_Finalize` | none — the registry `weak_ptr` clears when the `shared_ptr` drops |
| `#include <LibreSCRS/Pkcs11/SessionInjection.h>` / `AttachHook.h` | headers removed; include `<LibreSCRS/SmartCard/CardSession.h>` |

Practically: delete the `SessionAttachment` plumbing, make sure the live
session is owned by a `std::shared_ptr<CardSession>`, and pass that pointer
to the in-process consumer. The SM-reuse behaviour you previously got from a
successful `attach` now happens automatically.

## See also

- [`../card-session-sm/`](../card-session-sm/) — opening the `CardSession`
  and activating secure-channel state.
- [`../secure-channels/`](../secure-channels/) — the protocols (PACE, BAC,
  plain) whose state is preserved across the in-process boundary.
- [`../whats-new-in-4-2/`](../whats-new-in-4-2/) — overview of the 4.2
  API changes and migration notes.
