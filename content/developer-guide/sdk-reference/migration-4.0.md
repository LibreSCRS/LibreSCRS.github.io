---
title: "4.0 SDK Migration Guide"
description: "Source-level changes between 3.x preview and the LibreSCRS 4.0 public API"
weight: 25
aliases:
  - /dev/migration-4.0/
---

# 4.0 SDK Migration Guide

LibreSCRS 4.0 is the first release tagged from the post-hardening surface. Versions tagged 3.x predate the API-POLICY work and are no longer supported. SDK consumers tracking `feature/api-boundary-hardening` during the 3.x preview cycle will need the changes documented below to compile against 4.0.

This guide covers ABI breaks landed in the **Tier 2** trust-service extraction and the **Tier 2.5 + Tier 3** SOTA hardening pass. Each entry names the public symbol affected, the 3.x shape, the 4.0 shape, and a short "what changes for the call site" note.

For the full API policy (versioning, deprecation, validation-vs-runtime errors), see [API Policy]({{< ref "developer-guide/sdk-reference/api-policy" >}}).

---

## Trust lifecycle moves to `Trust::TrustStoreService`

**Audit refs:** Tier 2 follow-up

Before:

```cpp
LibreSCRS::Signing::SigningService service{trustConfig, tsa};
auto store = service.trustStore();
```

After (4.0):

```cpp
auto trustService = LibreSCRS::Trust::TrustStoreService::create(trustConfig);
LibreSCRS::Signing::SigningService service{trustService, tsa};
auto store = trustService->trustStore();
```

`Signing::TrustStoreManager` is removed entirely; `Signing::SigningService::trustStore()` is removed; consumers obtain the store from the lifecycle owner that constructed it. The 4.0 service is asynchronous (eager TL fetches run on internal `std::jthread` workers; observers fire on completion) and non-throwing at construction.

---

## `LocalizedText` moves to top-level `LibreSCRS::` namespace

**Audit refs:** LM-I2 / CC3

Before:

```cpp
#include <LibreSCRS/Auth/LocalizedText.h>

LibreSCRS::Auth::LocalizedText msg{"key", "Fallback"};
LibreSCRS::Auth::AuthRequirement::forSigning(LibreSCRS::Auth::LocalizedText{...}, retries);
```

After (4.0):

```cpp
#include <LibreSCRS/LocalizedText.h>

LibreSCRS::LocalizedText msg{"key", "Fallback"};
LibreSCRS::Auth::AuthRequirement::forSigning(LibreSCRS::LocalizedText{...}, retries);
```

The type is consumed across `Auth`, `SmartCard`, `Plugin`, and `Signing` — keeping it under `Auth` was a vestige of the original credential-prompt-only producer set. Drop the `Auth::` qualifier; from any nested `LibreSCRS::*` namespace the unqualified `LocalizedText` resolves via enclosing-namespace lookup. The old header path is removed; update the `#include` line.

---

## `SyncProvider<Result, Context>` template alias

**Audit refs:** LM-I3

`Auth::CredentialProvider` and `Signing::TsaProvider` now alias a single canonical generic:

```cpp
namespace LibreSCRS {
template <typename Result, typename Context>
using SyncProvider = std::function<Result(const Context&)>;
}
```

Source-compatible at the call site — both pre-existing aliases keep their names. The duplicated 30-line invocation/thread-safety contract paragraphs collapse to a single canonical block on `LibreSCRS::SyncProvider`. New runtime-secret callbacks added in 4.x follow the same template specialisation pattern.

---

## `CardPlugin` private members renamed

**Audit refs:** LM-C2

Affects plugin authors compiling against the protected/private surface of `LibreSCRS::Plugin::CardPlugin`. Public accessor names are unchanged.

| 3.x preview | 4.0 |
| --- | --- |
| `CardPlugin::id` (private) | `CardPlugin::pluginIdValue` |
| `CardPlugin::name` (private) | `CardPlugin::displayNameValue` |
| `CardPlugin::priority` (private) | `CardPlugin::probePriorityValue` |

Public accessors unchanged: `pluginId()`, `displayName()`, `probePriority()`. Plugins that defined their own `id`/`name`/`priority` member never got a build error from the shadow under the old layout — that bug-class is closed by the rename.

---

## `CardPlugin::canHandle` / `canHandleConnection` take `std::span`

**Audit refs:** LM-I5

Before:

```cpp
bool canHandle(const std::vector<std::uint8_t>& atr) override;
bool canHandleConnection(const std::vector<std::uint8_t>& atr,
                         smartcard::PCSCConnection& conn) override;
```

After:

```cpp
bool canHandle(std::span<const std::uint8_t> atr) override;
bool canHandleConnection(std::span<const std::uint8_t> atr,
                         smartcard::PCSCConnection& conn) override;
```

Each plugin override updates the parameter type. Implementations that read `.size()` / iterate / `data()` are span-compatible without further changes.

---

## `AutoReaderError::Kind::RegistryEmpty` enum value

**Audit refs:** LM-C3

`Plugin::AutoReader::AutoReaderError::Kind` gains a new value `RegistryEmpty` distinguishing "no plugins installed or all plugins failed to load" from "card present but no plugin matched its ATR". Any host code that exhaustively switches on `AutoReaderError::Kind` MUST add a case for `RegistryEmpty` (or a `default:` branch per [API-POLICY §9](api-policy/#9-enum-exhaustiveness-and-forward-compatibility)).

`Plugin::CardPluginRegistry::isUsable() noexcept` is the corresponding probe — use it at host startup to surface "no plugins installed" before the first card insert.

---

## `CardData::groupAt` / `fieldAt` bounds policy

**Audit refs:** LM-I8

Before (3.x preview): `noexcept` accessors with undefined behaviour on out-of-range indices.

After (4.0):

```cpp
// Bounds-checked variants (throw std::out_of_range)
CardFieldGroup&        groupAt(std::size_t index);
CardField&             fieldAt(std::size_t g, std::size_t f);
CardField&             fieldAt(std::pair<std::size_t, std::size_t> idx);

// Unchecked variants (noexcept, hot-path)
CardFieldGroup&        groupAtUnchecked(std::size_t index)        noexcept;
CardField&             fieldAtUnchecked(std::size_t g, std::size_t f) noexcept;
```

Host-supplied indices flow through the throwing form per [API-POLICY §5.1](api-policy/#51-construction--validation-failures--throw). Internal callers that already bounds-check (e.g. via `findGroup` / `findField` returning `optional<size_t>`) may use the unchecked variants for the noexcept hot-path.

---

## `SigningResult` / `CredentialResult` factory `userMessage` uniformity

**Audit refs:** LM-I11 / CC4

Every error-producing factory now takes `std::optional<LocalizedText> userMessage = std::nullopt` followed by `std::optional<std::string> diagnosticDetail = std::nullopt`.

Before (3.x preview, mixed shapes):

```cpp
SigningResult::invalidRequest(LocalizedText userMessage, std::optional<std::string> diag = nullopt);
SigningResult::invalidRequestDiagnosticOnly(std::string diag);
SigningResult::trustStoreUnavailable(std::optional<std::string> diag = nullopt);
SigningResult::tsaUnreachable(LocalizedText userMessage, std::optional<std::string> diag = nullopt);
CredentialResult::error(LocalizedText message);
CredentialResult::error();
```

After (4.0, single shape):

```cpp
SigningResult::invalidRequest(std::optional<LocalizedText> userMessage = nullopt,
                              std::optional<std::string> diag = nullopt);
SigningResult::trustStoreUnavailable(std::optional<LocalizedText> userMessage = nullopt,
                                     std::optional<std::string> diag = nullopt);
SigningResult::tsaUnreachable(std::optional<LocalizedText> userMessage = nullopt,
                              std::optional<std::string> diag = nullopt);
CredentialResult::error(std::optional<LocalizedText> userMessage = nullopt);
```

Migration: positional callers move the `LocalizedText` argument into a `std::optional` (implicit) and add the optional second arg. The `invalidRequestDiagnosticOnly(std::string)` overload is removed — express the diagnostic-only intent as `invalidRequest(std::nullopt, "diag string")`.

---

## `TrustConfig::Builder` (additive)

**Audit refs:** LM-I12

The aggregate `Trust::TrustConfig` remains a plain-data struct with public fields; existing callers that prefer designated-initialiser syntax (`TrustConfig{.includeSystemTrustStore = false}`) continue to compile.

The 4.0 release introduces a `TrustConfig::Builder` with per-setter validation per [API-POLICY §5.1](api-policy/#51-construction--validation-failures--throw):

```cpp
auto cfg = std::move(LibreSCRS::Trust::TrustConfig::Builder{}
              .addTrustedListSource("https://lotl.example.org/lotl.xml", true /*lotl*/, false /*eager*/)
              .addTrustedListSource("https://tl.example.org/tl.xml")
              .setCacheDirectory(cacheDir)
              .setIncludeSystemTrustStore(false))
              .build();
```

Setters throw `std::invalid_argument` on bad URLs (empty, wrong scheme, duplicates), unwritable cache parent paths, or missing trusted-list files. `build()` is `noexcept` once the per-setter contract is satisfied. Recommended path for new SDK consumers; existing aggregate callers continue to work.

---

## `Secure::String::equalConstantTime`

**Audit refs:** LM-I7

Before: `Secure::String::operator==` only — byte-identity, not constant-time. Documentation suggested callers "implement your own constant-time comparison."

After:

```cpp
LibreSCRS::Secure::String stored = ...;
LibreSCRS::Secure::String candidate = ...;
if (stored.equalConstantTime(candidate)) {
    // PIN matches
}
```

The new member runs in time proportional to the longer input regardless of where the first byte difference occurs (uses OpenSSL `CRYPTO_memcmp` internally; OpenSSL is already a private LM dependency, no new include surface). Use for any security-sensitive equality check on user-supplied input. `operator==` retains its byte-identity semantics for non-secret comparisons.

---

## `Trust::TrustStore::ChainStatus` keeps current shape

**Audit refs:** LM-I4

Per the [resolution decision](https://github.com/LibreSCRS/knowledge/blob/main/reviews/2026-04-29-lm-i4-resolution.md), `ChainStatus` does NOT add an `Unsettled` value. Consumers that need to disambiguate "really untrusted" from "still loading" query `Trust::TrustStoreService::status()` (or `sourceStatuses()`) in addition to inspecting the `ChainStatus` value. The two-source check is strictly more informative than a collapsed `Unsettled` enum value would be — the service's status enum distinguishes `Loading`, `PartialFailure`, `Settled`, etc.

---

## Plugin-internal: `smartcard::PCSCConnection` no longer in public CardSession.h

**Audit refs:** LM-I10

Plugin authors continue to call `LibreSCRS::SmartCard::detail::unwrap(session)` exactly as before — the call shape is unchanged. The internal change is structural: the public `<LibreSCRS/SmartCard/CardSession.h>` no longer forward-declares `namespace smartcard`. Plugin source files that include `<LibreSCRS/SmartCard/detail/Unwrap.h>` (the LM-internal-only header that exposes `unwrap`) keep working without modification.

If your plugin's source ever forward-declared `smartcard::PCSCConnection` itself relying on the public CardSession.h pull-in, replace that with the explicit include of `<LibreSCRS/SmartCard/detail/Unwrap.h>`.

---

## Service-suffix consistency rename (Tier 4 Phase F)

**Audit refs:** CC6

The three service-flavoured types in `LibreSCRS::Plugin` and `LibreSCRS::SmartCard` adopt the `*Service` suffix that `Signing::SigningService` and `Trust::TrustStoreService` already established. Pure data / event / outcome types (e.g. `MonitorEvent`, `AutoReaderError`, `LoadOutcome`) keep their current names.

| 3.x preview / pre-rename | 4.0 |
| --- | --- |
| `LibreSCRS::Plugin::AutoReader`            | `LibreSCRS::Plugin::AutoReaderService`            |
| `LibreSCRS::Plugin::CardPluginRegistry`    | `LibreSCRS::Plugin::CardPluginService`            |
| `LibreSCRS::SmartCard::Monitor`            | `LibreSCRS::SmartCard::MonitorService`            |
| `<LibreSCRS/Plugin/AutoReader.h>`          | `<LibreSCRS/Plugin/AutoReaderService.h>`          |
| `<LibreSCRS/Plugin/CardPluginRegistry.h>`  | `<LibreSCRS/Plugin/CardPluginService.h>`          |
| `<LibreSCRS/SmartCard/Monitor.h>`          | `<LibreSCRS/SmartCard/MonitorService.h>`          |

Mechanical migration (covered by `tools/migrate-3x-to-4.0.sh`):

```sh
sed -i \
    -e 's|LibreSCRS/Plugin/AutoReader\.h|LibreSCRS/Plugin/AutoReaderService.h|g' \
    -e 's|LibreSCRS/Plugin/CardPluginRegistry\.h|LibreSCRS/Plugin/CardPluginService.h|g' \
    -e 's|LibreSCRS/SmartCard/Monitor\.h|LibreSCRS/SmartCard/MonitorService.h|g' \
    -e 's|\bAutoReader\b|AutoReaderService|g' \
    -e 's|\bCardPluginRegistry\b|CardPluginService|g' \
    -e 's|LibreSCRS::SmartCard::Monitor\b|LibreSCRS::SmartCard::MonitorService|g' \
    *.cpp *.h
```

Take care not to globally rename the unrelated 3.x internal `smartcard::Monitor` symbol if your code happens to reference it through a `using namespace smartcard;` (no public 4.0 surface uses that name).

---

## `CardSession::open` returns `std::variant` (Tier 4 Phase G)

**Audit refs:** CC7

`OpenSessionResult` migrates from a struct of two `std::optional` slots to a `std::variant<CardSession, OpenError>` — exactly one alternative is held, eliminating the "both empty / both populated" invariant the previous shape silently allowed.

Before:

```cpp
struct OpenSessionResult {
    std::optional<CardSession> session;
    std::optional<OpenError>   error;
};
```

After:

```cpp
struct OpenSessionResult : std::variant<CardSession, OpenError>
{
    using std::variant<CardSession, OpenError>::variant;
};
```

Consumer pattern-matching idiom:

```cpp
auto result = SmartCard::CardSession::open(reader);
if (auto* session = std::get_if<SmartCard::CardSession>(&result)) {
    // *session is the live handle
    plugin->readCard(*session, ...);
} else {
    const auto& err = std::get<SmartCard::OpenError>(result);
    qCWarning(category) << "open failed:" << static_cast<int>(err.kind);
}
```

Equivalent `std::visit`:

```cpp
std::visit([&](auto&& alt) {
    using T = std::decay_t<decltype(alt)>;
    if constexpr (std::is_same_v<T, SmartCard::CardSession>) {
        plugin->readCard(alt, ...);
    } else {
        // OpenError branch
    }
}, result);
```

This change is mechanical for the common `if (sessionResult.session) {...} else {...}` consumer pattern but cannot be auto-rewritten — `migrate-3x-to-4.0.sh` flags `OpenSessionResult` consumer sites for manual review.

---

## Reference

- [API Policy]({{< ref "developer-guide/sdk-reference/api-policy" >}}) — versioning, deprecation, validation-vs-runtime rules.
- [SDK Reference]({{< ref "developer-guide/sdk-reference" >}}) — narrative per-namespace tour.
- `examples/sdk-consumer/main.cpp` in the LibreMiddleware source tree — the minimal-working consumer that exercises the post-Tier-2 surface.
