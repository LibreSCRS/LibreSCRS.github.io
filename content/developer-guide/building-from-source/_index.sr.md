---
layout: "simple"
title: "Изградња из изворног кода"
description: "Предуслови, упутства за изградњу и покретање тестова"
---

Тренутне опције изградње одражавају LibreSCRS 4.1; основа 4.0 подржавала је само STATIC изградњу.

## Предуслови

| Зависност | Верзија | Напомена |
|---|---|---|
| CMake | 3.24+ | Систем за изградњу |
| C++ компајлер | GCC 13+ или Clang 17+ | За LibreMiddleware потребна је подршка за C++23; LibreCelik и даље циља C++20 (прелазак на C++23 је на 4.x роадмапи) |
| Qt 6.6+ | Widgets, PrintSupport, LinguistTools | Само за LibreCelik |
| PC/SC | `libpcsclite-dev` (Linux) | Уграђено на macOS-у |
| OpenSSL 3 | — | Укључено у LibreMiddleware `thirdparty/` |
| UUID | `uuid-dev` (Linux) | Генерисање UUID-а |

---

## Изградња LibreMiddleware-а

LibreMiddleware је самостална C++23 библиотека без зависности од Qt-а.

```bash
git clone https://github.com/LibreSCRS/LibreMiddleware.git
cd LibreMiddleware
cmake -B build
cmake --build build
```

Покретање тестова:

```bash
cd build && ctest --output-on-failure
```

---

## Изградња LibreCelik-а

LibreCelik је Qt6 GUI апликација. Аутоматски преузима LibreMiddleware преко CMake `FetchContent`.

```bash
git clone https://github.com/LibreSCRS/LibreCelik.git
cd LibreCelik
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

---

## Локални развој

Када радите на оба пројекта истовремено, усмерите LibreCelik на локалну копију LibreMiddleware-а уместо преузимања са GitHub-а:

```bash
cmake -B build -DFETCHCONTENT_SOURCE_DIR_LIBREMIDDLEWARE=/path/to/LibreMiddleware
cmake --build build
```

На овај начин се измене у LibreMiddleware-у одмах преузимају без потребе за commit-овањем или push-овањем.

---

## Опције изградње (LibreMiddleware 4.1)

LibreMiddleware 4.1.0 увео је две опције система за изградњу које утичу на пакување и употребу са стране клијената.

`LIBREMIDDLEWARE_BUILD_SHARED` (`ON` | `OFF`, подразумевано `OFF`) бира врсту библиотеке. Када је `ON`, сваки `LibreSCRS_*` циљ се гради као `.so`/`.dylib`, што је неопходно за 4.x клијенте (укључујући планирани LibreKDE интерфејс) који LibreMiddleware учитавају као зависност током извршавања. Када је `OFF`, граде се статичке архиве.

`LIBREMIDDLEWARE_INSTALL_P11KIT_MODULE` (подразумевано `ON`) инсталира `packaging/librescrs.module` у `${CMAKE_INSTALL_DATADIR}/p11-kit/modules/`. Након `cmake --install`, апликације које препознају p11-kit (Firefox, Chromium, GnuPG-gpgsm, Kleopatra, Thunderbird, Evolution) аутоматски проналазе `librescrs-pkcs11.so` без подешавања по апликацији.

CMake Config пакет (`LibreMiddlewareConfig.cmake`) се генерише и инсталира **само** када је `LIBREMIDDLEWARE_BUILD_SHARED=ON`. Клијентски CMake пројекти којима је потребан `find_package(LibreMiddleware CONFIG)` морају стога да конфигуришу горњу изградњу са `-DLIBREMIDDLEWARE_BUILD_SHARED=ON` и да покрену `cmake --install`.

Једном инсталиран, LibreMiddleware се у клијентским CMake пројектима користи преко свог config пакета:

```cmake
find_package(LibreMiddleware CONFIG REQUIRED)

add_executable(my_consumer main.cpp)
target_link_libraries(my_consumer PRIVATE
    LibreSCRS::SmartCard
    LibreSCRS::Pkcs11Inject
)
```

`LibreSCRS::*` ALIAS циљеви чине јавну површину; повежите се са њима, а не са основним именима CMake циљева.

Статичка изградња остаје подразумевана ради компатибилности са линијом издања 4.0.

---

## Покретање тестова

Оба пројекта користе Google Test (аутоматски преузет преко CMake-а). Покретање свих тестова:

```bash
cd build && ctest --output-on-failure
```

Покретање појединачног теста:

```bash
cd build && ctest -R <test_name> --output-on-failure
```

Потпуно искључивање тестова:

```bash
cmake -B build -DBUILD_TESTING=OFF
```

### Проблем са LibreCelik покретачем тестова

`ctest` може пријавити "No tests found" због проблема са временским усклађивањем `gtest_discover_tests`. Ако се то деси, покрените тест бинарне датотеке директно:

```bash
cd build
./test/LibreCelikTests
./test/CardWidgetPluginRegistryTests
./test/AsyncCardReaderTests
```
