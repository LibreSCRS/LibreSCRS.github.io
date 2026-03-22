---
title: "Инсталирајте LibreCelik"
description: "Преузимање и инсталација LibreCelik десктоп апликације на Linux-у или macOS-у"
---

LibreCelik је десктоп апликација за читање и приказивање података са смарт картица на Linux-у и macOS-у. Подржава растући број типова картица кроз своју плагин архитектуру.

## Linux

Преузмите `.AppImage` са [странице издања](https://github.com/LibreSCRS/LibreCelik/releases), дозволите извршавање и покрените:

```bash
chmod +x LibreCelik-*.AppImage
./LibreCelik-*.AppImage
```

Инсталација није потребна. AppImage садржи све зависности укључујући Qt.

### Подршка за PC/SC читач

`pcscd` сервис мора бити покренут за приступ картици:

```bash
# Debian/Ubuntu
sudo apt install pcscd pcsc-tools
sudo systemctl enable --now pcscd

# Fedora/RHEL
sudo dnf install pcsc-lite pcsc-tools
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

Преузмите и отворите `.dmg` са [странице издања](https://github.com/LibreSCRS/LibreCelik/releases), превуците LibreCelik у Applications.

macOS има уграђену PC/SC подршку — додатни софтвер није потребан.

---

## Захтеви

- USB читач смарт картица (контактни или бесконтактни, у зависности од картице)
- Linux: `pcscd` сервис мора бити покренут
- macOS: нема додатних захтева

---

## Компајлирање из изворног кода

Погледајте [Водич за програмере — Изградња из изворног кода]({{< ref "developer-guide/building-from-source" >}}) за комплетна упутства.
