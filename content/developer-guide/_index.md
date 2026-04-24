---
title: "Developer Guide"
description: "Technical documentation for developers extending LibreSCRS"
layout: "simple"
---

This guide is for developers who want to understand the LibreSCRS internals, build from source, extend the system with new card plugins, or consume the C++20 SDK from another application.

## Topics

- [Architecture Overview]({{< ref "developer-guide/architecture" >}}) — system components, public API layout, plugin model, ownership + error-handling conventions, card-insert-to-display data flow.
- [Signing Architecture]({{< ref "developer-guide/signing-architecture" >}}) — native signing engine, format support, certificate handling, end-to-end signing flow.
- [Signing Integration Guide]({{< ref "developer-guide/signing-integration" >}}) — integrating digital signing into applications using LibreMiddleware.
- [SDK Reference]({{< ref "developer-guide/sdk-reference" >}}) — per-namespace narrative reference for `LibreSCRS::{Auth,SmartCard,Plugin,Signing,Secure}`, plugin authoring walk-through, migration notes from 3.x.
- [API Policy]({{< ref "developer-guide/sdk-reference/api-policy" >}}) — versioning (SemVer), deprecation cadence, validation vs. runtime error handling, plugin ABI rules.
- [Building From Source]({{< ref "developer-guide/building-from-source" >}}) — prerequisites, build commands, running tests, sdk-consumer example.
