---
title: "Downloads"
description: "Download LibreCelik and LibreMiddleware packages"
layout: "simple"
---

All releases are published on GitHub. Choose the package for your platform.

---

## LibreCelik

Desktop application for reading Serbian smart cards.

| Platform | Package |
|----------|---------|
| Linux (x86_64) | `.AppImage` |
| macOS (Apple Silicon) | `.dmg` |

[LibreCelik releases on GitHub](https://github.com/LibreSCRS/LibreCelik/releases)

---

## LibreMiddleware — PKCS#11 module

Load this module in your browser, email client, or SSH to use your smart card for authentication and digital signatures.

| Platform | Package |
|----------|---------|
| Linux (x86_64) | `.tar.gz` |
| macOS (Apple Silicon) | `.zip` |

[LibreMiddleware releases on GitHub](https://github.com/LibreSCRS/LibreMiddleware/releases)

See [PKCS#11 setup docs]({{< ref "docs/pkcs11" >}}) for Firefox, Chrome, and Thunderbird configuration.

---

## LibreMiddleware — OpenSC card driver

An OpenSC external card driver. Required only if you want OpenSC tools (`pkcs15-tool`, `pkcs11-tool`) to work with Serbian eID / PKS cards.

| Platform | Package |
|----------|---------|
| Linux (x86_64, OpenSC 0.26.x) | `.tar.gz` |
| macOS (Apple Silicon, OpenSC 0.26.x) | `.zip` |

[LibreMiddleware releases on GitHub](https://github.com/LibreSCRS/LibreMiddleware/releases)

See [OpenSC driver docs]({{< ref "docs/opensc-driver" >}}) for installation and configuration.
