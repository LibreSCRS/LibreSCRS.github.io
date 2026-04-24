---
layout: "simple"
title: "PKCS#11 модул"
description: "Коришћење LibreSCRS PKCS#11 модула са Firefox-ом, Chrome-ом, Thunderbird-ом и SSH-ом"
---

> **Напомена:** Уграђени драјвер за српске картице ([srbeid](https://github.com/OpenSC/OpenSC/pull/3595)) је интегрисан у главну грану OpenSC-а. Биће укључен у следеће издање OpenSC-а. До тада, овај модул остаје препоручена опција за PKCS#11 приступ смарт картицама.

LibreSCRS PKCS#11 модул је универзални криптографски интерфејс који аутоматски препознаје тип картице и користи одговарајући провајдер. Ради са било којом PKCS#11 апликацијом — Firefox, Chrome, SSH, клијенти електронске поште — без потребе да LibreCelik буде отворен.

**Типови картица који се аутоматски препознају:**
- **CardEdge** — Лична карта Gemalto (2014+), IF2020 за странце, ПКС картица Привредне коморе
- **PKCS#15** — било која PKCS#15-компатибилна смарт картица (генерички PKI стандард)
- **PIV** — америчке федералне ID картице (NIST SP 800-73)

## Инсталација

Преузмите пакет за вашу платформу са [странице издања](https://github.com/LibreSCRS/LibreMiddleware/releases) и распакујте га.

### Linux

```bash
tar -xzf librescrs-pkcs11-*-linux-*.tar.gz
sudo cp lib/librescrs-pkcs11.so* /usr/local/lib/
sudo ldconfig
```

#### p11-kit регистрација (опционо)

Региструјте модул на нивоу система тако да све p11-kit апликације (Chromium, GnuTLS итд.) могу аутоматски да га користе:

```bash
sudo cp p11-kit/librescrs.module /usr/share/p11-kit/modules/
```

Или за тренутног корисника:

```bash
mkdir -p ~/.config/pkcs11/modules
cp p11-kit/librescrs.module ~/.config/pkcs11/modules/
```

Проверите са: `p11-kit list-modules | grep -A5 librescrs`

### macOS

```bash
unzip librescrs-pkcs11-*-macos-universal.zip
sudo cp librescrs-pkcs11.dylib /usr/local/lib/
```

---

## Firefox

1. Отворите **Settings** > **Privacy & Security** > скролујте до **Security** > **Security Devices**
2. Кликните **Load**
3. Унесите име (нпр. `LibreSCRS`) и путању до модула:
   - Linux: `/usr/local/lib/librescrs-pkcs11.so`
   - macOS: `/usr/local/lib/librescrs-pkcs11.dylib`
4. Кликните **OK**

Убаците смарт картицу и освежите — Firefox ће тражити PIN када је сертификат потребан. На овај начин се аутентификујете на сервисе који захтевају аутентификацију клијентским сертификатом, као што је српска еУправа.

---

## Chrome / Chromium

Chrome на Linux-у користи NSS базу. Региструјте модул једном:

```bash
# Инсталирајте modutil ако није присутан
sudo apt install libnss3-tools     # Debian/Ubuntu
sudo dnf install nss-tools         # Fedora

# Региструјте за тренутног корисника
modutil -dbdir sql:$HOME/.pki/nssdb -add "LibreSCRS" \
    -libfile /usr/local/lib/librescrs-pkcs11.so
```

Рестартујте Chrome. Сертификати картице ће се појавити у **Settings** > **Privacy and security** > **Manage certificates**.

---

## Thunderbird

Исто као Firefox — **Preferences** > **Privacy & Security** > **Security Devices** > **Load**.

---

## OpenSSH

Листање јавних кључева на картици:

```bash
ssh-keygen -D /usr/local/lib/librescrs-pkcs11.so
```

Коришћење модула за SSH аутентификацију:

```bash
ssh -I /usr/local/lib/librescrs-pkcs11.so user@host
```

Или додајте у `~/.ssh/config`:

```
Host myserver
    PKCS11Provider /usr/local/lib/librescrs-pkcs11.so
```

---

## Компајлирање из изворног кода

Погледајте [LibreMiddleware на GitHub-у](https://github.com/LibreSCRS/LibreMiddleware) за упутства за компајлирање.

```bash
cmake -S /path/to/LibreMiddleware -B build
cmake --build build --target librescrs-pkcs11
```
