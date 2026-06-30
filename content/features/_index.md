---
title: "Features"
layout: "simple"
description: "Supported smart cards and capabilities"
---

## Supported Cards

**Full PKI through OpenSC.** OpenSC is the PKI engine. It works with every card OpenSC supports — the Serbian CardEdge cards (eID, qualified-signature/PKS, health) via the `srbeid` driver, plus IAS-ECC, CardOS, PIV, OpenPGP and more. Where OpenSC does not cover something, a built-in PKCS#15 plugin fills the gap (for example, on-card SHA-256 signing on the NAM card).

**Card data through plugins.** Built-in plugins read the document data: Serbian eID, Serbian health insurance, EU vehicle registration, and electronic passports (eMRTD).

---

## Capabilities

- **Automatic card detection** — insert a card, LibreCelik identifies it and shows the data. No manual selection needed.
- **Progressive reading** — data appears as it is read from the card. No waiting for the full read to finish.
- **Print** — card data views support formatted printout.
- **Multi-PIN management** — cards with multiple PINs (e.g., separate authentication and signing PINs) show each PIN's status and allow independent change.
- **Plugin architecture** — add support for new card types by dropping in a shared library. Both middleware (card communication) and GUI (data display) are extensible.
- **Multilingual** — English and Serbian (Cyrillic) interface.
- **PKCS#11 module** — universal cryptographic token interface supporting OpenSC-backed PKI cards (Serbian eID/PKS, generic PKCS#15). Use in Firefox, Chrome, SSH, and email signing.
- **OpenSC integration** — Serbian CardEdge driver merged into OpenSC mainline. External driver available for current OpenSC releases.

---

## For Developers

LibreMiddleware is a set of C++23 libraries (static or shared build, with CMake Config package and p11-kit auto-registration) with no Qt dependency. Use them to build your own smart card application.

- Plugin API for adding new card types
- Streaming card read API
- SmartCard Monitor for event-driven card detection
- Secure Messaging, PACE, BAC implementations

See the [Developer Guide](/developer-guide/) for architecture details and build instructions.
