---
title: "Install LibreCelik"
description: "Download and install the LibreCelik desktop application on Linux or macOS"
---

LibreCelik is a desktop application for reading and displaying smart card data on Linux and macOS. It supports a growing range of card types through its plugin architecture.

## Linux

Download the `.AppImage` from the [releases page](https://github.com/LibreSCRS/LibreCelik/releases), make it executable, and run it:

```bash
chmod +x LibreCelik-*.AppImage
./LibreCelik-*.AppImage
```

No installation required. The AppImage bundles all dependencies including Qt.

### PC/SC reader support

The `pcscd` daemon must be running for card access:

```bash
# Debian/Ubuntu
sudo apt install pcscd pcsc-tools
sudo systemctl enable --now pcscd

# Fedora/RHEL
sudo dnf install pcsc-lite pcsc-tools
sudo systemctl enable --now pcscd

# Arch/Manjaro
sudo pacman -S ccid pcsc-tools
sudo systemctl enable --now pcscd
```

Verify your card reader is detected:

```bash
pcsc_scan
```

## macOS

Download and open the `.dmg` from the [releases page](https://github.com/LibreSCRS/LibreCelik/releases), drag LibreCelik to Applications.

macOS includes PC/SC support natively — no extra software needed.

---

## Requirements

- A USB smart card reader (contact or contactless, depending on the card)
- Linux: `pcscd` daemon running
- macOS: no additional requirements

---

## Building from source

See [BUILDING.md](https://github.com/LibreSCRS/LibreCelik/blob/main/BUILDING.md) in the source repository.

**Requirements**: CMake 3.24+, Qt 6.6+, OpenSSL 3, a C++20 compiler.
