---
title: "LibreCelik"
description: "Setup and usage guide for the LibreCelik desktop application"
---

LibreCelik is a desktop application for reading and printing Serbian government smart cards on Linux and macOS.

## Installation

### Linux

Download the `.AppImage` from the [releases page](https://github.com/LibreSCRS/LibreCelik/releases), make it executable, and run it:

```bash
chmod +x LibreCelik-*.AppImage
./LibreCelik-*.AppImage
```

No installation required. The AppImage bundles all dependencies including Qt.

#### PC/SC reader support

The `pcscd` daemon must be running for card access:

```bash
# Debian/Ubuntu
sudo apt install pcscd pcsc-tools
sudo systemctl enable --now pcscd

# Fedora/RHEL
sudo dnf install pcsc-lite pcsc-tools
sudo systemctl enable --now pcscd
```

Verify your card reader is detected:

```bash
pcsc_scan
```

### macOS

Download and open the `.dmg` from the [releases page](https://github.com/LibreSCRS/LibreCelik/releases), drag LibreCelik to Applications.

macOS includes PC/SC support (`CryptoTokenKit`) natively — no extra software needed.

---

## Supported cards

Insert your card and LibreCelik automatically detects the card type.

| Card | Data shown |
|------|-----------|
| Serbian eID (Gemalto / IF2020) | Personal data, document info, digital signature certificates, PIN management |
| Vehicle registration | All fields including owner, vehicle, and registration dates |
| Health insurance card | Insured person, employer, insurance details |
| PKS Chamber of Commerce | Qualified signature certificates, PIN management |

---

## Language

LibreCelik supports English and Serbian (Cyrillic). Change via the language menu in the top-right corner.

---

## Building from source

See [BUILDING.md](https://github.com/LibreSCRS/LibreCelik/blob/main/BUILDING.md) in the source repository.

**Requirements**: CMake 3.24+, Qt 6.6+, OpenSSL 3, a C++20 compiler.
