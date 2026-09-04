---
title: "Contribute"
layout: "simple"
description: "How to contribute to LibreSCRS"
---

The project is open source. Here's how to contribute.

---

## Ways to Contribute

- **Report a bug** — in the repository the bug is in: [LibreMiddleware](https://github.com/LibreSCRS/LibreMiddleware/issues) (card communication, plugins, signing), [LibreAgent](https://github.com/LibreSCRS/LibreAgent/issues) (agent core, wire protocol, Qt client library), [LibreLinux](https://github.com/LibreSCRS/LibreLinux/issues) (the daemon, the prompter, the PKCS#11 module), [LibreCelik](https://github.com/LibreSCRS/LibreCelik/issues) (the Qt GUI), [LibreKDE](https://github.com/LibreSCRS/LibreKDE/issues) (Plasma). If you are unsure, the client you were using is a fine place to start.
- **Suggest a feature** — open an issue on the relevant repository
- **Submit a Pull Request** — see below for setup and conventions

---

## Development Setup

Every repository builds with CMake 3.24+ and a C++23 compiler (GCC 13+ /
Clang 17+). They are built in dependency order, and each one after the first
consumes the previous as an installed package rather than fetching it:

```bash
PREFIX=$PWD/prefix

git clone https://github.com/LibreSCRS/LibreMiddleware.git
git clone https://github.com/LibreSCRS/LibreAgent.git
git clone https://github.com/LibreSCRS/LibreLinux.git
git clone https://github.com/LibreSCRS/LibreCelik.git

# 1. middleware
cmake -S LibreMiddleware -B LibreMiddleware/build \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX"
cmake --build LibreMiddleware/build && cmake --install LibreMiddleware/build

# 2. agent — ClientQt is OFF by default; a Qt client needs it
cmake -S LibreAgent -B LibreAgent/build \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" \
      -DCMAKE_PREFIX_PATH="$PREFIX" \
      -DLIBREAGENT_BUILD_CLIENT_QT=ON -DLIBREAGENT_BUILD_PKCS11_FACADE=ON
cmake --build LibreAgent/build && cmake --install LibreAgent/build

# 3. Linux host — daemon, prompter, PKCS#11 module
cmake -S LibreLinux -B LibreLinux/build \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$PREFIX" \
      -DLIBRELINUX_USE_INSTALLED_AGENT_CORE=ON -DLIBRELINUX_USER_INSTALL=ON
cmake --build LibreLinux/build && cmake --install LibreLinux/build

# 4. the GUI, against a working agent checkout
cmake -S LibreCelik -B LibreCelik/build -DCMAKE_BUILD_TYPE=Release \
      -DFETCHCONTENT_SOURCE_DIR_LIBREAGENT=$PWD/LibreAgent
cmake --build LibreCelik/build
```

LibreCelik consumes **LibreAgent**, not the middleware: it links no PC/SC stack
of its own, because card access happens in the agent.

For details, see [Building From Source](/developer-guide/building-from-source/).

---

## Coding Standards

- C++23 throughout. Use `std::span`, `std::format`, `std::expected`, smart pointers. A public factory that can fail returns `std::expected` — see [Expected result handling](/developer-guide/sdk-reference/expected-result-handling/).
- Compiler warnings: `-Wall -Wextra -Wpedantic`
- Naming: `camelCase` for variables, `PascalCase` for types. No trailing underscores on member variables.
- SPDX license headers on all source files.
- Every change must include tests.

---

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Push and open a Pull Request
5. Describe what the change does and why
6. CI must pass
7. Code review before merge

---

## Adding Support for a New Card

If you want to add support for a new smart card type:

1. **Analyze the card** — use the `card_mapper` CLI tool (part of LibreMiddleware) to explore the card's file system and APDU responses. This is a useful first step to understand what the card contains.

2. **Middleware plugin** — implement the `CardPlugin` interface in LibreMiddleware. This handles card detection (ATR matching or connection probe) and data reading. Declare the plugin ABI version with `LIBRESCRS_DECLARE_CARD_PLUGIN`; the rules are in the [API policy](/developer-guide/sdk-reference/api-policy/).

3. **GUI plugin** — implement the `CardWidgetPlugin` interface in LibreCelik. This provides the Qt6 widget that displays the card data.

See the [Architecture Overview](/developer-guide/architecture/) for details on the plugin system and interfaces.

---

## Development Process

- AI-assisted development — we use AI tools as part of the development workflow
- Test-driven development
- Code review on every pull request
- CI pipeline runs tests on all supported platforms
