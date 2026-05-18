---
layout: "simple"
title: "CardSession Secure-Messaging API"
description: "Activating PACE/BAC/plain channels from a card session, with credential preload and RAII channel lifetime — introduced in LibreSCRS 4.1.0"
weight: 50
---

This page is for plugin authors and host applications that coordinate secure messaging through a `LibreSCRS::SmartCard::CardSession`. Introduced in LibreSCRS 4.1.0, the API moves channel activation, credential caching, and PC/SC transaction lifetime onto the session itself, so plugins no longer install a `TransmitFilter` on a bare PC/SC connection. For the underlying channel protocol classes, see [Secure Channels](../secure-channels/).

## New `CardSession` methods (4.1)

The methods below extend the 4.0 `CardSession` surface. They all live on the public `LibreSCRS::SmartCard::CardSession` class declared in `LibreMiddleware/include/LibreSCRS/SmartCard/CardSession.h`.

| Method | Signature (short) | Purpose |
|---|---|---|
| `activateChannelFor` | `(AppletAid, CancelToken) → expected<ActiveChannelHolder, ChannelActivationError>` | Begin a transaction, SELECT the AID, and install a `PlainChannel`. |
| `activateChannelWithSm` | `(AppletAid, SmProtocolRequest, CancelToken) → expected<ActiveChannelHolder, ChannelActivationError>` | Same flow, but the channel is `PaceChannel` or `BacChannel` chosen by the variant. |
| `setPaceSecret` | `(PaceSecretKind, Secure::String) → void` | Pre-populate the per-session PACE credentials cache. |
| `setBacInput` | `(BacInput) → void` | Pre-populate the BAC MRZ triplet (document number, date of birth, date of expiry). |
| `clearCachedPaceCredentials` | `() → void` | Wipe every PACE cache slot and the BAC input. |
| `markDead` | `() noexcept → void` | Mark the session dead after a `CardRemoved` event; later activations return `CardRemoved`. |
| `isDead` | `() const noexcept → bool` | Predicate paired with `markDead`. |
| `setCredentialProvider` | `(LibreSCRS::Auth::CredentialProvider) → void` | Install the host callback used on cache miss to prompt for a CAN/PIN/MRZ. The provider is invoked **without** the session mutex held; implementations MAY safely call back into the same `CardSession` (for example `setPaceSecret` to deposit a just-collected CAN). |

## Parameter and result types

| Type | Header | Purpose |
|---|---|---|
| `LibreSCRS::SmartCard::SmProtocolRequest` | `LibreSCRS/SmartCard/SmProtocolRequest.h` | `std::variant<BacRequest, PaceRequest>` — chooses which SM protocol to establish. |
| `LibreSCRS::SmartCard::BacRequest` | `LibreSCRS/SmartCard/SmProtocolRequest.h` | Empty tag; BAC is always keyed on MRZ. |
| `LibreSCRS::SmartCard::PaceRequest` | `LibreSCRS/SmartCard/SmProtocolRequest.h` | Carries `secretKind` (default `Can`). |
| `LibreSCRS::Auth::PaceSecretKind` | `LibreSCRS/Auth/PaceSecretKind.h` | Enumerator `Can` / `Mrz` / `Pin` / `Puk`; cardinality exposed as `kPaceSecretKindCount`. |
| `LibreSCRS::SecureChannel::PACEParams` | `LibreSCRS/SecureChannel/PaceParams.h` | OID + paramId + password type + password — populated from EF.CardAccess and the credentials cache. |
| `LibreSCRS::SecureChannel::BacInput` | `LibreSCRS/SecureChannel/BacParams.h` | MRZ-Z subset (`documentNumber`, `dateOfBirth`, `dateOfExpiry`) in `Secure::String`. |
| `LibreSCRS::SecureChannel::parsePaceOidsFromCardAccess` | `LibreSCRS/SecureChannel/PaceParams.h` | Free helper that returns the `(OID, paramId)` pairs the card advertises in EF.CardAccess. Pure function, no card I/O. |
| `LibreSCRS::Auth::CredentialProvider` | `LibreSCRS/Auth/CredentialProvider.h` | `SyncProvider<CredentialResult, AuthRequirement>` — the host UI callback. |
| `LibreSCRS::SecureChannel::ChannelActivationError` | `LibreSCRS/SecureChannel/ChannelErrors.h` | Error enum returned in the `std::expected` failure arm (e.g. `PaceWrongSecret`, `CardRemoved`). |

## `ActiveChannelHolder` — RAII channel guard

Both activation entry points return an `ActiveChannelHolder` (declared in `LibreSCRS/SmartCard/ActiveChannelHolder.h`). While the holder is alive it owns three resources at once: the session-level mutex that serialises per-process access, the PC/SC transaction that gives cross-process atomicity, and the active `ISecureChannel` bound to one applet AID. All APDUs sent through `holder.transmit(cmd, token)` go through that channel; the predicate `holder.isActive()` reports whether the guard still owns its transaction and mutex.

Only one holder can exist per session at a time. The destructor releases the transaction first, then the mutex; call `holder.release()` to end both before scope exit. `release()` does not wipe the cached SM keys — a follow-up `activateChannelFor` on the same AID can fast-path. Use `clearCachedPaceCredentials()` when an explicit wipe is needed.

## Example: activate PACE on an applet with retry

```cpp
namespace SC = LibreSCRS::SmartCard;
namespace Sec = LibreSCRS::SecureChannel;
using LibreSCRS::Auth::PaceSecretKind;
using LibreSCRS::Secure::String;

const auto oids = Sec::parsePaceOidsFromCardAccess(cardAccess);
if (oids.empty()) { return; }

session.setPaceSecret(PaceSecretKind::Can, String{"123456"});

auto holder = session.activateChannelWithSm(
    aid, SC::PaceRequest{PaceSecretKind::Can}, token);

if (!holder && holder.error() == Sec::ChannelActivationError::PaceWrongSecret) {
    session.clearCachedPaceCredentials();
    session.setPaceSecret(PaceSecretKind::Can, promptForCan());
    holder = session.activateChannelWithSm(
        aid, SC::PaceRequest{PaceSecretKind::Can}, token);
}
if (!holder) { return; }

const auto rsp = holder->transmit(selectApdu, token);
// holder destructor releases transaction + mutex at scope end
```

Coverage of this flow lives in `LibreMiddleware/test/LibreSCRS_CardSessionTests.cpp`.

## Credential preload pattern

When the host has already collected the CAN out of band, pre-populating the cache through `setPaceSecret` before calling `activateChannelWithSm` avoids a second UI prompt. The PKCS#11 module uses this path: it parses the host-supplied "CAN:PIN" string out of `C_Login`, deposits the CAN into the session cache, then activates the SM channel and forwards the bare PIN to `VERIFY`. See [PKCS#11 session injection](../pkcs11-session-injection/) for the host-side wiring.

## See also

- [Secure Channels](../secure-channels/)
- [PKCS#11 session injection](../pkcs11-session-injection/)
- [What's new in 4.1](../whats-new-in-4-1/)
