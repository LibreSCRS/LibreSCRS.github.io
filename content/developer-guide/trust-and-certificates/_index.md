---
layout: "simple"
title: "Trust, Certificates and Secure Values"
description: "LibreMiddleware's Trust, Certificate, Secure and SecureChannel surfaces — trust anchors, the CSCA master-list import, certificate parsing, and cleansing secret types"
weight: 45
---

Twelve public LibreMiddleware headers make up the trust and certificate
surface: `Trust/` (4), `Certificate/` (3), `Secure/` (2) and `SecureChannel/`
(3).

Two of these groups are worth reading before you write anything new, for
opposite reasons. `Secure::String` and `Secure::Buffer` are the types you are
expected to reuse rather than reinvent; `Trust::CscaMasterList` is a surface
whose *defaults* are the substance, and a caller cannot check them from
outside.

## Cleansing secrets: `Secure::String` and `Secure::Buffer`

Both zero their storage on destruction and on move-from, through a cleansing
allocator hook plus an explicit pass over short-string-optimised bytes that
never reach the allocator. Neither is a general-purpose container.

They differ in exactly one respect, deliberately:

| | `Secure::String` | `Secure::Buffer` |
|---|---|---|
| Copy | **copyable**, each copy cleansed independently | **move-only**, copy deleted |
| For | human-typed secrets — PINs, passphrases, bearer tokens | derived or binary secrets — key bytes, APDU responses, signing intermediates |

That asymmetry is intentional and not drift. A text secret usually wants to sit
inside a `std::optional` or a configuration struct and travel through function
arguments, and forbidding copies would cost more than it buys. A byte secret is
more naturally passed through a single owner by `std::move`, and there copy
deletion prevents an accidental duplicate of key material.

Both are **thread-compatible**: distinct instances may be used in parallel
without external synchronisation, a single instance may not. Pass ownership
across threads by moving; share read-only access through independent copies,
never through references to one shared instance.

The project's own rule is to reach for these before inventing anything — a new
type has to be functionally distinct *and* reused at least twice to justify
existing at all.

## Reading a certificate

`Certificate::ParsedCertificate` is the read-only view over a DER-encoded
X.509 certificate. Its factory is fallible, and follows the
[`std::expected` mandate](/developer-guide/sdk-reference/expected-result-handling/):

```cpp
#include <LibreSCRS/Certificate/ParsedCertificate.h>

auto parsed = LibreSCRS::Certificate::ParsedCertificate::fromDer(der);
if (!parsed) {
    show(parsed.error().userMessage);     // ParseError, never empty
    return;
}

const auto subject = parsed->subject();               // DistinguishedName
const auto notAfter = parsed->notAfter();             // system_clock::time_point
const auto usage   = parsed->keyUsage();              // optional<vector<KeyUsageBit>>
const auto sans    = parsed->subjectAlternativeNames();
```

The accessors cover what a certificate viewer or a policy check needs: subject
and issuer, serial, version, validity window, signature algorithm (as an
`ObjectIdentifier` and as a description), public key info, key usage and
extended key usage, subject and issuer alternative names, and basic
constraints. The optional-returning accessors are absent when the extension is
absent — which is a different statement from an empty list, and the difference
matters for key usage in particular.

`Certificate::DistinguishedName` and `Certificate::ObjectIdentifier` are the
two value types those accessors return.

## `TrustStore` and `TrustStoreService`

`TrustStore` is the composed anchor store the signing engine validates chains
against:

```cpp
[[nodiscard]] ChainStatus validateChain(std::span<const CertificateView> chain) const;  // leaf first
[[nodiscard]] std::optional<TrustAnchor> findIssuerOf(CertificateView certDer) const;
[[nodiscard]] std::vector<TrustAnchor> enumerableAnchors() const;
```

A `TrustAnchor` carries the DER bytes plus a human-readable **provenance tag**,
so a surface can say where an anchor came from rather than showing an
unattributed certificate.

`TrustStoreService` owns the lifecycle. It is the asynchronous, non-throwing
factory that replaced the legacy manager deleted in 4.0:

```cpp
auto service = LibreSCRS::Trust::TrustStoreService::create(trustConfig);
if (!service) { /* CreateError, with its Kind and userMessage */ }

std::shared_ptr<const TrustStore> store = (*service)->trustStore();
```

Consumers — the signing service, the plugin registry, hosts — take a
`shared_ptr<TrustStoreService>` by pure constructor injection.

Beyond the store it exposes what a UI needs in order to be honest about
incomplete trust material: a per-source `SourceStatus`, an `AggregateStatus`,
`sourceStatuses()` naming each source, an observer for fetch completion, and
`waitForEagerFetches(deadline, token)` for a caller that wants to block on
startup fetches with a deadline and a cancellation token.

### Eager versus lazy trusted lists

```cpp
struct TrustedListSource {
    std::string url;
    bool lotl  = false;   // this source is a List Of Trusted Lists
    bool eager = false;   // fetch at configure time rather than at sign time
};
```

`eager` defaults to **false**, and the default is a decision rather than an
oversight: an offline host, or a consumer that never asks for a signature level
requiring a trusted-list anchor, is not forced into a startup HTTPS round-trip.
A deployment that would rather fail loudly at startup opts back in per source.

Note what `lotl` implies about cost. A List Of Trusted Lists points at further
lists, so a lazy LOTL source makes the *first* signature that needs it fetch
the LOTL plus the lists it names.

## Importing an ICAO CSCA master list

`Trust/CscaMasterList.h` is three functions and no state, and it is the newest
surface here. It is published rather than left to callers because a host that
grew its own would grow an OpenSSL dependency, a CMS verifier and a path
builder alongside it — and would have to rediscover two verification defaults
and one path-building flag that decide whether genuine documents are accepted.

The header declares **no OpenSSL type**, and must not: anchors, certificates
and fingerprints all cross the boundary as bytes, so a consumer including a
trust header does not inherit the bundled OpenSSL declarations into its own
translation units.

```cpp
std::expected<VerifiedMasterList, MasterListError>
parseAndVerifyMasterList(const std::vector<std::uint8_t>& der,
                         const std::array<std::uint8_t, kSpkiSha256Size>* expectedSpkiSha256);

std::optional<std::array<std::uint8_t, kSpkiSha256Size>>
spkiSha256FromCertificateDer(/* publisher certificate */);

bool signerChainsToAnyAnchor(const std::vector<std::uint8_t>& signerCertDer,
                             const std::vector<std::vector<std::uint8_t>>& anchorsDer);
```

### What verification does, in order

1. The bytes decode as one CMS `ContentInfo`, or the answer is
   `NotAMasterList`.
2. **Every** `SignerInfo` is verified over the content the object carries.
3. If a fingerprint was supplied, *some* signer's SubjectPublicKeyInfo
   fingerprint must equal it.
4. The anchors are read, and a failure there reaches the caller unchanged.

Four things about that sequence are load-bearing, and none of them is visible
from the signature.

**"Signer" means a certificate that verified a `SignerInfo`** — never one the
object merely carries. A CMS certificate bag is unauthenticated, so a stranger
can plant the trusted publisher's certificate beside a list of their own
without touching a signature. The claim established is "the pinned key signed
this", not "the pinned certificate travels with this".

**Step 4 is a barrier, not a formality.** Only the signed `contentType`
attribute is under the signature; the `eContentType` field beside it is not. An
object genuinely signed by the pinned signer, over genuine master-list bytes,
under some other content type and relabelled afterwards, passes steps 2 and 3
outright. Comparing the two places is the only thing that stops it.

**Steps 2 and 3 are in that order deliberately.** Comparing the fingerprint
first would answer "does this fingerprint match" about a list whose signature
does not hold — a question with no security content, since anyone may copy a
certificate into an object they did not sign. So a list that both fails its
signature and names an unexpected signer is reported as `BadSignature`.

**No chain is built.** The signer's certificate is not chained, and is not
checked for expiry, key usage, extended key usage, basic constraints or
revocation. Identity rests entirely on the pinned fingerprint, which the caller
obtained some other way. That is not an omission: a master list is what
*supplies* trust anchors, so at first import there is nothing to chain it to,
and once identity rests on a pinned key the certificate around it is a
container rather than a credential. Two of those checks would refuse perfectly
good lists — expiry, because a master list outlives by years the key that
signed it; extended key usage, because the CMS default demands
`emailProtection`, so it is precisely the correctly ICAO-profiled certificate
that such a check turns away.

The function remembers nothing between calls. Pinning across imports is the
caller's to store.

### Pinning the key, not the certificate

`spkiSha256FromCertificateDer()` is **the only supported way** to produce the
value the verifier compares against, and there are two obvious ways to get it
wrong. It is not the hash of the certificate: a publisher renews its
certificate while keeping its key, and every renewal would then change the pin.

### Following a lawful rotation

`signerChainsToAnyAnchor()` is the decision the verifier deliberately does not
make: accept a new publisher if it chains to an anchor the list already trusted
carried.

**Any anchor may terminate the chain, self-signed or not**, and that is
load-bearing rather than tidy. A CSCA **link certificate** carries the same
subject and public key as a country's new self-signed root but is signed by the
*outgoing* key — so it is not self-signed, and ICAO master lists carry link
certificates beside self-signed ones. A path builder insisting on a self-signed
terminus would answer `false` about a signer that authority genuinely issued,
whenever the link certificate is the only anchor held for it, or merely the one
reached first among anchors sharing a subject.

**The answer contains no statement about time**, at either end. An expired
signer chains, and so does an expired or not-yet-valid anchor. A signer's key
lives months while what it signed lives years, so a lapsed signer is the
ordinary case rather than the suspicious one. A caller that needs a date
checked must check it, and must not read one into this.

What *is* enforced, so this is not read as "no checks": every signature in the
chain, the basic constraints that stop a leaf acting as a CA mid-chain, and the
key usage that lets an issuer sign certificates. Revocation is not consulted.

One question, and three situations share one answer: "no anchors were
configured", "none of them decoded" and "it does not chain" are all `false`. A
caller that must distinguish them knows its own configuration and can say so.

### A worked import

```cpp
using namespace LibreSCRS::Trust;

// First import: accept any signer, and record who it was.
auto first = parseAndVerifyMasterList(bytes, nullptr);
if (!first) { return refuse(first.error()); }

store.remember(first->signerSpkiSha256, first->anchors);   // caller's storage

// A later list from the same publisher: pin the recorded key.
auto next = parseAndVerifyMasterList(newBytes, &recordedFingerprint);
if (!next) {
    if (next.error() == MasterListError::SignerMismatch) {
        // The key changed. Lawful rotation, or an attack — they look identical
        // from here, so ask whether the new signer descends from what we hold.
        if (signerChainsToAnyAnchor(newSignerCertDer, heldAnchors)) {
            // follow the rotation, and record the new fingerprint
        }
    }
    return refuse(next.error());
}
```

Every returned error is a refusal: there is no "unknown" case. A call either
yields anchors or names the first check that failed, and rejections are silent
— the error is the whole diagnosis, and nothing is logged.

## Secure channel parameters

`SecureChannel/PaceParams.h` and `BacParams.h` carry the parameters for the two
ePassport channel-establishment protocols. `ChannelErrors.h` carries the
lifecycle state and the activation error taxonomy:

```cpp
enum class ChannelState : std::uint8_t { Open, Closed, Failed };
enum class ChannelActivationError : std::uint8_t {
    None, SelectAppletFailed, WrongSecret, ProtocolFailure,
    PacePinBlocked, PaceUnsupported, /* ... */
};
```

`Failed` means the channel was invalidated — by a status word indicating a
secure-messaging fault, or by a MAC verification failure — and the caller
should drop it and re-activate rather than retrying on it.

Two of these values dropped a `Pace` prefix in the 4.x line, because the BAC
path returns them too: `WrongSecret` and `ProtocolFailure`. `PacePinBlocked`
and `PaceUnsupported` keep theirs, since BAC never returns them. The
[API policy](/developer-guide/sdk-reference/api-policy/) records why that
rename was an in-place correction rather than a deprecation cycle.

Most consumers never touch these types directly: they hand a request to
`CardSession`, which owns the channel lifetime. See
[Secure Channels](/developer-guide/secure-channels/) and the
[CardSession secure-messaging API](/developer-guide/card-session-sm/).

## Related pages

- [API policy](/developer-guide/sdk-reference/api-policy/)
- [Expected result handling](/developer-guide/sdk-reference/expected-result-handling/)
- [The agent's wire protocol](/developer-guide/agent-wire-protocol/)
- [Secure Channels](/developer-guide/secure-channels/)
