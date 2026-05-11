---
layout: "simple"
title: "Signing Architecture"
description: "Internal architecture of the LibreMiddleware digital signing engine"
weight: 40
---

This page describes the internal architecture of the LibreMiddleware signing engine for contributors who want to understand how the system works, add new signature formats, or debug signing issues.

> Looking to **consume** the signing engine from your own application?
> The public seam is `LibreSCRS::Signing::SigningService` —
> see [Signing Integration Guide]({{< ref "developer-guide/signing-integration" >}}).
> The rest of this page covers what lives behind that seam.

## Public seam: `LibreSCRS::Signing`

Downstream consumers never touch `libresign::*`. They link against
`LibreSCRS::Signing` and call:

```cpp
SigningService(std::shared_ptr<Trust::TrustStoreService>, TsaProvider);

SigningResult sign(const SigningRequest&,
                   Auth::CredentialProvider,
                   std::shared_ptr<Plugin::CardPlugin>,
                   std::shared_ptr<SmartCard::CardSession>);
```

`LibreSCRS::Signing::SigningService` is a thin pimpl-backed facade that
performs request validation, resolves the trust snapshot from the injected
`TrustStoreService`, drives the credential provider, and forwards to the
internal `libresign::SigningService`. The libresign types described below
are reachable **only** through this facade.

## Trust lifecycle (4.0): `LibreSCRS::Trust::TrustStoreService`

The trust subsystem has its own lifecycle owner separate from signing.
`TrustStoreService::create(TrustConfig)` is `[[nodiscard]] noexcept` and
returns `std::expected<std::shared_ptr<TrustStoreService>, CreateError>`.
The factory builds the local anchor set synchronously (bundled
`thirdparty/certs/` + optional OS root store) and kicks off all configured
Trusted-List fetches on internal worker threads. The signing service holds
a `shared_ptr<TrustStoreService>` for its full lifetime, so eager TL fetches
populate the same `TrustStore` that `sign()` observes; lazy fetches that
happen during a `sign()` call merge into the same store, ensuring the
certificate viewer, plugin registry, and signing service all share one
trust universe.

Consumers observe fetch progress via three orthogonal mechanisms:

- `status()` returns an `AggregateStatus` snapshot (`Loading` / `Ready` /
  `Degraded`).
- `addObserver(cb)` registers a callback for state transitions — the
  GUI-friendly path.
- `waitForEagerFetches(deadline, token)` blocks until every eager source
  settles; intended for tests, CLI tooling, and headless consumers.

The service is move-disabled and reference-shared, so the same trust universe
is naturally consumed by multiple signing services or non-signing tools
(certificate viewer, plugin registry) running in the same process.

## End-to-End Signing Flow

The complete flow from user action to signed document:

```
1. User clicks "Sign" in LibreCelik
   └─ SignPage wizard collects: document, format, level, TSA, visual params

2. LibreCelik builds SigningRequest and calls SigningService::sign()
   └─ PIN passed as span<const uint8_t> from SecureBuffer

3. NativeSigningService::sign()
   ├─ Opens Pkcs11Token (loads PKCS#11 module, logs in with PIN)
   ├─ Reads signing certificate + chain from token
   └─ Dispatches to format module based on request.format

4. Format module (e.g., PAdESModule::sign())
   ├─ Prepares the signature container (PDF incremental save, CMS, XML, JSON, or ZIP)
   ├─ Computes document digest (SHA-256)
   ├─ Calls Pkcs11Token::sign(hash) → raw signature bytes from card
   ├─ Embeds signature + certificate chain into container
   └─ If level >= B-T: calls TSAClient::timestamp(hash)
      └─ Sends RFC 3161 request to TSA server
      └─ Embeds TimeStampToken in signature

5. If level >= B-LT:
   ├─ RevocationClient fetches CRL + OCSP responses for certificate chain
   └─ Format module embeds revocation data in signature

6. If level == B-LTA:
   └─ Archive timestamp added over entire signature + revocation data

7. NativeSigningService returns SigningResult { success, signedDocument }

8. LibreCelik saves the signed document to disk
```

---

## Module Structure

The signing engine lives in `lib/libresign/` within LibreMiddleware. It is organized into three layers:

Public headers live under `include/libresign/` (top-level types) and `include/libresign/native/` (native backend classes). Implementations and backend-internal helpers live under `src/`.

### Core Service Layer

| File | Purpose |
|---|---|
| `include/libresign/signing_service.h` | `SigningService` abstract interface — `configure()`, `sign()`, `isAvailable()` |
| `include/libresign/signing_service_factory.h` | Factory function `createSigningService(Backend)` |
| `include/libresign/types.h` | Data types: `SigningRequest`, `SigningResult`, `TrustConfig`, `TSAConfig`, enums |
| `include/libresign/trust_store_manager.h` | `TrustStoreManager` — aggregates system, bundled, and TL-derived certificates across signing and non-signing consumers |

### Format Modules

Each signature format is implemented as an independent module. All modules follow the same pattern: accept a document + certificate + signing callback, produce signed output bytes.

| Module | File | Standard |
|---|---|---|
| PAdES | `src/native/pades_module.cpp` | PDF incremental save with CMS signature |
| CAdES | `src/native/cades_module.cpp` | Detached CMS/PKCS#7 signature |
| XAdES | `src/native/xades_module.cpp` | XML Digital Signature with XAdES properties |
| JAdES | `src/native/jades_module.cpp` | JSON Web Signature with JAdES header |
| ASiC-E | `src/native/asic_module.cpp` | ZIP container with XAdES signature (uses miniz) |

Format modules receive a `Pkcs11Token&` reference for signing operations. The token handles PKCS#11 session management, key lookup, and raw signing internally.

### Infrastructure

| Component | Files | Purpose |
|---|---|---|
| `Pkcs11Token` | `include/libresign/native/pkcs11_token.h` + `src/native/pkcs11_token.cpp` | PKCS#11 session management — module loading, login, key lookup, raw sign, certificate extraction |
| `TSAClient` | `include/libresign/native/tsa_client.h` + `src/native/tsa_client.cpp` | RFC 3161 timestamp requests via HTTP (libcurl) |
| `RevocationClient` | `include/libresign/native/revocation_client.h` + `src/native/revocation_client.cpp` | CRL and OCSP fetching for B-LT/B-LTA levels |
| `SigningProvider` | `include/libresign/native/signing_provider.h` + `src/native/signing_provider.cpp` | Abstraction over Pkcs11Token for downstream consumers |
| `TrustedListParser` | `include/libresign/native/trusted_list_parser.h` + `src/native/trusted_list_parser.cpp` | XML parser for EU Trusted Lists (LOTL and TL) |
| `TlCache` | (internal) `src/native/tl_cache.h/.cpp` | Disk cache for downloaded Trusted List XML files |
| `TlSignatureVerifier` | (internal) `src/native/tl_signature_verifier.h/.cpp` | XML-DSIG verification of Trusted List signatures |
| `PinnedTlCerts` | (internal) `src/native/pinned_tl_certs.h/.cpp` | Compiled-in LOTL signing certificates used to bootstrap trust |
| PDF parser | (internal) `src/native/pdf_parser.h/.cpp` | Minimal PDF parser for PAdES incremental save — finds xref, appends signature dictionary |
| OpenSSL RAII | (internal) `src/native/openssl_raii.h` | RAII wrappers for OpenSSL types (`BIO`, `X509`, `EVP_PKEY`, etc.) |

---

## Trust Model

The signing engine uses a three-tier trust model for certificate validation:

### Tier 1: System Certificates

The operating system's default certificate store. Used as the root of trust for TLS connections (TSA, CRL/OCSP endpoints) and as a fallback for certificate chain building.

### Tier 2: Bundled Certificates

Certificates shipped with LibreMiddleware in `thirdparty/certs/`. These include root CAs for Serbian government PKI infrastructure that may not be in system stores. Used for card certificate chain verification.

### Tier 3: Trusted List-Derived Certificates

Certificates extracted from EU Trusted Lists (TL/LOTL). The engine downloads and parses the EU List of Trusted Lists, follows links to national trusted lists, and extracts signing CA certificates. These are used for B-LT and B-LTA validation — they provide the trust anchors that connect the signer's certificate to an EU-recognized trust service provider.

**Authentication chain:** The LOTL itself is signed. The engine verifies the LOTL signature using pinned certificates (`pinned_tl_certs.cpp`) that are compiled into the library. National TLs are verified using certificates found in the LOTL. This creates a chain: pinned cert verifies LOTL signature, LOTL provides certs that verify national TL signatures, national TLs provide trust service certificates.

```
Pinned LOTL signing certificates (compiled in)
  └─ verify → EU LOTL XML signature
       └─ contains → national TL signing certificates
             └─ verify → national TL XML signatures
                   └─ contain → trust service provider certificates
                         └─ validate → signer's certificate chain
```

---

## DSS Validation Oracle

The project includes a DSS (Digital Signature Services) backend that can be used as a **validation oracle** in tests. DSS is the EU reference implementation for signature creation and validation, maintained by the European Commission.

**What it does:** The DSS backend delegates signing to a running DSS server via REST API. This is useful for cross-validating that signatures produced by the native engine are accepted by the EU reference implementation.

**Test usage:** When `SIGNING_BACKEND=both` is set, tests can create a signature with the native backend and validate it with DSS, or vice versa. This catches subtle format compliance issues that unit tests alone would miss.

**Note:** The DSS backend is deprecated for production use. It exists solely as a test oracle. The native backend is the production signing engine.

---

## Data Flow: LibreCelik to LibreMiddleware

LibreCelik (the GUI) and LibreMiddleware (the engine) are separate projects with a clean boundary. Here is how signing data crosses that boundary:

```
┌─────────────────────────────────────────────────┐
│                 LibreCelik (GUI)                 │
│                                                  │
│  ┌────────────┐    ┌──────────────────────────┐ │
│  │  SignPage   │───▶│ SigningRequest            │ │
│  │  (wizard)   │    │ ┌─ document bytes        │ │
│  │             │    │ ├─ format (PAdES/CAdES/..)│ │
│  │ Collects:   │    │ ├─ level (B-B/B-T/..)    │ │
│  │ - file path │    │ ├─ TSA URL               │ │
│  │ - format    │    │ ├─ visual sig params     │ │
│  │ - level     │    │ └─ PIN (SecureBuffer)     │ │
│  │ - PIN       │    └──────────┬───────────────┘ │
│  └────────────┘               │                  │
│                               ▼                  │
├───────────────────────────────┬──────────────────┤
│              LibreMiddleware  │                   │
│                               │                  │
│  ┌────────────────────────────▼───────────────┐  │
│  │         NativeSigningService               │  │
│  │                                            │  │
│  │  ┌──────────────┐  ┌───────────────────┐   │  │
│  │  │ Pkcs11Token  │  │  Format Module    │   │  │
│  │  │ (card I/O)   │  │  (PAdES/CAdES/..) │   │  │
│  │  └──────┬───────┘  └────────┬──────────┘   │  │
│  │         │ raw sig           │ signed doc    │  │
│  │         ▼                   ▼               │  │
│  │  ┌──────────────────────────────────────┐   │  │
│  │  │ SigningResult { success, bytes, err } │   │  │
│  │  └──────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

**Key design decisions:**

- **No Qt dependency** — the entire signing engine is pure C++23 with no Qt types. LibreCelik converts between Qt types (`QString`, `QByteArray`) and standard types (`std::string`, `std::vector<uint8_t>`) at the boundary.
- **No card protocol knowledge** — the signing engine does not send APDU commands or know about card types. All card access goes through PKCS#11, which is a standard interface that any compliant token can satisfy.
- **PIN is never stored** — the PIN travels as a non-owning `span<const uint8_t>` from the GUI's `SecureBuffer` through to the PKCS#11 `C_Login` call. No intermediate copy persists after the call returns.
- **Format modules are stateless** — each `sign()` call is self-contained. There is no session state between calls, making the engine safe for concurrent use from multiple threads.

---

## Adding a New Signature Format

To add a new format module:

1. Create `include/libresign/native/newformat_module.h` and `src/native/newformat_module.cpp`
2. Implement a `sign()` function that accepts the document, `Pkcs11Token&`, and format-specific parameters
3. Register the format in `NativeSigningService::sign()` by adding a case for the new `SignatureFormat` enum value
4. Add the new enum value to `SignatureFormat` in `types.h`
5. Add the source files to `lib/libresign/CMakeLists.txt`
6. Write tests — use the DSS oracle (`SIGNING_BACKEND=both`) to validate format compliance
