---
title: "API Policy"
description: "LibreSCRS public API versioning, deprecation, and stability rules"
weight: 20
aliases:
  - /dev/api-policy/
---

# LibreSCRS API Policy

**Scope:** governs the `LibreSCRS::*` public API surface exposed by LibreMiddleware and any other LibreSCRS repo.

## 1. Versioning (SemVer 2.0)

- **Major** (`X.0.0`) — intentional breaking changes; removal of previously deprecated symbols; signature changes that invalidate source compatibility.
- **Minor** (`X.Y.0`) — new public symbols (backward-compatible); deprecation annotations on legacy symbols; build-system evolutions that preserve the public-link contract.
- **Patch** (`X.Y.Z`) — bug fixes only. No public signature changes; no new deprecations.

## 2. Public Surface

```
Public API = everything under LibreSCRS::{Auth,SmartCard,Secure,Plugin,Signing}::*,
             reachable via the public CMake targets LibreSCRS::{Auth,SmartCard,
             Plugin,Signing,All}. Everything else — smartcard::, libresign::,
             internal headers, all non-LibreSCRS namespaces — is implementation
             detail and may change in any release without semver impact.
```

## 3. Deprecation Rules (apply from 4.0 onward)

### 3.1 Release-bridging deprecation (the default shape)

Applies to every symbol users outside this repo can observe — public headers, installed CMake targets, plugin ABI, anything a third-party SDK consumer can link against.

1. A symbol marked `[[deprecated("<reason>; use <replacement> since <version>")]]` in release X.Y **must stay callable** throughout the X.* line.
2. The `@deprecated` Doxygen tag must be paired with an `@since` tag on the replacement symbol.
3. Deprecated symbols are **removed** in the next major (X+1.0). No deprecation survives a major version bump.
4. Release notes for any X.Y introducing deprecations must list every new deprecation under a "Deprecated in X.Y" heading.
5. The migration guide in each major release's notes documents every removed symbol and its pre-major replacement.

### 3.2 Transitional in-repo deprecation (exception — internal refactors only)

Applies when an internal refactor needs to switch in-tree callers from an old overload/signature to a new one ACROSS MULTIPLE COMMITS on the SAME branch, with NO external consumers affected between the first and last commit. Example: a multi-commit refactor that replaced `TSAClient::timestamp(hash, url, timeout)` with `TSAClient::timestamp(hash, TSARequest)` over three commits on the same branch — first commit added the new overload alongside the old, second migrated all in-tree callers, third removed the old overload.

Rules:

1. **Preferred path**: do the migration in a SINGLE commit — add the new overload, migrate callers, delete the old overload. No `[[deprecated]]` marker needed. Reserves `[[deprecated]]` for surfaces end-users see.
2. **Multi-commit path** (when a single commit would be too large or would mix concerns): annotate the old overload `[[deprecated(<reason>)]]` with an explicit note stating this is transitional in-repo; migrate callers in subsequent commits; delete the old overload in the final commit. The entire cycle MUST land on the same branch before it merges to `main`.
3. **Never mix 3.1 and 3.2**: a symbol intended for 3.2 transitional treatment MUST NOT stay deprecated past the branch merge. If the branch ships a release, the symbol is removed before tagging.
4. The commit message of the delete-commit must reference the intro-deprecate commit SHA so reviewers can confirm the cycle closes cleanly.

### 3.3 Distinguishing the two

If the `[[deprecated]]` survives a release-tagged commit on `main`: it's §3.1 — external consumers now see it, remove in next major.

If the `[[deprecated]]` lands and disappears entirely on a feature branch before that branch merges: it's §3.2 — the marker was a refactoring convenience, never a contract.

## 4. Plugin ABI

`CardPlugin` interface ABI is independently versioned (current: **v6**, introduced by the 4.0 major release). The ABI version increases when the virtual table layout changes (new non-default methods, removed methods, reordered methods, or a plugin-facing aggregate struct's layout changes). Non-ABI plugin-interface changes (adding a virtual method with a safe default, adding an enumerator at the end of a closed-at-default-arm enum) do NOT bump ABI.

Third-party plugin authors target a specific ABI version. `LibreSCRS::Plugin::kCardPluginAbiVersion` exposes the current ABI integer, and the `LIBRESCRS_DECLARE_CARD_PLUGIN(PluginType, AbiVersion)` macro `static_assert`s compile-time equality between the plugin's declared version and the current header's constant — so an ABI drift surfaces as a plugin build failure rather than a runtime mismatch. The registry additionally re-checks the version at load time via the `card_plugin_abi_version()` extern "C" symbol and rejects mismatches as `LoadOutcome::Status::AbiMismatch`.

**Append-only discipline for plugin-facing enums.** `ReadResult::Status`, `PINResultOutcome`, `SignResultOutcome`, `SignMechanism`, `CardCapabilities`, and any future plugin-facing enum must be treated as append-only across ABI revisions — old values keep their numeric identity, new values land at the tail. Removal of a value requires an ABI bump. Consumer switches on these enums should either close over every value (`-Wswitch-enum` compile-time check) or include a `default:` branch so a plugin returning a post-version value against a pre-version host degrades predictably.

Future-work candidates for the next plugin ABI bump are tracked as an internal roadmap that ships alongside the release notes of the introducing major version; third-party plugin authors should rely on the published ABI integer (`kCardPluginAbiVersion`) as the sole compatibility signal rather than forward-predicting against unpublished candidates.

## 5. Validation vs. Runtime Error Handling

Two distinct kinds of failure surface cleanly in LibreSCRS 4.0. The error-reporting mechanism must match the kind.

### 5.1 Construction / validation failures — throw

Builders, factories, and constructors that validate caller-supplied inputs throw `std::invalid_argument` (or a more specific `std::logic_error` subtype) with a message identifying the bad field. This includes:

- `SigningRequest::Builder::build() &&` — missing required field (input/output file, format); format-level mismatch.
- `VisualSignatureParams::Builder::rect(x, y, w, h)` — non-positive width or height.
- `VisualSignatureParams::Builder::pageIndex(i)` — negative index.
- `AuthRequirement::forSigning(...)`, `forChangePin(...)`, `forUnblockPin(...)` — empty PIN label.

The caller is expected to scope exception handling around construction phase (e.g., wizard-page "Next" clicks, SDK consumer app setup), then treat the constructed object as valid in the runtime phase.

### 5.2 Runtime / environmental failures — status-code result

Methods that can fail for environmental reasons (card absent, file I/O, network, user cancellation, etc.) return a result type carrying a `Status` enum. These methods DO NOT throw across the LibreSCRS 4.0 public API boundary. This includes:

- `SigningService::sign(...)` → `SigningResult` with `SigningResult::Status`.
- `CardPlugin::verifyPIN(...)`, `changePIN(...)`, `unblockPIN(...)` → `PINResult` (plugin ABI).
- `CardPluginService` (ctor) — catches dlopen failures, factory throws, and ABI mismatches internally; each file scanned produces a `LoadOutcome` entry in `loadReport()` rather than propagating an exception.

Engine-internal errors that truly cannot be classified as one of the `Status` values are reported via `SigningResult::Status::SigningEngineError` + a `diagnosticDetail` string for logs. Callers never receive thrown exceptions from `sign()`.

### 5.3 Pure accessors — noexcept where possible

Getters (e.g. `SigningRequest::inputFile()`, `TrustConfig::trustedListFile`, pimpl-backed `operator==`) are `noexcept` and return by const reference or value as appropriate. Lifetime of returned references is documented on each accessor.

### 5.4 Rationale

Throwing at construction makes validation tractable — the caller can scope exception handling around the construction phase, then treat the constructed object as valid throughout its lifetime. Mixing throw + status-code within a single method is the anti-pattern LibreSCRS avoids.

SDK consumers write:
```cpp
// Validation phase — may throw
try {
    auto request = std::move(SigningRequest::Builder{}
                     .inputFile(inPath)
                     .outputFile(outPath)
                     .format(SignatureFormat::Pades)
                     .level(SignatureLevel::B_LT))
                 .build();
    // Runtime phase — status-code results
    auto result = signingService->sign(request, credProvider, plugin, session);
    switch (result.status) {
        case SigningResult::Status::Ok: ...
        case SigningResult::Status::UserCancelled: ...
        // ...
    }
} catch (const std::invalid_argument& e) {
    // Builder validation failed — UI error message
}
```

## 6. 3.0 → 4.0 Transition (historical note)

The API-boundary hardening pass is itself the 4.0 major bump. 3.0 ships without any `[[deprecated]]` annotations; the 4.0 migration guide documents the full set of removed `smartcard::*` / `libresign::*` symbols with their `LibreSCRS::*` replacements. Subsequent cycles (4.x → 5.0, 5.x → 6.0, ...) follow the formal deprecate-in-minor → remove-in-major pattern in §3 above.

## 7. Enum value naming

LibreSCRS enums use **PascalCase** for value identifiers by default:

- `SignatureFormat::Pades`, `Cades`, `Xades`, `Jades`, `AsicE`
- `Status::Ok`, `Cancelled`, `Error`

Two deliberate exceptions:

1. **Standardised acronyms (3-letter or longer) stay all-caps** when they appear as standalone tokens in identifiers: `PKI`, `EID`, `MRZ`, `CAN`, `PIN`, `PUK`. Compound words use PascalCase: `EmrtdCrypto`, not `EMRTDCrypto`.
2. **ETSI-spec tokens preserve underscores**: `SignatureLevel::B_B`, `B_T`, `B_LT`, `B_LTA` mirror the AdES standards' canonical form. Underscores here stand for the spec's hyphens.

When in doubt, prefer PascalCase. Acronym-vs-PascalCase tie-breakers go to PascalCase for readability.

## 8. Implementation details consumers should not rely on

The library reads a small number of environment variables at runtime. These are **internal escape hatches** — not part of the public API surface and subject to change without an ABI bump:

| Variable | Effect |
|---|---|
| `LIBRESCRS_SIGNING_BACKEND` | Switches between `native` (default) and `dss` (Java Digital Signature Services oracle, used for cross-validation in tests). |

Consumers should not set these in production. The names use the `LIBRESCRS_*` prefix; if a future release exposes a stable knob, it will move to a typed configuration field on the relevant Builder.
