---
title: "About"
layout: "simple"
---

LibreSCRS started as a reverse-engineering effort to liberate Serbian government smart cards from Windows-only proprietary software. Through protocol analysis and AI-assisted development, we built open-source tools that now support any smart card — from national eIDs to vehicle registration documents and eMRTD e-passports.

---

## Timeline

1. **Mid 2025** — Project begins: LibreCelik, GUI reader for Serbian eID and vehicle cards
2. **Early 2026** — LibreMiddleware extracted as standalone C++20 library (no Qt dependency)
3. **Early 2026** — PKCS#11 module ships; OpenSC Serbian eID driver contributed upstream (PR #3595, approved)
4. **Early 2026** — Plugin architecture: both middleware and GUI become card-agnostic
5. **2026** — eMRTD + PKCS#15 support: e-passports, any PKI card. Universal toolkit.

---

## The Story

It started with a Gemalto card and a hex editor. Serbian eID cards have no public protocol documentation — no spec sheets, no reference implementations, nothing. The only way in was to trace what the proprietary Windows software did over PC/SC, capture the APDU sequences, and figure out what each byte meant. SELECT this AID, READ BINARY at that offset, parse the TLV structure that comes back. The first time citizen data appeared from raw bytes on a Linux terminal — name, address, photo — decoded from a protocol nobody had documented — that was the moment the project became real.

Each new card type brought its own puzzles. Vehicle registration cards used a different file structure. Health insurance cards had their own quirks. PKS qualified signature cards from the Chamber of Commerce shared the same CardEdge PKI applet for cryptographic operations but wrapped demographic data in entirely different formats. Every card meant more APDU tracing, more hex dump analysis, more iterative testing against real hardware until the protocol clicked into place.

As the codebase grew, it became clear that the card communication logic needed to stand on its own. LibreMiddleware was extracted as a pure C++20 library — no Qt, no GUI dependencies — just smart card protocols, TLV parsing, and a clean API. This made it possible to build a PKCS#11 module that lets any application (Firefox, Chrome, OpenSSL CLI) use Serbian smart cards for authentication and digital signatures without the GUI.

Then came the plugin architecture revolution. Instead of hardcoding support for specific cards, both the middleware and the GUI became extensible. CardPluginRegistry discovers card handlers at runtime via dlopen; CardWidgetPluginRegistry loads GUI plugins via QPluginLoader. Add a new card type by dropping in a shared library — no recompilation needed. The system went from "Serbian card reader" to "smart card toolkit."

The latest frontier is eMRTD e-passports and PKCS#15 generic card support. Implementing BAC and PACE key agreement from the ICAO 9303 specification meant real cryptography — Diffie-Hellman over elliptic curves, key derivation functions, Secure Messaging with session keys. PKCS#15 adds the ability to discover and use certificates and keys on any compliant card. From one country's cards to a universal toolkit — built by reading hex dumps and writing parsers, one APDU at a time.

---

## OpenSC

LibreSCRS is designed to complement OpenSC. For cards without a native LibreMiddleware plugin, it can fall back to OpenSC for PKI operations (certificate discovery, authentication, signing) while providing its own GUI and demographic data reading. Native plugins always take priority when available.

---

## AI-Assisted Development

This project was built with AI as a development partner — from analyzing hex dumps of unknown APDU responses to generating TLV parsers and validating PACE cryptography implementations. Every line was verified against real hardware.

---

## Projects

| Project | Description | License |
|---|---|---|
| LibreCelik | Qt6 desktop GUI smart card reader | GPL-3.0 |
| LibreMiddleware | C++20 smart card middleware libraries | LGPL-2.1 |

---

## Contributing

Bug reports, pull requests, and protocol analysis contributions are welcome on GitHub.

- [LibreCelik issues](https://github.com/LibreSCRS/LibreCelik/issues)
- [LibreMiddleware issues](https://github.com/LibreSCRS/LibreMiddleware/issues)

---

## Supporting the Project

LibreSCRS is developed and maintained in spare time. If these tools are useful to you — whether you use them to read your own cards, integrate smart card support into your application, or simply believe open-source infrastructure matters — please consider sponsoring the project.

[Become a sponsor on GitHub](https://github.com/sponsors/LibreSCRS)
