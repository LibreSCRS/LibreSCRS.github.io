---
title: "LibreSCRS 4.0.0 — first stable of the 4.0 cycle"
date: 2026-05-11
summary: "LibreMiddleware 4.0.0 + LibreCelik 4.0.0 released. C++23 core, ABI v6, native PAdES/XAdES/JAdES/CAdES/ASiC-E signing, RFC 5280 trust chain, eMRTD PACE, Serbian eID + AET SafeSign + PIV + generic PKCS#15 cards."
draft: false
---

LibreSCRS 4.0.0 lands today. After two release candidates and extensive
community testing on Linux and macOS, both
**LibreMiddleware 4.0.0** and **LibreCelik 4.0.0** carry GPG-signed git
tags and cosign-signed release artifacts.

## What's in 4.0

- **C++23 core** with `std::expected`-based fallible-factory API
  surface, `LocalizedText` i18n metadata, and `CancelToken` for
  cooperative cancellation.
- **Native PAdES / XAdES / JAdES / CAdES / ASiC-E signing** via
  `LibreSCRS::Signing::SigningService` — no external signing daemon.
- **Auto-fit visual signature layout** (`layoutVisualSignature`) —
  preview in the wizard renders pixel-exact against the embedded
  PAdES output.
- **RFC 5280 trust chain validation** with eIDAS qcStatements
  conformance.
- **eMRTD PACE** for contactless passport reading; **CardEdge,
  PKCS#15, PIV** providers; **OpenSC fallback** in the card-plugin
  path.
- **Bundled CardEdge OpenSC external driver** built against OpenSC
  0.26.1 and 0.27.1, available as a sidecar tarball until upstream
  OpenSC ships our srbeid driver in a numbered release.

## Known issue — multi-card PIN routing

When more than one Serbian smart card is inserted simultaneously and
the user initiates a signing flow, the PIN entry prompt may be
associated with a different slot than the certificate selected.
Single-card setups are unaffected. The fix is architectural — a
Card+Slot model — and shipped as the headline feature of 4.1.0.

## Downloads

- [LibreMiddleware 4.0.0 release](https://github.com/LibreSCRS/LibreMiddleware/releases/tag/4.0.0)
- [LibreCelik 4.0.0 release](https://github.com/LibreSCRS/LibreCelik/releases/tag/4.0.0)

All artifacts ship with `.sigstore.json` cosign signatures; verify
with `cosign verify-blob --bundle <name>.sigstore.json <name>`.
