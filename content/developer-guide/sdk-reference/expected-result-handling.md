---
title: "Handling std::expected results"
description: "How to consume LM 4.0 std::expected fallible factories — short-circuit, monadic chain, kind dispatch"
weight: 30
aliases:
  - /dev/expected-result-handling/
---

# Handling `std::expected` results

LibreMiddleware 4.0 returns `std::expected<T, E>` from every public fallible factory. This page shows the canonical idioms for consuming them.

## The three factories

| Factory | Return | Error type |
|---|---|---|
| `LibreSCRS::Certificate::ParsedCertificate::fromDer(span)` | `ParsedCertificate` | `ParsedCertificate::ParseError` |
| `LibreSCRS::SmartCard::CardSession::open(string)` | `CardSession` | `OpenError` |
| `LibreSCRS::Trust::TrustStoreService::create(TrustConfig)` | `std::shared_ptr<TrustStoreService>` | `TrustStoreService::CreateError` |

Every Error type carries:

- `enum class Kind` — coarse classification (additive growth in minor versions)
- `LocalizedText userMessage` — mandatory translator-friendly text
- `std::optional<std::string> diagnosticDetail` — dev-facing detail (logs, telemetry)

## Idiom 1: short-circuit on failure (preferred)

```cpp
auto result = LibreSCRS::SmartCard::CardSession::open("MyReader 0");
if (!result) {
    std::cerr << "Could not open session: "
              << result.error().userMessage.defaultText << "\n";
    return;
}
LibreSCRS::SmartCard::CardSession session = std::move(*result);
```

## Idiom 2: monadic chaining (C++23 `transform` / `or_else`)

```cpp
auto sharedSession = LibreSCRS::SmartCard::CardSession::open("MyReader 0")
    .transform([](auto s) { return std::make_shared<LibreSCRS::SmartCard::CardSession>(std::move(s)); })
    .or_else([](auto err) -> std::expected<std::shared_ptr<LibreSCRS::SmartCard::CardSession>,
                                            LibreSCRS::SmartCard::OpenError> {
        log_warning(err.userMessage.defaultText);
        return std::unexpected{err};
    });
```

## Idiom 3: pattern dispatch on error kind

```cpp
if (!result) {
    using K = LibreSCRS::SmartCard::OpenError::Kind;
    switch (result.error().kind) {
        case K::ReaderUnavailable: showReaderError();   break;
        case K::NoCardPresent:     showInsertPrompt();  break;
        case K::ProtocolError:     showProtocolError(); break;
    }
}
```

## Mandatory `userMessage` discipline

Every Error type carries a non-empty `LocalizedText userMessage`. Hosts may forward it to translation catalogs (`qtTrId` for Qt, `NSLocalizedString` for AppKit/SwiftUI, `ki18n` for KF6) by the `key` field; every key has an English `defaultText` fallback so an untranslated host still has readable text.

The `userMessage.key` follows the convention `librescrs.error.<domain>.<specific>` — e.g. `librescrs.error.cert.derInvalid`, `librescrs.error.trust.configInvalid`.

## Why `std::expected` and not `std::optional` / `variant` / `shared_ptr<T>`?

LM 3.x used three different shapes for the same "fallible factory" concept; 4.0 unifies. The single-shape approach:

- Forces a non-empty user-facing message on every failure — `std::optional` couldn't enforce this
- Removes the `std::variant<T, E>` + `std::get_if<T>(&result)` ceremony in favour of `result.has_value()` / `result.error()`
- Eliminates the `nullptr`-on-fail vestige from the trust-store factory

