---
layout: "simple"
title: "OpenSC интеграција"
description: "Нативна OpenSC подршка за српске картице и екстерни драјвер за тренутна издања OpenSC-а"
aliases:
  - /sr/user-guide/cardedge-opensc-driver/
---

## Нативна OpenSC подршка

[srbeid драјвер](https://github.com/OpenSC/OpenSC/pull/3595) за српске смарт картице је интегрисан у главну грану OpenSC-а. Српска лична карта (Gemalto 2014+, IF2020 за странце) и ПКС картице Привредне коморе биће подржане из кутије у следећем издању OpenSC-а.

Ако компајлирате OpenSC из изворног кода (main грана), нативна подршка је већ доступна — без екстерног драјвера или конфигурације.

---

## Екстерни драјвер

За кориснике на тренутним издањима OpenSC-а (0.26.x, 0.27.x) која још не укључују нативни srbeid драјвер, LibreSCRS пружа екстерни модул. Када се инсталира, свака PKCS#11 апликација може транспарентно користити српске личне картице и ПКС картице преко OpenSC PKCS#11 моста.

**Подржане картице**:
- Лична карта Gemalto (2014+) — препознавање по ATR `3B:FF:94`
- Лична карта IF2020 за странце — препознавање по AID
- ПКС картица Привредне коморе — препознавање по AID

**Није подржана**: Apollo 2008 лична карта (нема CardEdge аплет).

### Преузимање

Прекомпајлирани пакети за OpenSC 0.26.x и 0.27.x су доступни на [страници издања](https://github.com/LibreSCRS/LibreMiddleware/releases).

Распакујте и копирајте:

```bash
# Linux
sudo cp librescrs-cardedge-opensc.so /usr/local/lib/

# macOS
sudo cp librescrs-cardedge-opensc.dylib /usr/local/lib/
```

### Компајлирање из изворног кода

#### Linux

```bash
sudo apt install libopensc-dev        # Debian/Ubuntu
# sudo dnf install opensc-devel       # Fedora/RHEL

cmake -S /path/to/LibreMiddleware -B build -DBUILD_CARDEDGE_OPENSC_DRIVER=ON
cmake --build build --target librescrs-cardedge-opensc
sudo cp build/lib/cardedge-opensc-driver/librescrs-cardedge-opensc.so /usr/local/lib/
```

#### macOS

Homebrew инсталира OpenSC али не и развојна заглавља. Клонирајте OpenSC извор на одговарајућем тагу верзије:

```bash
brew install opensc
opensc-tool --version          # забележите верзију, нпр. 0.26.1
git clone --branch 0.26.1 --depth 1 https://github.com/OpenSC/OpenSC /tmp/opensc-src

cmake -S /path/to/LibreMiddleware -B build \
    -DBUILD_CARDEDGE_OPENSC_DRIVER=ON \
    -DOPENSC_INCLUDE_DIR=/tmp/opensc-src/src
cmake --build build --target librescrs-cardedge-opensc
sudo cp build/lib/cardedge-opensc-driver/librescrs-cardedge-opensc.dylib /usr/local/lib/
```

### Конфигурација

Додајте следеће у ваш `opensc.conf`:

| Платформа | Локација opensc.conf |
|-----------|----------------------|
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

### Верификација

#### Детекција картице

```bash
opensc-tool --list-readers
# Gemalto USB SmartCard Reader  Slot 0  ATR: 3B FF ...
```

#### PKCS#15 објекти

```bash
pkcs15-tool --list-certificates
pkcs15-tool --list-keys
pkcs15-tool --list-pins          # приказује преостале покушаје
```

За потписивање и верификацију датотека, погледајте страницу [Дигитално потписивање](/sr/user-guide/digital-signing/).

### Дебаговање

Укључите OpenSC логовање у `opensc.conf`:

```
app default {
    debug = 3;
    debug_file = /tmp/opensc-debug.txt;
    ...
}
```

Прегледајте `/tmp/opensc-debug.txt` после покретања било које `pkcs15-tool` или `pkcs11-tool` команде.
