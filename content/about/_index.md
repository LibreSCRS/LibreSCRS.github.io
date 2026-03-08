---
title: "About"
description: "About the LibreSCRS project"
layout: "simple"
---

## What is LibreSCRS?

LibreSCRS is an open-source initiative to provide free, auditable software for Serbian government smart cards.

Serbian citizens carry multiple government-issued smart cards — eID, vehicle registration, health insurance, and other cards. The official software for these cards has historically been closed-source, Windows-only, and difficult to audit.

LibreSCRS reverse-engineered the card protocols through direct PC/SC APDU communication and published the results as open-source software under GPL/LGPL licences.

---

## Development

LibreSCRS was developed by reverse-engineering the smart card protocols used on Serbian government cards. No official documentation or specifications were available — the entire protocol stack was reconstructed through systematic APDU tracing, behavioral analysis of the CardEdge PKI applet, and iterative testing on real hardware.

AI tooling assisted throughout the development process, from analyzing captured APDU traces and identifying protocol patterns to implementing and refactoring the driver code. Every result was validated against physical cards to ensure correctness.

The project supports the Gemalto (2014+) Serbian eID, IF2020 Foreigner eID, PKS Chamber of Commerce qualified signature cards, and health insurance cards — each with distinct protocol variations discovered through this process.

---

## Projects

| Project | Description | Licence |
|---------|-------------|---------|
| [LibreCelik](https://github.com/LibreSCRS/LibreCelik) | Desktop app (Linux, macOS) | GPL-3.0-or-later |
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
