---
layout: "simple"
title: "PIN & Credential Lifecycle"
description: "Per-credential lifecycle records from getPINList — kind, state, counters and capability flags with conservative defaults — plus the transport-PIN and signing-key activation entry points, introduced in the LibreSCRS 4.x cycle"
weight: 48
---

This page is for host applications (LibreCelik, agents, third-party
integrators) and plugin authors that present or drive PIN lifecycle
state. `CardPlugin::getPINList` returns one
`LibreSCRS::Plugin::PinStatusEntry` per credential the card exposes;
the record carries a lifecycle classification, capability flags, and
counters, all governed by a single conservative-defaults rule. Two
activation entry points, `activateTransportPin` and
`activateSigningKey`, complete the surface.

The record is declared in
`LibreMiddleware/include/LibreSCRS/Plugin/PinStatusEntry.h`; the entry
points live on `LibreSCRS::Plugin::CardPlugin`
(`LibreMiddleware/include/LibreSCRS/Plugin/CardPlugin.h`). All types
are plain value aggregates — thread-compatible, with defaulted
member-wise equality on `PinStatusEntry`.

## Classification enums

Four `std::uint8_t` enums classify each credential. All four are
**append-only** once landed, and every one has an `Unknown` first
enumerator that doubles as the conservative default.

### `PinKind` — what the credential is

| Enumerator | Meaning |
|---|---|
| `Unknown` | No safe classification evidence. |
| `UserPin` | General-authentication PIN. |
| `SignPin` | Signature/QSCD PIN (local to the signature DF). |
| `Puk` | Unblocking key (PUK). |
| `Can` | PACE Card Access Number pseudo-credential. |

### `PinState` — objective lifecycle state

| Enumerator | Meaning |
|---|---|
| `Unknown` | Not determinable safely. |
| `Transport` | Transport value set at issuance; not yet personalized. |
| `Operational` | Initialized and usable. |
| `NeedsChange` | Card signals the PIN must be changed before use. |
| `Blocked` | Retry counter exhausted. |

Precedence when several apply: `Blocked` > `NeedsChange` >
`Transport` > `Operational`. Two invariants bind the state to the flat
flags: `state == Blocked` ⇔ `blocked == true`, and `Transport` implies
`initialized == false` on transport-capable families.

### `UnblockStyle` — how a PUK-based unblock behaves

Meaningful only when `unblockable` is `true`; it MUST be `Unknown`
otherwise.

| Enumerator | Meaning |
|---|---|
| `Unknown` | Not unblockable, or style not known. |
| `ResetOnly` | Counter reset; old PIN value retained. |
| `SetsNewPin` | New PIN mandatory as part of the unblock. |
| `UnblockAndChange` | Holder chooses: reset-only or set a new value. |

### `PinRecovery` — who can recover a blocked credential

| Enumerator | Meaning |
|---|---|
| `Unknown` | No evidence — clients show generic contact-issuer guidance. |
| `HolderViaPuk` | Holder can unblock with the PUK through this software. |
| `IssuerProcess` | Only the issuer can recover (e.g. counter challenge/response). |
| `None` | Terminal — card replacement only. |

## The `PinStatusEntry` record

Identity and limits:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `label` | `std::string` | — | Plugin-defined label; used as the `pinLabel` selector in change/activation flows. |
| `reference` | `std::uint8_t` | `0` | Card-native PIN reference (where applicable). |
| `retriesLeft` | `std::optional<int>` | `nullopt` | Remaining PIN retry count; `nullopt` when unknown. |
| `initialized` | `bool` | `true` | The PIN has been initialised on-card. |
| `blocked` | `bool` | `false` | The PIN is currently blocked. |
| `minLength` / `maxLength` | `std::optional<std::size_t>` | `nullopt` | Enforced length limits; `nullopt` when unknown. |
| `canChange` | `bool` | `false` | The PIN value is user-changeable. Plugins that support change MUST set it explicitly. |
| `unblockable` | `bool` | `false` | The plugin supports PUK-based unblock for this PIN. |
| `blockedGuidance` | `std::optional<LocalizedText>` | `nullopt` | Message shown when `blocked` is true and unblock is unavailable. |

Lifecycle classification, counters, and capabilities:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `kind` | `PinKind` | `Unknown` | Credential classification derived from card evidence. |
| `state` | `PinState` | `Unknown` | Objective lifecycle state (see invariants above). |
| `retriesMax` | `std::optional<int>` | `nullopt` | Maximum retry count (family knowledge). |
| `usesLeft` | `std::optional<int>` | `nullopt` | Remaining usage budget of this credential itself (PUK usage counter); `nullopt` when not exposed or not safely readable. |
| `usesMax` | `std::optional<int>` | `nullopt` | Maximum usage budget of this credential (PUK max uses); `nullopt` when not exposed. |
| `unblocksLeft` | `std::optional<int>` | `nullopt` | Remaining times this PIN may be unblocked. |
| `unblockStyle` | `UnblockStyle` | `Unknown` | Unblock behaviour; `Unknown` unless `unblockable`. |
| `activatable` | `bool` | `false` | Transport→operational activation supported **and** currently available. |
| `keyActivationPending` | `bool` | `false` | The associated signing key is still deactivated (bring-up incomplete). |
| `keyActivatable` | `bool` | `false` | The holder can activate that key through this software (`false` where activation is issuer-tool-only). |
| `recovery` | `PinRecovery` | `Unknown` | Who can recover this credential when blocked. |
| `probeSafe` | `bool` | `false` | Counter queries are known safe on this family. Display-only — see below. |
| `keyActivationGuidance` | `std::optional<LocalizedText>` | `nullopt` | Guidance shown when key activation is pending but not holder-activatable. |

## Conservative defaults: no evidence, no offer

Every classification defaults to `Unknown`, every capability flag to
`false`, every counter to `nullopt`. A host MUST treat absence of
evidence as "do not offer the operation":

- `canChange == false` → no PIN-change action in the UI.
- `activatable == false` → no transport-PIN activation flow, even if
  `state == Transport`.
- `keyActivatable == false` → no key-activation flow; when
  `keyActivationPending` is also true, surface
  `keyActivationGuidance` instead.
- `blocked == true` with `unblockable == false` → surface
  `blockedGuidance` rather than offering a PUK-unblock action.
- `recovery == Unknown` → show generic contact-issuer guidance.

The rationale is defensive: a plugin that forgets to populate a flag
must never accidentally advertise a capability it does not implement.
Only positive, explicitly-set evidence enables a UI affordance.

## Invariants

**`getPINList` never consumes retry or usage budget.** Plugins gather
lifecycle state exclusively through non-consuming means. A host may
therefore call `getPINList` freely — on card insert, on view refresh,
after every operation — without eroding `retriesLeft`, `usesLeft`, or
`unblocksLeft`.

**`probeSafe` is display-only.** When `true`, counter queries are
known safe on this card family, so an absent counter means the value
is genuinely unavailable rather than deliberately left unread. Hosts
use the flag solely to phrase the counter display ("not available on
this card" vs. "not read"). Clients MUST NOT use it as a trigger to
issue probes of their own — all card interrogation stays inside the
plugin.

## Activation entry points

Both entry points are `[[nodiscard]] virtual` members of
`CardPlugin`, take secrets as `LibreSCRS::Secure::String` (cleansed on
destruction), and return a `PINResult`. Their base implementations
return `PINResultOutcome::Unsupported` — family support is introduced
per card family, so a caller can always distinguish "this plugin does
not implement the flow" from a genuine card-side failure.

Relevant `PINResult` outcomes (`r.ok()` is equivalent to
`outcome == PINResultOutcome::Ok`):

| Outcome | Meaning |
|---|---|
| `Ok` | Operation succeeded. |
| `InvalidPin` | Card rejected the presented value (`retriesLeft` updated). |
| `Blocked` | Card reports the credential is now blocked. |
| `KeyActivationFailed` | PIN verify succeeded but the key ACTIVATE step failed. |
| `Unsupported` | Default base implementation — the plugin does not implement this flow. |

### `activateTransportPin`

```cpp
[[nodiscard]] virtual PINResult
activateTransportPin(LibreSCRS::SmartCard::CardSession& session,
                     std::string_view pinLabel,
                     const LibreSCRS::Secure::String& transportValue,
                     const LibreSCRS::Secure::String& newPin) const;  // @since 4.x
```

Activates a transport-mode PIN: sets the holder's value using the
issuance transport value (card operation: CHANGE REFERENCE DATA; the
exact command form is family-specific). Offer the flow only on the
record's positive evidence — `state == PinState::Transport` **and**
`activatable`:

```cpp
using namespace LibreSCRS::Plugin;
using LibreSCRS::Secure::String;

// Never consumes retry/usage budget — safe on every refresh.
const auto pins = plugin->getPINList(session);

for (const auto& entry : pins) {
    if (entry.state != PinState::Transport || !entry.activatable)
        continue; // no positive evidence — do not offer activation

    const String transportValue = promptForTransportPin();
    const String newPin         = promptForNewPin();

    const auto r = plugin->activateTransportPin(session, entry.label,
                                                transportValue, newPin);
    if (r.outcome == PINResultOutcome::Unsupported) {
        // Family support not present in this build — do not retry.
    } else if (r.ok()) {
        // Credential now operational; re-read getPINList for fresh state.
    }
}
```

### `activateSigningKey`

```cpp
[[nodiscard]] virtual PINResult
activateSigningKey(LibreSCRS::SmartCard::CardSession& session,
                   const LibreSCRS::Secure::String& signPin) const;   // @since 4.x
```

Activates a still-deactivated signing key: VERIFY of the operational
SIGN PIN and the key ACTIVATE run self-contained within one locked
session/transaction (PIN-ALWAYS lock discipline). On success the
plugin clears any security state it established before returning. On
`InvalidPin`/`Blocked` the VERIFY step failed and `retriesLeft` refers
to the SIGN PIN; `KeyActivationFailed` means VERIFY succeeded but
ACTIVATE failed. Gate on `keyActivationPending` **and**
`keyActivatable`:

```cpp
using namespace LibreSCRS::Plugin;
using LibreSCRS::Secure::String;

const auto pins = plugin->getPINList(session);
const auto it = std::ranges::find_if(pins, [](const PinStatusEntry& e) {
    return e.kind == PinKind::SignPin;
});
if (it == pins.end() || !it->keyActivationPending || !it->keyActivatable)
    return; // nothing to offer (show keyActivationGuidance if pending)

const String signPin = promptForSignPin();
const auto r = plugin->activateSigningKey(session, signPin);

switch (r.outcome) {
case PINResultOutcome::Ok:                  /* key active — signing works */ break;
case PINResultOutcome::InvalidPin:          /* retriesLeft = SIGN PIN retries */ break;
case PINResultOutcome::Blocked:             /* SIGN PIN now blocked */ break;
case PINResultOutcome::KeyActivationFailed: /* VERIFY ok, ACTIVATE failed */ break;
case PINResultOutcome::Unsupported:         /* family support not present */ break;
default:                                    break;
}
```

## Availability

In the current increment the two entry points ship with their safe
base defaults: every plugin inherits `Unsupported`. Family support is
introduced per card family in subsequent releases; the record-side
capability flags (`activatable`, `keyActivatable`) follow the same
per-family schedule and remain `false` until a family populates them.

## See also

- [CardSession Secure-Messaging API](../card-session-sm/)
- [Architecture Overview](../architecture/)
