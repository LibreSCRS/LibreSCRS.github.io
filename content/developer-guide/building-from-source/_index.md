---
layout: "simple"
title: "Building From Source"
description: "Prerequisites, build instructions, and running tests"
---

Current build options reflect LibreSCRS 4.2; the 4.0 baseline supported only the STATIC build.

## Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| CMake | 3.24+ | Build system |
| C++ compiler | GCC 13+ or Clang 17+ | C++23 support required for LibreMiddleware; LibreCelik still targets C++20 (bump to C++23 is on the 4.x roadmap) |
| Qt 6.6+ | Widgets, PrintSupport, LinguistTools | LibreCelik only |
| PC/SC | `libpcsclite-dev` (Linux) | Built-in on macOS |
| OpenSSL 3 | — | Bundled in LibreMiddleware `thirdparty/` |
| UUID | `uuid-dev` (Linux) | UUID generation |

---

## Building LibreMiddleware

LibreMiddleware is a standalone C++23 library with no Qt dependency.

```bash
git clone https://github.com/LibreSCRS/LibreMiddleware.git
cd LibreMiddleware
cmake -B build
cmake --build build
```

Run the test suite:

```bash
cd build && ctest --output-on-failure
```

---

## Building LibreCelik

LibreCelik is the Qt6 GUI application. It fetches LibreMiddleware automatically via CMake `FetchContent`.

```bash
git clone https://github.com/LibreSCRS/LibreCelik.git
cd LibreCelik
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

---

## Local Development

When working on both projects simultaneously, point LibreCelik to your local LibreMiddleware checkout instead of fetching from GitHub:

```bash
cmake -B build -DFETCHCONTENT_SOURCE_DIR_LIBREMIDDLEWARE=/path/to/LibreMiddleware
cmake --build build
```

This way changes to LibreMiddleware are picked up immediately without committing or pushing.

---

## Build options (LibreMiddleware 4.2)

LibreMiddleware 4.1.0 introduced two build-system options that affect packaging and downstream consumption; they carry forward unchanged in 4.2.

`LIBREMIDDLEWARE_BUILD_SHARED` (`ON` | `OFF`, default `OFF`) selects the library kind. When `ON`, every `LibreSCRS_*` target is built as a `.so`/`.dylib`, which is required for downstream 4.x consumers (including the planned LibreKDE host) that load LibreMiddleware as a runtime dependency. When `OFF`, the static archives are produced.

`LIBREMIDDLEWARE_INSTALL_P11KIT_MODULE` (default `ON`) installs `packaging/librescrs.module` to `${CMAKE_INSTALL_DATADIR}/p11-kit/modules/`. After `cmake --install`, p11-kit-aware applications (Firefox, Chromium, GnuPG-gpgsm, Kleopatra, Thunderbird, Evolution) discover `librescrs-pkcs11.so` automatically with no per-application configuration.

The CMake Config package (`LibreMiddlewareConfig.cmake`) is generated and installed **only** when `LIBREMIDDLEWARE_BUILD_SHARED=ON`. Downstream CMake projects that need `find_package(LibreMiddleware CONFIG)` must therefore configure the upstream build with `-DLIBREMIDDLEWARE_BUILD_SHARED=ON` and run `cmake --install` first.

Once installed, downstream CMake projects consume LibreMiddleware through its config package:

```cmake
find_package(LibreMiddleware CONFIG REQUIRED)

add_executable(my_consumer main.cpp)
target_link_libraries(my_consumer PRIVATE
    LibreSCRS::SmartCard
    LibreSCRS::Signing
)
```

The `LibreSCRS::*` ALIAS targets are the public surface; link against them rather than the underlying CMake target names.

The static build remains the default for compatibility with the 4.0 release line.

---

## Running Tests

Both projects use Google Test (auto-fetched via CMake). Run all tests with:

```bash
cd build && ctest --output-on-failure
```

To run a single test:

```bash
cd build && ctest -R <test_name> --output-on-failure
```

Disable tests entirely with:

```bash
cmake -B build -DBUILD_TESTING=OFF
```

### LibreCelik test runner gotcha

`ctest` may report "No tests found" due to a `gtest_discover_tests` timing issue. If this happens, run the test binaries directly:

```bash
cd build
./test/LibreCelikTests
./test/CardWidgetPluginRegistryTests
./test/AsyncCardReaderTests
```
