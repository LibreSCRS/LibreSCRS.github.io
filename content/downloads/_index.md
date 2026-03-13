---
title: "Downloads"
description: "Download LibreCelik and LibreMiddleware packages"
layout: "simple"
---

All releases are published on GitHub. Choose the package for your platform.

---

## LibreCelik

Desktop application for reading and displaying Serbian smart cards — eID, vehicle registration, health insurance, and PKS cards.

| Platform | Package |
|----------|---------|
| Linux (x86_64) | `.AppImage` |
| macOS (Apple Silicon) | `.dmg` |

[LibreCelik releases on GitHub](https://github.com/LibreSCRS/LibreCelik/releases)

---

## LibreMiddleware — PKCS#11 module

> **Note:** Once OpenSC includes built-in Serbian card support, you can use OpenSC's PKCS#11 module instead. This module remains available as an alternative.

Use your smart card for browser authentication (e.g. eUprava login) and digital signatures in Firefox, Chrome, Thunderbird, or OpenSSH.

| Platform | Package |
|----------|---------|
| Linux (x86_64) | `.tar.gz` |
| macOS (Apple Silicon) | `.zip` |

[LibreMiddleware releases on GitHub](https://github.com/LibreSCRS/LibreMiddleware/releases)

See [PKCS#11 setup docs]({{< ref "docs/pkcs11" >}}) for Firefox, Chrome, and Thunderbird configuration.

---

## LibreMiddleware — OpenSC card driver

> **Deprecated.** A built-in Serbian card driver has been contributed to OpenSC and is pending inclusion in the next release. Once available, install OpenSC directly — no external driver needed.

An OpenSC external card driver for CLI tools (`pkcs15-tool`, `pkcs11-tool`, `pkcs15-crypt`) and PKCS#11 applications.

| Platform | Package |
|----------|---------|
| Linux (x86_64, OpenSC 0.26.x) | `.tar.gz` |
| macOS (Apple Silicon, OpenSC 0.26.x) | `.zip` |

[LibreMiddleware releases on GitHub](https://github.com/LibreSCRS/LibreMiddleware/releases)

See [OpenSC driver docs]({{< ref "docs/opensc-driver" >}}) for installation and configuration.
