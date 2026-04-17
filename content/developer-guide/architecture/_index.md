---
layout: "simple"
title: "Architecture Overview"
description: "System components, data flow, plugin architecture, and design patterns"
---

LibreSCRS consists of two main projects that work together to read, process, and display smart card data.

## Components

### LibreMiddleware (LGPL-2.1)

A Qt-free C++20 static library collection for smart card communication. It handles everything from low-level APDU command/response exchanges to high-level card data extraction. **All PC/SC communication lives exclusively in LibreMiddleware** — LibreCelik has no direct dependency on PC/SC.

| Library | Purpose |
|---|---|
| `smartcard` | PCSCConnection, Monitor (card event polling), APDU command/response, TLV and BER-TLV parsing (ISO 7816-4), TransmitFilter (transparent Secure Messaging layer) |
| `plugin` | CardPlugin interface (with streaming support), CardData model, CardPluginRegistry (dlopen), AutoReader (Monitor + plugin discovery bridge) |
| `pkcs15` | Generic PKCS#15/ISO 7816-15 parser and card library — EF.ODF/EF.DIR discovery, certificate and key enumeration. Works with any PKCS#15-compliant card |
| `rs-eid` | Serbian eID card API with card reader implementations (Apollo 2008, Gemalto 2014+, Foreigner IF2020) |
| `eu-vrc` | EU Vehicle Registration Certificate (Directive 2003/127/EC) |
| `rs-health` | Serbian health insurance card (RFZO) |
| `cardedge` | CardEdge PKI applet for Serbian smart cards — certificates, PIN management, digital signing |
| `emrtd` | eMRTD e-passport communication — data group reading, MRZ parsing |
| `emrtd-crypto` | eMRTD cryptography — BAC, PACE (ECDH-GM), Secure Messaging |
| `piv` | PIV card communication (NIST SP 800-73) |
| `pkcs11` | PKCS#11 shared library (`librescrs-pkcs11`) — supports all card types |
| `*-plugin` | Card plugins (`.so`): rs-eid, rs-health, eu-vrc, emrtd, piv, pkcs15, cardedge, opensc |

### LibreCelik (GPL-3.0)

A Qt6 desktop GUI application that displays card data. It is a **pure presentation layer** — no PC/SC, no APDU, no card protocol knowledge. It receives `CardData` from middleware plugins and renders it through GUI plugins.

| Module | Purpose |
|---|---|
| `smartcard` | SmartCardReaderListener — Qt adapter wrapping middleware `smartcard::Monitor` |
| `plugin` | CardWidgetPlugin interface and CardWidgetPluginRegistry (QPluginLoader) |
| `asynccardreader` | Generic async card reader using middleware CardPlugin fallback chain |
| `document` | Shared PKI UI (TokenSection), PIN change dialog, printing |
| `certificate` | X.509 certificate viewer (tree model + dialog) |
| `plugins/` | GUI plugins (rs-eid, rs-health, eu-vrc, emrtd, piv, token) as Qt MODULE `.so` files |

LibreCelik fetches LibreMiddleware via CMake `FetchContent`. For local development, you can point it to a local checkout instead.

---

## Plugin Architecture

The entire system is built around plugins. There are two independent plugin layers — **middleware plugins** handle card communication, **GUI plugins** handle display. They connect through `CardData`, a universal data model that any middleware plugin produces and any GUI plugin consumes.

```
┌─────────────────────────────────────────────────────────┐
│                      LibreCelik (GUI)                   │
│                                                         │
│  ┌──────────────────────┐ ┌────────────────────────┐    │
│  │SmartCardReaderListener│ │ CardWidgetPluginRegistry│    │
│  │(Qt adapter for Monitor│ │ (QPluginLoader)        │    │
│  └──────────────────────┘ └──────────┬─────────────┘    │
│           ▲                          │ loads             │
│           │ wraps             ┌──────▼──────────────┐   │
│           │                   │  GUI Plugins (.so)   │   │
│           │                   │ ┌──────┐ ┌────────┐ │   │
│           │                   │ │rs-eid│ │eu-vrc  │ │   │
│           │                   │ ├──────┤ ├────────┤ │   │
│           │                   │ │rs-   │ │ emrtd  │ │   │
│           │                   │ │health│ ├────────┤ │   │
│           │                   │ ├──────┤ │  piv   │ │   │
│           │                   │ │token │ └────────┘ │   │
│           │                   │ └──────┘            │   │
│           │                   └─────────────────────┘   │
│           │                          ▲                  │
│           │                          │ CardData         │
├───────────┼──────────────────────────┼──────────────────┤
│           │           LibreMiddleware│                   │
│           │                          │                  │
│  ┌────────┴─────────┐ ┌─────────────┴──────────┐       │
│  │ smartcard::Monitor│ │ CardPluginRegistry     │       │
│  │ (PC/SC polling)  │ │ (dlopen)               │       │
│  └──────────────────┘ └──────────┬─────────────┘       │
│                                  │ loads                │
│  ┌───────────────────────────────▼─────────────────┐   │
│  │           Middleware Plugins (.so)                │   │
│  │ ┌─────────┐ ┌──────────┐ ┌───────────────────┐ │   │
│  │ │ rs-eid  │ │  emrtd   │ │     opensc         │ │   │
│  │ ├─────────┤ ├──────────┤ │ (PKI fallback)     │ │   │
│  │ │ eu-vrc  │ │ cardedge │ └───────────────────┘ │   │
│  │ ├─────────┤ ├──────────┤ ┌───────────────────┐ │   │
│  │ │rs-health│ │   piv    │ │     pkcs15         │ │   │
│  │ └─────────┘ └──────────┘ └───────────────────┘ │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                             │
│                          │ APDU (ISO 7816-4)           │
│                          ▼                             │
│                   ┌──────────────┐                     │
│                   │PCSCConnection│                     │
│                   │  (PC/SC)     │                     │
│                   └──────┬──────┘                      │
└──────────────────────────┼─────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ Smart Card  │
                    └─────────────┘
```

### Card Detection: smartcard::Monitor

Card detection lives in LibreMiddleware as `smartcard::Monitor` — a pure C++20 class with no Qt dependency. It polls PC/SC for card insert/remove events on a background thread and notifies subscribers via callbacks:

- **`subscribe(MonitorCallback)`** — register for `MonitorEvent` notifications (card inserted/removed, reader name, ATR)
- **`unsubscribe(id)`** — stop receiving events

The monitor lazy-starts its polling thread on the first subscription and stops when the last subscriber unsubscribes. In LibreCelik, `SmartCardReaderListener` wraps the monitor and marshals events to the Qt main thread via signals.

### Middleware Plugins (CardPlugin)

A middleware plugin is a shared library (`.so` / `.dylib`) loaded by `CardPluginRegistry` via `dlopen` at runtime. Each plugin implements:

- **`canHandle(const std::vector<uint8_t>& atr)`** — fast ATR-only check. Returns `bool` — does this plugin recognize the ATR? No card communication needed. Plugins also expose `probePriority()` (an `int`) so the registry can rank candidates.
- **`canHandleConnection(PCSCConnection& conn)`** — live connection probe. Sends SELECT commands for known AIDs to confirm card support. Called only on plugins that did **not** match in `canHandle()` — giving them a second chance to claim the card via live communication.
- **`readCard(PCSCConnection& conn)`** — extract all data from the card. Sends APDU commands, parses TLV/BER-TLV responses, and returns a `CardData` object containing typed field groups (personal data, document data, photos, certificates).

**Two-phase probe:** The registry first calls `canHandle(atr)` on all plugins — those that return `true` go into the candidate list immediately, ranked by `probePriority()`. Then `canHandleConnection(conn)` is called only on plugins that returned `false` in Phase 1, giving generic plugins (like OpenSC) a chance to claim the card by probing the live connection. This avoids unnecessary card communication for plugins that already matched by ATR.

**Streaming support:** Plugins can implement `readCardStreaming()` in addition to `readCard()`. Streaming delivers `CardData` incrementally — fields appear in the GUI as they are read from the card, rather than waiting for the entire read to complete. This is especially useful for eMRTD where data groups are read sequentially through encrypted channels.

**Fallback chain:** If the top-ranked plugin's `readCard()` fails, the next candidate is tried automatically. The OpenSC plugin serves as a generic fallback for any card it doesn't natively support.

**PKI fallback:** Data plugins (eID, vehicle, health) read demographic data but do not handle PKI operations. After a data plugin finishes, the system can trigger a separate PKI plugin (CardEdge, PKCS#15, or OpenSC) to provide certificate discovery, signing, and PIN management. This decoupling means data plugins don't need to know about PKI.

**To add a new card type:** Write a class that inherits `CardPlugin`, implement `canHandle()`, `canHandleConnection()`, and `readCard()` (optionally `readCardStreaming()`), build as a shared library, and drop it into the plugin directory. The registry discovers it automatically at next startup.

### GUI Plugins (CardWidgetPlugin)

A GUI plugin is a Qt shared library loaded by `CardWidgetPluginRegistry` via `QPluginLoader`. Each plugin implements:

- **`cardType()`** — returns the card type string this plugin can display (must match what the middleware plugin sets in `CardData`).
- **`createWidget(const CardData&, QWidget* parent)`** — builds and returns a Qt widget that renders the card data. Full control over layout — text fields, photos, certificates, whatever the card contains.

**To add a new card display:** Write a class that inherits `CardWidgetPlugin` and `Q_PLUGIN_METADATA`, implement `cardType()` and `createWidget()`, build as a Qt MODULE library.

### How They Connect

Adding support for a completely new card type requires two plugins:

1. **Middleware plugin** — knows how to talk to the card (SELECT, READ BINARY, parse response)
2. **GUI plugin** — knows how to display the data (layout, labels, formatting)

The bridge is `CardData` — a map of field groups, where each group contains key-value pairs. The middleware plugin populates it, the GUI plugin reads it. Neither needs to know about the other. No recompilation of the core application is needed — just drop in the `.so` files.

### eMRTD: Cryptographic Card Access

The eMRTD plugin demonstrates the most complex card communication in the system. E-passports require cryptographic key agreement before any data can be read:

- **BAC** (Basic Access Control) — derives session keys from the Machine Readable Zone (MRZ) printed on the passport
- **PACE** (Password Authenticated Connection Establishment) — elliptic curve Diffie-Hellman key agreement, the modern replacement for BAC. May require the user to enter the CAN (Card Access Number) printed on the passport.
- **Secure Messaging** — all subsequent APDU commands and responses are encrypted and MACed with session keys. Implemented as a `TransmitFilter` on `PCSCConnection` — once installed, encryption is transparent to all higher-level code.

The `emrtd-crypto` library implements these protocols from the ICAO 9303 specification, while the `emrtd` library handles data group reading and MRZ parsing. The `emrtd-plugin` ties them together as a standard `CardPlugin` with streaming support — data groups are read progressively and delivered to the GUI as they become available. From the rest of the system's perspective, it's just another plugin that returns `CardData`.

---

## Data Flow

The complete flow when a smart card is inserted:

```
1. Card inserted into reader

2. smartcard::Monitor (LibreMiddleware, PC/SC polling thread)
   └─ SCardGetStatusChange detects card presence
   └─ creates MonitorEvent { CardInserted, readerName, atr }
   └─ notifies subscribers via callback

3. SmartCardReaderListener (LibreCelik, Qt adapter)
   └─ receives MonitorEvent on monitor thread
   └─ marshals to Qt main thread via QMetaObject::invokeMethod
   └─ emits signal with MonitorEvent

4. Main window receives signal, starts two-phase plugin discovery:
   Phase 1 — ATR filtering (no card communication):
   └─ CardPluginRegistry::findAllCandidates(atr, connection)
      ├─ eidcard-plugin::canHandle(atr)     → true  (recognized Serbian eID ATR)
      ├─ vehicle-plugin::canHandle(atr)     → false
      ├─ emrtd-plugin::canHandle(atr)       → false
      └─ opensc-plugin::canHandle(atr)      → false
      Candidates so far: [eidcard-plugin (priority 100)]
   Phase 2 — connection probe (only on plugins that returned false):
      ├─ vehicle-plugin::canHandleConnection(conn)  → false
      ├─ emrtd-plugin::canHandleConnection(conn)    → false
      └─ opensc-plugin::canHandleConnection(conn)   → true (found PKCS#15)
      Final candidates: [eidcard-plugin (100), opensc-plugin (50)]

5. AsyncCardReader::requestData(topCandidate)
   └─ std::async → background thread
   └─ eidcard-plugin::readCard(connection)
      ├─ SELECT AID, READ BINARY personal data
      ├─ parse BER-TLV response
      └─ return CardData { type: "rs.eid", fields: {...} }

6. Result marshalled back to Qt main thread (QMetaObject::invokeMethod)

7. CardWidgetPluginRegistry::findByCardType("rs.eid")
   └─ rseid-gui-plugin matches

8. rseid-gui-plugin::createWidget(cardData, parent)
   └─ builds widget: photo, name, address, document number, certificates

9. Widget displayed in main window
```

---

## Design Patterns

### Strategy

`CardReaderBase` defines the interface for communicating with a specific card reader chip. Concrete implementations — `CardReaderApollo` (Apollo 2008 chips) and `CardReaderGemalto` (Gemalto 2014+ chips) — encapsulate the differences in APDU sequences and file structures.

### Async

`AsyncCardReader` wraps middleware plugin calls with `std::async` to keep the GUI responsive. Results are marshalled back to the Qt main thread via `QMetaObject::invokeMethod` and Qt signals. Supports both batch (`readCard`) and streaming (`readCardStreaming`) modes. In the middleware layer, `AutoReader` provides a convenience wrapper that bridges `smartcard::Monitor` events directly to `CardPluginRegistry` discovery and card reading — useful for applications that want automatic card handling without manual wiring.

### Observer

`smartcard::Monitor` uses a callback-based subscription model in the middleware layer. In the GUI layer, `SmartCardReaderListener` wraps the monitor and re-emits events as Qt signals, propagating card insert/remove events to the main window and any registered listeners.

### Singleton

`SmartCardReaderListener::instance()` provides a single dispatch point for card events across the GUI application.

---

## Namespaces

| Namespace | Scope |
|---|---|
| `smartcard::` | SmartCard library — APDU, TLV, BER, PCSCConnection, Monitor |
| `plugin::` | Plugin system types — CardData, CardPlugin, CertificateData, CardPluginRegistry |
| `eidcard::` | Serbian eID library types and API |
| `euvrc::` | EU Vehicle Registration Certificate types and API |
| `healthcard::` | Serbian health insurance card types |
| `cardedge::` | CardEdge PKI applet — certificates, PIN, signing |
| `emrtd::` | eMRTD data structures and MRZ parsing |
| `emrtd::crypto` | eMRTD cryptography — BAC, PACE, Secure Messaging |
| `piv::` | PIV card types and API |
| `pkcs15::` | PKCS#15 parser types |
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
| NIST SP 800-73 | PIV card interface — certificate discovery, authentication, digital signing |
| BSI TR-03110 | PACE protocol — password-authenticated key agreement for eMRTD |
