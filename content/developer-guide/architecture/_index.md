---
title: "Architecture Overview"
description: "System components, data flow, plugin architecture, and design patterns"
---

LibreSCRS consists of two main projects that work together to read, process, and display smart card data.

## Components

### LibreMiddleware (LGPL-2.1)

A Qt-free C++20 static library collection for smart card communication. It handles everything from low-level APDU command/response exchanges to high-level card data extraction.

| Library | Purpose |
|---|---|
| `smartcard` | PCSCConnection, APDU command/response, TLV and BER-TLV parsing (ISO 7816-4) |
| `eidcard` | Serbian eID card API with card reader implementations (Apollo 2008, Gemalto 2014+, Foreigner IF2020) |
| `vehiclecard` | Vehicle registration document API |
| `healthcard` | Health insurance card (RFZO) |
| `pkscard` | PKS qualified signature card (Chamber of Commerce) |
| `cardedge` | Generic CardEdge/PKCS#15 applet — PIN operations, signing, certificate discovery |
| `emrtd` | eMRTD e-passport communication — data group reading, MRZ parsing |
| `emrtd-crypto` | eMRTD cryptography — BAC, PACE (ECDH-GM), Secure Messaging |
| `pkcs11` | PKCS#11 shared library (`librescrs-pkcs11`) |
| `*-plugin` | Card plugins (`.so`): eidcard, vehiclecard, healthcard, pkscard, opensc, emrtd |

### LibreCelik (GPL-3.0)

A Qt6 desktop GUI application that displays card data. It is a pure presentation layer with its own plugin system for card-specific widgets.

| Module | Purpose |
|---|---|
| `smartcard` | SmartCardScanner — detects card insert/remove events via PC/SC polling |
| `plugin` | CardWidgetPlugin interface and CardWidgetPluginRegistry (QPluginLoader) |
| `asynccardreader` | Generic async card reader using middleware CardPlugin fallback chain |
| `document` | Shared PKI UI (TokenSection), PIN change dialog, printing |
| `certificate` | X.509 certificate viewer (tree model + dialog) |
| `plugins/` | GUI plugins (rseid, vehicle, health, pks) as Qt MODULE `.so` files |

LibreCelik fetches LibreMiddleware via CMake `FetchContent`. For local development, you can point it to a local checkout instead.

---

## Plugin Architecture

The entire system is built around plugins. There are two independent plugin layers — **middleware plugins** handle card communication, **GUI plugins** handle display. They connect through `CardData`, a universal data model that any middleware plugin produces and any GUI plugin consumes.

```
┌─────────────────────────────────────────────────────────┐
│                      LibreCelik (GUI)                   │
│                                                         │
│  ┌─────────────────┐     ┌────────────────────────┐     │
│  │ SmartCardScanner │────▶│ CardWidgetPluginRegistry│     │
│  │ (PC/SC polling)  │     │ (QPluginLoader)        │     │
│  └─────────────────┘     └──────────┬─────────────┘     │
│                                     │ loads              │
│                          ┌──────────▼─────────────┐     │
│                          │   GUI Plugins (.so)     │     │
│                          │ ┌────────┐ ┌─────────┐ │     │
│                          │ │ rseid  │ │ vehicle │ │     │
│                          │ ├────────┤ ├─────────┤ │     │
│                          │ │ health │ │  pks    │ │     │
│                          │ └────────┘ └─────────┘ │     │
│                          └────────────────────────┘     │
│                                     ▲                   │
│                                     │ CardData          │
├─────────────────────────────────────┼───────────────────┤
│                      LibreMiddleware│                    │
│                                     │                   │
│  ┌────────────────────────┐         │                   │
│  │ CardPluginRegistry     │─────────┘                   │
│  │ (dlopen)               │                             │
│  └──────────┬─────────────┘                             │
│             │ loads                                      │
│  ┌──────────▼──────────────────────────────────┐        │
│  │         Middleware Plugins (.so)              │        │
│  │ ┌─────────┐ ┌──────────┐ ┌───────────────┐ │        │
│  │ │ eidcard │ │ vehicle  │ │    opensc      │ │        │
│  │ ├─────────┤ ├──────────┤ │ (PKI fallback) │ │        │
│  │ │ health  │ │  emrtd   │ └───────────────┘ │        │
│  │ ├─────────┤ ├──────────┤                    │        │
│  │ │  pks    │ │ pkcs15   │                    │        │
│  │ └─────────┘ └──────────┘                    │        │
│  └─────────────────────────────────────────────┘        │
│                          │                              │
│                          │ APDU (ISO 7816-4)            │
│                          ▼                              │
│                   ┌─────────────┐                       │
│                   │ PCSCConnection│                      │
│                   │  (PC/SC)     │                       │
│                   └──────┬──────┘                       │
└──────────────────────────┼──────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ Smart Card  │
                    └─────────────┘
```

### Middleware Plugins (CardPlugin)

A middleware plugin is a shared library (`.so` / `.dylib`) loaded by `CardPluginRegistry` via `dlopen` at runtime. Each plugin implements two key methods:

- **`probe(PCSCConnection&)`** — detect whether the inserted card is supported by this plugin. Typically sends SELECT commands for known AIDs and returns a confidence score. The registry calls `probe()` on every registered plugin and builds a ranked candidate list.
- **`readCard(PCSCConnection&)`** — extract all data from the card. Sends APDU commands, parses TLV/BER-TLV responses, and returns a `CardData` object containing typed field groups (personal data, document data, photos, certificates).

**Fallback chain:** If the top-ranked plugin's `readCard()` fails, the next candidate is tried automatically. The OpenSC plugin serves as a generic fallback — it delegates PKI operations (certificates, signing) to OpenSC for any card it doesn't natively support.

**To add a new card type:** Write a class that inherits `CardPlugin`, implement `probe()` and `readCard()`, build as a shared library, and drop it into the plugin directory. The registry discovers it automatically at next startup.

### GUI Plugins (CardWidgetPlugin)

A GUI plugin is a Qt shared library loaded by `CardWidgetPluginRegistry` via `QPluginLoader`. Each plugin implements:

- **`cardTypes()`** — returns a list of card type strings this plugin can display (must match what the middleware plugin sets in `CardData`).
- **`createWidget(CardData)`** — builds and returns a Qt widget that renders the card data. Full control over layout — text fields, photos, certificates, whatever the card contains.

**To add a new card display:** Write a class that inherits `CardWidgetPlugin` and `Q_PLUGIN_METADATA`, implement `cardTypes()` and `createWidget()`, build as a Qt MODULE library.

### How They Connect

Adding support for a completely new card type requires two plugins:

1. **Middleware plugin** — knows how to talk to the card (SELECT, READ BINARY, parse response)
2. **GUI plugin** — knows how to display the data (layout, labels, formatting)

The bridge is `CardData` — a map of field groups, where each group contains key-value pairs. The middleware plugin populates it, the GUI plugin reads it. Neither needs to know about the other. No recompilation of the core application is needed — just drop in the `.so` files.

---

## Data Flow

The complete flow when a smart card is inserted:

```
1. Card inserted into reader

2. SmartCardScanner (PC/SC polling thread)
   └─ SCardGetStatusChange detects card presence
   └─ emits cardInserted signal via SmartCardReaderListener

3. Main window receives signal, starts plugin discovery:
   └─ CardPluginRegistry::findAllCandidates(connection)
      ├─ eidcard-plugin::probe()     → score: 100 (recognized AID)
      ├─ vehicle-plugin::probe()     → score: 0 (wrong AID)
      ├─ emrtd-plugin::probe()       → score: 0 (no eMRTD applet)
      └─ opensc-plugin::probe()      → score: 50 (found PKCS#15)
      Result: [eidcard-plugin (100), opensc-plugin (50)]

4. AsyncCardReader::requestData(topCandidate)
   └─ std::async → background thread
   └─ eidcard-plugin::readCard(connection)
      ├─ SELECT AID, READ BINARY personal data
      ├─ parse BER-TLV response
      └─ return CardData { type: "rs.eid", fields: {...} }

5. Result marshalled back to Qt main thread (QMetaObject::invokeMethod)

6. CardWidgetPluginRegistry::findByCardType("rs.eid")
   └─ rseid-gui-plugin matches

7. rseid-gui-plugin::createWidget(cardData)
   └─ builds widget: photo, name, address, document number, certificates

8. Widget displayed in main window
```

---

## Design Patterns

### Strategy

`CardReaderBase` defines the interface for communicating with a specific card reader chip. Concrete implementations — `CardReaderApollo` (Apollo 2008 chips) and `CardReaderGemalto` (Gemalto 2014+ chips) — encapsulate the differences in APDU sequences and file structures.

### Async

`AsyncCardReader` wraps middleware plugin calls with `std::async` to keep the GUI responsive. Results are marshalled back to the Qt main thread via `QMetaObject::invokeMethod` and Qt signals.

### Observer

Qt signals and slots propagate smart card events from the `SmartCardScanner` (polling thread) through `SmartCardReaderListener` (singleton) to the main window and any registered listeners.

### Singleton

`SmartCardReaderListener::instance()` provides a single dispatch point for card insert/remove events across the application.

---

## Namespaces

| Namespace | Scope |
|---|---|
| `plugin::` | Plugin system types — CardData, CardPlugin, CertificateData, CardPluginRegistry |
| `eidcard::` | EIdCard library types and API |
| `vehiclecard::` | VehicleCard library types and API |
| `smartcard::` | SmartCard library — APDU, TLV, BER, PCSCConnection |
| `LibreSCRS::` | GUI application types |

---

## Standards

The following standards are relevant to the codebase:

| Standard | Usage |
|---|---|
| ISO 7816-4 | Smart card communication — APDU command/response structure, TLV and BER-TLV encoding |
| PC/SC | Reader access layer — card detection, connection management, transaction control |
| PKCS#11 | Cryptographic token interface — browser authentication, digital signatures |
| PKCS#15 | Cryptographic information application — certificate and key discovery on smart cards |
| ICAO 9303 | eMRTD (e-passports) — BAC and PACE key agreement, Secure Messaging, data group structure |
