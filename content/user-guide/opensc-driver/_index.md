---
layout: "simple"
title: "OpenSC Card Driver"
description: "Building, installing, and using the LibreSCRS OpenSC external card driver"
---

> **Temporary — this driver will be deprecated.** A built-in Serbian card driver has been [contributed to OpenSC](https://github.com/OpenSC/OpenSC/pull/3595) and approved for inclusion by the OpenSC maintainers. Once the next OpenSC release ships, this external driver will no longer be needed — just install OpenSC. Until then, this driver remains fully functional.

The LibreSCRS OpenSC card driver is an external card driver module for OpenSC. Once installed, any PKCS#11-aware application can use Serbian eID and PKS cards transparently via OpenSC's PKCS#11 bridge.

**Supported cards**:
- Serbian eID Gemalto (2014+) — matched by ATR `3B:FF:94`
- Serbian eID IF2020 Foreigner — matched by AID
- PKS Chamber of Commerce card — matched by AID

**Not supported**: Apollo 2008 eID (no CardEdge applet).

---

## Download

Pre-built packages are available on the [releases page](https://github.com/LibreSCRS/LibreMiddleware/releases):

| Platform | File |
|----------|------|
| Linux (x86_64, OpenSC 0.26.x) | `librescrs-opensc-*-opensc0.26.x-linux-x86_64.tar.gz` |
| macOS (Apple Silicon, OpenSC 0.26.x) | `librescrs-opensc-*-opensc0.26.x-macos-arm64.zip` |

Extract and copy:

```bash
# Linux
sudo cp librescrs-opensc.so /usr/local/lib/

# macOS
sudo cp librescrs-opensc.dylib /usr/local/lib/
```

---

## Build from source

### Linux

```bash
sudo apt install libopensc-dev        # Debian/Ubuntu
# sudo dnf install opensc-devel       # Fedora/RHEL

cmake -S /path/to/LibreMiddleware -B build -DBUILD_OPENSC_DRIVER=ON
cmake --build build --target librescrs-opensc
sudo cp build/lib/opensc-driver/librescrs-opensc.so /usr/local/lib/
```

### macOS

Homebrew installs OpenSC but not its development headers. Clone the OpenSC source at the matching version tag:

```bash
brew install opensc
opensc-tool --version          # note the version, e.g. 0.26.1
git clone --branch 0.26.1 --depth 1 https://github.com/OpenSC/OpenSC /tmp/opensc-src

cmake -S /path/to/LibreMiddleware -B build \
    -DBUILD_OPENSC_DRIVER=ON \
    -DOPENSC_INCLUDE_DIR=/tmp/opensc-src/src
cmake --build build --target librescrs-opensc
sudo cp build/lib/opensc-driver/librescrs-opensc.dylib /usr/local/lib/
```

---

## Configuration

Add the following to your `opensc.conf`:

| Platform | opensc.conf location |
|----------|----------------------|
| Linux | `/etc/opensc/opensc.conf` · `/etc/opensc.conf` · `~/.config/opensc/opensc.conf` |
| macOS | `/opt/homebrew/etc/opensc.conf` · `/Library/Application Support/OpenSC/opensc.conf` |

```
app default {
    card_drivers = librescrs, internal;

    card_driver librescrs {
        module = /usr/local/lib/librescrs-opensc.so;   # Linux
        # module = /usr/local/lib/librescrs-opensc.dylib;  # macOS
    }

    framework pkcs15 {
        emulate librescrs {
            module = /usr/local/lib/librescrs-opensc.so;   # Linux
            # module = /usr/local/lib/librescrs-opensc.dylib;  # macOS
        }
    }
}
```

---

## Verification

### Card detection

```bash
opensc-tool --list-readers
# Gemalto USB SmartCard Reader  Slot 0  ATR: 3B FF ...
```

### PKCS#15 objects

```bash
pkcs15-tool --list-certificates
pkcs15-tool --list-keys
pkcs15-tool --list-pins          # shows tries remaining
```

For signing and verifying files, see the [Digital Signing]({{< ref "user-guide/digital-signing" >}}) page.

---

## Debugging

Enable OpenSC debug logging in `opensc.conf`:

```
app default {
    debug = 3;
    debug_file = /tmp/opensc-debug.txt;
    ...
}
```

Inspect `/tmp/opensc-debug.txt` after running any `pkcs15-tool` or `pkcs11-tool` command.
