---
layout: "simple"
title: "Изградња из изворног кода"
description: "Предуслови, упутства за изградњу и покретање тестова"
---

Тренутне опције изградње одговарају LibreSCRS 5.0. Производ се гради редом по
зависностима — middleware, агент, домаћин, па клијент — и сваки корак после
првог троши претходни као инсталиран CMake пакет:

```
LibreMiddleware  →  LibreAgent  →  LibreLinux  →  LibreCelik / LibreKDE
```

## Предуслови

| Зависност | Верзија | Напомена |
|---|---|---|
| CMake | 3.24+ | 3.28+ тамо где се користи `FetchContent` |
| C++ преводилац | GCC 13+ или Clang 17+ | C++23 |
| Qt 6 | Core, DBus, Widgets, LinguistTools | LibreCelik, LibreKDE, упитник и `LibreAgent::ClientQt` |
| PC/SC | `libpcsclite-dev` (Linux) | уграђено на macOS-у |
| OpenSSL 3 | — | уграђен у LibreMiddleware `thirdparty/` |
| sdbus-c++ | 2.0+ | LibreLinux (D-Bus агента и упитника) |
| systemd | `libsystemd-dev` | LibreLinux (петља догађаја, `sd_notify`) |
| p11-kit | — | LibreLinux (разрешава PKCS#11 модул и конфигурационе директоријуме) |
| UUID | `uuid-dev` (Linux) | генерисање UUID-а |

---

## Изградња LibreMiddleware-а

Самостална збирка C++23 библиотека без Qt зависности.

```bash
git clone https://github.com/LibreSCRS/LibreMiddleware.git
cd LibreMiddleware
cmake -B build -DCMAKE_INSTALL_PREFIX=<prefix>
cmake --build build
cmake --install build
```

Покретање тестова:

```bash
ctest --test-dir build --output-on-failure
```

Инсталирајте га пре него што кренете даље: све низводно разрешава га преко
`find_package(LibreMiddleware 5.0 CONFIG)`, не довлачењем.

---

## Изградња LibreAgent-а

Платформски неутрално језгро агента, жичана библиотека и Qt клијентска
библиотека. Шта од тога добијате бира се по компоненти, јер домаћин без Qt-а и
Qt клијент желе различите половине овог спремишта:

| Опција | Подразумевано | Даје |
|---|---|---|
| `LIBREAGENT_BUILD_CORE` | `ON` | `LibreAgent::Core` — повезује LibreMiddleware и OpenSSL |
| `LIBREAGENT_BUILD_WIRE` | `ON` | `LibreAgent::Wire` — не повезује ништа наше |
| `LIBREAGENT_BUILD_CLIENT_QT` | `OFF` | `LibreAgent::ClientQt` — повезује Qt6 |
| `LIBREAGENT_BUILD_PKCS11_FACADE` | `OFF` | PKCS#11 језгро на коме домаћин гради свој модул |

```bash
git clone https://github.com/LibreSCRS/LibreAgent.git
cd LibreAgent
cmake -B build -DCMAKE_PREFIX_PATH=<prefix> -DCMAKE_INSTALL_PREFIX=<prefix> \
      -DLIBREAGENT_BUILD_CLIENT_QT=ON \
      -DLIBREAGENT_BUILD_PKCS11_FACADE=ON
cmake --build build
cmake --install build
```

Потрошач именује компоненте које су му потребне. Тражење пакета без списка
компоненти тера га да испита сваку коју нађе и за сваку покрене њен
`find_dependency()` — што увуче Qt6 у изградњу која га није хтела:

```cmake
find_package(LibreAgent 5.0 CONFIG REQUIRED COMPONENTS Core Wire)
```

---

## Изградња LibreLinux-а

Linux домаћин: демон `librescrs-agent`, KDE упитник и клијентски PKCS#11 модул.
Троши **инсталиран** LibreAgent уместо да га довлачи:

```bash
git clone https://github.com/LibreSCRS/LibreLinux.git
cd LibreLinux
cmake -B build -DCMAKE_PREFIX_PATH=<prefix> \
      -DLIBRELINUX_USE_INSTALLED_AGENT_CORE=ON
cmake --build build
cmake --install build
```

`LIBRELINUX_USER_INSTALL=ON` смешта systemd кориснички unit, D-Bus сервисне
фајлове и p11-kit конфигурацију модула под ваш префикс уместо системског — што
је оно што хоћете за радни checkout, а није оно што хоће пакет.

---

## Изградња LibreCelik-а

Qt6 GUI апликација. Троши `LibreAgent::ClientQt` преко CMake `FetchContent`-а,
закуцан у `cmake/libreagent.pin`; не повезује сопствени PC/SC слој, јер сав
приступ картици иде кроз агента.

```bash
git clone https://github.com/LibreSCRS/LibreCelik.git
cd LibreCelik
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

---

## Изградња LibreKDE-а

Интеграција са Plasma 6. Тражи LibreAgent 5.0 или новији, инсталиран **са
компонентом `ClientQt`** — голи `cmake -B build` више не конфигурише:

```bash
git clone https://github.com/LibreSCRS/LibreKDE.git
cd LibreKDE
cmake -B build -DCMAKE_PREFIX_PATH=<prefix>
cmake --build build
```

---

## Локални развој

Када радите на два спремишта истовремено, упутите потрошача на свој локални
checkout уместо на закуцано довлачење:

```bash
# LibreCelik према радном LibreAgent-у
cmake -B build -DFETCHCONTENT_SOURCE_DIR_LIBREAGENT=/path/to/LibreAgent
```

То доказује ваше **изворе**, не пин. Изградња која тако прође не говори ништа о
томе да ли би се закуцана ревизија такође изградила, па подигните пин и
покрените поново пре него што се на то ослоните.

---

## Опције изградње (LibreMiddleware 5.0)

`LIBREMIDDLEWARE_BUILD_SHARED` (подразумевано `ON`) гради сваку `LibreSCRS_*`
мету као `.so`/`.dylib`, што низводни потрошачи учитавају у раду; `OFF` даје
статичке архиве. CMake Config пакет се генерише и инсталира само у дељеној
конфигурацији, па је низводном `find_package(LibreMiddleware CONFIG)` потребан.

`LIBREMIDDLEWARE_INSTALL_P11KIT_MODULE` (подразумевано **`OFF`** од 5.0)
инсталира p11-kit декларацију за директан PKCS#11 модул самог middleware-а.
Искључен је зато што је регистровани добављач сада клијентски модул агента, а
једна картица треба да нуди једног добављача; укључите га за домаћина без
интерфејса који не покреће агента. Види
[водич за PKCS#11](/sr/user-guide/pkcs11/).

Низводни CMake пројекти троше middleware преко његовог config пакета:

```cmake
find_package(LibreMiddleware CONFIG REQUIRED)

add_executable(my_consumer main.cpp)
target_link_libraries(my_consumer PRIVATE
    LibreSCRS::SmartCard
    LibreSCRS::Signing
)
```

Извезене мете носе простор имена `LibreSCRS::`. До 4.x је извоз био
`LibreMiddleware::` са `LibreSCRS::` пресликавањем поред њега; пресликавања у
5.0 нема, па потрошач који је повезивао `LibreMiddleware::Auth` прелази на
`LibreSCRS::Auth`.

---

## Покретање тестова

Сва спремишта користе Google Test. Све у једном стаблу изградње:

```bash
ctest --test-dir build --output-on-failure
```

Упутите `ctest` на **корен** стабла изградње, не на `build/test`: неколико
поддиректоријума библиотека региструје сопствене пакете тестова, а сужавање на
`build/test` чита један `CTestTestfile.cmake` и тихо покрене део пакета.

Покретање једног теста:

```bash
ctest --test-dir build -R <test_name> --output-on-failure
```

Тестове потпуно искључује `-DBUILD_TESTING=OFF`.

Пакетима заснованим на Qt-у треба платформски додатак без екрана, а D-Bus
пакетима приватна сесијска магистрала:

```bash
QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure
```
