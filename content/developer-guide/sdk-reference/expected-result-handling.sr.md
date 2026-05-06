---
title: "Руковање std::expected резултатима"
description: "Како конзумирати LM 4.0 std::expected фабрике које могу да отказу — кратки спој, монадично ланчање, диспеч по врсти"
weight: 30
aliases:
  - /dev/expected-result-handling/
---

# Руковање `std::expected` резултатима

LibreMiddleware 4.0 враћа `std::expected<T, E>` из сваке јавне фабрике која може да откаже. Ова страница приказује канонске идиоме за њихово конзумирање.

## Три фабрике

| Фабрика | Повратни тип | Тип грешке |
|---|---|---|
| `LibreSCRS::Certificate::ParsedCertificate::fromDer(span)` | `ParsedCertificate` | `ParsedCertificate::ParseError` |
| `LibreSCRS::SmartCard::CardSession::open(string)` | `CardSession` | `OpenError` |
| `LibreSCRS::Trust::TrustStoreService::create(TrustConfig)` | `std::shared_ptr<TrustStoreService>` | `TrustStoreService::CreateError` |

Сваки тип грешке носи:

- `enum class Kind` — груба класификација (адитивно расте у минорним верзијама)
- `LocalizedText userMessage` — обавезан текст погодан за преводиоце
- `std::optional<std::string> diagnosticDetail` — детаљ за развојне сврхе (логови, телеметрија)

## Идиом 1: кратки спој при отказу (препоручено)

```cpp
auto result = LibreSCRS::SmartCard::CardSession::open("MyReader 0");
if (!result) {
    std::cerr << "Could not open session: "
              << result.error().userMessage.defaultText << "\n";
    return;
}
LibreSCRS::SmartCard::CardSession session = std::move(*result);
```

## Идиом 2: монадично ланчање (C++23 `transform` / `or_else`)

```cpp
auto sharedSession = LibreSCRS::SmartCard::CardSession::open("MyReader 0")
    .transform([](auto s) { return std::make_shared<LibreSCRS::SmartCard::CardSession>(std::move(s)); })
    .or_else([](auto err) -> std::expected<std::shared_ptr<LibreSCRS::SmartCard::CardSession>,
                                            LibreSCRS::SmartCard::OpenError> {
        log_warning(err.userMessage.defaultText);
        return std::unexpected{err};
    });
```

## Идиом 3: диспеч по врсти грешке

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

## Обавезна дисциплина `userMessage`

Сваки тип грешке носи непразан `LocalizedText userMessage`. Хостови могу да га проследе у каталоге превода (`qtTrId` за Qt, `NSLocalizedString` за AppKit/SwiftUI, `ki18n` за KF6) преко поља `key`; сваки кључ има енглески `defaultText` као резервну варијанту, тако да непреведени хост и даље има читљив текст.

Поље `userMessage.key` прати конвенцију `librescrs.error.<домен>.<специфично>` — нпр. `librescrs.error.cert.derInvalid`, `librescrs.error.trust.configInvalid`.

## Зашто `std::expected`, а не `std::optional` / `variant` / `shared_ptr<T>`?

LM 3.x је користио три различита облика за исти концепт „фабрике која може да откаже”; 4.0 их уједињује. Приступ са једним обликом:

- Форсира непразну поруку усмерену кориснику при сваком отказу — `std::optional` то није могао да наметне
- Уклања церемонију `std::variant<T, E>` + `std::get_if<T>(&result)` у корист `result.has_value()` / `result.error()`
- Уклања рудиментарну `nullptr`-на-отказ семантику фабрике trust-store-а

