---
title: "Contribute"
layout: "simple"
description: "How to contribute to LibreSCRS"
---

The project is open source. Here's how to contribute.

---

## Ways to Contribute

- **Report a bug** — [LibreCelik issues](https://github.com/LibreSCRS/LibreCelik/issues), [LibreMiddleware issues](https://github.com/LibreSCRS/LibreMiddleware/issues)
- **Suggest a feature** — open an issue on the relevant repository
- **Submit a Pull Request** — see below for setup and conventions

---

## Development Setup

Both projects build with CMake 3.24+ and a C++20 compiler.

```bash
# Clone both repositories
git clone https://github.com/LibreSCRS/LibreCelik.git
git clone https://github.com/LibreSCRS/LibreMiddleware.git

# Build LibreMiddleware
cd LibreMiddleware
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build

# Build LibreCelik with local LibreMiddleware
cd ../LibreCelik
cmake -B build -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_LIBREMIDDLEWARE=../LibreMiddleware
cmake --build build
```

For details, see [Building From Source](/developer-guide/building-from-source/).

---

## Coding Standards

- C++20. Use `std::span`, `std::format`, smart pointers.
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

2. **Middleware plugin** — implement the `CardPlugin` interface in LibreMiddleware. This handles card detection (ATR matching or connection probe) and data reading.

3. **GUI plugin** — implement the `CardWidgetPlugin` interface in LibreCelik. This provides the Qt6 widget that displays the card data.

See the [Architecture Overview](/developer-guide/architecture/) for details on the plugin system and interfaces.

---

## Development Process

- AI-assisted development — we use AI tools as part of the development workflow
- Test-driven development
- Code review on every pull request
- CI pipeline runs tests on all supported platforms
