---
title: ""
description: "Open-source software for Serbian government smart cards"
---

## Projects

### LibreCelik

A desktop application for reading and printing Serbian smart cards:

- **eID** — personal identity, document, and digital signature certificates
- **Vehicle registration** — all fields from the vehicle registration document
- **Health insurance card** — insured person and coverage data
- **PKS card** — Chamber of Commerce qualified signature certificates

{{< button href="/downloads/" >}}Download LibreCelik{{< /button >}} [Docs](/docs/librecelik/)

---

### LibreMiddleware (PKCS#11 / OpenSC)

A PKCS#11 module and OpenSC external card driver for browser and OS integration:

- **PKCS#11** — load directly in Firefox, Chrome, Thunderbird, OpenSSH
- **OpenSC driver** — transparent PKCS#15 emulation via OpenSC's card driver API

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
