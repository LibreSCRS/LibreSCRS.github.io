---
layout: "simple"
title: "API Policy"
description: "Versioning, the public surface, deprecation rules, the plugin ABI and its changelog, enum discipline, and the shared-object SONAME"
aliases:
  - /dev/api-policy/
---

This is the normative API policy for the `LibreSCRS::*` public surface exposed
by LibreMiddleware and by every other LibreSCRS repository. Doxygen comments
throughout the public headers reference it by section number — "per API-POLICY
§5.1" and the like — and this page is the text they mean.

Error handling has its own page: see
[Expected result handling](/developer-guide/sdk-reference/expected-result-handling/)
for §5 and for the `std::expected` mandate on fallible factories.

## 1. Versioning (SemVer 2.0)

- **Major** (`X.0.0`) — intentional breaking changes; removal of previously
  deprecated symbols; signature changes that invalidate source compatibility.
- **Minor** (`X.Y.0`) — new public symbols (backward-compatible); deprecation
  annotations on legacy symbols; build-system evolutions that preserve the
  public-link contract.
- **Patch** (`X.Y.Z`) — bug fixes only. No public signature changes; no new
  deprecations.

## 2. Public Surface

```
Public API = everything under LibreSCRS::{Auth,SmartCard,Secure,Plugin,Signing,
             Trust,Certificate}::*, reachable via the public CMake targets
             LibreSCRS::{Auth,SmartCard,Plugin,Signing,Trust,Certificate,All}.
             Everything else — smartcard::, libresign::, internal headers, all
             non-LibreSCRS namespaces — is implementation detail and may change
             in any release without semver impact.
```

The `Trust` namespace owns trust-anchor lifecycle and trusted-list ingestion;
its public surface is `Trust::TrustConfig`, `Trust::TrustStore` and
`Trust::TrustStoreService` (asynchronous, non-throwing factory introduced in
4.0; replaces the legacy `Signing::TrustStoreManager` deleted in the same
release). Construction is `Trust::TrustStoreService::create(TrustConfig)`;
consumers (`Signing::SigningService`, `Plugin::CardPluginRegistry`, hosts) take
a `shared_ptr<TrustStoreService>` by pure constructor injection. See
[Trust, certificates and secure values](/developer-guide/trust-and-certificates/).

## 3. Deprecation Rules (apply from 4.0 onward)

### 3.1 Release-bridging deprecation (the default shape)

Applies to every symbol users outside the repository can observe — public
headers, installed CMake targets, plugin ABI, anything a third-party SDK
consumer can link against.

1. A symbol marked `[[deprecated("<reason>; use <replacement> since <version>")]]`
   in release X.Y **must stay callable** throughout the X.\* line.
2. The `@deprecated` Doxygen tag must be paired with an `@since` tag on the
   replacement symbol.
3. Deprecated symbols are **removed** in the next major (X+1.0). No deprecation
   survives a major version bump.
4. Release notes for any X.Y introducing deprecations must list every new
   deprecation under a "Deprecated in X.Y" heading.
5. The migration guide in each major release's notes documents every removed
   symbol and its pre-major replacement.

### 3.2 Transitional in-repo deprecation (exception — internal refactors only)

Applies when an internal refactor needs to switch in-tree callers from an old
overload or signature to a new one across multiple commits on the same branch,
with no external consumers affected between the first and last commit.

1. **Preferred path**: do the migration in a single commit — add the new
   overload, migrate callers, delete the old overload. No `[[deprecated]]`
   marker needed. That reserves `[[deprecated]]` for surfaces end users see.
2. **Multi-commit path** (when a single commit would be too large or would mix
   concerns): annotate the old overload `[[deprecated(<reason>)]]` with an
   explicit note stating this is transitional and in-repo; migrate callers in
   subsequent commits; delete the old overload in the final commit. The entire
   cycle must land on the same branch before it merges to `main`.
3. **Never mix 3.1 and 3.2**: a symbol intended for 3.2 treatment must not stay
   deprecated past the branch merge. If the branch ships a release, the symbol
   is removed before tagging.
4. The commit message of the delete-commit references the introducing commit so
   a reviewer can confirm the cycle closes cleanly.

### 3.3 Distinguishing the two

If the `[[deprecated]]` survives a release-tagged commit on `main`, it is
§3.1 — external consumers now see it, so it is removed in the next major.

If it lands and disappears entirely on a feature branch before that branch
merges, it is §3.2 — the marker was a refactoring convenience, never a
contract.

## 4. Plugin ABI

The `CardPlugin` interface ABI is versioned independently of the release
(current: **v9**; v6 was introduced by the 4.0 major release). The ABI version
increases when the virtual table layout changes — a new non-default method, a
removed method, reordered methods, or a layout change in a plugin-facing
aggregate struct. Non-ABI plugin-interface changes (adding a virtual method
with a safe default, appending an enumerator to an enum whose consumers close
over a `default:` arm) do **not** bump the ABI.

**ABI changelog** (append-only; the authoritative integer is
`Plugin::kCardPluginAbiVersion`):

| ABI | Introduced | Change |
|---|---|---|
| **v6** | 4.0 | Initial 4.0 plugin surface (`CardPlugin` vtable + closed-shape result types). |
| **v7** | 4.x | Uniform credential-activation virtuals — `activationProfile` + `seedCredentials` slots, consumed by the `readCard` NVI wrapper (the activate-then-read seam moved into the plugin surface). |
| **v8** | 4.x | Decipher (RSA decrypt) support — the `doDecipher` vtable slot + the plugin-facing `DecipherMechanism` / `DecipherResultOutcome` enums. The same-cycle credential-lifecycle surface rides this bump: the `activateTransportPin` + `activateSigningKey` vtable slots (safe `Unsupported` defaults), the `PinStatusEntry` lifecycle fields appended at the END of the struct (`kind`, `state`, `retriesMax`, `usesLeft`, `unblocksLeft`, `unblockStyle`, `activatable`, `keyActivationPending`, `keyActivatable`, `recovery`, `probeSafe`, `keyActivationGuidance`), the new `PinKind` / `PinState` / `UnblockStyle` / `PinRecovery` enums, and `PINResultOutcome::KeyActivationFailed` (appended). |
| **v9** | 5.0 | Removal of the superseded `getPINTriesLeft` vtable slot. This bump also *retroactively* covers the two shape changes described in the correction below — the mid-table `readCounters` insertion and the three new `CardPlugin` members. First plugin ABI revision that moves together with the shared objects' SONAME (`LIBRESCRS_ABI_SOVERSION` 4 → 5; see §12). |

> **Correction to the v8 row, recorded in the 5.0 cycle rather than at the
> time.** From 2026-06-14 onward `kCardPluginAbiVersion == 8` named **two
> mutually incompatible shapes**. Two commits after the v8 bump changed the
> layout and raised nothing: one inserted the `readCounters` virtual into the
> MIDDLE of the `CardPlugin` vtable rather than appending it — so every slot
> behind it moved — and introduced the plugin-facing `CredentialCounters`
> aggregate it returns; the other added three members to `CardPlugin`
> (`sizeof` 80 → 168). Anyone who built a plugin against `main` between those
> two points holds an artefact that announces v8 and carries the second shape.
> Raising the integer to v9 does not rescue them, which is exactly why this
> note exists and not only the v9 row above. For the published 4.2 → 5.0 step
> the collision is harmless by accident (6 ≠ 9 rejects everything from the
> previous release), and no such artefact was ever published.

**`CardPlugin::getPINTriesLeft(CardSession&)` is removed in 5.0.0**, not
deprecated. It was never marked `[[deprecated]]` in a released version, so it
goes straight from present to gone at the major boundary, per this project's
zero-legacy policy for major releases. Callers migrate to
`readCounters(session, pinLabel)`, which returns a `Plugin::CredentialCounters`
carrying the retry count as a named field rather than a bare
`std::optional<int>`:

```cpp
// Before (4.x):
std::optional<int> tries = plugin.getPINTriesLeft(session);

// After (5.0):
const auto counters = plugin.readCounters(session);       // default user PIN
const auto pukCounters = plugin.readCounters(session, "PUK");
if (counters.retriesLeft) { /* ... */ }
```

`CredentialCounters` carries `retriesLeft`, `retriesMax`, `usesLeft`, `usesMax`
and `unblocksLeft`, each an `std::optional<int>` that is absent unless the card
exposed it. Backends fill what they can; the base implementation returns an
empty aggregate, so a plugin that does not override `readCounters` reports
"nothing known" rather than a wrong zero.

Note: the on-card SHA-256 (hash-specific) signing added in the same cycle did
**not** bump the ABI — it rides the existing `doSign` slot via a
`SignMechanism` value (the card hashes internally; the host sends raw data per
the PKCS#15 hash-specific rule), which is an append-only enum change, not a
vtable change.

**Paired-commit rule (mandatory).** Any bump of `kCardPluginAbiVersion` must
land in the **same commit** as the policy edit that records it here — this
changelog row plus any §4/§9 enum-list additions the bump introduces. A header
ABI bump that does not touch this document is rejected in review, and so is the
reverse. This is what keeps §4 from going stale against the header, which is
exactly how the v6 → v8 drift above happened.

Third-party plugin authors target a specific ABI version.
`LibreSCRS::Plugin::kCardPluginAbiVersion` exposes the current ABI integer, and
the `LIBRESCRS_DECLARE_CARD_PLUGIN(PluginType, AbiVersion)` macro
`static_assert`s compile-time equality between the plugin's declared version and
the current header's constant — so an ABI drift surfaces as a plugin build
failure rather than a runtime mismatch. The registry additionally re-checks the
version at load time through the `card_plugin_abi_version()` `extern "C"` symbol
and rejects mismatches as `LoadOutcome::Status::AbiMismatch`.

**Append-only discipline for plugin-facing enums.** `ReadResult::Status`,
`PINResultOutcome`, `SignResultOutcome`, `SignMechanism`, `CardCapabilities`,
`DecipherMechanism`, `DecipherResultOutcome` (the last two added at ABI v8),
`PinKind`, `PinState`, `UnblockStyle`, `PinRecovery` (credential-lifecycle
enums, added within the v8 cycle), and any future plugin-facing enum are
append-only across ABI revisions — old values keep their numeric identity, new
values land at the tail. Removing a value requires an ABI bump. Consumer
switches on these enums should either close over every value (a compile-time
`-Wswitch-enum` check) or carry a `default:` branch, so that a plugin returning
a post-version value against a pre-version host degrades predictably.

Rely on the published ABI integer (`kCardPluginAbiVersion`) as the sole
compatibility signal; do not forward-predict against unreleased candidates.

## 6. 3.0 → 4.0 Transition (historical note)

The API-boundary hardening introduced for the 4.0 major version is itself the
4.0 major bump. 3.0 shipped without any `[[deprecated]]` annotations; the 4.0
migration guide documents the full set of removed `smartcard::*` /
`libresign::*` symbols with their `LibreSCRS::*` replacements. Subsequent
cycles (4.x → 5.0, 5.x → 6.0, ...) follow the formal deprecate-in-minor →
remove-in-major pattern in §3 above.

### 6.1 Trust lifecycle move (pre-4.0)

`TrustStore` lifecycle moved from `Signing::SigningService::trustStore()` to
`Trust::TrustStoreService::create(...)->trustStore()`. An ABI break, made
pre-tag with a single in-tree consumer updated atomically.

```cpp
// Before (3.x preview):
LibreSCRS::Signing::SigningService service{trustConfig, tsa};
auto store = service.trustStore();

// After (4.0):
auto trustService = LibreSCRS::Trust::TrustStoreService::create(trustConfig);
LibreSCRS::Signing::SigningService service{trustService, tsa};
auto store = trustService->trustStore();
```

`Signing::TrustStoreManager` is removed entirely; it was transitional retention
pending replacement by `Trust::TrustStore`. The rationale for the replacement:
asynchronous fetches, an observer pattern, and no-throw construction — the same
shape the
[expected-result page](/developer-guide/sdk-reference/expected-result-handling/)
documents for every fallible factory. The
`Signing::SigningService::trustStore()` getter is removed too; consumers obtain
the store from the lifecycle owner that constructed it.

## 7. Enum value naming

LibreSCRS enums use **PascalCase** for value identifiers by default:

- `SignatureFormat::Pades`, `Cades`, `Xades`, `Jades`, `AsicE`
- `Status::Ok`, `Cancelled`, `Error`

Two deliberate exceptions:

1. **Standardised acronyms of three letters or more stay all-caps** when they
   appear as standalone tokens in identifiers: `PKI`, `EID`, `MRZ`, `CAN`,
   `PIN`, `PUK`. Compound words use PascalCase: `EmrtdCrypto`, not
   `EMRTDCrypto`.
2. **ETSI-spec tokens preserve underscores**: `SignatureLevel::B_B`, `B_T`,
   `B_LT`, `B_LTA` mirror the AdES standards' canonical form. The underscores
   stand for the spec's hyphens.

When in doubt, prefer PascalCase.

## 8. Thread-safety vocabulary

Every `LIBRESCRS_PUBLIC_API` class states its concurrency contract in a
`@par Thread-safety` Doxygen paragraph. Three terms are normative — public
headers and design documents use one of these, or a named exception with an
explicit justification:

- **thread-safe.** Any combination of methods, including modifying ones, may be
  invoked concurrently from multiple threads on the same instance without
  external synchronisation. The implementation serialises its own state.
  Examples: `Trust::TrustStoreService`,
  `Plugin::CardPluginRegistry::findPluginForCard` (lookup-only).
- **thread-compatible.** Distinct instances may be used concurrently from
  different threads without external synchronisation. A single instance may be
  read concurrently (`const`-method calls), but any mutating method requires
  the caller to serialise access. This is the C++ standard library's default.
  Most plain-data types (`SigningRequest`, `TrustConfig`, `LocalizedText`) and
  result types fall here, as do `Plugin::CardData` and `SmartCard::OpenError`.
- **single-threaded.** The instance is not safe to share across threads, even
  for read access, after construction. Reserved for types backed by
  thread-affine resources — Qt widgets in a host application, PC/SC handles,
  OpenSSL contexts. Public LibreMiddleware headers should rarely use this
  category.

A `@par Thread-safety` paragraph in a public header references this section
rather than repeating the definitions inline. Inline elaboration is allowed
when the type's contract is non-obvious, such as the observer-fire-once
semantics on `TrustStoreService`.

## 9. Enum exhaustiveness and forward-compatibility

Per §4, plugin-facing enums are append-only across ABI revisions. A symmetric
obligation applies to host code that consumes them:

1. Every `switch` on a public LibreSCRS enum must either close over every value
   (compile-time enforced with `-Wswitch-enum`), or include a `default:` branch
   that handles "value introduced by a newer plugin against an older host"
   gracefully — typically log and map to a generic failure state — or both.
2. Hosts must not assume `enum_value < kHistoricalMax`. New values land at the
   tail; an older host receiving a newer value sees an integer it does not
   recognise, and the `default:` branch is the safety net.
3. New enumerators in a release X.Y are documented in the release notes under
   the enum's name with a one-line semantic note. The migration guide of the
   next major re-states which values were added in each X.Y minor.

This applies to `SigningResult::Status`, `OpenError::Kind`,
`ReadResult::Status`, `AutoReaderError::Kind`, `PINResultOutcome`,
`SignResultOutcome`, `SignMechanism`, `CardCapabilities`, `DecipherMechanism`,
`DecipherResultOutcome`, `LoadOutcome::Status`, `ChainStatus`, and to any
future plugin-facing or status-reporting enum.

## 10. Plugin capability bit reservation

`Plugin::CardCapabilities` is a bit-flag enum exposed across the plugin ABI. To
avoid collisions when third-party plugins are recompiled against a newer
header, bit positions are reserved:

- Bits 0–3: in use as of 4.0 (the header carries the canonical mapping).
- Bit 4: reserved for the next capability addition; it lands on `main` in a
  policy-paired commit before any plugin defines or consumes it.
- Bits 5–31: unallocated. Reservations land on `main` in policy commits, never
  on feature branches.

A contributor proposing a new capability bit submits two artefacts together:
the policy edit moving the bit from "reserved next" to "in use", and the header
change defining the enumerator. A change that touches one without the other is
rejected. That is what keeps the canonical bit-allocation history in a single
document.

## 11. Implementation details consumers should not rely on

The library reads a number of environment variables at runtime. These are
**internal escape hatches** — not part of the public API surface, and subject
to change without an ABI bump. The full set of `LIBRESCRS_*` runtime knobs read
in LibreMiddleware:

| Variable | Effect |
|---|---|
| `LIBRESCRS_SIGNING_BACKEND` | Switches between `native` (default) and `dss` (the Java Digital Signature Services oracle, used for cross-validation in tests). |
| `LIBRESCRS_DSS_JAR` | Overrides the resolved path to the DSS oracle JAR (used with `SIGNING_BACKEND=dss`). |
| `LIBRESCRS_CERTIFICATES_DIR` | Overrides the directory the bundled-certificates provider loads trust material from. |
| `LIBRESCRS_CSCA_STORE` | Overrides the CSCA master-list store path used by ePassport passive authentication. |
| `LIBRESCRS_PKCS11_MODULE` | Overrides the PKCS#11 module path the signing service loads. |
| `LIBRESCRS_MONITOR_COALESCE_MS` | Sets the reader/card monitor event-coalescing window, in milliseconds. |
| `LIBRESCRS_PCSC_TRACE` | Enables PC/SC APDU tracing (PIN-bearing INS bytes are redacted). |
| `LIBRESCRS_SIGN_TRACE` | Enables signing-path tracing (the PKCS#15 sign flow). |
| `LIBRESCRS_PROBE_TRACE` | Enables card-probe and plugin-activation tracing. |
| `LIBRESCRS_OPENSC_DEBUG` | Enables OpenSC-backed card debug logging. |

Do not set these in production. If a future release exposes a stable knob, it
moves to a typed configuration field on the relevant builder.

## 12. Shared-object ABI (`.so` SONAME)

§1 owns the source contract and §4 owns the plugin ABI. Neither owns what
`ld.so` consults, so this section does.

> The `LibreSCRS_*` shared libraries carry a SONAME integer independent of the
> release version. It is bumped in any release where the layout gate reports a
> non-additive change, whether or not that release is a major.

The integer lives in exactly one place, `LIBRESCRS_ABI_SOVERSION` in the
top-level `CMakeLists.txt`, and every `LibreSCRS_*` target plus the in-tree
PKCS#11 module reads it. It is deliberately **not** `PROJECT_VERSION_MAJOR`:
were it tied to the release major, the only way to satisfy the layout gate
inside a minor line would be to declare a new major — which would make the gate
a reason to route around it rather than a reason to think. In 5.0 the two
happen to coincide at 5.

**Non-additive means shape, not symbols.** A type whose `sizeof` moved, a
member whose offset shifted, a virtual whose slot changed occupant. Inline
members emit no symbol at all, so a demangled symbol list is structurally blind
to all three; the layout check records sizes, member offsets and the full
vtable slot order from the public headers, and its baseline is what a change
has to survive.

**Regenerating that baseline is an exit, and it is priced.** Regeneration
across a non-additive difference is refused while `LIBRESCRS_ABI_SOVERSION`
still equals the integer recorded in the baseline's own header. Raising that
integer is exactly the act being asked for, so this is a toll rather than an
impossibility. Regeneration is permitted only on the canonical configuration
(Linux / x86_64 / libstdc++), because member offsets are facts about one
toolchain and one standard library; the baseline header records the compiler
and `_GLIBCXX_RELEASE` it was taken with, so a mismatch reads as a mismatch
instead of as an ABI finding.

## Value renames in the 4.x line

Two `ChannelActivationError` values dropped a misleading `Pace` prefix, because
the BAC activation path returns them too: `PaceWrongSecret` → `WrongSecret` and
`PaceProtocolFailure` → `ProtocolFailure`. `PacePinBlocked` and
`PaceUnsupported` stay PACE-prefixed, since BAC never returns them. This is a
§7 honesty correction, not an append-only concern: the enum is not in §4's
plugin-facing append-only list, and the numeric ordinals are unchanged, so an
in-place rename preserves binary plugin compatibility.

It is not purely in-tree, though — the enum is the error type of the public
factory `Plugin::acquireChannelForProfile`, and both LibreAgent and this
developer guide consume it by name. Those in-family consumers migrate in
lockstep with the header change; there is no `[[deprecated]]` same-value alias,
because one would poison the §9 `-Wswitch-enum` exhaustiveness check and
violate the project's aggressive-legacy-removal rule. Because
`PaceWrongSecret` and `PaceProtocolFailure` shipped in tagged 4.1 and 4.2
headers, the 5.0.0 release notes document the rename for third-party SDK
consumers; with that note the §3.1 deprecation cycle is not required at this
adoption stage.
