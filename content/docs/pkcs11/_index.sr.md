---
title: "PKCS#11 модул"
description: "Коришћење LibreSCRS PKCS#11 модула са Firefox-ом, Chrome-ом, Thunderbird-ом и SSH-ом"
---

LibreSCRS PKCS#11 модул омогућава свакој PKCS#11 апликацији да користи српске смарт картице за аутентификацију и дигиталне потписе — без потребе да LibreCelik буде отворен.

## Инсталација

Преузмите пакет за вашу платформу са [странице издања](https://github.com/LibreSCRS/LibreMiddleware/releases) и распакујте га.

### Linux

```bash
tar -xzf LibreSCRS-pkcs11-*-linux-*.tar.gz
sudo cp librescrs-pkcs11.so /usr/local/lib/
```

### macOS

```bash
unzip LibreSCRS-pkcs11-*-macos.zip
sudo cp librescrs-pkcs11.dylib /usr/local/lib/
```

---

## Firefox

1. Отворите **Settings** → **Privacy & Security** → скролујте до **Security** → **Security Devices**
2. Кликните **Load**
3. Унесите име (нпр. `LibreSCRS`) и путању до модула:
   - Linux: `/usr/local/lib/librescrs-pkcs11.so`
   - macOS: `/usr/local/lib/librescrs-pkcs11.dylib`
4. Кликните **OK**

Убаците личну карту или ПКС картицу и освежите — Firefox ће тражити PIN када је сертификат потребан.

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

Рестартујте Chrome. Сертификати картице ће се појавити у **Settings** → **Privacy and security** → **Manage certificates**.

---

## Thunderbird

Исто као Firefox — **Preferences** → **Privacy & Security** → **Security Devices** → **Load**.

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
cmake -S /path/to/LibreMiddleware -B build -DBUILD_PKCS11=ON
cmake --build build --target rescrs-pkcs11
```
