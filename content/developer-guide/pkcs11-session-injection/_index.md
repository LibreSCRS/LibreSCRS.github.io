---
layout: "simple"
title: "PKCS#11 Session Injection"
description: "Embedding librescrs-pkcs11.so in-process and sharing a CardSession across display and signing — introduced in LibreSCRS 4.1.0"
weight: 60
---

Introduced in **LibreSCRS 4.1.0**. This page is for host applications
(LibreCelik, third-party signing tools, browser-style integrators) that load
`librescrs-pkcs11.so` **in-process** and want a single `CardSession` shared
between their display thread and the PKCS#11 sign path. Opening a second
PC/SC handle to the same reader from the module would lose any PACE-derived
secure-messaging state established by the host, so the module exposes a
versioned injection hook the host can call to share its live session
instead.

## C ABI: `AttachHook.h`

The C-callable surface lives in
`include/LibreSCRS/Pkcs11/AttachHook.h` and is `extern "C"` — safe to
resolve via `dlsym` from any language with a C FFI.

### Magic cookie

```c
#define LIBRESCRS_PKCS11_ATTACH_MAGIC_V1 0x4C53435253415431ULL
```

The byte pattern spells `LSCRSAT1` in ASCII. The v1 magic is **frozen**:
future incompatible token layouts will ship as a new
`LibrescrsPkcs11AttachTokenV2` struct paired with a matching
`LIBRESCRS_PKCS11_ATTACH_MAGIC_V2` constant, and the v1 surface remains
supported.

### Token struct

```c
typedef struct LibrescrsPkcs11AttachTokenV1
{
    unsigned long long magic;
    void*              session_ptr;
    unsigned long      flags;
} LibrescrsPkcs11AttachTokenV1;
```

The caller owns the token. `session_ptr` is opaque to the C ABI; the module
internally casts it to its known `CardSession` shared-pointer type, and the
caller must keep the referent alive until after the matching detach call.
`flags` is reserved and must be zero in v1.

### Entry points

| Function | Purpose |
|---|---|
| `int librescrs_pkcs11_attach_session(const char* reader_name, const LibrescrsPkcs11AttachTokenV1* token)` | Park `session_ptr` against `reader_name` for the next `C_GetSlotList` probe. Re-attaching for the same reader replaces the prior entry. Thread-safe. |
| `int librescrs_pkcs11_detach_session(const char* reader_name)` | Idempotent removal. Releases the module-side `shared_ptr` reference. No-op if no entry exists. |

Neither function ever throws across the C boundary.

### Return codes

| Code | Macro | Meaning |
|---|---|---|
| 0 | `LIBRESCRS_PKCS11_ATTACH_OK` | Success. |
| 1 | `LIBRESCRS_PKCS11_ATTACH_BAD_MAGIC` | `token->magic` mismatch. |
| 2 | `LIBRESCRS_PKCS11_ATTACH_BAD_FLAGS` | `token->flags` non-zero. |
| 3 | `LIBRESCRS_PKCS11_ATTACH_NULL_PTR` | `reader_name`, `token`, or `token->session_ptr` is `NULL`. |
| 4 | `LIBRESCRS_PKCS11_ATTACH_NOT_INITIALIZED` | `C_Initialize` not called yet. |
| 5 | `LIBRESCRS_PKCS11_ATTACH_OUT_OF_MEMORY` | Internal allocation failure (also mapped from caught exceptions). |

## C++ RAII wrapper: `SessionAttachment`

`include/LibreSCRS/Pkcs11/SessionInjection.h` adds a move-only `final`
class `LibreSCRS::Pkcs11::SessionAttachment` that wraps the C ABI in
idiomatic C++23. Construction goes through the static factory:

```cpp
[[nodiscard]] static std::expected<SessionAttachment, Error>
attach(const std::filesystem::path& modulePath,
       std::string                  readerName,
       std::shared_ptr<LibreSCRS::SmartCard::CardSession> session) noexcept;
```

The factory pins the module via `RTLD_NOLOAD` so an already-loaded
`librescrs-pkcs11.so` is not unloaded under the host's feet, then resolves
the inject hook by name. The factory is `noexcept`: any `std::bad_alloc` or
unexpected exception is translated to `Error::OutOfMemory` and surfaced
through `std::expected`.

| `Error` enumerator | Cause |
|---|---|
| `ModuleNotLoaded` | `modulePath` could not be opened by the dynamic loader. |
| `DlsymFailed` | Module is loaded but does not export the inject hook (older module). |
| `InvalidArguments` | Empty `modulePath` / empty `readerName` / null `session`. |
| `Rejected` | Module returned a non-OK numeric status from the inject hook. |
| `OutOfMemory` | `std::bad_alloc` surfaced from internal copy / allocation. |

The destructor calls the matching detach hook and releases the module
mapping; `detach()` is also available for explicit early teardown and is
idempotent. `readerName()` returns the bound reader name (empty after
detach). Move operations are `noexcept`; the moved-from instance is in a
detached state and its destructor is a no-op.

## Lifecycle ordering

1. Host calls `C_Initialize` on the loaded module.
2. Host opens a `CardSession` for the active reader on its display thread.
3. Host calls `SessionAttachment::attach(modulePath, readerName, session)`
   — **after** `C_Initialize`, **before** `C_GetSlotList`.
4. Host calls `C_GetSlotList` / `C_OpenSession` / `C_Login` / `C_Sign` —
   the module's probe path adopts the injected session instead of opening
   its own PC/SC handle to the same reader.
5. Host destroys the `SessionAttachment` (or calls `detach()` explicitly)
   before `C_Finalize`.

Re-attaching for the same reader replaces the prior entry; the previous
module-side reference drops.

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

## Example: minimal host attaches the session

```cpp
#include <LibreSCRS/Pkcs11/SessionInjection.h>
#include <LibreSCRS/SmartCard/CardSession.h>

namespace lp = LibreSCRS::Pkcs11;
namespace ls = LibreSCRS::SmartCard;

void run_signing(const std::string& readerName)
{
    auto session = ls::CardSession::open(readerName).value();

    // C_Initialize on librescrs-pkcs11.so has already succeeded here
    // (illustrative — the host owns the PKCS#11 init/finalize pair).

    auto attached = lp::SessionAttachment::attach(
        "/usr/lib/librescrs-pkcs11.so", readerName, session);
    if (!attached) {
        // Fall back to a standalone PKCS#11 path; sign may still succeed
        // for non-PACE cards. Log the structured Error and bail.
        return;
    }

    // C_GetSlotList / C_OpenSession / C_Login / C_Sign reuse `session`.
    // Scope exit detaches automatically, then the host calls C_Finalize.
}
```

The executable reference is
`LibreMiddleware/lib/pkcs11_inject/test/SessionAttachmentTests.cpp`, which
exercises the factory, error paths, and idempotent destructor.

## See also

- [`../card-session-sm/`](../card-session-sm/) — opening the `CardSession`
  and activating secure-channel state before attaching.
- [`../secure-channels/`](../secure-channels/) — the protocols (PACE, BAC,
  plain) whose state survives across the injection boundary.
- [`../whats-new-in-4-1/`](../whats-new-in-4-1/) — overview of every
  4.1.0 API surface and migration notes from 4.0.
