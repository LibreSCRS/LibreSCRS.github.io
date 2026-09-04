---
layout: "simple"
title: "Обрада очекиваног исхода"
description: "Када LibreSCRS API баца изузетак а када враћа статус, и обавеза std::expected за сваку јавну фабрику која може да омане"
---

LibreSCRS раздваја две врсте неуспеха, и механизам пријаве мора да одговара
врсти. Када се то помеша, добије се API у коме свако место позива тражи и
`try` блок и `switch` по статусу.

Остатак политике — верзионисање, јавна површина, застаревање, плагин ABI —
стоји на [страници о API политици](/developer-guide/sdk-reference/api-policy/).

## 1. Неуспеси конструкције и провере — бацање изузетка

Градитељи, фабрике и конструктори који проверавају улаз који је дао позивалац
бацају `std::invalid_argument`, или конкретнији подтип `std::logic_error`-а, уз
поруку која именује лоше поље. Ту спадају:

- `SigningRequest::Builder::build() &&` — недостаје обавезно поље (улазни или
  излазни фајл, формат), или се формат не поклапа;
- `VisualSignatureParams::Builder::rect(x, y, w, h)` — ширина или висина која
  није позитивна;
- `VisualSignatureParams::Builder::pageIndex(i)` — негативан индекс;
- `AuthRequirement::forSigning(...)`, `forChangePin(...)`, `forUnblockPin(...)`
  — празна ознака PIN-а.

Од позиваоца се очекује да обраду изузетака ограничи на фазу конструкције —
клик на „Даље“ у чаробњаку, подешавање SDK потрошача — а затим да конструисани
објекат до краја живота третира као исправан.

## 2. Неуспеси у раду и у окружењу — исход са статусом

Методе које могу да омане из разлога у окружењу — нема картице, улаз/излаз,
мрежа, корисник је одустао — враћају тип исхода који носи `Status` набрајање.
Те методе **не бацају** изузетак преко границе јавног API-ја. Ту спадају:

- `SigningService::sign(...)` → `SigningResult`, са `SigningResult::Status`;
- `CardPlugin::verifyPIN(...)`, `changePIN(...)`, `unblockPIN(...)` →
  `PINResult` (плагин ABI);
- конструктор `CardPluginRegistry`-ја — интерно хвата неуспехе `dlopen`-а,
  изузетке из фабрике и неслагања ABI-ја; сваки прегледан фајл даје по један
  `LoadOutcome` унос у `loadReport()` уместо да изузетак путује даље.

Интерне грешке мотора које заиста не могу да се сврстају ни у једну вредност
`Status`-а пријављују се као `SigningResult::Status::SigningEngineError` уз
`diagnosticDetail` низ за логове. Позивалац никада не добија бачен изузетак из
`sign()`.

## 3. Чисти приступници — `noexcept` где год је могуће

Приступници — `SigningRequest::inputFile()`, `TrustConfig::trustedListFile`,
`operator==` над pimpl-ом — су `noexcept` и враћају константну референцу или
вредност, како одговара. Век трајања враћене референце документован је на
сваком приступнику.

## 4. Зашто та подела

Бацање при конструкцији чини проверу подношљивом: позивалац обраду изузетака
ограничи на фазу конструкције, а затим објекат до краја живота третира као
исправан. Мешање бацања и статусног исхода унутар једне методе је управо
антиобразац због кога ово правило постоји.

Потрошач SDK-а пише:

```cpp
// Фаза провере — може да баци
try {
    auto request = std::move(SigningRequest::Builder{}
                     .inputFile(inPath)
                     .outputFile(outPath)
                     .format(SignatureFormat::Pades)
                     .level(SignatureLevel::B_LT))
                 .build();

    // Фаза рада — исход са статусом
    auto result = signingService->sign(request, credProvider, plugin, session);
    switch (result.status) {
        case SigningResult::Status::Ok:            /* ... */ break;
        case SigningResult::Status::UserCancelled: /* ... */ break;
        // ...
    }
} catch (const std::invalid_argument& e) {
    // Провера у градитељу је пала — прикажи поруку
}
```

## 5. Фабрике које могу да омане — обавеза `std::expected`

Свака јавна LibreMiddleware фабрика чија *конструкција* може да омане враћа
`std::expected<T, E>`, где је `E` структура грешке за тај домен, овог облика:

- `enum class Kind` — груба класификација; расте додавањем у мањим издањима;
- `LocalizedText userMessage` — обавезна, никада празна;
- `std::optional<std::string> diagnosticDetail` — детаљ за програмера.

Типови грешака по домену угнежђени су у саму класу фабрике
(`ParsedCertificate::ParseError`, `OpenError`, `CreateError`) да би опсег имена
остао узак. Поновна употреба облика међу фабрикама је ствар договора.

`std::optional<T>` (тих неуспех), `std::variant<T, E>` (означена унија) и
`std::shared_ptr<T>` (`nullptr` при неуспеху) **нису** дозвољени као повратни
облици фабрика које могу да омане, од 4.0 надаље. Свако од та три губи нешто
што обавеза чува: разлог, тип разлога, и јемство да позивалац који игнорише
неуспех добије дијагностику преводиоца уместо разименовања нултог показивача.

Јавне `std::expected` фабрике:

| Фабрика | Тип грешке |
|---|---|
| `Certificate::ParsedCertificate::fromDer` | `Certificate::ParsedCertificate::ParseError` |
| `SmartCard::CardSession::open` | `SmartCard::OpenError` |
| `Trust::TrustStoreService::create` | `Trust::TrustStoreService::CreateError` |
| `Plugin::acquireChannelForProfile` | `SecureChannel::ChannelActivationError` |

Прве три су прешле у 4.0. `Plugin::acquireChannelForProfile` — слободна
функција-фабрика која враћа
`std::expected<SmartCard::ActiveChannelHolder, …>` — додата је касније по истој
обавези. Њен `ChannelActivationError` је набрајање исхода, а не канонска
структура `{Kind, LocalizedText, optional<string>}`, зато што прибављање
држача износи један једини статус активације канала; уговорна тачка је облик
`std::expected`, не сам тип грешке.

```cpp
auto session = LibreSCRS::SmartCard::CardSession::open(readerName);
if (!session) {
    const auto& error = session.error();          // SmartCard::OpenError
    show(error.userMessage);                      // никада празна
    log(error.diagnosticDetail.value_or("none")); // детаљ за програмера
    return;
}
// сесија је овде исправна — без провере на nullptr, без поновног читања статуса
useCard(**session);
```

Две последице вреди рећи наглас. Прво, грешка носи `LocalizedText` за који је
зајемчено да није празан, па домаћин никада не мора да измишља поруку за
неуспех који не препознаје. Друго, игнорисање неуспеха се не преводи у тих
успех: до исправног `T` се не може доћи а да се претходно не запита да ли он
уопште постоји.
