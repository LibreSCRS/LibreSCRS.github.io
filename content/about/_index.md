---
title: "About"
description: "About the LibreSCRS project"
layout: "simple"
---

## What is LibreSCRS?

Serbian citizens carry multiple government-issued smart cards — eID, vehicle registration, and health insurance. Additionally, the Serbian Chamber of Commerce (PKS) issues qualified signature cards for businesses and individuals. The official software (Celik) is closed-source, Windows-only, and unavailable on Linux or macOS. There is no way to read your own card, authenticate to government services, or digitally sign documents on these platforms using the official tools.

LibreSCRS provides open-source, cross-platform alternatives. The card protocols were reverse-engineered through direct PC/SC APDU communication, and the results published under GPL/LGPL licences so anyone can read, audit, and improve the code.

---

## Development

LibreSCRS was developed by reverse-engineering the smart card protocols used on Serbian government cards. No official documentation or specifications were available — the entire protocol stack was reconstructed through systematic APDU tracing, behavioral analysis of the CardEdge PKI applet, and iterative testing on real hardware.

AI tooling assisted throughout the development process, from analyzing captured APDU traces and identifying protocol patterns to implementing and refactoring the code. Every result was validated against physical cards to ensure correctness.

A built-in Serbian card driver has been contributed to the [OpenSC](https://github.com/OpenSC/OpenSC) project and approved for inclusion. Once merged into the next OpenSC release, Serbian smart cards will work out of the box with any PKCS#11 application — no external drivers needed.

The project supports the Gemalto (2014+) Serbian eID, IF2020 Foreigner eID, health insurance cards, and PKS Chamber of Commerce qualified signature cards. All share the same CardEdge PKI applet for cryptographic operations, but differ in their demographic data formats.

---

## Projects

| Project | Description | Licence |
|---------|-------------|---------|
| [LibreCelik](https://github.com/LibreSCRS/LibreCelik) | Desktop app for reading smart cards (Linux, macOS) | GPL-3.0-or-later |
| [LibreMiddleware](https://github.com/LibreSCRS/LibreMiddleware) | PKCS#11 module + OpenSC driver | LGPL-2.1-or-later |

---

## Contributing

Bug reports, pull requests, and protocol analysis contributions are welcome on GitHub.

- [LibreCelik issues](https://github.com/LibreSCRS/LibreCelik/issues)
- [LibreMiddleware issues](https://github.com/LibreSCRS/LibreMiddleware/issues)

---

## Supporting the project

LibreSCRS is developed and maintained in spare time. If this software is useful to you, please consider sponsoring the project.

[Become a sponsor on GitHub](https://github.com/sponsors/LibreSCRS)
