---
title: "Developer Guide"
description: "Technical documentation for developers extending LibreSCRS"
layout: "simple"
---

This guide is for developers who want to understand the LibreSCRS internals, build from source, or extend the system with new card plugins.

## Release notes

- [What's new in 4.2]({{< ref "developer-guide/whats-new-in-4-2" >}}) — reader-list snapshot API, CardData accessors, in-process session sharing, and migration from 4.1
- [What's new in 4.1]({{< ref "developer-guide/whats-new-in-4-1" >}}) — secure channels and the (now-superseded) PKCS#11 attach surface

## Getting started

- [Architecture Overview]({{< ref "developer-guide/architecture" >}}) — system components, data flow, plugin system, and design patterns
- [Building From Source]({{< ref "developer-guide/building-from-source" >}}) — prerequisites, build instructions, and running tests

## Signing

- [Signing Architecture]({{< ref "developer-guide/signing-architecture" >}}) — native signing engine, format support, and certificate handling
- [Signing Integration Guide]({{< ref "developer-guide/signing-integration" >}}) — integrating digital signing into applications using LibreMiddleware
- [Multi-Sign: appendSigner]({{< ref "developer-guide/signing-append-signer" >}}) — adding signatures to an already-signed container

## Smart-card and secure messaging

- [Secure Channels]({{< ref "developer-guide/secure-channels" >}}) — the PACE / BAC / plain channel protocol classes
- [CardSession Secure-Messaging API]({{< ref "developer-guide/card-session-sm" >}}) — activating channels and managing credentials from a session
- [Reader-List Snapshot API]({{< ref "developer-guide/monitor-reader-list" >}}) — the 4.2 `MonitorService::subscribeReaderList` snapshot stream
- [CardData Convenience Accessors]({{< ref "developer-guide/card-data-access" >}}) — the 4.2 Qt-free `textValue` / `textValueAt` helpers
- [In-Process Session Sharing]({{< ref "developer-guide/pkcs11-session-injection" >}}) — reusing a live `CardSession` across the in-process PKCS#11 sign path

For plugin API details, see the `CardPlugin` and `CardWidgetPlugin` interfaces in the [Architecture Overview]({{< ref "developer-guide/architecture" >}}).
