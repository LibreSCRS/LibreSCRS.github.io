---
layout: "simple"
title: "Signing Integration Guide"
description: "How to integrate LibreMiddleware's digital signing capabilities into your application"
weight: 30
---

LibreMiddleware includes a native C++ digital signing engine that supports five signature formats, four conformance levels, and hardware-backed signing via PKCS#11. This guide explains how to integrate signing into your own application.

## Signature Formats and Levels

The engine produces signatures conforming to the EU eIDAS/ETSI baseline profiles:

| Format | Standard | Input | Output | Packaging |
|---|---|---|---|---|
| PAdES | ETSI EN 319 142 | PDF | Signed PDF | Enveloped |
| CAdES | ETSI EN 319 122 | Any file | `.p7s` (PKCS#7/CMS) | Detached |
| XAdES | ETSI EN 319 132 | Any file | `.xml` (XML-DSIG) | Enveloped or detached |
| JAdES | ETSI EN 319 182 | Any file | `.json` (JWS) | Detached |
| ASiC-E | ETSI EN 319 162 | Any file(s) | `.asice` (ZIP container) | Detached (XAdES inside) |

Each format supports four levels of increasing assurance:

| Level | Content | Requires |
|---|---|---|
| B-B | Basic signature | Signing certificate only |
| B-T | B-B + trusted timestamp | TSA server |
| B-LT | B-T + revocation data (CRL/OCSP) | TSA + revocation sources |
| B-LTA | B-LT + archive timestamp | TSA + revocation sources |

---

## CMake Integration

LibreMiddleware is designed to be consumed via CMake `FetchContent`. Signing support is enabled by default.

```cmake
include(FetchContent)
FetchContent_Declare(
    LibreMiddleware
    GIT_REPOSITORY https://github.com/LibreSCRS/LibreMiddleware.git
    GIT_TAG        v2.0.2
)
FetchContent_MakeAvailable(LibreMiddleware)

target_link_libraries(MyApp PRIVATE LibreSign)
```

For local development, point to a local checkout instead of fetching from Git:

```bash
cmake -B build -DFETCHCONTENT_SOURCE_DIR_LIBREMIDDLEWARE=/path/to/LibreMiddleware
```

### Build Options

| Option | Default | Description |
|---|---|---|
| `BUILD_SIGNING` | `ON` | Enable digital signing support (LibreSign library) |
| `SIGNING_BACKEND` | `native` | Backend selection: `native`, `dss`, or `both`. The DSS backend is deprecated |

The build exports `LIBREMIDDLEWARE_HAS_SIGNING` so downstream projects can conditionally compile signing features.

---

## Minimal Signing Example

```cpp
#include <libresign/signing_service_factory.h>
#include <libresign/types.h>

#include <fstream>
#include <vector>

int main()
{
    // 1. Create the signing service (native backend)
    auto service = libresign::createSigningService(libresign::Backend::Native);
    if (!service || !service->isAvailable()) {
        return 1;
    }

    // 2. Optionally configure trust (EU Trusted Lists for B-LT/B-LTA)
    libresign::TrustConfig trust;
    trust.cacheDirectory = "/tmp/tl-cache";
    trust.trustedLists.push_back({
        .url = "https://ec.europa.eu/tools/lotl/eu-lotl.xml",
        .isLotl = true,
        .eager = true
    });
    service->configure(trust);

    // 3. Load the document to sign
    std::ifstream file("document.pdf", std::ios::binary);
    std::vector<uint8_t> content(
        (std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>()
    );

    // 4. Build the signing request
    libresign::SigningRequest request;
    request.document = std::move(content);
    request.fileName = "document.pdf";
    request.format = libresign::SignatureFormat::PAdES;
    request.level = libresign::SignatureLevel::B_T;
    request.tsa.url = "http://timestamp.digicert.com";

    // 5. Sign via PKCS#11 token
    std::string pin = "1234";  // in production, use SecureBuffer
    auto result = service->sign(
        request,
        "/usr/local/lib/librescrs-pkcs11.so",  // PKCS#11 module path
        libresign::as_pin(pin),          // PIN as byte span
        "SIGN"                           // key alias on the card
    );

    if (!result.success) {
        // result.errorMessage contains the failure reason
        return 1;
    }

    // 6. Write the signed document
    std::ofstream out("document-signed.pdf", std::ios::binary);
    out.write(reinterpret_cast<const char*>(result.signedDocument.data()),
              result.signedDocument.size());
    return 0;
}
```

---

## API Reference

All types live in the `libresign` namespace. Headers are in `libresign/`.

### SigningService

The abstract interface for all signing operations. Obtained via the factory function.

```cpp
// Factory — creates a concrete service instance
std::unique_ptr<SigningService> createSigningService(Backend backend);

enum class Backend { Native, DSS };
```

**Methods:**

| Method | Description |
|---|---|
| `configure(const TrustConfig&)` | Load trusted lists and configure revocation. Optional for B-B/B-T, required for B-LT/B-LTA |
| `sign(request, pkcs11Path, pin, keyAlias, tokenLabel)` | Sign a document. Returns `SigningResult` |
| `isAvailable()` | Check whether the backend is functional |

### SigningRequest

Describes what to sign and how.

| Field | Type | Default | Description |
|---|---|---|---|
| `document` | `vector<uint8_t>` | — | Raw document bytes |
| `fileName` | `string` | — | Original filename (used for format detection in ASiC-E) |
| `format` | `SignatureFormat` | `PAdES` | Target signature format |
| `packaging` | `SignaturePackaging` | `ENVELOPED` | Enveloped or detached |
| `level` | `SignatureLevel` | `B_T` | Conformance level |
| `tsa` | `TSAConfig` | — | Timestamp authority configuration |
| `visual` | `VisualSignatureParams` | disabled | Visual signature overlay (PAdES only) |
| `allowExpiredCertificate` | `bool` | `false` | Allow signing with expired certificates (testing only) |

### SigningResult

| Field | Type | Description |
|---|---|---|
| `success` | `bool` | Whether signing succeeded |
| `signedDocument` | `vector<uint8_t>` | The signed output bytes |
| `errorMessage` | `string` | Human-readable error on failure |

### TrustConfig

Configuration for EU Trusted Lists, used for B-LT and B-LTA levels.

| Field | Type | Default | Description |
|---|---|---|---|
| `trustedLists` | `vector<TrustedListEntry>` | — | Trusted List sources |
| `cacheDirectory` | `string` | — | Disk cache for downloaded lists |
| `crlEnabled` | `bool` | `true` | Fetch CRLs for revocation checking |
| `ocspEnabled` | `bool` | `true` | Use OCSP for revocation checking |

### TSAConfig

| Field | Type | Default | Description |
|---|---|---|---|
| `url` | `string` | — | RFC 3161 timestamp server URL |
| `timeoutSeconds` | `int` | `10` | HTTP timeout for TSA requests |
| `crlEnabled` | `bool` | `true` | CRL checking for B-LT/B-LTA |
| `ocspEnabled` | `bool` | `true` | OCSP checking for B-LT/B-LTA |

---

## PKCS#11 Token Support

The signing engine accesses private keys through PKCS#11. It does not communicate with smart cards directly — all card I/O goes through the PKCS#11 module.

LibreMiddleware ships its own PKCS#11 module (`librescrs-pkcs11.so`) that supports all card types recognized by the middleware plugin system: Serbian eID (CardEdge), PKCS#15-compliant cards, PIV, and OpenSC-backed cards.

You can also use any third-party PKCS#11 module (e.g., OpenSC's `opensc-pkcs11.so`).

**Token selection:** Pass a `tokenLabel` string to `sign()` to select a specific PKCS#11 slot by label. If empty, the service auto-detects the first available token.

**Key selection:** The `keyAlias` parameter matches the `CKA_LABEL` attribute on the private key object. For Serbian eID cards, the signing key label is typically `"SIGN"`.

**PIN handling:** The `pin` parameter is a `std::span<const uint8_t>` — a non-owning view into caller-managed memory. In production code, store the PIN in a `smartcard::SecureBuffer` which automatically zeroes memory on destruction. The signing service does not retain the PIN past the `sign()` call.

---

## Error Handling

The `sign()` method returns a `SigningResult` rather than throwing exceptions. Check `result.success` and read `result.errorMessage` on failure:

```cpp
auto result = service->sign(request, pkcs11Path, pin, keyAlias);
if (!result.success) {
    // Common errors:
    // - "PKCS#11 module not found"
    // - "PIN verification failed"
    // - "TSA server unreachable"
    // - "Certificate has expired"
    log(result.errorMessage);
}
```

The `configure()` method returns `false` if trust list loading fails. This is non-fatal for B-B and B-T levels (which do not require trust lists) but will cause B-LT and B-LTA signing to fail later.
