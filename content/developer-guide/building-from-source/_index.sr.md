---
title: "Изградња из изворног кода"
description: "Предуслови, упутства за изградњу и покретање тестова"
---

## Предуслови

| Зависност | Верзија | Напомена |
|---|---|---|
| CMake | 3.24+ | Систем за изградњу |
| C++ компајлер | GCC 12+ или Clang 15+ | Потребна подршка за C++20 |
| Qt 6.6+ | Widgets, PrintSupport, LinguistTools | Само за LibreCelik |
| PC/SC | `libpcsclite-dev` (Linux) | Уграђено на macOS-у |
| OpenSSL 3 | — | Укључено у LibreMiddleware `thirdparty/` |
| UUID | `uuid-dev` (Linux) | Генерисање UUID-а |

---

## Изградња LibreMiddleware-а

LibreMiddleware је самостална C++20 библиотека без зависности од Qt-а.

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
