---
layout: "simple"
title: "Building From Source"
description: "Prerequisites, build instructions, and running tests"
---

Current build options reflect LibreSCRS 5.0. The product is built in
dependency order — middleware, agent, host, then a client — and every step
after the first consumes the previous one as an installed CMake package:

```
LibreMiddleware  →  LibreAgent  →  LibreLinux  →  LibreCelik / LibreKDE
```

## Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| CMake | 3.24+ | 3.28+ where a `FetchContent` path is used |
| C++ compiler | GCC 13+ or Clang 17+ | C++23 |
| Qt 6 | Core, DBus, Widgets, PrintSupport, LinguistTools | LibreCelik, LibreKDE, the prompter, and `LibreAgent::ClientQt` |
| PC/SC | `libpcsclite-dev` (Linux) | built in on macOS |
| OpenSSL 3 | — | bundled in LibreMiddleware `thirdparty/` |
| sdbus-c++ | 2.0+ | LibreLinux (agent and prompter D-Bus) |
| systemd | `libsystemd-dev` | LibreLinux (event loop, `sd_notify`) |
| p11-kit | — | LibreLinux (resolves the PKCS#11 module and config directories) |
| UUID | `uuid-dev` (Linux) | UUID generation |

---

## Building LibreMiddleware

A standalone C++23 library collection with no Qt dependency.

```bash
git clone https://github.com/LibreSCRS/LibreMiddleware.git
cd LibreMiddleware
cmake -B build -DCMAKE_INSTALL_PREFIX=<prefix>
cmake --build build
cmake --install build
```

Run the test suite:

```bash
ctest --test-dir build --output-on-failure
```

Install it before going further: everything downstream resolves it with
`find_package(LibreMiddleware 5.0 CONFIG)`, not by fetching it.

---

## Building LibreAgent

The platform-neutral agent core, the wire library, and the Qt client library.
Which of them you get is a per-component option, because a Qt-free host and a
Qt client want different halves of this repository:

| Option | Default | Gives you |
|---|---|---|
| `LIBREAGENT_BUILD_CORE` | `ON` | `LibreAgent::Core` — links LibreMiddleware and OpenSSL |
| `LIBREAGENT_BUILD_WIRE` | `ON` | `LibreAgent::Wire` — links nothing first-party |
| `LIBREAGENT_BUILD_CLIENT_QT` | `OFF` | `LibreAgent::ClientQt` — links Qt6 |
| `LIBREAGENT_BUILD_PKCS11_FACADE` | `OFF` | the PKCS#11 core a host builds its module on |

```bash
git clone https://github.com/LibreSCRS/LibreAgent.git
cd LibreAgent
cmake -B build -DCMAKE_PREFIX_PATH=<prefix> -DCMAKE_INSTALL_PREFIX=<prefix>       -DLIBREAGENT_BUILD_CLIENT_QT=ON       -DLIBREAGENT_BUILD_PKCS11_FACADE=ON
cmake --build build
cmake --install build
```

A consumer names the components it needs. Asking for the package without a
component list makes it probe every component it can find and run each one's
`find_dependency()` — which drags Qt6 into a build that wanted none:

```cmake
find_package(LibreAgent 5.0 CONFIG REQUIRED COMPONENTS Core Wire)
```

---

## Building LibreLinux

The Linux host: the `librescrs-agent` daemon, the KDE prompter, and the
client PKCS#11 module. It consumes an **installed** LibreAgent rather than
fetching one:

```bash
git clone https://github.com/LibreSCRS/LibreLinux.git
cd LibreLinux
cmake -B build -DCMAKE_PREFIX_PATH=<prefix> \
      -DLIBRELINUX_USE_INSTALLED_AGENT_CORE=ON
cmake --build build
cmake --install build
```

`LIBRELINUX_USER_INSTALL=ON` puts the systemd user unit, the D-Bus service
files and the p11-kit module config under your own prefix instead of the system
one — which is what you want for a working checkout, and not what a package
wants.

---

## Building LibreCelik

The Qt6 GUI application. It consumes `LibreAgent::ClientQt` through CMake
`FetchContent`, pinned by `cmake/libreagent.pin`; it links no PC/SC stack of
its own, because all card access happens in the agent.

```bash
git clone https://github.com/LibreSCRS/LibreCelik.git
cd LibreCelik
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

---

## Building LibreKDE

The Plasma 6 integration. It needs LibreAgent 5.0 or newer installed **with its
`ClientQt` component** — a bare `cmake -B build` no longer configures:

```bash
git clone https://github.com/LibreSCRS/LibreKDE.git
cd LibreKDE
cmake -B build -DCMAKE_PREFIX_PATH=<prefix>
cmake --build build
```

---

## Local Development

When working on two repositories at once, point the consumer at your local
checkout instead of the pinned fetch:

```bash
# LibreCelik against a working LibreAgent
cmake -B build -DFETCHCONTENT_SOURCE_DIR_LIBREAGENT=/path/to/LibreAgent
```

That proves your **sources**, not the pin. A build that passes this way says
nothing about whether the pinned revision would also build, so bump the pin and
re-run before relying on it.

---

## Build options (LibreMiddleware 5.0)

`LIBREMIDDLEWARE_BUILD_SHARED` (default `ON`) builds every `LibreSCRS_*` target
as a `.so`/`.dylib`, which is what downstream consumers load at runtime; `OFF`
produces static archives. The CMake Config package is generated and installed
only in the shared configuration, so a downstream `find_package(LibreMiddleware
CONFIG)` needs it.

`LIBREMIDDLEWARE_INSTALL_P11KIT_MODULE` (default **`OFF`** since 5.0) installs
the p11-kit declaration for the middleware's own direct PKCS#11 module. It is
off because the registered provider is now the agent's client module and one
card should offer one provider; turn it on for a headless host that runs no
agent. See the [PKCS#11 guide](/user-guide/pkcs11/).

Downstream CMake projects consume the middleware through its config package:

```cmake
find_package(LibreMiddleware CONFIG REQUIRED)

add_executable(my_consumer main.cpp)
target_link_libraries(my_consumer PRIVATE
    LibreSCRS::SmartCard
    LibreSCRS::Signing
)
```

The exported targets carry the `LibreSCRS::` namespace. Up to 4.x the export
was `LibreMiddleware::` with a `LibreSCRS::` mirror beside it; the mirror is
gone in 5.0, so a consumer that linked `LibreMiddleware::Auth` moves to
`LibreSCRS::Auth`.

---

## Running Tests

All repositories use Google Test. Run everything in a build tree with:

```bash
ctest --test-dir build --output-on-failure
```

Point `ctest` at the build **root**, not at `build/test`: several library
subdirectories register their own suites, and scoping to `build/test` reads one
`CTestTestfile.cmake` and silently runs a fraction of the suite.

To run a single test:

```bash
ctest --test-dir build -R <test_name> --output-on-failure
```

Disable tests entirely with `-DBUILD_TESTING=OFF`.

Qt-based suites need a headless platform plugin, and the D-Bus suites need a
private session bus:

```bash
QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure
```
