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

## Data Flow

When a smart card is inserted, data flows through the system in the following sequence:

```
Card inserted into reader
  │
  ▼
SmartCardScanner (PC/SC polling thread)
  │  detects card presence via SCardGetStatusChange
  ▼
SmartCardReaderListener (singleton, Qt signals)
  │  emits cardInserted signal
  ▼
Main window receives signal
  │
  ▼
CardPluginRegistry::findAllCandidates()
  │  tries each middleware plugin's probe() in priority order
  │  returns list of plugins that recognize the card
  ▼
AsyncCardReader::requestData()
  │  wraps middleware call with std::async
  │  marshals result back to Qt main thread via signal
  ▼
CardPlugin::readCard() (middleware plugin)
  │  communicates with card via APDU commands
  │  parses response data (TLV, BER-TLV)
  │  returns CardData with extracted fields
  ▼
CardWidgetPluginRegistry::findByCardType()
  │  maps card type string to a GUI plugin
  ▼
CardWidgetPlugin::createWidget(CardData)
  │  builds Qt widget displaying the card data
  ▼
Widget displayed in main window
```

---

## Plugin Architecture

The system uses two independent plugin registries — one for card communication (middleware) and one for display (GUI).

### Middleware Plugins (CardPlugin)

Loaded by `CardPluginRegistry` via `dlopen` at runtime. Each plugin implements:

- **`probe()`** — detect whether the inserted card is supported by this plugin. Returns a confidence score. The registry tries plugins in priority order and builds a candidate list.
- **`readCard()`** — extract all data from the card. Returns a `CardData` object containing typed fields (text, images, dates, certificates).

The fallback chain means if the primary plugin fails, the next candidate is tried automatically. The OpenSC plugin serves as a generic fallback for any PKCS#15-compliant card.

### GUI Plugins (CardWidgetPlugin)

Loaded by `CardWidgetPluginRegistry` via `QPluginLoader`. Each plugin implements:

- **`cardTypes()`** — list of card type strings this plugin can display.
- **`createWidget(CardData)`** — build and return a Qt widget that renders the card data.

Adding support for a new card type means writing two shared libraries — a middleware plugin for card communication and a GUI plugin for display — and dropping them into the plugin directories. No recompilation of the core application is needed.

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
