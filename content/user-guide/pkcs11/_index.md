---
layout: "simple"
title: "PKCS#11 Module"
description: "Using the LibreSCRS PKCS#11 module with Firefox, Chrome, Thunderbird, and SSH"
---

> **Note:** A built-in Serbian card driver has been contributed to OpenSC and approved for inclusion. Once released, you can use OpenSC's PKCS#11 module instead. This module is maintained until Serbian eID support ships in OpenSC upstream and remains available as an alternative.

The LibreSCRS PKCS#11 module lets any PKCS#11-aware application use your smart card for authentication and digital signatures — without LibreCelik being open.

## Installation

Download the package for your platform from the [releases page](https://github.com/LibreSCRS/LibreMiddleware/releases) and extract it.

### Linux

```bash
tar -xzf LibreSCRS-pkcs11-*-linux-*.tar.gz
sudo cp lib/librescrs-pkcs11.so* /usr/local/lib/
sudo ldconfig
```

#### p11-kit registration (optional)

Register the module system-wide so all p11-kit consumers (Chromium, GnuTLS apps, etc.) can use it automatically:

```bash
sudo cp p11-kit/librescrs.module /usr/share/p11-kit/modules/
```

Or per-user:

```bash
mkdir -p ~/.config/pkcs11/modules
cp p11-kit/librescrs.module ~/.config/pkcs11/modules/
```

Verify with: `p11-kit list-modules | grep -A5 librescrs`

### macOS

```bash
unzip LibreSCRS-pkcs11-*-macos.zip
sudo cp librescrs-pkcs11.dylib /usr/local/lib/
```

---

## Firefox

1. Open **Settings** > **Privacy & Security** > scroll to **Security** > **Security Devices**
2. Click **Load**
3. Enter a name (e.g. `LibreSCRS`) and the path to the module:
   - Linux: `/usr/local/lib/librescrs-pkcs11.so`
   - macOS: `/usr/local/lib/librescrs-pkcs11.dylib`
4. Click **OK**

Insert your smart card and refresh — Firefox will prompt for PIN when a certificate is needed. This is how you authenticate to services that require client certificate authentication, such as Serbian eUprava.

---

## Chrome / Chromium

Chrome on Linux uses the NSS database. Register the module once:

```bash
# Install modutil if not present
sudo apt install libnss3-tools     # Debian/Ubuntu
sudo dnf install nss-tools         # Fedora

# Register for the current user
modutil -dbdir sql:$HOME/.pki/nssdb -add "LibreSCRS" \
    -libfile /usr/local/lib/librescrs-pkcs11.so
```

Restart Chrome. The card's certificates will appear in **Settings** > **Privacy and security** > **Manage certificates**.

---

## Thunderbird

Same as Firefox — **Preferences** > **Privacy & Security** > **Security Devices** > **Load**.

---

## OpenSSH

List the public keys on the card:

```bash
ssh-keygen -D /usr/local/lib/librescrs-pkcs11.so
```

Use the module for SSH authentication:

```bash
ssh -I /usr/local/lib/librescrs-pkcs11.so user@host
```

Or add to `~/.ssh/config`:

```
Host myserver
    PKCS11Provider /usr/local/lib/librescrs-pkcs11.so
```

---

## Building from source

See [LibreMiddleware on GitHub](https://github.com/LibreSCRS/LibreMiddleware) for build instructions.

```bash
cmake -S /path/to/LibreMiddleware -B build
cmake --build build --target librescrs-pkcs11
```
