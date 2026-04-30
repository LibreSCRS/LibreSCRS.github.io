---
title: "4.0 SDK Migration Guide"
description: "Промене на нивоу изворног кода између 3.x прегледа и LibreSCRS 4.0 јавног API-ја"
weight: 25
aliases:
  - /dev/migration-4.0/
---

# 4.0 SDK миграциони водич

LibreSCRS 4.0 је прво издање означено са пост-хардеnинг површине. Верзије означене као 3.x претходе раду на API политици и више нису подржане. SDK потрошачи који су пратили 3.x циклус прегледа треба да примене промене документоване у наставку да би се компилирали против 4.0.

Овај водич покрива ABI прекиде направљене кроз Trust-Service екстракцију и пролаз за стабилизацију API границе. Сваки унос именује јавни симбол на који се односи, облик пре 3.x, нови облик у 4.0, и кратко објашњење шта се мења на месту позива.

За пуну API политику (верзионисање, застаревање, валидација-наспрам-извршавања), погледајте [API политику]({{< ref "developer-guide/sdk-reference/api-policy" >}}).

---

## Trust животни циклус прелази на `Trust::TrustStoreService`

Пре:

```cpp
LibreSCRS::Signing::SigningService service{trustConfig, tsa};
auto store = service.trustStore();
```

После (4.0):

```cpp
auto trustService = LibreSCRS::Trust::TrustStoreService::create(trustConfig);
LibreSCRS::Signing::SigningService service{trustService, tsa};
auto store = trustService->trustStore();
```

`Signing::TrustStoreManager` је уклоњен у потпуности; `Signing::SigningService::trustStore()` је уклоњен; потрошачи добијају складиште од власника животног циклуса који га је конструисао. Сервис у 4.0 је асинхрон (хитна TL преузимања раде на интерним `std::jthread` радницима; посматрачи се позивају по завршетку) и не баца изузетке при конструкцији.

---

## `LocalizedText` се сели на врх `LibreSCRS::` именског простора

Пре:

```cpp
#include <LibreSCRS/Auth/LocalizedText.h>

LibreSCRS::Auth::LocalizedText msg{"key", "Fallback"};
LibreSCRS::Auth::AuthRequirement::forSigning(LibreSCRS::Auth::LocalizedText{...}, retries);
```

После (4.0):

```cpp
#include <LibreSCRS/LocalizedText.h>

LibreSCRS::LocalizedText msg{"key", "Fallback"};
LibreSCRS::Auth::AuthRequirement::forSigning(LibreSCRS::LocalizedText{...}, retries);
```

Тип се користи у `Auth`, `SmartCard`, `Plugin` и `Signing` — задржавање у `Auth` је био реликт оригиналног скупа произвођача који је био само за упите за акредитиве. Уклоните `Auth::` квалификатор; из било ког угнежденог `LibreSCRS::*` именског простора, неквалификовано `LocalizedText` се разрешава преко претраге у спољашњем именском простору. Стара путања заглавља је уклоњена; ажурирајте `#include` линију.

---

## `SyncProvider<Result, Context>` шаблонски алијас

`Auth::CredentialProvider` и `Signing::TsaProvider` сада обоје алијасују једну канонску генеричку дефиницију:

```cpp
namespace LibreSCRS {
template <typename Result, typename Context>
using SyncProvider = std::function<Result(const Context&)>;
}
```

Изворно компатибилно на месту позива — оба претходна алијаса задржавају своје име. Дуплирани параграф уговора о позивању/безбедности нити од 30 линија се сажима у један канонски блок на `LibreSCRS::SyncProvider`. Нови callback-ови за тајне у 4.x прате исти образац специјализације шаблона.

---

## Преименовани приватни чланови `CardPlugin`

Утиче на ауторе додатака који се компилирају против заштићене/приватне површине `LibreSCRS::Plugin::CardPlugin`. Имена јавних приступних метода су непромењена.

| 3.x преглед | 4.0 |
| --- | --- |
| `CardPlugin::id` (приватно) | `CardPlugin::pluginIdValue` |
| `CardPlugin::name` (приватно) | `CardPlugin::displayNameValue` |
| `CardPlugin::priority` (приватно) | `CardPlugin::probePriorityValue` |

Јавни акцесори непромењени: `pluginId()`, `displayName()`, `probePriority()`. Додаци који су дефинисали свој сопствени `id`/`name`/`priority` члан никада нису добили грешку при изградњи због сенке у старом распореду — ова класа грешака је затворена овом променом имена.

---

## `CardPlugin::canHandle` / `canHandleConnection` примају `std::span`

Пре:

```cpp
bool canHandle(const std::vector<std::uint8_t>& atr) override;
bool canHandleConnection(const std::vector<std::uint8_t>& atr,
                         smartcard::PCSCConnection& conn) override;
```

После:

```cpp
bool canHandle(std::span<const std::uint8_t> atr) override;
bool canHandleConnection(std::span<const std::uint8_t> atr,
                         smartcard::PCSCConnection& conn) override;
```

Свако преоптерећење додатка ажурира тип параметра. Имплементације које читају `.size()` / итерирају / користе `data()` су компатибилне са спан-ом без додатних промена.

---

## `AutoReaderError::Kind::RegistryEmpty` нова вредност енум-а

`Plugin::AutoReader::AutoReaderError::Kind` добија нову вредност `RegistryEmpty` која разликује „нема инсталираних додатака или су сви додаци пали при учитавању" од „картица присутна али ниједан додатак није одговарао њеном ATR-у". Сваки код домаћина који исцрпно прелази преко `AutoReaderError::Kind` MORA додати случај за `RegistryEmpty` (или `default:` грану по [API политици §9](api-policy/#9-enum-exhaustiveness-and-forward-compatibility)).

`Plugin::CardPluginRegistry::isUsable() noexcept` је одговарајућа сонда — користите је при покретању домаћина да би се појавило „нема инсталираних додатака" пре прве убациване картице.

---

## `CardData::groupAt` / `fieldAt` граничне политике

Пре (3.x преглед): `noexcept` акцесори са недефинисаним понашањем за индексе ван опсега.

После (4.0):

```cpp
// Варијанте са провером граница (бацају std::out_of_range)
CardFieldGroup&        groupAt(std::size_t index);
CardField&             fieldAt(std::size_t g, std::size_t f);
CardField&             fieldAt(std::pair<std::size_t, std::size_t> idx);

// Варијанте без провере (noexcept, врућа путања)
CardFieldGroup&        groupAtUnchecked(std::size_t index)        noexcept;
CardField&             fieldAtUnchecked(std::size_t g, std::size_t f) noexcept;
```

Индекси које даје домаћин теку кроз облик који баца изузетак по [API политици §5.1](api-policy/#51-construction--validation-failures--throw). Интерни позиваоци који већ проверавају границе (нпр. путем `findGroup` / `findField` који враћају `optional<size_t>`) могу користити варијанте без провере за `noexcept` врућу путању.

---

## Уједначавање `userMessage` параметара у `SigningResult` / `CredentialResult` фабрикама

Свака фабрика која производи грешку сада прима `std::optional<LocalizedText> userMessage = std::nullopt` праћен `std::optional<std::string> diagnosticDetail = std::nullopt`.

Пре (3.x преглед, мешани облици):

```cpp
SigningResult::invalidRequest(LocalizedText userMessage, std::optional<std::string> diag = nullopt);
SigningResult::invalidRequestDiagnosticOnly(std::string diag);
SigningResult::trustStoreUnavailable(std::optional<std::string> diag = nullopt);
SigningResult::tsaUnreachable(LocalizedText userMessage, std::optional<std::string> diag = nullopt);
CredentialResult::error(LocalizedText message);
CredentialResult::error();
```

После (4.0, један облик):

```cpp
SigningResult::invalidRequest(std::optional<LocalizedText> userMessage = nullopt,
                              std::optional<std::string> diag = nullopt);
SigningResult::trustStoreUnavailable(std::optional<LocalizedText> userMessage = nullopt,
                                     std::optional<std::string> diag = nullopt);
SigningResult::tsaUnreachable(std::optional<LocalizedText> userMessage = nullopt,
                              std::optional<std::string> diag = nullopt);
CredentialResult::error(std::optional<LocalizedText> userMessage = nullopt);
```

Миграција: позициони позиваоци премештају аргумент `LocalizedText` у `std::optional` (имплицитно) и додају опциони други аргумент. Преоптерећење `invalidRequestDiagnosticOnly(std::string)` је уклоњено — изразите намеру само-за-дијагностику као `invalidRequest(std::nullopt, "diag string")`.

---

## `TrustConfig::Builder` (адитивно)

Агрегат `Trust::TrustConfig` остаје обична-податковна структура са јавним пољима; постојећи позиваоци који преферирају синтаксу са одређеним иницијализаторима (`TrustConfig{.includeSystemTrustStore = false}`) настављају да се компилирају.

Издање 4.0 уводи `TrustConfig::Builder` са валидацијом по сетеру по [API политици §5.1](api-policy/#51-construction--validation-failures--throw):

```cpp
auto cfg = std::move(LibreSCRS::Trust::TrustConfig::Builder{}
              .addTrustedListSource("https://lotl.example.org/lotl.xml", true /*lotl*/, false /*eager*/)
              .addTrustedListSource("https://tl.example.org/tl.xml")
              .setCacheDirectory(cacheDir)
              .setIncludeSystemTrustStore(false))
              .build();
```

Сетери бацају `std::invalid_argument` за лоше URL-ове (празни, погрешна шема, дупликати), за надкорена кеша која се не могу писати, или за непостојеће фајлове Trusted-List-а. `build()` је `noexcept` када је уговор по сетеру задовољен. Препоручена путања за нове SDK потрошаче; постојећи позиваоци агрегата настављају да раде.

---

## `Secure::String::equalConstantTime`

Пре: само `Secure::String::operator==` — идентитет бајта, не у константном времену. Документација је сугерисала позиваоцима да „имплементирају своје упоређивање у константном времену."

После:

```cpp
LibreSCRS::Secure::String stored = ...;
LibreSCRS::Secure::String candidate = ...;
if (stored.equalConstantTime(candidate)) {
    // PIN је тачан
}
```

Нови члан се извршава у времену пропорционалном дужем улазу без обзира где се појављује прва различита бајт-вредност (интерно користи OpenSSL `CRYPTO_memcmp`; OpenSSL је већ приватна LM зависност, нема нове површине заглавља). Користите за било коју безбедносно-осетљиву проверу једнакости на улазу који даје корисник. `operator==` задржава своју семантику идентитета бајта за неосетљива упоређивања.

---

## `Trust::TrustStore::ChainStatus` задржава тренутни облик

`ChainStatus` НЕ додаје вредност `Unsettled`. Потрошачи којима треба разликовање „заиста неповерено" од „још се учитава" упитују `Trust::TrustStoreService::status()` (или `sourceStatuses()`) поред инспекције вредности `ChainStatus`. Провера два извора је строго информативнија него што би била сажета `Unsettled` вредност енум-а — статус сервиса разликује `Loading`, `PartialFailure`, `Settled`, итд.

---

## Интерно за додатке: `smartcard::PCSCConnection` није више у јавном CardSession.h

Аутори додатака настављају да позивају `LibreSCRS::SmartCard::detail::unwrap(session)` тачно као пре — облик позива је непромењен. Интерна промена је структурна: јавни `<LibreSCRS/SmartCard/CardSession.h>` више не декларише унапред `namespace smartcard`. Изворни фајлови додатака који укључују `<LibreSCRS/SmartCard/detail/Unwrap.h>` (LM-интерно-само заглавље које излаже `unwrap`) настављају да раде без модификације.

Ако је извор вашег додатка икада сам декларисао унапред `smartcard::PCSCConnection` ослањајући се на јавни CardSession.h pull-in, замените то експлицитним укључивањем `<LibreSCRS/SmartCard/detail/Unwrap.h>`.

---

## Доследност `*Service` суфикса

Три service-flavoured типа у `LibreSCRS::Plugin` и `LibreSCRS::SmartCard` усвајају `*Service` суфикс који су `Signing::SigningService` и `Trust::TrustStoreService` већ устоличили. Чисти data / event / outcome типови (нпр. `MonitorEvent`, `AutoReaderError`, `LoadOutcome`) задржавају своја тренутна имена.

| 3.x preview / пре-rename | 4.0 |
| --- | --- |
| `LibreSCRS::Plugin::AutoReader`            | `LibreSCRS::Plugin::AutoReaderService`            |
| `LibreSCRS::Plugin::CardPluginRegistry`    | `LibreSCRS::Plugin::CardPluginService`            |
| `LibreSCRS::SmartCard::Monitor`            | `LibreSCRS::SmartCard::MonitorService`            |
| `<LibreSCRS/Plugin/AutoReader.h>`          | `<LibreSCRS/Plugin/AutoReaderService.h>`          |
| `<LibreSCRS/Plugin/CardPluginRegistry.h>`  | `<LibreSCRS/Plugin/CardPluginService.h>`          |
| `<LibreSCRS/SmartCard/Monitor.h>`          | `<LibreSCRS/SmartCard/MonitorService.h>`          |

Механичка миграција (покривена `tools/migrate-3x-to-4.0.sh`):

```sh
sed -i \
    -e 's|LibreSCRS/Plugin/AutoReader\.h|LibreSCRS/Plugin/AutoReaderService.h|g' \
    -e 's|LibreSCRS/Plugin/CardPluginRegistry\.h|LibreSCRS/Plugin/CardPluginService.h|g' \
    -e 's|LibreSCRS/SmartCard/Monitor\.h|LibreSCRS/SmartCard/MonitorService.h|g' \
    -e 's|\bAutoReader\b|AutoReaderService|g' \
    -e 's|\bCardPluginRegistry\b|CardPluginService|g' \
    -e 's|LibreSCRS::SmartCard::Monitor\b|LibreSCRS::SmartCard::MonitorService|g' \
    *.cpp *.h
```

Опрез: не преименујте глобално неповезан 3.x интерни `smartcard::Monitor` симбол ако се ваш код позива на њега кроз `using namespace smartcard;` (никаква 4.0 јавна површина не користи то име).

---

## `CardSession::open` враћа `std::variant`

`OpenSessionResult` мигрира са структуре две `std::optional` слотова на `std::variant<CardSession, OpenError>` — тачно једна алтернатива се чува, елиминишући „оба празна / оба попуњена" инваријанту коју је претходни облик тихо дозвољавао.

Пре:

```cpp
struct OpenSessionResult {
    std::optional<CardSession> session;
    std::optional<OpenError>   error;
};
```

После:

```cpp
struct OpenSessionResult : std::variant<CardSession, OpenError>
{
    using std::variant<CardSession, OpenError>::variant;
};
```

Идиом провере код потрошача:

```cpp
auto result = SmartCard::CardSession::open(reader);
if (auto* session = std::get_if<SmartCard::CardSession>(&result)) {
    // *session је живи handle
    plugin->readCard(*session, ...);
} else {
    const auto& err = std::get<SmartCard::OpenError>(result);
    qCWarning(category) << "open неуспех:" << static_cast<int>(err.kind);
}
```

Еквивалентан `std::visit`:

```cpp
std::visit([&](auto&& alt) {
    using T = std::decay_t<decltype(alt)>;
    if constexpr (std::is_same_v<T, SmartCard::CardSession>) {
        plugin->readCard(alt, ...);
    } else {
        // OpenError грана
    }
}, result);
```

Промена је механичка за уобичајени `if (sessionResult.session) {...} else {...}` шаблон, али се не може ауто-преписати — `migrate-3x-to-4.0.sh` означава консумере `OpenSessionResult`-а за ручни преглед.

---

## Референце

- [API политика]({{< ref "developer-guide/sdk-reference/api-policy" >}}) — верзионисање, застаревање, правила валидације-наспрам-извршавања.
- [SDK референца]({{< ref "developer-guide/sdk-reference" >}}) — наративни обилазак по именским просторима.
- `examples/sdk-consumer/main.cpp` у изворном стаблу LibreMiddleware — минимални радни потрошач који користи површину после Tier-2.
