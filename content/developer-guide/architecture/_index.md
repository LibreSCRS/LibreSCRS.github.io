---
layout: "simple"
title: "Architecture Overview"
description: "System components, public API surface, plugin model, and data flow"
---

LibreSCRS is two cooperating projects that together read, process, and display Serbian government smart-card data. The public 4.0 API surface is stable C++20 + LGPL in LibreMiddleware; the Qt desktop GUI sits on top under GPL-3.0.

## Projects

### LibreMiddleware (LGPL-2.1)

A Qt-free C++20 static-library collection. All PC/SC and card-protocol code lives here. Consumers link against the public targets and reach everything through the `LibreSCRS::*` namespaces.

### LibreCelik (GPL-3.0)

A Qt6 desktop application that consumes LibreMiddleware. **Pure presentation layer** — no PC/SC, no APDU, no cryptographic protocol knowledge. It takes `LibreSCRS::Plugin::CardData` from middleware plugins and renders it through GUI plugins.

LibreCelik fetches LibreMiddleware via CMake `FetchContent`. For local development, point it at a local checkout through `FETCHCONTENT_SOURCE_DIR_LIBREMIDDLEWARE`.

---

## Public API surface

Everything consumers are expected to use lives under one of five namespaces.

| Namespace | Purpose |
|---|---|
| `LibreSCRS::Auth` | Credential-collection vocabulary — `AuthRequirement` with `forPreRead` / `forSigning` / `forChangePin` / `forUnblockPin` factories, `FieldDescriptor`, `CredentialProvider` callback alias, `CredentialResult`, `LocalizedText` i18n bundle |
| `LibreSCRS::SmartCard` | PC/SC reader access — `Monitor` (multi-subscriber reader/card-event fan-out), `CardSession` (pimpl session handle opened via the noexcept `open()` factory returning `OpenSessionResult`) |
| `LibreSCRS::Plugin` | Plugin framework — `CardPlugin` abstract base, `CardPluginRegistry`, `CardData` / `CardFieldGroup` / `CardField`, `ReadResult`, `PinStatusEntry`, `SecurityCheck` / `SecurityStatus`, `AutoReader` |
| `LibreSCRS::Signing` | PAdES / XAdES / JAdES / CAdES / ASiC-E signing — `SigningService` (pure-DI, move-only), `SigningRequest::Builder`, `VisualSignatureParams::Builder`, `TsaProvider` runtime-secret callback, `TrustConfig`, `SigningResult` |
| `LibreSCRS::Secure` | Cleansing types for short-lived secret material — `Secure::String` (PIN/token text; zeroed on destruction and move-from), `Secure::Buffer` (binary keys / APDU bytes) |

Everything outside these namespaces — `smartcard::*`, `libresign::*`, `pkcs11::*`, `pkcs15::*`, internal `detail::*` headers — is implementation detail. It may change in any release without semver impact.

---

## Plugin model

The system has two independent plugin layers: **middleware plugins** handle card communication, **GUI plugins** handle display. They meet at `CardData`, a universal data model produced by a middleware plugin and consumed by a GUI plugin.

```
┌───────────────────────────────────────────────────────────┐
│                      LibreCelik (GUI)                     │
│                                                           │
│  ┌──────────────────────────┐ ┌───────────────────────┐   │
│  │ QSmartCardMonitor        │ │ CardWidgetPluginReg.  │   │
│  │ (Qt adapter for Monitor) │ │ (QPluginLoader)       │   │
│  └──────────────────────────┘ └──────────┬────────────┘   │
│           ▲                              │ loads           │
│           │ wraps                 ┌──────▼──────────────┐  │
│           │                       │  GUI Plugins (.so)   │  │
│           │                       └─────────────────────┘  │
│           │                              ▲                 │
│           │                              │ CardData        │
├───────────┼──────────────────────────────┼─────────────────┤
│           │         LibreMiddleware      │                 │
│           │                              │                 │
│  ┌────────┴────────────┐  ┌──────────────┴───────────┐     │
│  │ LibreSCRS::SmartCard│  │ LibreSCRS::Plugin::       │     │
│  │          ::Monitor  │  │   CardPluginRegistry     │     │
│  │ (PC/SC event poll)  │  │ (dlopen + ABI v6 static  │     │
│  └─────────────────────┘  │  assert + ATR/AID probe) │     │
│                           └──────────┬───────────────┘     │
│                                      │ loads                │
│  ┌───────────────────────────────────▼─────────────────┐   │
│  │           Middleware Plugins (.so)                   │   │
│  │   cardedge, emrtd, pkcs15, piv, opensc, …           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                      │                     │
│                                      │ APDU (ISO 7816-4)   │
│                                      ▼                     │
│                               ┌────────────┐               │
│                               │ PC/SC      │               │
│                               └─────┬──────┘               │
└─────────────────────────────────────┼─────────────────────┘
                                      │
                               ┌──────▼──────┐
                               │ Smart Card  │
                               └─────────────┘
```

### Middleware plugins — `LibreSCRS::Plugin::CardPlugin`

A middleware plugin is a shared library (`.so` / `.dylib`) loaded by `CardPluginRegistry` via `dlopen` at runtime. Each plugin is a subclass of `CardPlugin` that calls `setIdentity(id, displayName, probePriority)` in its constructor and overrides the virtual methods relevant to the card family it supports. Declarative surface:

- **`CardCapabilities capabilities() const`** — bitfield advertising which categories the plugin implements: `None`, `PKI`, `IdentityData`, `EmrtdCrypto`, `PinManagement`. The host reads this at load time; methods outside the advertised set return `NotImplemented` by default.
- **`bool canHandle(const std::vector<uint8_t>& atr) const`** — fast ATR-only test. No card I/O.
- **`bool canHandleConnection(const std::vector<uint8_t>& atr, CardSession& session) const`** — connection probe for plugins that didn't match on ATR alone. The session's ATR is pre-passed so plugins don't re-read it.
- **`ReadResult readCard(CardSession& session, GroupCallback onGroup = {}) const`** — extract card data. Returns a status-coded `ReadResult`; the optional callback receives each `CardFieldGroup` as it becomes available so hosts can render progressively (replaces the older separate `readCardStreaming` method).
- **Signing methods** (when `CardCapabilities::PKI` is advertised) — `discoverKeyReferences`, `sign`, `getPINList`, `verifyPIN`, `changePIN`, `unblockPIN`. Return structured `SignResult` / `PINResult` with `bool ok()` predicate.

The plugin ABI is independently versioned as an integer constant `LibreSCRS::Plugin::kCardPluginAbiVersion` (current: **v6**). The one-line `LIBRESCRS_DECLARE_CARD_PLUGIN(MyPlugin, 6)` macro emits the three C-linkage factory symbols (`create_card_plugin`, `destroy_card_plugin`, `card_plugin_abi_version`) and pins the version with a compile-time `static_assert`. Exceptions MUST NOT cross the plugin ABI boundary — the macro wraps `new MyPlugin()` in a `noexcept` try/catch; failures surface as `LoadOutcome::Status::FactoryThrew`.

**Two-phase probe.** `CardPluginRegistry::findAllCandidates(atr, session)` first calls `canHandle(atr)` on every loaded plugin. Plugins that return `true` enter the candidate list immediately, ordered by `probePriority` (lower number wins). Plugins that returned `false` get a second chance via `canHandleConnection(atr, session)` — letting generic drivers (OpenSC, PKCS#15) claim the card by live AID probe.

**Fallback chain.** If the top-ranked candidate's `readCard` fails, the next is tried automatically. Data plugins (eID, vehicle, health) read demographic data; PKI plugins (CardEdge, PKCS#15, OpenSC) are triggered separately for signing and certificate operations. Decoupling means a data plugin never needs to know about PKI and vice versa.

### GUI plugins — `CardWidgetPlugin`

A GUI plugin is a Qt MODULE library loaded by `CardWidgetPluginRegistry` via `QPluginLoader`. Each plugin declares a `cardType()` string (matching the `LibreSCRS::Plugin::CardData::cardType` its paired middleware plugin emits) and implements `createWidget(const CardData&, QWidget* parent)` returning a fully-built Qt widget. Adding a new card display requires no core recompilation — drop in the `.so`, the registry discovers it.

---

## Ownership model

The Export.h top-of-tree doc states the project-wide convention explicitly: **every public service that depends on another service takes the dependency by `std::shared_ptr`**. This eliminates the "must outlive" destruction-order footgun that plagued pre-4.0 code at process shutdown.

Concrete consequences:

- `LibreSCRS::Signing::SigningService::sign(request, credProvider, plugin, session)` — `plugin` and `session` are `shared_ptr`; internal workers promote from `weak_ptr` at use.
- `LibreSCRS::Plugin::AutoReader` ctor — `monitor` and `registry` are `shared_ptr`.
- `LibreSCRS::Plugin::CardPluginRegistry::plugins()` — returns `vector<shared_ptr<CardPlugin>>`; the custom deleter runs the plugin's destructor and then calls `dlclose`, so the underlying `.so` stays mapped until the last external reference drops.

**Move-only** where duplication would be wrong: `SigningRequest` (two concurrent sign operations against the same I/O files is a footgun), `Secure::Buffer` (no accidental secret duplication), `CardSession` (hardware handle), `SigningService` (the object *is* the configured pipeline), `Monitor` (owns a live poll thread and subscription table keyed by stable tokens).

**Copyable** where value semantics are the natural fit: `AuthRequirement` (plain-data plus `std::vector<FieldDescriptor>`), `VisualSignatureParams` (pimpl deep-copies small-data), `CredentialResult` and `SigningResult` (each copy carries its own cleansed `Secure::String` storage), `LocalizedText`.

---

## Error-handling model

API-POLICY §5 splits errors into three shapes, applied uniformly across the public surface:

1. **Construction / validation errors — throw.** Builders, factories, and constructors that validate caller-supplied inputs throw `std::invalid_argument` identifying the bad field. Examples: `VisualSignatureParams::Builder::rect(r)` with non-positive dimensions, `SigningRequest::Builder::build()` with missing required fields, `AuthRequirement::forSigning(label, retries)` with an empty label. Callers scope exception handling around the construction phase.

2. **Runtime / environmental errors — structured status.** Methods that can fail for environmental reasons (card absent, network, user cancellation, protocol mismatch) return a result type carrying a `Status` enum + optional payload + optional translator-friendly message. These methods **do not throw** across the 4.0 public boundary. Examples: `SigningService::sign` → `SigningResult`, `CardPlugin::readCard` → `ReadResult`, `CardSession::open` → `OpenSessionResult {optional<CardSession>, optional<OpenError>}`, `Monitor::listReaders` → `optional<vector<string>>`.

3. **Pure accessors — `noexcept`.** Getters return by `const&` or by value without throwing. Accessors on a moved-from pimpl object are undefined behaviour; `explicit operator bool()` on every pimpl-backed type lets callers defensively check without triggering UB.

The plugin ABI boundary is a hard exception barrier: `readCard` and the plugin factory are `noexcept`; internal throws are translated into `ReadResult::Status::CommunicationError` / `ParseError` and `LoadOutcome::Status::FactoryThrew` at the boundary.

---

## Data flow

The complete path from card insertion to display:

```
1. Card inserted into reader

2. LibreSCRS::SmartCard::Monitor (LibreMiddleware, PC/SC poll thread)
   └─ detects card presence via SCardGetStatusChange
   └─ creates MonitorEvent { CardInserted, readerName, atr }
   └─ fans out to every subscriber callback (thread-safe subscription table)

3. QSmartCardMonitor (LibreCelik, Qt adapter)
   └─ receives MonitorEvent on monitor thread
   └─ marshals to Qt main thread via QMetaObject::invokeMethod
   └─ emits Qt signal

4. Main window starts two-phase plugin discovery:
   Phase 1 — ATR filter (no card I/O):
   └─ CardPluginRegistry::findAllCandidates(atr, session)
      ├─ cardedge-plugin::canHandle(atr)  → true
      ├─ emrtd-plugin::canHandle(atr)     → false
      └─ pkcs15-plugin::canHandle(atr)    → false
      Candidates: [cardedge (priority 840)]
   Phase 2 — connection probe (only plugins that returned false):
      ├─ emrtd-plugin::canHandleConnection(atr, session)  → false
      └─ pkcs15-plugin::canHandleConnection(atr, session) → true (found EF.ODF)
      Final: [cardedge (840), pkcs15 (2000)]  — lower wins

5. AsyncCardReader::requestData(topCandidate)
   └─ std::async → background thread
   └─ cardedge-plugin::readCard(session, options, groupCallback)
      ├─ SELECT AID, SM setup if required
      ├─ parse BER-TLV responses
      └─ emits CardFieldGroups progressively via callback
      └─ returns ReadResult::Status::Ok

6. Main thread marshals results back via QMetaObject::invokeMethod

7. CardWidgetPluginRegistry::findByCardType(cardData.cardType)
   └─ cardedge-gui-plugin matches

8. createWidget(cardData, parent) → rendered Qt widget

9. Widget displayed in main window
```

---

## Standards

The public API interoperates with or cites these standards:

| Standard | Usage |
|---|---|
| ISO 7816-4 | Smart card communication — APDU command/response, TLV / BER-TLV encoding |
| PC/SC | Reader access layer — card detection, connection management |
| PKCS#11 | Cryptographic token interface — `librescrs-pkcs11.so` for browsers and desktop PKI clients |
| PKCS#15 / ISO 7816-15 | Cryptographic information application — certificate and key discovery |
| ICAO 9303 | eMRTD — Basic Access Control, PACE, Secure Messaging, data group structure |
| NIST SP 800-73 | PIV card interface — certificate discovery, authentication, signing |
| BSI TR-03110 | PACE protocol — password-authenticated key agreement |
| ISO 32000-1 | PDF signature dictionary fields (reason, location, contactInfo) |
| ETSI EN 319 412 / 319 102 | AdES profiles — CAdES / PAdES / XAdES / JAdES / ASiC-E signing levels |
| RFC 3161 / 7617 / 6750 / 7230 | TSA timestamping + HTTP auth + header semantics |

---

## Extending the SDK

The 4.0 surface is intentionally narrow. Adding new functionality generally requires touching N independent files in coordination — the sections below are cookbooks for the common cases.

### Adding a new signature format

E.g. adding PKCS#7-enveloping or a hypothetical CAdES-Enveloping variant:

1. Add the format to `LibreSCRS::Signing::SignatureFormat` enum (`include/LibreSCRS/Signing/Enums.h`).
2. Add the matching backend module under `lib/libresign/src/native/`, following the pattern of `pades_module.{h,cpp}` (typed `Module` class, `sign()` returning `SigningResult`).
3. Add the format dispatch case to `lib/LibreSCRS/Signing/detail/RequestBridge.cpp::mapFormat()`.
4. Add a test path in `test/native_*_test.cpp` (one new file or a new fixture in an existing one).
5. Update the [SDK Reference]({{< ref "developer-guide/sdk-reference" >}})'s "Signing" section to mention the new format.

The closed-enum design makes step 4 catchable — any switch over `SignatureFormat` that the new value isn't added to will warn under `-Wswitch-enum`.

### Adding a new SigningResult::Status

1. Add to `LibreSCRS::Signing::SigningResult::Status` enum.
2. Add a named factory (`SigningResult::myNewStatus(...)`) in `SigningResult.h`.
3. Add the libresign-internal → public mapping in `lib/LibreSCRS/Signing/detail/ErrorClassifier.h::classify()`.
4. Update the [SDK Reference]({{< ref "developer-guide/sdk-reference" >}})'s status table.

### Adding a new card type (Plugin)

The plugin ABI is `kCardPluginAbiVersion = 6` (see `include/LibreSCRS/Plugin/PluginTypes.h`). New card types ship as separate shared libraries under `LIBRESCRS_PLUGIN_PATH`. Plugin authors:

1. Subclass `LibreSCRS::Plugin::CardPlugin`.
2. In the constructor call `setIdentity(id, displayName, probePriority)`.
3. Override `capabilities()` to advertise the bitfield of supported features (`PKI`, `IdentityData`, `EmrtdCrypto`, etc.).
4. Override the relevant virtual methods per advertised capability.
5. Export the entry points via `LIBRESCRS_DECLARE_CARD_PLUGIN(MyType, 6)`.

The `LIBRESCRS_DECLARE_CARD_PLUGIN` macro `static_assert`s at compile time that the plugin matches the current ABI version.

See `lib/cardedge/`, `lib/pkcs15/`, and `lib/piv/` for production examples.
