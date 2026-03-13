---
title: ""
description: "Open-source software for Serbian government smart cards"
---

## Liberate Your Smart Cards

Read, sign, and authenticate with Serbian government smart cards on Linux and macOS. No proprietary middleware, no closed-source binaries.

{{< button href="/downloads/" >}}Downloads{{< /button >}} [Documentation](/docs/)

---

## Why LibreSCRS?

Serbian government smart cards — eID, vehicle registration, health insurance, PKS — come with official software that only works on Windows and cannot be audited. LibreSCRS changes that:

- **Open source** — all code is published under GPL/LGPL licences
- **Cross-platform** — works on Linux and macOS
- **Auditable** — no proprietary middleware, no closed-source binaries
- **Standards-based** — built on PC/SC, PKCS#11, and PKCS#15

---

## Which package do I need?

### Just want to read your card?

**Download LibreCelik.** It reads and displays all data from your eID, vehicle registration, health insurance, and PKS cards. No setup needed — just plug in your card reader.

{{< button href="/downloads/" >}}Download LibreCelik{{< /button >}} [Docs](/docs/librecelik/)

### Need browser authentication or digital signatures?

**Use OpenSC.** A built-in Serbian card driver has been contributed to OpenSC and is pending inclusion in the next release. Once available, install OpenSC directly — no extra drivers needed.

In the meantime, you can use the **LibreSCRS PKCS#11 module** for Firefox authentication (e.g. eUprava login) and digital signing.

{{< button href="/downloads/" >}}Download PKCS#11 module{{< /button >}} [Docs](/docs/pkcs11/)

---

## Supported cards

| Card | Type |
|------|------|
| Serbian eID — Gemalto (2014+) | Personal identity |
| Serbian eID — IF2020 Foreigner | Residence permit |
| Vehicle registration document | Vehicle data |
| Health insurance card (RFZO) | Health coverage |
| PKS Chamber of Commerce card | Qualified signature |

## Licence

- **LibreCelik**: GPL-3.0-or-later
- **LibreMiddleware**: LGPL-2.1-or-later
