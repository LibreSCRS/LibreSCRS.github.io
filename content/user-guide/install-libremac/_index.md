---
layout: "simple"
title: "Install LibreMac and LibreCelik"
description: "Install LibreMac, which carries the LibreSCRS card agent, and LibreCelik on macOS from one disk image, and get both past Gatekeeper"
---

On macOS the card agent ships inside **LibreMac**, a menu bar application. One
disk image, `LibreSCRS-*-macos.dmg`, carries both applications —
**LibreMac** and **LibreCelik** — and LibreMac brings four things:

- the **menu bar host**, which shows the card in the reader and offers signing
  and credential management from its menu;
- the **card agent and its PIN prompter** (built from LibreDarwin), which own
  the card and collect PINs, CANs and MRZs, as the agent does on Linux;
- a **CryptoTokenKit extension** that publishes a present card's signing
  certificates to the Keychain, where Safari, Mail and other Keychain clients
  can use them;
- a **PKCS#11 module** for applications that load one, such as Firefox,
  Thunderbird and `ssh`; see the [PKCS#11 guide](/user-guide/pkcs11/#macos).

LibreCelik, the card reader application, is in the same disk image and is a
client of this agent. You do not install the two in a particular order: if the
agent is not running when LibreCelik opens, LibreCelik launches LibreMac and
starts the agent itself.

**Requirements:** macOS 15 (Sequoia) or later. The image is universal — one
download for Apple silicon and Intel Macs.

## Before you open them: they are not notarised

The applications in this disk image (5.0.0) are signed ad hoc, not with an Apple Developer ID, and they are not
notarised by Apple. Gatekeeper therefore refuses to open them the first time, and
the steps below are how you tell macOS that you trust them. That makes checking
the download yourself the step that matters: verify the disk image against the
release's `SHA256SUMS` and its cosign signature, as described on
[verifying a release](/security/), **before** you open it.

## Install

1. Download the disk image from the
   [downloads page](/downloads/#macos).
2. Open it and drag both **LibreMac** and **LibreCelik** to **Applications**.
3. Eject the disk image.
4. Open either application. Opening LibreCelik is enough — it starts LibreMac
   and the agent when they are not running.

## First launch past Gatekeeper

1. Open **LibreMac** (or **LibreCelik**) from Applications. macOS refuses and says it cannot verify
   the developer or check the application for malicious software. Choose
   **Done** — not **Move to Trash**.
2. Open **System Settings → Privacy & Security** and scroll to **Security**.
   A line says the application was blocked; choose **Open Anyway** and confirm with
   your password or Touch ID.
3. Open the same application again and choose **Open** in the dialog that follows.

macOS remembers the decision for this copy. Installing a new version repeats
the three steps, for each application — nothing installed from this release updates itself.

On macOS 15 and later, Control-click → **Open** no longer skips this dialog;
**Open Anyway** in System Settings is the way. From Terminal the equivalent is
removing the quarantine attribute from the copy you verified:

```
xattr -d com.apple.quarantine /Applications/LibreMac.app
xattr -d com.apple.quarantine /Applications/LibreCelik.app
```

## Approve the agent

LibreMac has no Dock icon; it lives in the menu bar. The agent and the prompter
run as login items, and macOS asks you to allow them once: choose
**Approve the signing agent in Login Items…** in the LibreMac menu, and switch
LibreMac on under **Allow in the Background** in **System Settings → General →
Login Items & Extensions**. Until then the menu shows that item and no card
operation can run.

## What an ad-hoc signature means

Without a Developer ID, the agent and the prompter cannot check who connects to
them beyond the fact that the connecting process runs as your user. Any program
running as you can therefore ask the agent for work and raise its credential
window — every PIN operation still needs your PIN in the prompter. A build
signed with a Developer ID checks the caller's signature as well. The
[LibreMac security policy](https://github.com/LibreSCRS/LibreMac/blob/main/SECURITY.md)
states the details.
