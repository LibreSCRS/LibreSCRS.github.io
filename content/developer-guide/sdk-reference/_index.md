---
title: "SDK Reference"
description: "Per-namespace developer reference for the LibreSCRS 4.0 public API"
weight: 30
---

LibreMiddleware ships a C++20 SDK under the `LibreSCRS::*` umbrella. The surface is intentionally narrow — six namespaces, ~28 public headers — and is stable across the 4.x line per the [API Policy]({{< ref "developer-guide/sdk-reference/api-policy" >}}).

This page is the **narrative reference**: what each namespace is for, when you reach for it, and one idiomatic snippet per component. For the full auto-generated entity list (every class, every member, every parameter) consult the Doxygen output on the project's GitHub Pages.

The minimal working consumer is `examples/sdk-consumer/main.cpp` in the LibreMiddleware source tree — a 70-line program that exercises one call per public target.

---

## `LibreSCRS::Auth` — credential prompts

Describes **what the middleware needs from the user** (PIN, PUK, MRZ, CAN) and how the host should answer.

- `AuthRequirement` — the request. Built via closed-set factories:
  - `forPreRead(PreReadAuthMethod::BacMrz | PaceCan | None)` — travel-document unlock material.
  - `forSigning(pinLabel, retriesLeft)` — single PIN for signing.
  - `forSigning(LocalizedText pinLabel, retriesLeft)` — translatable variant (4.0); preserves `key` end-to-end.
  - `forChangePin(pinLabel, retriesLeft)` — current + new + confirm triple.
  - `forChangePin(LocalizedText pinLabel, retriesLeft)` — translatable variant (4.0); same bundle on all three fields, role distinguished via field id.
  - `forUnblockPin(pinLabel)` — PUK + new + confirm triple.
  - `forUnblockPin(LocalizedText pinLabel)` — translatable variant (4.0).
- `FieldDescriptor` — each input the provider must collect (one `std::vector` of these per requirement).
- `CredentialProvider` — `std::function<CredentialResult(const AuthRequirement&)>` the host implements.
- `CredentialResult` — returned bundle; values keyed by `FieldDescriptor::id`, each stored as a cleansing `Secure::String`.
- `LocalizedText` — `{key, defaultText, placeholders}` triple used for every user-visible message produced by the middleware.

```cpp
using namespace LibreSCRS;

auto req = Auth::AuthRequirement::forSigning("PIN", /*retriesLeft=*/3);
std::vector<Auth::CredentialResult::Entry> values;
for (const auto& field : req.fields()) {
    Secure::String pin = askUser(field.label.defaultText);
    values.emplace_back(field.id, std::move(pin));
}
auto answer = Auth::CredentialResult::ok(std::move(values));
```

`CredentialResult` has no default constructor — it is deliberately forced through one of the named factories (`ok`, `cancelled`, `error`) so every producer commits to an explicit `Status`. If the user dismisses the prompt, return `Auth::CredentialResult::cancelled()`.

Factories are preferred here (closed-shape requirement) over a Builder; see [`AuthRequirement` class doc](#) for rule-of-thumb.

---

## `LibreSCRS::SmartCard` — PC/SC access

Two services on top of PC/SC, both pimpl-backed.

- `MonitorService` — reader + card event source. Non-copyable, non-movable (lifetime coupling with its subscription table). Multi-subscriber fan-out: the polling thread auto-starts on first `subscribe` and auto-stops on last `unsubscribe`.
- `CardSession` — opaque session handle. Construct via the noexcept `open(readerName)` factory returning `std::expected<CardSession, OpenError>`. Move-only.

```cpp
auto mon = std::make_shared<SmartCard::MonitorService>();
auto readers = mon->listReaders();               // optional<vector<string>>
if (!readers) return;                            // PC/SC subsystem unavailable

auto token = mon->subscribe([](const SmartCard::MonitorEvent& e) {
    if (e.kind == SmartCard::MonitorEvent::Kind::CardInserted) {
        auto sessionResult = SmartCard::CardSession::open(e.readerName);
        if (sessionResult) {
            handleCard(std::move(*sessionResult));
        }
    }
});
// ... mon->unsubscribe(token); when done
```

`listReaders`, `open`, and `subscribe` are thread-safe; callbacks fire on the polling thread — marshal to your UI thread.

---

## `LibreSCRS::Plugin` — card driver framework

Everything about extending support to new card types.

- `CardPlugin` — abstract base. Every `.so` plugin implements a subclass, calls `setIdentity(id, displayName, probePriority)` in its ctor, and overrides whichever virtuals its `CardCapabilities` flags advertise.
- `CardPluginService` — load-at-construction, multi-directory. Returns structured `LoadOutcome` per file so hosts surface plugin errors rather than silently ignoring them.
- `CardData` / `CardFieldGroup` / `CardField` — the universal payload type a plugin produces.
- `ReadResult` — structured `readCard` outcome (status enum + payload).
- `PinStatusEntry`, `SecurityCheck` / `SecurityStatus` — per-PIN and verification-check reporting.
- `AutoReaderService` — convenience wrapper that pairs a `MonitorService` with a `CardPluginService` and hands you `CardData` on insert events.

### Authoring a plugin

```cpp
// my_plugin.cpp
#include <LibreSCRS/Plugin/CardPlugin.h>
#include <LibreSCRS/Plugin/PluginExport.h>
#include <LibreSCRS/Plugin/ReadResult.h>

class MyPlugin final : public LibreSCRS::Plugin::CardPlugin {
public:
    MyPlugin() {
        setIdentity("example.my-card", "Example card", /*probePriority=*/1000);
    }
    LibreSCRS::Plugin::CardCapabilities capabilities() const override {
        return LibreSCRS::Plugin::CardCapabilities::IdentityData;
    }
    bool canHandle(const std::vector<uint8_t>& atr) const override {
        return atr == std::vector<uint8_t>{0x3B, 0x80, /* ... */};
    }
    LibreSCRS::Plugin::ReadResult readCard(
        LibreSCRS::SmartCard::CardSession& session,
        GroupCallback onGroup = {}) const override   // GroupCallback is nested inside CardPlugin
    {
        // ...send APDUs via session, emit CardFieldGroups via onGroup callback...
        return LibreSCRS::Plugin::ReadResult::ok({});
    }
};

LIBRESCRS_DECLARE_CARD_PLUGIN(MyPlugin, 7)  // ABI version pinned at compile time
```

Build as a `.so`, install to the directory passed to `CardPluginService`. The registry's ABI `static_assert` will fire at compile time if you target the wrong version. Exceptions MUST NOT cross the plugin boundary — the factory macro wraps `new MyPlugin()` in a noexcept try/catch; throws surface as `LoadOutcome::Status::FactoryThrew`.

### Consuming the registry

```cpp
LibreSCRS::Plugin::CardPluginService registry{std::filesystem::path{"/usr/lib/librescrs/plugins"}};

for (const auto& outcome : registry.loadReport()) {
    if (outcome.status != LibreSCRS::Plugin::LoadOutcome::Status::Loaded) {
        log("plugin {} failed: {}", outcome.soPath, outcome.diagnostic);
    }
}

auto candidates = registry.findAllCandidates(atr, session);   // priority-ordered
for (const auto& plugin : candidates) {
    auto result = plugin->readCard(session);   // GroupCallback defaulted — no streaming
    if (result.status == LibreSCRS::Plugin::ReadResult::Status::Ok)
        break;
}
```

---

## `LibreSCRS::Trust` — trust anchors & async TL fetch

Lifecycle owner of the unified trust store: bundled CA anchors, optional OS root store, and any number of asynchronously-fetched eIDAS Trusted Lists.

- `TrustStore` — the read-only composed anchor set. Grows monotonically as eager and lazy TL fetches complete; safe for concurrent reads.
- `TrustConfig` — declarative inputs: TL sources, cache directory, system-trust toggle, optional local TL file.
- `TrustStoreService` — the lifecycle owner. **Asynchronous, non-throwing factory.** `create(TrustConfig)` returns a usable service immediately with bundled + system anchors; eager TL fetches run on internal worker threads and merge into the public store as they complete. Consumers observe completion via `status()`, `addObserver(...)`, or the opt-in `waitForEagerFetches(deadline, stop_token)`.

```cpp
namespace Trust = LibreSCRS::Trust;

Trust::TrustConfig config;
config.trustedListSources.push_back({
    "https://www.mit.gov.rs/TrustedList/TSL-RS.xml", /*lazy=*/false, /*verify=*/true});
config.includeSystemTrustStore = true;

// create() never blocks on network IO and never throws.
auto trustService = Trust::TrustStoreService::create(std::move(config));

// Render UI immediately with bundled + system anchors; new TL anchors land
// asynchronously. GUI consumers should subscribe via addObserver:
auto handle = trustService->addObserver(
    [](std::string_view url, Trust::TrustStoreService::SourceStatus s) {
        // marshal back to the UI thread (e.g. QMetaObject::invokeMethod) and
        // refresh anything that depends on chain resolution.
    });

// Tests / CLI tooling that legitimately want a synchronous wait:
auto status = trustService->waitForEagerFetches(std::chrono::seconds(5));

// Read-only access to the composed store:
std::shared_ptr<const Trust::TrustStore> store = trustService->trustStore();
```

`TrustStoreService` is constructed via private ctor + factory; ownership is always `std::shared_ptr` because internal worker threads hold weak references to its `Impl`. The dtor cancels in-flight fetches via `std::stop_source` and joins workers with a bounded grace period.

**Threading.** All public methods are thread-safe. Observer callbacks fire on internal worker threads — UI consumers must marshal to their main thread via the platform's queued-invocation primitive.

**Behavioural note.** TL anchors arrive asynchronously. Consumers that absolutely require synchronous availability (rare — typically only test fixtures) call `waitForEagerFetches`. GUI consumers tolerate eventual consistency: render with whatever the store has at open time and refresh on observer events.

---

## `LibreSCRS::Signing` — PAdES / XAdES / JAdES / CAdES / ASiC-E

Digital signing against a smart-card-resident key.

- `SigningService` — the entry point. **Pure DI**: takes a `shared_ptr<Trust::TrustStoreService>` + `TsaProvider` in its constructor and never mutates afterwards. Move-only. Construct once per trust/TSA policy; reuse across sign calls.
- `SigningRequest` + `SigningRequest::Builder` — one sign operation's parameters (input/output paths, format, level, visual params, TSA override, contactInfo, reason, location). Builder validates at `build() &&`.
- `VisualSignatureParams` + `VisualSignatureParams::Builder` — PAdES annotation appearance. Geometry validated per setter. `kDefaultVisualSignatureRect` exposed for hosts that just want "the default".
- `TsaProvider` — `std::function<TsaRequest(const TsaContext&)>`. Invoked per sign to fetch URL + credentials (Basic / Bearer / mTLS / extra headers).
- `SigningResult` — status enum + `outputPath` (signed-document path on success) + optional translator-friendly message + diagnostic detail.

Trust material is injected via `Trust::TrustStoreService` (see the `LibreSCRS::Trust` section above) — `SigningService` no longer owns trust lifecycle.

```cpp
LibreSCRS::Trust::TrustConfig trust;
trust.includeSystemTrustStore = true;
auto trustService = LibreSCRS::Trust::TrustStoreService::create(std::move(trust));

auto tsa = LibreSCRS::Signing::staticTsaChecked("https://tsa.example.com");  // validates URL
LibreSCRS::Signing::SigningService service{trustService, tsa};

LibreSCRS::Signing::SigningRequest::Builder sb;
sb.inputFile("/tmp/document.pdf");
sb.outputFile("/tmp/document.signed.pdf");
sb.format(LibreSCRS::Signing::SignatureFormat::Pades);
sb.level(LibreSCRS::Signing::SignatureLevel::B_LT);
sb.reason("Approval");
sb.contactInfo("signer@example.com");
auto request = std::move(sb).build();  // throws invalid_argument on missing required fields

// cardPlugin and cardSession are std::shared_ptr<...> — sign() takes shared
// ownership for the duration of the call.
auto result = service.sign(request, credentialProvider, cardPlugin, cardSession);
switch (result.status) {
    case LibreSCRS::Signing::SigningResult::Status::Ok:
        log("signed: {}", result.outputPath->string());
        break;
    case LibreSCRS::Signing::SigningResult::Status::UserCancelled:
    case LibreSCRS::Signing::SigningResult::Status::PinVerificationFailed:
    case LibreSCRS::Signing::SigningResult::Status::TsaUnreachable:
        if (result.userMessage) showUserMessage(*result.userMessage);
        break;
    // ... other Status values ...
}
```

`build()` is rvalue-qualified. The named-builder form is the canonical pattern:

```cpp
LibreSCRS::Signing::SigningRequest::Builder b;
b.inputFile(...).outputFile(...);    // setters return Builder&
auto request = std::move(b).build(); // explicit rvalue cast
```

A pure single-expression chain off a temporary works because the temporary outlives the full expression — `auto p = SigningRequest::Builder{}.inputFile(...).outputFile(...).build();` is well-formed (the rvalue temporary satisfies `build() &&`). The shape that does NOT compile is mixing the two: a *named lvalue* builder cannot satisfy `build() &&` without an explicit `std::move`. In practice the named-builder form is preferred — error paths read more clearly when each setter is its own statement, and the diagnostics on a missing `std::move` at the call site are friendlier than on a runaway chain.

### Unicode visual signature appearance — 4.0+

Visible signature text on PAdES PDFs renders any Latin-Extended and Cyrillic
character correctly. The engine embeds and subsets a Liberation Sans font
program per signed document, with a `/ToUnicode` CMap so the rendered text
is searchable, copy-pasteable, and accessible. Pre-4.0 signatures used a
Helvetica Type1 font with single-byte StandardEncoding — non-ASCII signer
names rendered as garbled glyphs (e.g. `Hiršl` displayed as `Hir¯¡l`).

The fix is entirely below the public API: the same `VisualSignatureParams`
shape (geometry + `textTemplate`) carries the user-visible text; nothing
needs to change in calling code.

```cpp
// 4.0: any Unicode text in visual signatures renders correctly.
LibreSCRS::Signing::VisualSignatureParams::Builder vb;
vb.pageIndex(0);
vb.rect({50, 50, 250, 60});
vb.textTemplate("Potpisao: Hiršl Ćirković\nDatum: 2026-04-25");
auto visual = std::move(vb).build();
```

The font subset is per-signature: each signed PDF carries only the glyphs it
references (~5-10 KB typical). Liberation Sans 2.1.5 is bundled under the SIL
Open Font License 1.1; the engine's TTF subsetter is implemented from
scratch with no external font dependency.

---

## `LibreSCRS::Secure` — cleansing secrets

Short-lived secret material zeroed on destruction and on move-from. Backed by `OPENSSL_cleanse`.

- `Secure::String` — PIN / PUK / token text. Move-only-by-default but **copyable** with per-copy cleansing, so it composes with `std::function`-captured `CredentialProvider` closures and with `std::optional<CredentialResult>`. Deliberately backed by `std::vector<char>` (not `std::string`) to avoid Small-String-Optimisation leakage.
- `Secure::Buffer` — binary material (APDU responses, key bytes). Move-only. Four constructors: default (empty, no allocation), `(size, fill)` (fixed-size pre-filled), `std::string_view` (text fragments), and `std::span<const std::uint8_t>` (binary).

```cpp
LibreSCRS::Secure::String pin{"1234"};
// ... use pin.view() with a PKCS#11 verify ...
// destructor OPENSSL_cleanse's the bytes; original std::string literal is copied in, not referenced

auto b = LibreSCRS::Secure::Buffer{std::span<const std::uint8_t>{apduBytes.data(), apduBytes.size()}};
// b.data() valid for b.size() bytes; cleared on ~Buffer() or move-assign
```

**Equality on `Secure::String` is NOT constant-time** — deliberate, documented on the header. Callers that need constant-time compare should take the `view()` and feed it to their own primitive.

---

## Migration 3.x → 4.0

The 4.0 umbrella refactor removed every non-`LibreSCRS::*` public namespace. If you maintained code against a 3.x release, here's the one-line migration map:

| 3.x | 4.0 |
|---|---|
| `smartcard::PCSCConnection`, `smartcard::MonitorService` (public) | `LibreSCRS::SmartCard::CardSession`, `LibreSCRS::SmartCard::MonitorService`; internal transport stays `smartcard::*` but is no longer shipped in the install tree |
| `plugin::CardPlugin`, `plugin::CardData` | `LibreSCRS::Plugin::CardPlugin`, `LibreSCRS::Plugin::CardData` — see per-method changes below |
| `libresign::SigningService`, `libresign::SignRequest` | `LibreSCRS::Signing::SigningService`, `LibreSCRS::Signing::SigningRequest` + `Builder` |
| `eidcard::`, `healthcard::`, `euvrc::`, `piv::` public APIs | Removed — consumers now drive everything through `LibreSCRS::Plugin::CardPluginService` + `CardData`. Per-card-family fields still exist inside the plugins. |
| `smartcard::SecureBuffer` | `LibreSCRS::Secure::Buffer` (binary) + `LibreSCRS::Secure::String` (text) |
| `readCard` throws on failure | `readCard` returns `LibreSCRS::Plugin::ReadResult` with a status enum (exceptions no longer cross the plugin boundary) |
| `readCardStreaming` separate method | Merged into `readCard` with optional `GroupCallback` — implement one method, opt into streaming by calling the callback |
| `canHandleConnection(PCSCConnection&)` | `canHandleConnection(const vector<uint8_t>& atr, CardSession&)` — ATR pre-passed |
| `SigningService::instance()` / `configure*()` | Removed — construct once via `make_shared<SigningService>(trustService, tsa)` per policy |
| `SigningService(TrustConfig, TsaProvider)` (3.x preview) | `SigningService(shared_ptr<Trust::TrustStoreService>, TsaProvider)` — trust lifecycle moved into a separate first-class service. Migration: replace `SigningService(trustConfig, tsa)` with `Trust::TrustStoreService::create(trustConfig)` followed by `SigningService(trustService, tsa)`. |
| `Signing::SigningService::trustStore()` getter | Removed — read the store from the service that owns it: `trustService->trustStore()` |
| `Signing::TrustStoreManager` | Removed — `Trust::TrustStoreService` is the single lifecycle owner |
| Empty `SignResult` meant "plugin does not sign" | `SignResult::outcome == NotImplemented` — explicit signal |
| `PINResult.success` / `SignResult.success` bool | `bool ok() const noexcept` derived from `.outcome` |
| `extraHeaders` was `std::map` | `std::vector<std::pair>` — preserves insertion order, allows duplicates |
| `SigningResult::invalidRequest(std::string)` | `SigningResult::invalidRequestDiagnosticOnly(std::string)` — the name advertises the "no user-visible LocalizedText" trade-off |
| `PCSCConnection::Pcsc(reader)` (throws on failure) | `CardSession::open(reader)` returns `std::expected<CardSession, OpenError>` (`noexcept`) |
| `CredentialResult::errorMessage` | `CredentialResult::userMessage` (renamed for consistency across result types) |
| `OpenError::message` | `OpenError::userMessage` (renamed for consistency across result types) |
| `MonitorEvent::errorDetail` | `MonitorEvent::diagnosticDetail` (renamed for consistency across result types) |

**Plugin ABI:** v5 (3.x) → **v6** (4.0). Third-party plugins MUST be rebuilt against 4.0 headers. The `LIBRESCRS_DECLARE_CARD_PLUGIN(T, 6)` macro's `static_assert` catches version mismatch at compile time.

**Dynamic-library distribution:** LibreMiddleware's public static-link contract is unchanged — static archives, consistent-toolchain consumer, no ABI stability promised across `libstdc++` versions. The only shipped shared library is `librescrs-pkcs11.so` which carries its own C ABI boundary for PKCS#11 consumers.

For the full removed-symbol list and per-release migration notes, see the LibreCelik release-notes in the source tree.
