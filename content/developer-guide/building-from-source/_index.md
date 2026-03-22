---
layout: "simple"
title: "Building From Source"
description: "Prerequisites, build instructions, and running tests"
---

## Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| CMake | 3.24+ | Build system |
| C++ compiler | GCC 12+ or Clang 15+ | C++20 support required |
| Qt 6.6+ | Widgets, PrintSupport, LinguistTools | LibreCelik only |
| PC/SC | `libpcsclite-dev` (Linux) | Built-in on macOS |
| OpenSSL 3 | — | Bundled in LibreMiddleware `thirdparty/` |
| UUID | `uuid-dev` (Linux) | UUID generation |

---

## Building LibreMiddleware

LibreMiddleware is a standalone C++20 library with no Qt dependency.

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
