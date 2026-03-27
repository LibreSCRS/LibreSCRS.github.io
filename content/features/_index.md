---
title: "Features"
layout: "simple"
description: "Supported smart cards and capabilities"
---

## Supported Cards

### Serbian eID

Apollo 2008, Gemalto 2014+, IF2020 Foreigner. Personal data, address, document info, photo. Gemalto and IF2020 support digital signature certificates and PIN management.

### Serbian Vehicle Registration (EU VRC)

EU Directive 2003/127/EC compliant. Owner, vehicle data, registration dates — all EU mandatory and optional fields. Print support.

### Serbian Health Insurance (RFZO)

Insured person, employer, insurance details.

### eMRTD / ePassport

PACE and BAC authentication, Secure Messaging, biometric data (photo, MRZ), data groups. Passive Authentication, Chip Authentication, and Active Authentication for document authenticity verification.

### PIV (NIST SP 800-73)

US federal ID standard. Certificates, photo, fingerprints, PIN management.

### PKCS#15 Compatible Cards

Gemalto, CardEdge, and other generic PKI cards. Certificate discovery, PIN verification and change, multi-PIN support.

---

## Capabilities

- **Automatic card detection** — insert a card, LibreCelik identifies it and shows the data. No manual selection needed.
- **Progressive reading** — data appears as it is read from the card. No waiting for the full read to finish.
- **Print** — card data views support formatted printout.
- **Multi-PIN management** — cards with multiple PINs (e.g., separate authentication and signing PINs) show each PIN's status and allow independent change.
- **Plugin architecture** — add support for new card types by dropping in a shared library. Both middleware (card communication) and GUI (data display) are extensible.
- **Multilingual** — English and Serbian (Cyrillic) interface.
- **PKCS#11 module** — for CardEdge cards: use in Firefox, Chrome, SSH, and email signing. Installed separately.
- **OpenSC external driver** — for CardEdge cards: extends OpenSC for cards it doesn't natively support. Submitted upstream (PR #3595, approved — merge pending).

---

## For Developers

LibreMiddleware is a set of C++20 static libraries with no Qt dependency. Use them to build your own smart card application.

- Plugin API for adding new card types
- Streaming card read API
- SmartCard Monitor for event-driven card detection
- Secure Messaging, PACE, BAC implementations

See the [Developer Guide](/developer-guide/) for architecture details and build instructions.
