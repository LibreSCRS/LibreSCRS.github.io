---
title: "Признања трећих страна"
layout: "simple"
weight: 50
---

LibreSCRS не би био могућ без екосистема отвореног кода.
Ова страница наводи сваку компоненту треће стране уграђену у наша
бинарна издања, са одговарајућим признањима и условима лиценцирања.

---

## Статички повезане компоненте

### OpenSC (LGPL-2.1-or-later)

[OpenSC](https://github.com/OpenSC/OpenSC) — библиотека за паметне
картице отвореног кода. Испоручујемо измењени форк; погледајте
[LibreMiddleware thirdparty/patches/](https://github.com/LibreSCRS/LibreMiddleware/tree/main/thirdparty/patches)
директоријум за наше измене.

### OpenSSL (Apache-2.0)

[OpenSSL](https://www.openssl.org/) 3.5.5 — криптографска библиотека,
статички уграђена.

---

## Уграђене библиотеке

### nlohmann/json (MIT)

[json](https://github.com/nlohmann/json) — JSON за модерни C++.

### miniz (MIT/zlib-style)

[miniz](https://github.com/richgel999/miniz) — компресија без губитака.

### zlib (zlib license)

[zlib](https://zlib.net) — транзитивна зависност преко OpenSC.

### Liberation Sans (SIL-OFL-1.1)

[Liberation Fonts](https://github.com/liberationfonts/liberation-fonts)
— уграђени подскуп.

---

## Доступност изворног кода

Потпуни одговарајући изворни код за LibreSCRS, укључујући све
LGPL-лиценциране компоненте и наше измене на њима, јавно је доступан:

- **LibreMiddleware:** <https://github.com/LibreSCRS/LibreMiddleware>
- **LibreCelik:** <https://github.com/LibreSCRS/LibreCelik>

Ова понуда важи све док дистрибуирамо LibreSCRS.
