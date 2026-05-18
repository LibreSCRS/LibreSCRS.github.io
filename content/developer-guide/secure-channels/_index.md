---
layout: "simple"
title: "Secure Channels"
description: "Cross-plugin secure messaging via the LibreSCRS::SecureChannel API (PACE, BAC, plain) — introduced in LibreSCRS 4.1.0"
weight: 40
---

The `LibreSCRS::SecureChannel` namespace exposes the cross-plugin secure-messaging surface introduced in **LibreSCRS 4.1.0** as part of the cross-plugin secure-channel coordination work. It is intended for plugin authors and SM protocol implementers building directly on `LibreMiddleware`. Most consumers do not invoke these types directly — they hand a request to `LibreSCRS::SmartCard::CardSession`, which owns the channel lifetime and routes plugin APDUs through it; see [`card-session-sm/`](../card-session-sm/) for that integration surface.

## The `LibreSCRS::SecureChannel` namespace

All headers below live under `include/LibreSCRS/SecureChannel/` and are part of the supported consumer surface.

| Type | Header | Purpose |
|---|---|---|
| `ISecureChannel` | `SecureChannel/ISecureChannel.h` | Abstract single-applet secure-channel surface; `transmit`, `close`, `currentApplet`, `state`, `replaceKeys` |
| `PaceChannel` | `SecureChannel/PaceChannel.h` | PACE-derived SM channel (BSI TR-03110); session-scoped keys, static `establish()` factory |
| `BacChannel` | `SecureChannel/BacChannel.h` | BAC-derived SM channel (ICAO Doc 9303 Part 11); 3DES + ISO 9797-1 MAC algorithm 3 |
| `PlainChannel` | `SecureChannel/PlainChannel.h` | Pass-through channel for cards without SM (RS eID, AET, Zdravstvena, classical PKCS#15) |
| `SessionKeys` | `SecureChannel/SessionKeys.h` | Encryption key, MAC key, and send-sequence counter; zeroised via `OPENSSL_cleanse` on destruction |
| `SmCipher` | `SecureChannel/SessionKeys.h` | Cipher family enum: `Des3` (BAC) or `Aes` (PACE) |
| `ChannelState` | `SecureChannel/ChannelErrors.h` | Lifecycle enum: `Open`, `Closed`, `Failed` |
| `ChannelActivationError` | `SecureChannel/ChannelErrors.h` | Error taxonomy for handshake-time failures |
| `ChannelOperationError` | `SecureChannel/ChannelErrors.h` | Error taxonomy for post-establish `transmit` failures |
| `PACEParams` | `SecureChannel/PaceParams.h` | PACE handshake inputs: OID, password type, password, paramId |
| `BacInput` | `SecureChannel/BacParams.h` | MRZ-Z subset (document number, date of birth, date of expiry) |
| `parsePaceOidsFromCardAccess` | `SecureChannel/PaceParams.h` | Pure ASN.1 parser over EF.CardAccess bytes |

## Lifecycle and key material

A channel is opened by a concrete protocol class (`PaceChannel::establish`, `BacChannel::establish`, or direct construction of `PlainChannel`), transmits wrapped APDUs via `ISecureChannel::transmit`, and is closed when destructed or when `close()` is called explicitly. `close()` is idempotent and transitions the channel to `ChannelState::Closed`.

`SessionKeys` carries the encryption key, MAC key and send-sequence counter; its destructor zeroes every non-empty buffer through `OPENSSL_cleanse` before the underlying `std::vector` releases its allocation. Move-from leaves the source vectors empty so the post-move cleanse is a no-op — live key material follows ownership into the move destination, which carries the same cleansing contract.

PACE and BAC session keys are **session-scoped** (whole-card scope, not per-applet). The PACE handshake runs at MF and binds session keys to the card-side SM tunnel for the entire card session; applet switches happen via a wrapped `SELECT` issued through the channel itself, after which `CardSession` calls `PaceChannel::setCurrentApplet` to record the new AID. Do **not** re-PACE on every applet switch — that is a card-OS-level protocol error and is wrong by construction (memory entry `feedback_pace_sm_per_session_not_per_applet`, verified empirically on NAM and GEO contactless since 4.0.0).

## Example: activating a PACE channel via `CardSession`

The fragment below shows the public, idiomatic path: open a `CardSession`, pre-populate the CAN, and ask the session to activate a PACE-protected applet. The session owns the channel lifetime and serialises plugin APDUs through it. A runnable end-to-end version lives in `LibreMiddleware/test/LibreSCRS_SmChannelTests.cpp`.

```cpp
#include <LibreSCRS/SmartCard/CardSession.h>
#include <LibreSCRS/SmartCard/SmProtocolRequest.h>
#include <LibreSCRS/Auth/PaceSecretKind.h>
#include <LibreSCRS/Secure/String.h>

using namespace LibreSCRS;

auto session = SmartCard::CardSession::open(readerName).value();

// Pre-populate the per-process PACE cache with the user-entered CAN.
session.setPaceSecret(Auth::PaceSecretKind::Can, Secure::String{can});

SmartCard::SmProtocolRequest protocol = SmartCard::PaceRequest{
    .secretKind = Auth::PaceSecretKind::Can,
};

auto active = session.activateChannelWithSm(appletAid, protocol, token);
if (!active) {
    // active.error() is a ChannelActivationError; PaceWrongSecret is
    // retry-eligible inside activation, others are terminal.
    return;
}

// The ActiveChannelHolder owns the PC/SC transaction and the channel.
// Plugin APDUs go through it; destruction ends the transaction.
auto response = active->transmit(commandApdu, token);
```

In-tree plugin authors with access to the internal bucket-B `IConnection` header may construct channels directly via `PaceChannel::establish` etc.; downstream consumers should use the public `CardSession::activateChannelWithSm` API instead.

## Error model

Channel errors split into two enums by lifecycle phase. Handshake-time failures surface as `ChannelActivationError` from the static `establish()` factories (and from `CardSession::activateChannelWithSm` in the wider SM activation path); post-establish failures surface as `ChannelOperationError` from `transmit` and its callers.

### `ChannelActivationError` — handshake-time failures

| Enumerator | Meaning | Retryable? |
|---|---|---|
| `None` | Success | — |
| `SelectAppletFailed` | Applet absent or SELECT rejected | Terminal |
| `PaceWrongSecret` | Wrong CAN / MRZ / PIN / PUK | Retry-eligible inside activation |
| `PacePinBlocked` | PIN-as-PACE counter exhausted (reserved for 4.x) | Terminal |
| `PaceProtocolFailure` | Cryptographic or protocol failure during handshake | Terminal |
| `PaceUnsupported` | Card does not support the requested PACE mode | Terminal |
| `UserCancelled` | Credential provider returned a user-cancel | Terminal (retryable if the host wants to re-prompt) |
| `Cancelled` | `LibreSCRS::CancelToken` tripped | Terminal |
| `CardRemoved` | Card removal observed mid-handshake | Terminal |
| `ReaderError` | PC/SC-level error | Terminal (usually) |
| `CredentialsRequired` | Cache miss and no credential provider configured; maps to `CKR_USER_NOT_LOGGED_IN` on the PKCS#11 path | Terminal |
| `Internal` | Caller-visible bug | Terminal |

### `ChannelOperationError` — `transmit` failures

| Enumerator | Meaning |
|---|---|
| `None` | Success |
| `ChannelFailed` | Channel transitioned to `ChannelState::Failed`; drop and re-activate |
| `ChannelClosed` | Channel was closed before this call; re-activate |
| `CardRemoved` | Card removal observed mid-operation |
| `Cancelled` | `LibreSCRS::CancelToken` tripped |
| `ReaderError` | PC/SC-level error |
| `Sw6987Or6988` | Card returned SW 6987 or 6988 (SM data missing or incorrect); drop and re-activate |
| `MacVerificationFailed` | Response MAC failed verification (PACE/BAC channels); drop and re-activate |
| `Internal` | Caller-visible bug |

`ChannelFailed`, `MacVerificationFailed`, and `Sw6987Or6988` all mean the SM tunnel has desynchronised — the host channel must be dropped and re-activated through `CardSession`; reusing it will not recover.

## See also

- [Card session SM activation](../card-session-sm/)
- [PKCS#11 session injection](../pkcs11-session-injection/)
- [What's new in 4.1](../whats-new-in-4-1/)
