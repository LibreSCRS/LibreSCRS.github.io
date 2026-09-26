---
layout: "simple"
title: "Инсталирајте LibreCelik"
description: "Преузимање и инсталација LibreCelik десктоп апликације на Linux-у или macOS-у"
---

LibreCelik је десктоп апликација за читање и приказивање података са смарт картица на Linux-у и macOS-у. Подржава растући број типова картица кроз своју плагин архитектуру.

> **Прво инсталирајте картичног агента.** Од 5.0 LibreCelik не повезује
> сопствени PC/SC слој — сав приступ картици иде кроз LibreSCRS картичног
> агента, и без њега LibreCelik се нормално покрене а картицу не нађе. Види
> [Инсталацију картичног агента](/sr/user-guide/install-agent/).

## Linux

Преузмите `.AppImage` са [странице издања](https://github.com/LibreSCRS/LibreCelik/releases), дозволите извршавање и покрените:

```bash
chmod +x LibreCelik-*.AppImage
./LibreCelik-*.AppImage
```

AppImage не захтева инсталацију: садржи Qt и библиотеке које LibreCelik сам
повезује. **Не** садржи картичног агента, и не може — агент је systemd сервис по
кориснику на сесијској магистрали иза polkit-а, а њих може да инсталира само
системски пакет. Прво инсталирајте пакете агента за своју дистрибуцију, са
[странице за преузимање](/sr/downloads/); без њих се AppImage покрене и картицу
не нађе.

На Debian-у 13, Ubuntu-у 26.04 LTS, Fedora-и 43, Fedora-и 44 и openSUSE
Tumbleweed-у LibreCelik је и пакет, `librecelik`, на истој страници.

### Подршка за PC/SC читач

`pcscd` сервис мора бити покренут за приступ картици:

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

Проверите да ли је ваш читач детектован:

```bash
pcsc_scan
```

## macOS

Преузмите и отворите `.dmg` са [странице издања](https://github.com/LibreSCRS/LibreCelik/releases), па превуците LibreCelik у Applications. macOS носи
PC/SC, али од 5.0 LibreCelik не линкује сопствени PC/SC слој: картицу држи
агент, а на macOS-у агент излази у LibreMac-у — прво
[инсталирајте LibreMac](/sr/user-guide/install-libremac/). Без њега LibreCelik
се покрене и не нађе читач.

Ни LibreCelik слика диска није нотаризована, па њено прво покретање тражи исте
Gatekeeper кораке као LibreMac.

---

## Захтеви

- USB читач смарт картица (контактни или бесконтактни, у зависности од картице)
- Linux: `pcscd` сервис мора бити покренут
- macOS 15 или новији: LibreMac, који носи картичног агента

---

## Компајлирање из изворног кода

Погледајте [Водич за програмере — Изградња из изворног кода]({{< ref "developer-guide/building-from-source" >}}) за комплетна упутства.
