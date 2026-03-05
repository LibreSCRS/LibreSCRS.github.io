---
title: "LibreSCRS"
description: "Open-source software for Serbian government smart cards"
---

**LibreSCRS** is an open-source project providing free, transparent software for Serbian government smart cards — eID, vehicle registration, health insurance, and PKS Chamber of Commerce cards.

No proprietary middleware, no closed-source DLLs. Direct PCSC communication under a GPL/LGPL licence.

---

## Projects

### LibreCelik

A desktop application for reading and printing Serbian smart cards:

- **eID** — personal identity, document, and digital signature certificates
- **Vehicle registration** — all fields from the vehicle registration document
- **Health insurance card** — insured person and coverage data
- **PKS card** — Chamber of Commerce qualified signature certificates

[Download LibreCelik]({{< ref "downloads" >}}) · [Docs]({{< ref "docs/librecelik" >}})

---

### LibreMiddleware (PKCS#11 / OpenSC)

A PKCS#11 module and OpenSC external card driver for deep browser and OS integration:

- **PKCS#11** — load directly in Firefox, Chrome, Thunderbird, OpenSSH
- **OpenSC driver** — transparent PKCS#15 emulation via OpenSC's card driver API

[Download PKCS#11 module]({{< ref "downloads" >}}) · [Docs]({{< ref "docs/pkcs11" >}})

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
