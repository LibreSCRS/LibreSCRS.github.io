---
title: "About"
layout: "simple"
---

LibreSCRS started as a reverse-engineering effort to liberate Serbian government smart cards from Windows-only proprietary software. Through protocol analysis and AI-assisted development, we built open-source tools that now support a wide range of smart cards (national eIDs, PIV, eMRTD passports, vehicle registration, PKCS#15 PKI cards).

---

## Timeline

1. **Mid 2025** — Project begins: LibreCelik, GUI reader for Serbian eID and vehicle cards
2. **Early 2026** — LibreMiddleware extracted as standalone Qt-free library (no Qt dependency)
3. **Early 2026** — PKCS#11 module ships; OpenSC Serbian eID driver contributed upstream (PR #3595, merged)
4. **Early 2026** — Plugin architecture: both middleware and GUI become card-agnostic
5. **2026** — eMRTD, PKCS#15, and PIV support: e-passports, PKCS#15-based PKI cards, PIV smart cards. PKCS#11 module generalized across the supported card families.
6. **May 2026** — **4.0.0 release**: C++23 core, native PAdES / XAdES / JAdES / CAdES / ASiC-E signing, RFC 5280 trust chain validation, eIDAS qcStatements conformance, auto-fit visual signature layout.
7. **May 2026** — **4.1.0 release**: Card+Slot model fixing multi-card PIN routing, multi-PIN PKCS#11 dispatch, cross-plugin secure channels (PACE / BAC / plain), and in-process PKCS#11 session sharing.
8. **May 2026** — **4.2.0 release**: Qt-free reader-list snapshot API and CardData accessors, automatic in-process session sharing via the SessionPresence registry, AET SafeSign QSCD support, and a fail-closed bundled-license check.

---

## The Story

There was no native Linux application that could read all types of Serbian government smart cards. Existing open-source projects — JFreesteel (Java) and Bas Celik (Go) — proved that reading citizen data from eID cards was possible without proprietary software, but they focused on demographic data. Nobody had tackled the cryptographic side: the CardEdge PKI applet that handles certificates, digital signatures, and PIN management. LibreSCRS set out to cover both — data reading and full PKI support — across all Serbian card types, on Linux and macOS.

Serbian eID cards have no public protocol documentation. The approach was straightforward: trace what the proprietary Windows software does over PC/SC, capture the APDU sequences, and work out the protocol from there. Vehicle registration cards follow the EU Directive 2003/127/EC standard, so their structure was well-defined from the start. Health insurance cards have their own layout. PKS qualified signature cards from the Chamber of Commerce use CardEdge for cryptographic operations but carry no demographic data at all. Each card type meant testing against real hardware until the protocol was understood.

As the codebase grew, it became clear that the card communication logic needed to stand on its own. LibreMiddleware was extracted as a pure modern C++ library — no Qt, no GUI dependencies — just smart card protocols, TLV parsing, and a clean API. This made it possible to build a PKCS#11 module that lets any application (Firefox, Chrome, OpenSSL CLI) use any LM-supported smart card (Serbian eID, PKS, PIV, generic PKCS#15) for authentication and digital signatures without the GUI.

The next step was a plugin architecture. Instead of hardcoding support for specific cards, both the middleware and the GUI became extensible. CardPluginRegistry discovers card handlers at runtime via dlopen; CardWidgetPluginRegistry loads GUI plugins via QPluginLoader. Adding a new card type means dropping in a shared library — no recompilation needed.

Most recently, support was added for eMRTD e-passports and PKCS#15 generic cards. eMRTD required implementing BAC and PACE key agreement from the ICAO 9303 specification — Diffie-Hellman over elliptic curves, key derivation functions, and Secure Messaging with session keys. PKCS#15 adds the ability to discover and use certificates and keys on any compliant card.

---

## AI-Assisted Development

This project was built with AI as a development partner — from analyzing hex dumps of unknown APDU responses to generating TLV parsers and validating PACE cryptography implementations. Every line was verified against real hardware.

---

## Projects

| Project | Description | License |
|---|---|---|
| LibreCelik | Qt6 desktop GUI smart card reader | GPL-3.0 |
| LibreMiddleware | C++23 smart card middleware libraries | LGPL-2.1 |

---

## Related Projects

LibreSCRS is not the first open-source effort to liberate Serbian smart cards. We stand on the shoulders of those who came before:

- **[JFreesteel](https://github.com/grakic/jfreesteel)** — the pioneering open-source Serbian eID library by Goran Rakic (Java, 2015). JFreesteel proved it was possible to read Serbian eID cards without proprietary software and inspired others to follow.
- **[Bas Celik](https://github.com/ubavic/bas-celik)** — a actively maintained Go desktop reader for Serbian eID, vehicle, and health cards by Nikola Ubavic. A great alternative if you prefer a Go-based tool.

---

## Contributing

See the [Contribute](/contribute/) page for how to report bugs, submit pull requests, and add support for new card types.

---

## Supporting the Project

LibreSCRS is developed and maintained in spare time. If these tools are useful to you, please consider supporting the project.

[Donate via Open Source Collective](/donate/)
