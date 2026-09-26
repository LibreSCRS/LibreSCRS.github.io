---
layout: "simple"
title: "Install LibreMac"
description: "Install the LibreSCRS card agent on macOS from the LibreMac disk image, and get it past Gatekeeper"
---

On macOS the card agent ships inside **LibreMac**, a menu bar application. One
disk image carries three things:

- the **menu bar host**, which shows the card in the reader and offers signing
  and credential management from its menu;
- the **card agent and its PIN prompter** (built from LibreDarwin), which own
  the card and collect PINs, CANs and MRZs, as the agent does on Linux;
- a **CryptoTokenKit extension** that publishes a present card's signing
  certificates to the Keychain, where Safari, Mail and other Keychain clients
  can use them.

LibreCelik on macOS is a client of this agent: install LibreMac first.

**Requirements:** macOS 15 (Sequoia) or later. The image is universal — one
download for Apple silicon and Intel Macs.

## Before you open it: it is not notarised

LibreMac 5.0.0 is signed ad hoc, not with an Apple Developer ID, and it is not
notarised by Apple. Gatekeeper therefore refuses to open it the first time, and
the steps below are how you tell macOS that you trust it. That makes checking
the download yourself the step that matters: verify the disk image against the
release's `SHA256SUMS` and its cosign signature, as described on
[verifying a release](/security/), **before** you open it.

## Install

1. Download the disk image from the
   [downloads page](/downloads/#macos).
2. Open it and drag **LibreMac** to **Applications**.
3. Eject the disk image.

## First launch past Gatekeeper

1. Open **LibreMac** from Applications. macOS refuses and says it cannot verify
   the developer or check the application for malicious software. Choose
   **Done** — not **Move to Trash**.
2. Open **System Settings → Privacy & Security** and scroll to **Security**.
   A line says LibreMac was blocked; choose **Open Anyway** and confirm with
   your password or Touch ID.
3. Open LibreMac again and choose **Open** in the dialog that follows.

macOS remembers the decision for this copy. Installing a new version repeats
the three steps — nothing installed from this release updates itself.

On macOS 15 and later, Control-click → **Open** no longer skips this dialog;
**Open Anyway** in System Settings is the way. From Terminal the equivalent is
removing the quarantine attribute from the copy you verified:

```
xattr -d com.apple.quarantine /Applications/LibreMac.app
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
