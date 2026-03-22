---
title: "Developer Guide"
description: "Technical documentation for developers extending LibreSCRS"
layout: "simple"
---

This guide is for developers who want to understand the LibreSCRS internals, build from source, or extend the system with new card plugins.

## Topics

- [Architecture Overview]({{< ref "developer-guide/architecture" >}}) — system components, data flow, plugin system, and design patterns
- [Building From Source]({{< ref "developer-guide/building-from-source" >}}) — prerequisites, build instructions, and running tests

More pages will be added as APIs stabilize:

- **Plugin APIs** — writing middleware `CardPlugin` and GUI `CardWidgetPlugin` implementations
- **Standards Reference** — ISO 7816-4, PC/SC, PKCS#11, PKCS#15, ICAO 9303
