---
layout: "simple"
title: "Expected Result Handling"
description: "When a LibreSCRS API throws and when it returns a status, and the std::expected mandate for every fallible public factory"
---

LibreSCRS separates two kinds of failure, and the reporting mechanism has to
match the kind. Getting this wrong is what produces an API where every call
site needs both a `try` block and a status `switch`.

The rest of the policy — versioning, the public surface, deprecation, the
plugin ABI — is on the
[API policy page](/developer-guide/sdk-reference/api-policy/).

## 1. Construction and validation failures — throw

Builders, factories and constructors that validate caller-supplied inputs throw
`std::invalid_argument`, or a more specific `std::logic_error` subtype, with a
message naming the bad field. This includes:

- `SigningRequest::Builder::build() &&` — a missing required field (input or
  output file, format), or a format-level mismatch.
- `VisualSignatureParams::Builder::rect(x, y, w, h)` — non-positive width or
  height.
- `VisualSignatureParams::Builder::pageIndex(i)` — a negative index.
- `AuthRequirement::forSigning(...)`, `forChangePin(...)`, `forUnblockPin(...)`
  — an empty PIN label.

The caller is expected to scope exception handling around the construction
phase — a wizard page's "Next" click, an SDK consumer's setup — and then treat
the constructed object as valid for the rest of its life.

## 2. Runtime and environmental failures — status-code result

Methods that can fail for environmental reasons — card absent, file I/O,
network, user cancellation — return a result type carrying a `Status` enum.
These methods **do not throw** across the public API boundary. This includes:

- `SigningService::sign(...)` → `SigningResult`, with `SigningResult::Status`.
- `CardPlugin::verifyPIN(...)`, `changePIN(...)`, `unblockPIN(...)` →
  `PINResult` (plugin ABI).
- `CardPluginRegistry`'s constructor — it catches `dlopen` failures, factory
  throws and ABI mismatches internally; each file scanned produces a
  `LoadOutcome` entry in `loadReport()` instead of propagating an exception.

Engine-internal errors that genuinely cannot be classified as one of the
`Status` values are reported as `SigningResult::Status::SigningEngineError`
plus a `diagnosticDetail` string for logs. Callers never receive a thrown
exception from `sign()`.

## 3. Pure accessors — `noexcept` where possible

Getters — `SigningRequest::inputFile()`, `TrustConfig::trustedListFile`,
pimpl-backed `operator==` — are `noexcept` and return by const reference or by
value as appropriate. The lifetime of a returned reference is documented on
each accessor.

## 4. Why the split

Throwing at construction makes validation tractable: the caller scopes
exception handling around the construction phase and then treats the object as
valid throughout its lifetime. Mixing throw and status-code within a single
method is the anti-pattern this rule exists to avoid.

An SDK consumer writes:

```cpp
// Validation phase — may throw
try {
    auto request = std::move(SigningRequest::Builder{}
                     .inputFile(inPath)
                     .outputFile(outPath)
                     .format(SignatureFormat::Pades)
                     .level(SignatureLevel::B_LT))
                 .build();

    // Runtime phase — status-code results
    auto result = signingService->sign(request, credProvider, plugin, session);
    switch (result.status) {
        case SigningResult::Status::Ok:            /* ... */ break;
        case SigningResult::Status::UserCancelled: /* ... */ break;
        // ...
    }
} catch (const std::invalid_argument& e) {
    // Builder validation failed — show the message
}
```

## 5. Fallible factories — the `std::expected` mandate

Every public LibreMiddleware factory whose *construction* can fail returns
`std::expected<T, E>`, where `E` is a per-domain error struct of this shape:

- `enum class Kind` — coarse classification; grows additively in minor
  versions;
- `LocalizedText userMessage` — mandatory, never empty;
- `std::optional<std::string> diagnosticDetail` — developer-facing detail.

Per-domain error types nest inside the factory class
(`ParsedCertificate::ParseError`, `OpenError`, `CreateError`) to keep namespace
scoping tight. Shape reuse across factories is by convention.

`std::optional<T>` (silent failure), `std::variant<T, E>` (tagged union) and
`std::shared_ptr<T>` (nullptr on failure) are **not** permitted as
fallible-factory return shapes from 4.0 onward. Each of the three loses
something the mandate keeps: the reason, the type of the reason, and the
guarantee that a caller who ignores the failure gets a compiler diagnostic
rather than a null dereference.

The public `std::expected` factories:

| Factory | Error type |
|---|---|
| `Certificate::ParsedCertificate::fromDer` | `Certificate::ParsedCertificate::ParseError` |
| `SmartCard::CardSession::open` | `SmartCard::OpenError` |
| `Trust::TrustStoreService::create` | `Trust::TrustStoreService::CreateError` |
| `Plugin::acquireChannelForProfile` | `SecureChannel::ChannelActivationError` |

The first three migrated in 4.0. `Plugin::acquireChannelForProfile` — a
free-function factory returning
`std::expected<SmartCard::ActiveChannelHolder, …>` — was added later under the
same mandate. Its `ChannelActivationError` is an enum outcome rather than the
canonical `{Kind, LocalizedText, optional<string>}` struct, because holder
acquisition surfaces a single channel-activation status; the `std::expected`
shape is the contract point, not the particular error type.

```cpp
auto session = LibreSCRS::SmartCard::CardSession::open(readerName);
if (!session) {
    const auto& error = session.error();          // SmartCard::OpenError
    show(error.userMessage);                      // never empty
    log(error.diagnosticDetail.value_or("none")); // developer-facing
    return;
}
// session is valid here — no null check, no status re-read
useCard(**session);
```

Two consequences worth stating outright. First, the error carries a
`LocalizedText` that is guaranteed non-empty, so a host never has to invent a
message for a failure it does not recognise. Second, ignoring the failure does
not compile into a silent success: there is no valid `T` to reach without
first asking whether one exists.
