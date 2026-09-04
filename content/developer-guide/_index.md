---
title: "Developer Guide"
description: "Technical documentation for developers extending LibreSCRS"
layout: "simple"
---

This guide is for developers who want to understand the LibreSCRS internals, build from source, or extend the system with new card plugins.

## Release notes

- [What's new in 5.0]({{< ref "developer-guide/whats-new-in-5-0" >}}) — the card agent, CSCA passport trust anchors, the move to `.so.5`, and plugin ABI 9
- [What's new in 4.2]({{< ref "developer-guide/whats-new-in-4-2" >}}) — reader-list snapshot API, CardData accessors, in-process session sharing, and migration from 4.1
- [What's new in 4.1]({{< ref "developer-guide/whats-new-in-4-1" >}}) — secure channels and the (now-superseded) PKCS#11 attach surface

## Getting started

- [Architecture Overview]({{< ref "developer-guide/architecture" >}}) — system components, data flow, plugin system, and design patterns
- [Building From Source]({{< ref "developer-guide/building-from-source" >}}) — prerequisites, build instructions, and running tests

## The card agent

- [Core Architecture]({{< ref "developer-guide/agent-architecture" >}}) — `AgentCore`, the identity tokens, and the four interfaces a platform host implements
- [Card Operations]({{< ref "developer-guide/agent-operations" >}}) — the operation catalogue, the per-reader worker, the prompt gate and the rate limiter
- [Presence and Caching]({{< ref "developer-guide/agent-presence-and-cache" >}}) — which card is where, what is remembered between operations, and what is not
- [The Wire Protocol]({{< ref "developer-guide/agent-wire-protocol" >}}) — framing, the two error axes, the PKCS#11 broker and the anchor import
- [Building a Qt Client]({{< ref "developer-guide/agent-client-qt" >}}) — linking `LibreAgent::ClientQt`, issuing an operation, reading its outcome

## SDK reference

- [API Policy]({{< ref "developer-guide/sdk-reference/api-policy" >}}) — versioning, the public surface, deprecation, the plugin ABI and the SONAME
- [Expected Result Handling]({{< ref "developer-guide/sdk-reference/expected-result-handling" >}}) — when an API throws, when it returns a status, and the `std::expected` mandate
- [Trust, Certificates and Secure Values]({{< ref "developer-guide/trust-and-certificates" >}}) — trust anchors, the CSCA master-list import, certificate parsing, cleansing secret types

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
- [PIN & Credential Lifecycle]({{< ref "developer-guide/pin-lifecycle" >}}) — per-credential lifecycle records from `getPINList` and the activation entry points

For plugin API details, see the `CardPlugin` and `CardWidgetPlugin` interfaces in the [Architecture Overview]({{< ref "developer-guide/architecture" >}}).
