---
layout: "simple"
title: "Install LibreCelik"
description: "Download and install the LibreCelik desktop application on Linux or macOS"
---

LibreCelik is a desktop application for reading and displaying smart card data on Linux and macOS. It supports a growing range of card types through its plugin architecture.

> **Install the card agent first.** From 5.0 LibreCelik links no PC/SC stack
> of its own — all card access happens in the LibreSCRS card agent, and without
> it LibreCelik starts normally and finds no card. See
> [Install the card agent](/user-guide/install-agent/).

## Linux

Download the `.AppImage` from the [releases page](https://github.com/LibreSCRS/LibreCelik/releases), make it executable, and run it:

```bash
chmod +x LibreCelik-*.AppImage
./LibreCelik-*.AppImage
```

The AppImage needs no installation: it bundles Qt and the libraries LibreCelik
itself links. It does **not** bundle the card agent, and cannot — the agent is
a per-user systemd service on the session bus behind polkit, which only a
system package can install. Install the agent packages for your distribution
first, from the [downloads page](/downloads/); without them the AppImage starts
and finds no card.

On Debian 13, Ubuntu 26.04 LTS, Fedora 43, Fedora 44 and openSUSE Tumbleweed,
LibreCelik is also a package, `librecelik`, on the same page.

### PC/SC reader support

The `pcscd` daemon must be running for card access:

```bash
# Debian/Ubuntu
sudo apt install pcscd pcsc-tools
sudo systemctl enable --now pcscd

# Fedora/RHEL
sudo dnf install pcsc-lite pcsc-tools
sudo systemctl enable --now pcscd

# openSUSE
sudo zypper install pcsc-lite pcsc-ccid pcsc-tools
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

Download and open the `.dmg` from the [releases page](https://github.com/LibreSCRS/LibreCelik/releases), then drag LibreCelik to Applications. macOS
includes PC/SC support, but from 5.0 LibreCelik links no PC/SC stack of its
own: the card agent host owns the card, and the macOS host **is not a release
asset in 5.0.0** — it is built from source. Without it LibreCelik starts and
finds no reader.

---

## Requirements

- A USB smart card reader (contact or contactless, depending on the card)
- Linux: `pcscd` daemon running
- macOS: the card agent host, built from source

---

## Building from source

See the [Developer Guide — Building From Source]({{< ref "developer-guide/building-from-source" >}}) for full build instructions.
