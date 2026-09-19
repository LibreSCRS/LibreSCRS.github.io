---
title: "Features"
layout: "simple"
description: "Supported smart cards and capabilities"
---

## Supported Cards

**Full PKI through OpenSC.** OpenSC is the PKI engine. It works with every card OpenSC supports — the Serbian CardEdge cards (eID, qualified-signature/PKS, health) via the `srbeid` driver, plus IAS-ECC, CardOS, PIV, OpenPGP and more. Where OpenSC does not cover something, a built-in PKCS#15 plugin fills the gap (for example, on-card SHA-256 signing on the NAM card).

**Card data through plugins.** Built-in plugins read the document data: Serbian eID, Serbian health insurance, EU vehicle registration, and electronic passports (eMRTD, with PACE/BAC).

---

## Capabilities

- **Automatic card detection** — insert a card, LibreCelik identifies it and shows the data. No manual selection needed.
- **CSCA trust verification** — an electronic passport's chip data is checked against a locally imported CSCA master list, not just parsed. The import takes the directory export the ICAO Public Key Directory actually publishes, verifies every list in it against its own country's signer, and installs the union of what survived.
- **Progressive reading** — data appears as it is read from the card. No waiting for the full read to finish.
- **Print** — card data views support formatted printout.
- **Multi-PIN management** — cards with multiple PINs (e.g., separate authentication and signing PINs) show each PIN's status and allow independent change.
- **Plugin architecture** — add support for new card types by dropping in a shared library. Both middleware (card communication) and GUI (data display) are extensible.
- **Multilingual** — English and Serbian (Cyrillic) interface.
- **PKCS#11 module** — universal cryptographic token interface supporting OpenSC-backed PKI cards (Serbian eID/PKS, generic PKCS#15). Use in Firefox, Chrome, SSH, and email signing. From 5.0 the registered provider is the card agent's client module, so the PIN is collected by a separate prompter and never enters the browser's address space.
- **OpenSC integration** — the Serbian CardEdge driver is merged into OpenSC mainline.

---

## For Developers

LibreMiddleware is a set of C++23 libraries (static or shared build, with a CMake Config package) with no Qt dependency. Use them to build your own smart card application. LibreAgent is published as a library in its own right from 5.0, so a client of the card broker need not link the middleware at all.

- Plugin API for adding new card types
- Streaming card read API
- SmartCard Monitor for event-driven card detection
- Secure Messaging, PACE, BAC implementations
- **Card agent architecture** — one broker owns the card and its secrets; every client (LibreCelik, LibreKDE, standard PKCS#11 applications) is a thin client of it. See [Architecture](/developer-guide/architecture/).

See the [Developer Guide](/developer-guide/) for architecture details and build instructions.
