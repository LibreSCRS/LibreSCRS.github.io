---
title: "OpenSC драјвер"
description: "Инсталација и коришћење LibreSCRS OpenSC екстерног драјвера за картице"
---

> **Обавештење о застарелости:** Уграђени драјвер за српске картице је предложен за OpenSC и одобрен за укључивање. Када буде објављен, овај екстерни драјвер више неће бити потребан — само инсталирајте OpenSC. До тада, овај драјвер остаје потпуно функционалан.

LibreSCRS OpenSC драјвер је екстерни модул за OpenSC. Када се инсталира, свака PKCS#11 апликација може транспарентно користити српске личне картице и ПКС картице преко OpenSC PKCS#11 моста.

**Подржане картице**:
- Лична карта Gemalto (2014+) — препознавање по ATR `3B:FF:94`
- Лична карта IF2020 за странце — препознавање по AID
- ПКС картица Привредне коморе — препознавање по AID

**Није подржана**: Apollo 2008 лична карта (нема CardEdge аплет).

---

## Преузимање

Прекомпајлирани пакети су доступни на [страници издања](https://github.com/LibreSCRS/LibreMiddleware/releases):

| Платформа | Датотека |
|-----------|----------|
| Linux (x86_64, OpenSC 0.26.x) | `librescrs-opensc-*-opensc0.26.x-linux-x86_64.tar.gz` |
| macOS (Apple Silicon, OpenSC 0.26.x) | `librescrs-opensc-*-opensc0.26.x-macos-arm64.zip` |

Распакујте и копирајте:

```bash
# Linux
sudo cp librescrs-opensc.so /usr/local/lib/

# macOS
sudo cp librescrs-opensc.dylib /usr/local/lib/
```

---

## Компајлирање из изворног кода

### Linux

```bash
sudo apt install libopensc-dev        # Debian/Ubuntu
# sudo dnf install opensc-devel       # Fedora/RHEL

cmake -S /path/to/LibreMiddleware -B build -DBUILD_OPENSC_DRIVER=ON
cmake --build build --target librescrs-opensc
sudo cp build/lib/opensc-driver/librescrs-opensc.so /usr/local/lib/
```

### macOS

Homebrew инсталира OpenSC али не и развојна заглавља. Клонирајте OpenSC извор на одговарајућем тагу верзије:

```bash
brew install opensc
opensc-tool --version          # забележите верзију, нпр. 0.26.1
git clone --branch 0.26.1 --depth 1 https://github.com/OpenSC/OpenSC /tmp/opensc-src

cmake -S /path/to/LibreMiddleware -B build \
    -DBUILD_OPENSC_DRIVER=ON \
    -DOPENSC_INCLUDE_DIR=/tmp/opensc-src/src
cmake --build build --target librescrs-opensc
sudo cp build/lib/opensc-driver/librescrs-opensc.dylib /usr/local/lib/
```

---

## Конфигурација

Додајте следеће у ваш `opensc.conf`:

| Платформа | Локација opensc.conf |
|-----------|----------------------|
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

## Верификација

### Детекција картице

```bash
opensc-tool --list-readers
# Gemalto USB SmartCard Reader  Slot 0  ATR: 3B FF ...
```

### PKCS#15 објекти

```bash
pkcs15-tool --list-certificates
pkcs15-tool --list-keys
pkcs15-tool --list-pins          # приказује преостале покушаје
```

За потписивање и верификацију датотека, погледајте страницу [Дигитално потписивање](/sr/docs/digital-signing/).

---

## Дебаговање

Укључите OpenSC логовање у `opensc.conf`:

```
app default {
    debug = 3;
    debug_file = /tmp/opensc-debug.txt;
    ...
}
```

Прегледајте `/tmp/opensc-debug.txt` после покретања било које `pkcs15-tool` или `pkcs11-tool` команде.
