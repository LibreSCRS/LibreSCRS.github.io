---
layout: "simple"
title: "Multi-Sign: appendSigner"
description: "How to add additional signers to an already-signed document"
weight: 35
---

`LibreSCRS::Signing::SigningService::appendSigner` extends an existing
signed document with one additional signer, preserving every prior
signer's bytes and attributes. This is the API to use whenever a
co-signing, counter-signing, or parallel multi-signature flow is
required — never re-`sign()` a previously-signed payload.

## Public Signature

```cpp
[[nodiscard]] SigningResult
SigningService::appendSigner(
    const SigningRequest&          request,
    std::span<const std::uint8_t>  priorSignature,
    std::span<const std::uint8_t>  originalDocument,
    Auth::CredentialProvider       credentialProvider,
    std::shared_ptr<Plugin::CardPlugin>     cardPlugin,
    std::shared_ptr<SmartCard::CardSession> session);
```

Format is **inferred from `priorSignature`** (PDF / XML / JSON / CMS
SEQUENCE / ZIP magic) and overrides any value set in `request.format`.
The signer-side parameters in `request` (level, TSA configuration,
visual appearance, contactInfo) apply to the **new** signer only; prior
signers' attributes are left untouched.

`originalDocument` is mandatory for DETACHED priors (CAdES, XAdES
detached, JAdES) — the spec does not embed the original payload in a
detached container, so the engine cannot recover it. For ENVELOPED
priors (PAdES, XAdES enveloped) `originalDocument` can be empty; pass a
non-empty span to opt into a tamper-check assertion against the
recovered payload.

## When to Use

| Scenario | Call |
|---|---|
| First / only signer | `sign(...)` |
| Add a co-signer to an existing PDF / XML / etc. | `appendSigner(...)` |
| Re-sign with a different key | `appendSigner(...)` |
| Bulk-sign N independent documents | N × `sign(...)` |

The dispatcher in `sign()` will detect a previously-signed input via
`looksSignedAlready` and reject the request with
`SigningResult::Status::InvalidRequest`. The intent is explicit: choose
`appendSigner` deliberately when extending, `sign` deliberately when
creating.

## Per-Format Semantics

| Format | Container effect of `appendSigner` |
|---|---|
| PAdES | New incremental update appended after the prior `%%EOF`; new `/Sig` dict + xref/trailer chain via `/Prev` |
| XAdES (enveloped) | New `<ds:Signature>` sibling inserted under the document root; references re-anchored |
| XAdES (detached) | New `<ds:Signature>` merged into the `asic:Signatures` wrapper; Ids re-minted |
| CAdES | New `SignerInfo` added to the existing `SignedData` `signerInfos` SET |
| JAdES | New JWS appended to the JSON serialisation `signatures` array |
| ASiC-E | New XAdES signature added inside the existing container's `META-INF/` |

## Example

```cpp
#include <LibreSCRS/Auth/CredentialProvider.h>
#include <LibreSCRS/Secure/String.h>
#include <LibreSCRS/Signing/SigningRequest.h>
#include <LibreSCRS/Signing/SigningResult.h>
#include <LibreSCRS/Signing/SigningService.h>

#include <fstream>
#include <vector>

namespace lsc = LibreSCRS;

std::vector<std::uint8_t> readBytes(const std::filesystem::path& p)
{
    std::ifstream in{p, std::ios::binary};
    return {std::istreambuf_iterator<char>{in}, {}};
}

int main()
{
    // (trust + signingService + plugin + session set up as in the
    //  Signing Integration Guide; omitted here for brevity)

    // 1. First signer — Alice signs a fresh PDF with sign().
    auto firstReq = lsc::Signing::SigningRequest::Builder{}
                        .inputFile("contract.pdf")
                        .outputFile("contract-alice.pdf")
                        .format(lsc::Signing::SignatureFormat::Pades)
                        .level(lsc::Signing::SignatureLevel::B_T)
                        .build();
    auto first = signingService->sign(firstReq, alicePinProvider,
                                      cardPlugin, session);

    // 2. Second signer — Bob extends the same PDF with appendSigner.
    //    inputFile/outputFile in the request are NOT used by appendSigner
    //    for the priorSignature/originalDocument seams (the API is
    //    span-based) but ARE used for any builder-required fields and
    //    for the output write target. Provide both for forward
    //    compatibility.
    auto secondReq = lsc::Signing::SigningRequest::Builder{}
                         .inputFile("contract-alice.pdf")
                         .outputFile("contract-alice-bob.pdf")
                         .format(lsc::Signing::SignatureFormat::Pades)
                         .level(lsc::Signing::SignatureLevel::B_T)
                         .reason("Approved by Bob")
                         .build();

    const auto prior = readBytes("contract-alice.pdf");
    auto second = signingService->appendSigner(
        secondReq,
        std::span<const std::uint8_t>{prior},
        std::span<const std::uint8_t>{},      // empty: enveloped
        bobPinProvider,
        cardPlugin,
        session);

    if (second.status != lsc::Signing::SigningResult::Status::Ok) {
        std::cerr << "appendSigner failed: "
                  << second.userMessage.defaultText << '\n';
        return 1;
    }
}
```

For a DETACHED prior (CAdES `.p7s`, detached XAdES), pass the original
payload bytes in `originalDocument`:

```cpp
const auto prior    = readBytes("contract.pdf.p7s");
const auto original = readBytes("contract.pdf");           // mandatory
auto result = signingService->appendSigner(
    request, prior, original, pinProvider, cardPlugin, session);
```

## Known Limitations

- **PAdES and XAdES multi-sign are validated end-to-end for B-B**;
  higher-level multi-sign (B-T / B-LT / B-LTA) is under active
  development and not yet recommended for production B-LTA documents.
  In particular, multi-sign interaction with `/DocTimeStamp` and
  archive timestamps is being hardened against strict validators.
- **CAdES `appendSigner` with PKCS#11 keys** is undergoing rework to
  align `CMS_final` with the engine's PKCS#11-wrapped `EVP_PKEY`
  pipeline; expect interim failures with `error:17000085:CMS
  routines::no private key`.
- **XAdES detached multi-sign** does not yet re-mint Ids during the
  merge step, which trips strict DSS validators with "duplicate
  occurrences of the signature"; treat as work-in-progress.
- **ASiC-E multi-sign** through the DSS oracle bridge is impacted by an
  open content-type handling bug on the oracle side; native validation
  is unaffected.

These limitations are tracked in the project's 4.2-track bug ledger;
the basic `sign()` paths (single signer) remain fully supported
end-to-end. Consumers integrating `appendSigner` for production
multi-sign should validate produced documents through their target
validator (Adobe Acrobat, EU DSS, an Adobe Approved Trust List
validator) before declaring acceptance.
