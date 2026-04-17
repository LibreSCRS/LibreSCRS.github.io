---
layout: "simple"
title: "OpenSC Integration"
description: "Native OpenSC support for Serbian cards and the external driver for current OpenSC releases"
aliases:
  - /user-guide/cardedge-opensc-driver/
---

## Native OpenSC Support

The [srbeid driver](https://github.com/OpenSC/OpenSC/pull/3595) for Serbian smart cards has been merged into OpenSC mainline. Serbian eID (Gemalto 2014+, IF2020 Foreigner) and PKS Chamber of Commerce cards will be supported out of the box in the next OpenSC release.

If you build OpenSC from source (main branch), native support is already available — no external driver or configuration needed.

---

## External Driver

For users on current OpenSC release versions (0.26.x, 0.27.x) that do not yet include the native srbeid driver, LibreSCRS provides an external card driver module. Once installed, any PKCS#11-aware application can use Serbian eID and PKS cards transparently via OpenSC's PKCS#11 bridge.

**Supported cards**:
- Serbian eID Gemalto (2014+) — matched by ATR `3B:FF:94`
- Serbian eID IF2020 Foreigner — matched by AID
- PKS Chamber of Commerce card — matched by AID

**Not supported**: Apollo 2008 eID (no CardEdge applet).

### Download

Pre-built packages for OpenSC 0.26.x and 0.27.x are available on the [releases page](https://github.com/LibreSCRS/LibreMiddleware/releases).

Extract and copy:

```bash
# Linux
sudo cp librescrs-cardedge-opensc.so /usr/local/lib/

# macOS
sudo cp librescrs-cardedge-opensc.dylib /usr/local/lib/
```

### Build from source

#### Linux

```bash
sudo apt install libopensc-dev        # Debian/Ubuntu
# sudo dnf install opensc-devel       # Fedora/RHEL

cmake -S /path/to/LibreMiddleware -B build -DBUILD_CARDEDGE_OPENSC_DRIVER=ON
cmake --build build --target librescrs-cardedge-opensc
sudo cp build/lib/cardedge-opensc-driver/librescrs-cardedge-opensc.so /usr/local/lib/
```

#### macOS

Homebrew installs OpenSC but not its development headers. Clone the OpenSC source at the matching version tag:

```bash
brew install opensc
opensc-tool --version          # note the version, e.g. 0.26.1
git clone --branch 0.26.1 --depth 1 https://github.com/OpenSC/OpenSC /tmp/opensc-src

cmake -S /path/to/LibreMiddleware -B build \
    -DBUILD_CARDEDGE_OPENSC_DRIVER=ON \
    -DOPENSC_INCLUDE_DIR=/tmp/opensc-src/src
cmake --build build --target librescrs-cardedge-opensc
sudo cp build/lib/cardedge-opensc-driver/librescrs-cardedge-opensc.dylib /usr/local/lib/
```

### Configuration

Add the following to your `opensc.conf`:

| Platform | opensc.conf location |
|----------|----------------------|
| Linux | `/etc/opensc/opensc.conf` · `/etc/opensc.conf` · `~/.config/opensc/opensc.conf` |
| macOS | `/opt/homebrew/etc/opensc.conf` · `/Library/Application Support/OpenSC/opensc.conf` |

```
app default {
    card_drivers = librescrs, internal;

    card_driver librescrs {
        module = /usr/local/lib/librescrs-cardedge-opensc.so;   # Linux
        # module = /usr/local/lib/librescrs-cardedge-opensc.dylib;  # macOS
    }

    framework pkcs15 {
        emulate librescrs {
            module = /usr/local/lib/librescrs-cardedge-opensc.so;   # Linux
            # module = /usr/local/lib/librescrs-cardedge-opensc.dylib;  # macOS
        }
    }
}
```

### Verification

#### Card detection

```bash
opensc-tool --list-readers
# Gemalto USB SmartCard Reader  Slot 0  ATR: 3B FF ...
```

#### PKCS#15 objects

```bash
pkcs15-tool --list-certificates
pkcs15-tool --list-keys
pkcs15-tool --list-pins          # shows tries remaining
```

For signing and verifying files, see the [Digital Signing]({{< ref "user-guide/digital-signing" >}}) page.

### Debugging

Enable OpenSC debug logging in `opensc.conf`:

```
app default {
    debug = 3;
    debug_file = /tmp/opensc-debug.txt;
    ...
}
```

Inspect `/tmp/opensc-debug.txt` after running any `pkcs15-tool` or `pkcs11-tool` command.
