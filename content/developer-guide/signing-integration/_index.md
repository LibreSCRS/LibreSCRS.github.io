---
layout: "simple"
title: "Signing Integration Guide"
description: "How to integrate LibreMiddleware's digital signing capabilities into your application"
weight: 30
---

LibreMiddleware ships a native C++ digital signing engine that supports five
signature formats, four conformance levels, and hardware-backed signing via
PKCS#11. This guide shows downstream consumers how to integrate it through
the **public `LibreSCRS::Signing` API**.

The signing engine itself lives in the internal `libresign` library under
`lib/libresign/` — every header there is gated by `LIBRESCRS_INTERNAL_BUILD`
and is **not part of the supported consumer surface**. Downstream code links
against the `LibreSCRS::Signing` CMake alias and includes only
`<LibreSCRS/Signing/…>` headers.

## Signature Formats and Levels

The engine produces signatures conforming to the EU eIDAS / ETSI baseline
profiles:

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

LibreMiddleware is designed to be consumed via CMake `FetchContent`. Signing
support is enabled by default. Tags use the bare `X.Y.Z` form (no `v`
prefix):

```cmake
include(FetchContent)
FetchContent_Declare(
    LibreMiddleware
    GIT_REPOSITORY https://github.com/LibreSCRS/LibreMiddleware.git
    GIT_TAG        4.0.0
)
FetchContent_MakeAvailable(LibreMiddleware)

target_link_libraries(MyApp PRIVATE
    LibreSCRS::Signing
    LibreSCRS::Trust
    LibreSCRS::Plugin
    LibreSCRS::SmartCard
    LibreSCRS::Auth
)
```

For local development, point to a local checkout instead of fetching from Git:

```bash
cmake -B build -DFETCHCONTENT_SOURCE_DIR_LIBREMIDDLEWARE=/path/to/LibreMiddleware
```

### Build Options

| Option | Default | Description |
|---|---|---|
| `BUILD_SIGNING` | `ON` | Enable digital signing support (`LibreSCRS::Signing`) |
| `SIGNING_BACKEND` | `native` | Backend selection: `native`, `dss`, or `both`. The DSS backend is a test oracle and is deprecated for production use |

The build exports `LIBREMIDDLEWARE_HAS_SIGNING` so downstream projects can
conditionally compile signing features.

---

## Minimal Signing Example

The example below performs a complete PAdES B-T sign against a card
discovered by the plugin registry. It uses only the public API — every
include is from `<LibreSCRS/…>`.

```cpp
#include <LibreSCRS/Auth/CredentialProvider.h>
#include <LibreSCRS/Plugin/CardPluginService.h>
#include <LibreSCRS/Secure/String.h>
#include <LibreSCRS/Signing/SigningRequest.h>
#include <LibreSCRS/Signing/SigningResult.h>
#include <LibreSCRS/Signing/SigningService.h>
#include <LibreSCRS/Signing/TsaProvider.h>
#include <LibreSCRS/SmartCard/CardSession.h>
#include <LibreSCRS/SmartCard/MonitorService.h>
#include <LibreSCRS/Trust/TrustConfig.h>
#include <LibreSCRS/Trust/TrustStoreService.h>

#include <iostream>

namespace lsc = LibreSCRS;

int main()
{
    // 1. Build the trust store. The factory is noexcept and returns a
    //    usable service even when the network is unreachable — bundled
    //    and (optionally) system anchors are available immediately while
    //    eager Trusted-List fetches run on internal worker threads.
    lsc::Trust::TrustConfig trustConfig;
    trustConfig.cacheDirectory = "/var/cache/myapp/tl-cache";
    // trustConfig.sources.push_back({...});   // optional EU LOTL / national TLs

    auto trustResult = lsc::Trust::TrustStoreService::create(std::move(trustConfig));
    if (!trustResult) {
        std::cerr << "Trust store init failed: "
                  << trustResult.error().userMessage.defaultText << '\n';
        return 1;
    }
    std::shared_ptr<lsc::Trust::TrustStoreService> trust = *trustResult;

    // 2. Construct the SigningService. The TsaProvider is invoked at
    //    sign time for B-T / B-LT / B-LTA levels; staticTsa() is a
    //    convenience factory that always returns the same URL with no
    //    authentication. Pass a default-constructed TsaProvider{} to
    //    disable TSA — B-B signing still works, higher levels then fail
    //    with Status::TsaUnreachable.
    auto tsa = lsc::Signing::staticTsa("http://timestamp.digicert.com");
    auto signingService = std::make_shared<lsc::Signing::SigningService>(trust, std::move(tsa));

    // 3. Discover a card plugin + open a session. CardPluginService scans
    //    the configured plugin directory; MonitorService observes PC/SC
    //    events. Real apps subscribe to MonitorService and look up a
    //    plugin via findPluginForCard(atr) once a card has arrived; the
    //    helpers below collapse that flow into a single app-specific
    //    bootstrap step.
    lsc::Plugin::CardPluginService plugins{"/usr/local/lib/librescrs/plugins"};
    lsc::SmartCard::MonitorService monitor;
    auto session = openFirstSession(monitor, plugins);   // app-specific helper
    if (!session) {
        std::cerr << "No card available\n";
        return 1;
    }
    auto atr = session->atr();                            // std::span<const std::uint8_t>
    auto cardPlugin = plugins.findPluginForCard(atr);
    if (!cardPlugin) {
        std::cerr << "No plugin matches this card's ATR\n";
        return 1;
    }

    // 4. Build the signing request. The engine reads from inputFile and
    //    writes the signed payload to outputFile — there is no
    //    byte-buffer ingestion seam on the public API.
    auto request = lsc::Signing::SigningRequest::Builder{}
                       .inputFile("document.pdf")
                       .outputFile("document-signed.pdf")
                       .format(lsc::Signing::SignatureFormat::Pades)
                       .level(lsc::Signing::SignatureLevel::B_T)
                       .build();

    // 5. PIN provider — invoked by the service when the card requires it.
    //    The provider receives an AuthRequirement describing what to
    //    collect and returns a CredentialResult. In a GUI host this
    //    typically pops a PIN dialog; in batch tools it reads from a
    //    secure prompt or an env var.
    lsc::Auth::CredentialProvider pinProvider =
        [](const lsc::Auth::AuthRequirement&) {
            lsc::Secure::String pin{"1234"};  // host-collected, cleansed on dtor
            return lsc::Auth::CredentialResult::ok({{"pin", std::move(pin)}});
        };

    // 6. Sign. The call blocks for the duration of the operation (PIN
    //    verify + card APDU sign + optional TSA round-trip). GUI hosts
    //    run this on a worker thread.
    auto result = signingService->sign(request, std::move(pinProvider), cardPlugin, session);

    if (result.status != lsc::Signing::SigningResult::Status::Ok) {
        std::cerr << "Signing failed: "
                  << result.userMessage.defaultText << '\n';
        return 1;
    }

    // 7. Success — the signed document is on disk at the path the engine
    //    wrote to (i.e. the outputFile() the request was built with).
    std::cout << "Signed: " << result.outputPath->string() << '\n';
    return 0;
}
```

---

## API Reference

All public types live under the `LibreSCRS::*` PascalCase namespaces. Every
type referenced below has its full Doxygen contract in the corresponding
header under `include/LibreSCRS/`.

### `LibreSCRS::Signing::SigningService`

Public entry point. Constructed once with the trust lifecycle owner and a
TSA callback; reused for many `sign()` calls.

**Construction:**

```cpp
SigningService(std::shared_ptr<Trust::TrustStoreService> trustService,
               TsaProvider tsa);
```

**Signing call (4-arg, `[[nodiscard]]`):**

```cpp
SigningResult sign(const SigningRequest& request,
                   Auth::CredentialProvider credentialProvider,
                   std::shared_ptr<Plugin::CardPlugin> cardPlugin,
                   std::shared_ptr<SmartCard::CardSession> session);
```

The call is blocking and thread-safe across distinct `(cardPlugin, session)`
pairs. A null plugin or session, or an empty `credentialProvider`, returns
`SigningResult::Status::InvalidRequest` rather than throwing.

### `LibreSCRS::Trust::TrustStoreService`

Lifecycle owner of the trust store. Factory is `noexcept` and returns
`std::expected<std::shared_ptr<TrustStoreService>, CreateError>`. Eager
Trusted-List fetches run on internal worker threads; consumers observe
completion via `status()`, `addObserver()`, or the blocking
`waitForEagerFetches()`.

### `LibreSCRS::Signing::SigningRequest`

Immutable signing parameters built through the inner `Builder`. The engine
is file-path based — pass `inputFile()` and `outputFile()`; there is no
byte-buffer overload on the public API. Key builder methods:

| Builder method | Description |
|---|---|
| `inputFile(std::filesystem::path)` | Source document on disk |
| `outputFile(std::filesystem::path)` | Destination path the engine writes to |
| `format(SignatureFormat)` | `Pades` / `Cades` / `Xades` / `Jades` / `AsicE` |
| `level(SignatureLevel)` | `B_B` / `B_T` / `B_LT` / `B_LTA` |
| `packaging(PackagingMode)` | `Enveloped` or `Detached` |
| `reason` / `location` / `contactInfo` | PDF signature dictionary fields (ISO 32000-1 §12.8.1) |
| `certificateLabel(std::string)` | PKCS#11 key alias when the card carries more than one |
| `visualParams(VisualSignatureParams&&)` | PAdES visual signature overlay |
| `tsaOverride(TsaProvider)` | Per-request TSA override; pair with `staticTsa(url)` for a fixed URL |

`Builder::build()` is rvalue-qualified; finalise with
`std::move(builder).build()` and wrap the call in a `try/catch` for
`std::invalid_argument` if you set fields conditionally.

### `LibreSCRS::Signing::SigningResult`

| Field | Type | Description |
|---|---|---|
| `status` | `Status` enum | Always set; check before reading other fields |
| `outputPath` | `std::optional<std::filesystem::path>` | Path the signed document was written to on success |
| `userMessage` | `LocalizedText` | Translator-friendly user-facing message; mandatory in 4.0 |
| `diagnosticDetail` | `std::optional<std::string>` | Developer-facing diagnostic for logs |

`Status` values: `Ok`, `InvalidRequest`, `TrustStoreUnavailable`,
`UserCancelled`, `PinVerificationFailed`, `CardBlocked`, `TsaUnreachable`,
`SigningEngineError`. The enum is append-only; consumer `switch` statements
must include a `default` branch.

### `LibreSCRS::Auth::CredentialProvider`

`SyncProvider<CredentialResult, AuthRequirement>` — a host-supplied callable
that maps an `AuthRequirement` (what the card needs) to a `CredentialResult`
(filled credentials, a user-cancel, or a provider error). The signing
service invokes the provider at most once per card unlock.

### `LibreSCRS::Plugin::CardPlugin` and `LibreSCRS::SmartCard::CardSession`

The plugin drives card-specific operations (signing APDUs, key discovery)
and is obtained from `CardPluginService`. The session encapsulates an open
PC/SC channel and is obtained either through the monitor flow or directly
via `CardSession::open(readerName, plugin)`. The signing service holds
shared ownership of both for the duration of the call.

---

## PKCS#11 Token Support

The signing engine accesses private keys through the `CardPlugin` /
`CardSession` abstraction. Under the hood the plugin layer talks to the
card via the LibreSCRS PKCS#11 module (`librescrs-pkcs11.so`) plus
appropriate card-specific drivers — CardEdge, PKCS#15, PIV, or OpenSC.

Downstream consumers that already drive a PKCS#11 module directly can do
so independently of `LibreSCRS::Signing`; the 4.0 public signing API is
intentionally PKCS#11-agnostic at the seam (plugin + session).

The PIN never persists across the `sign()` call — it is delivered to the
card via `CredentialProvider` (which the host is expected to back with
zero-on-destruct storage such as `LibreSCRS::Secure::Buffer` /
`LibreSCRS::Secure::String`) and discarded immediately after `C_Login`.

---

## PDF Input Tolerance

For PAdES signing, the engine follows Adobe Acrobat Implementation Notes
§H.3 when ingesting PDF input, matching the behaviour of Acrobat, Foxit,
qpdf, and pdfinfo:

- Up to **1024 bytes** of non-PDF prefix before the `%PDF-` header are
  tolerated and stripped (e.g. `multipart/form-data` wrappers from
  web-form uploads).
- Trailing data after the last `%%EOF` is stripped (an optional single
  CR/LF is preserved).
- When `startxref` points to an offset that does not contain the `xref`
  keyword (common after a prefix strip, or a generator bug), the engine
  falls back to scanning the last ~10 KB for a standalone `xref` keyword
  and retries.

If the first 1024 bytes contain no `%PDF-` header the input is still
rejected with a structured `InvalidRequest` result. No caller-side
changes are needed — the tolerance is applied internally during PAdES
ingestion.

---

## Error Handling

`SigningService::sign()` returns a `SigningResult` rather than throwing.
Inspect `result.status` and `result.userMessage` on failure:

```cpp
auto result = signingService->sign(request, pinProvider, cardPlugin, session);
if (result.status != LibreSCRS::Signing::SigningResult::Status::Ok) {
    using S = LibreSCRS::Signing::SigningResult::Status;
    switch (result.status) {
        case S::TrustStoreUnavailable:  /* TL fetch / config rejected     */ break;
        case S::InvalidRequest:         /* null plugin/session, empty cb  */ break;
        case S::UserCancelled:          /* provider returned cancel       */ break;
        case S::PinVerificationFailed:  /* wrong PIN                      */ break;
        case S::CardBlocked:            /* signing PIN blocked by card    */ break;
        case S::TsaUnreachable:         /* B-T+ requested, TSA failed     */ break;
        case S::SigningEngineError:     /* libresign / APDU pipeline      */ break;
        default: break;                 // append-only enum; keep default
    }
    log(result.userMessage.defaultText);
    if (result.diagnosticDetail) {
        log(*result.diagnosticDetail);
    }
}
```

`TrustStoreService::create()` is similarly `[[nodiscard]] noexcept` and
returns `std::expected<…, CreateError>`. Checking the result up front
keeps failure paths explicit; no exception ever propagates across the
public API surface.
