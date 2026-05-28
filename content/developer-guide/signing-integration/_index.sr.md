---
layout: "simple"
title: "Водич за интеграцију потписивања"
description: "Како интегрисати могућности дигиталног потписивања LibreMiddleware-а у вашу апликацију"
weight: 30
---

LibreMiddleware испоручује нативни C++ engine за дигитално потписивање који
подржава пет формата потписа, четири нивоа усклађености и хардверско
потписивање преко PKCS#11. Овај водич показује спољним корисницима како
да га интегришу кроз **јавни `LibreSCRS::Signing` API**.

Сам engine за потписивање живи у интерној `libresign` библиотеци испод
`lib/libresign/` — свако заглавље тамо је закључано преко
`LIBRESCRS_INTERNAL_BUILD` и **није део подржане корисничке површине**.
Спољни код линкује против `LibreSCRS::Signing` CMake алијаса и укључује
само заглавља испод `<LibreSCRS/Signing/…>`.

## Формати и нивои потписа

Engine производи потписе у складу са EU eIDAS / ETSI baseline профилима:

| Формат | Стандард | Улаз | Излаз | Паковање |
|---|---|---|---|---|
| PAdES | ETSI EN 319 142 | PDF | Потписан PDF | Enveloped |
| CAdES | ETSI EN 319 122 | Било која датотека | `.p7s` (PKCS#7/CMS) | Detached |
| XAdES | ETSI EN 319 132 | Било која датотека | `.xml` (XML-DSIG) | Enveloped или detached |
| JAdES | ETSI EN 319 182 | Било која датотека | `.json` (JWS) | Detached |
| ASiC-E | ETSI EN 319 162 | Било која датотека(е) | `.asice` (ZIP контејнер) | Detached (XAdES унутра) |

Сваки формат подржава четири нивоа растуће сигурности:

| Ниво | Садржај | Захтева |
|---|---|---|
| B-B | Основни потпис | Само сертификат за потписивање |
| B-T | B-B + временски печат | TSA сервер |
| B-LT | B-T + подаци о опозиву (CRL/OCSP) | TSA + извори опозива |
| B-LTA | B-LT + архивски временски печат | TSA + извори опозива |

---

## CMake интеграција

LibreMiddleware је дизајниран за коришћење преко CMake `FetchContent`.
Подршка за потписивање је подразумевано укључена. Тагови користе голи
`X.Y.Z` облик (без `v` префикса):

```cmake
include(FetchContent)
FetchContent_Declare(
    LibreMiddleware
    GIT_REPOSITORY https://github.com/LibreSCRS/LibreMiddleware.git
    GIT_TAG        4.2.0
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

За локални развој усмерите на локалну копију уместо преузимања са Git-а:

```bash
cmake -B build -DFETCHCONTENT_SOURCE_DIR_LIBREMIDDLEWARE=/path/to/LibreMiddleware
```

### Опције изградње

| Опција | Подразумевано | Опис |
|---|---|---|
| `BUILD_SIGNING` | `ON` | Укључује подршку за дигитално потписивање (`LibreSCRS::Signing`) |
| `SIGNING_BACKEND` | `native` | Избор backend-а: `native`, `dss` или `both`. DSS backend је тест оracле и застарео је за продукциону употребу |

Изградња извози `LIBREMIDDLEWARE_HAS_SIGNING` тако да спољни пројекти могу
условно да компајлирају функционалности потписивања.

---

## Минималан пример потписивања

Пример испод обавља комплетан PAdES B-T потпис против картице коју је
открио регистар додатака. Користи само јавни API — сваки include је из
`<LibreSCRS/…>`.

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
    // 1. Конструишите trust store. Фабрика је noexcept и враћа употребљив
    //    сервис чак и када је мрежа недоступна — пакетски и (опционо)
    //    системски анкори су одмах доступни, док eager Trusted-List
    //    преузимања раде на интерним радним нитима.
    lsc::Trust::TrustConfig trustConfig;
    trustConfig.cacheDirectory = "/var/cache/myapp/tl-cache";
    // trustConfig.sources.push_back({...});   // опционо EU LOTL / национални TL-ови

    auto trustResult = lsc::Trust::TrustStoreService::create(std::move(trustConfig));
    if (!trustResult) {
        std::cerr << "Trust store init failed: "
                  << trustResult.error().userMessage.defaultText << '\n';
        return 1;
    }
    std::shared_ptr<lsc::Trust::TrustStoreService> trust = *trustResult;

    // 2. Конструишите SigningService. TsaProvider се позива у време
    //    потписивања за нивое B-T / B-LT / B-LTA; staticTsa() је
    //    помоћна фабрика која увек враћа исти URL без аутентификације.
    //    Прослеђивањем подразумевано конструисаног TsaProvider{} се
    //    искључује TSA — B-B потписивање и даље ради, а виши нивои тада
    //    падају са Status::TsaUnreachable.
    auto tsa = lsc::Signing::staticTsa("http://timestamp.digicert.com");
    auto signingService = std::make_shared<lsc::Signing::SigningService>(trust, std::move(tsa));

    // 3. Откријте card plugin + отворите сесију. CardPluginService скенира
    //    конфигурисани директоријум додатака; MonitorService прати PC/SC
    //    догађаје. Праве апликације се претплаћују на MonitorService и
    //    позивају findPluginForCard(atr) када картица стигне; помоћник
    //    испод сажима тај след у један app-specific корак.
    lsc::Plugin::CardPluginService plugins{"/usr/local/lib/librescrs/plugins"};
    lsc::SmartCard::MonitorService monitor;
    auto session = openFirstSession(monitor, plugins);   // помоћник специфичан за апликацију
    if (!session) {
        std::cerr << "No card available\n";
        return 1;
    }
    auto atr = session->atr();                            // std::span<const std::uint8_t>
    auto cardPlugin = plugins.findPluginForCard(atr);
    if (!cardPlugin) {
        std::cerr << "Ниједан додатак не одговара ATR-у ове картице\n";
        return 1;
    }

    // 4. Изградите захтев за потписивање. Engine чита из inputFile и
    //    пише потписан излаз у outputFile — не постоји улаз преко
    //    бафера бајтова на јавном API-ју.
    auto request = lsc::Signing::SigningRequest::Builder{}
                       .inputFile("document.pdf")
                       .outputFile("document-signed.pdf")
                       .format(lsc::Signing::SignatureFormat::Pades)
                       .level(lsc::Signing::SignatureLevel::B_T)
                       .build();

    // 5. PIN провајдер — позива га сервис када картица захтева PIN.
    //    Провајдер прима AuthRequirement који описује шта да прикупи и
    //    враћа CredentialResult. У GUI хосту ово обично отвара PIN
    //    дијалог; у batch алатима чита из сигурног упита или env
    //    променљиве.
    lsc::Auth::CredentialProvider pinProvider =
        [](const lsc::Auth::AuthRequirement&) {
            lsc::Secure::String pin{"1234"};  // хост прикупља, нулира се при уништавању
            return lsc::Auth::CredentialResult::ok({{"pin", std::move(pin)}});
        };

    // 6. Потпишите. Позив блокира за време трајања операције (PIN
    //    верификација + APDU потпис на картици + опционо TSA повратно
    //    путовање). GUI хостови ово покрећу на радној нити.
    auto result = signingService->sign(request, std::move(pinProvider), cardPlugin, session);

    if (result.status != lsc::Signing::SigningResult::Status::Ok) {
        std::cerr << "Signing failed: "
                  << result.userMessage.defaultText << '\n';
        return 1;
    }

    // 7. Успех — потписан документ је на диску на путањи на коју је
    //    engine писао (тј. outputFile() са којим је захтев изграђен).
    std::cout << "Signed: " << result.outputPath->string() << '\n';
    return 0;
}
```

---

## Референца API-ја

Сви јавни типови живе под `LibreSCRS::*` PascalCase именским просторима.
Сваки тип поменут испод има пуни Doxygen уговор у одговарајућем заглављу
испод `include/LibreSCRS/`.

### `LibreSCRS::Signing::SigningService`

Јавна улазна тачка. Конструише се једном са власником животног циклуса
поверења и TSA callback-ом; поново се користи за више `sign()` позива.

**Конструкција:**

```cpp
SigningService(std::shared_ptr<Trust::TrustStoreService> trustService,
               TsaProvider tsa);
```

**Позив потписивања (4 аргумента, `[[nodiscard]]`):**

```cpp
SigningResult sign(const SigningRequest& request,
                   Auth::CredentialProvider credentialProvider,
                   std::shared_ptr<Plugin::CardPlugin> cardPlugin,
                   std::shared_ptr<SmartCard::CardSession> session);
```

Позив је блокирајући и thread-safe преко различитих `(cardPlugin, session)`
парова. Null plugin или session, или празан `credentialProvider`, враћају
`SigningResult::Status::InvalidRequest` уместо бацања изузетка.

### `LibreSCRS::Trust::TrustStoreService`

Власник животног циклуса trust store-а. Фабрика је `noexcept` и враћа
`std::expected<std::shared_ptr<TrustStoreService>, CreateError>`. Eager
Trusted-List преузимања раде на интерним радним нитима; корисници посматрају
завршетак преко `status()`, `addObserver()` или блокирајућег
`waitForEagerFetches()`.

### `LibreSCRS::Signing::SigningRequest`

Непроменљиви параметри потписивања, граде се преко угнежденог `Builder`-а.
Engine је заснован на путањама фајлова — проследите `inputFile()` и
`outputFile()`; не постоји overload са бафером бајтова на јавном API-ју.
Кључне методе builder-а:

| Метода builder-а | Опис |
|---|---|
| `inputFile(std::filesystem::path)` | Изворни документ на диску |
| `outputFile(std::filesystem::path)` | Одредишна путања на коју engine пише |
| `format(SignatureFormat)` | `Pades` / `Cades` / `Xades` / `Jades` / `AsicE` |
| `level(SignatureLevel)` | `B_B` / `B_T` / `B_LT` / `B_LTA` |
| `packaging(PackagingMode)` | `Enveloped` или `Detached` |
| `reason` / `location` / `contactInfo` | Поља PDF речника потписа (ISO 32000-1 §12.8.1) |
| `certificateLabel(std::string)` | PKCS#11 алијас кључа када картица носи више од једног |
| `visualParams(VisualSignatureParams&&)` | PAdES визуелни потпис |
| `tsaOverride(TsaProvider)` | TSA override по захтеву; упарите са `staticTsa(url)` за фиксни URL |

`Builder::build()` је rvalue-квалификован; финализујте са
`std::move(builder).build()` и обмотајте позив у `try/catch` за
`std::invalid_argument` ако поља постављате условно.

### `LibreSCRS::Signing::SigningResult`

| Поље | Тип | Опис |
|---|---|---|
| `status` | `Status` enum | Увек постављен; проверите пре читања осталих поља |
| `outputPath` | `std::optional<std::filesystem::path>` | Путања на коју је потписан документ записан при успеху |
| `userMessage` | `LocalizedText` | Translator-friendly порука за корисника; обавезна у 4.0 |
| `diagnosticDetail` | `std::optional<std::string>` | Дијагностика за развојне логове |

Вредности `Status`: `Ok`, `InvalidRequest`, `TrustStoreUnavailable`,
`UserCancelled`, `PinVerificationFailed`, `CardBlocked`, `TsaUnreachable`,
`SigningEngineError`. Енумерација је append-only; `switch` код потрошача
мора да укључује `default` грану.

### `LibreSCRS::Auth::CredentialProvider`

`SyncProvider<CredentialResult, AuthRequirement>` — callable који обезбеђује
хост, мапира `AuthRequirement` (шта картица треба) у `CredentialResult`
(попуњени креденцијали, корисничко поништавање или грешка провајдера).
Сервис за потписивање позива провајдер највише једном по откључавању
картице.

### `LibreSCRS::Plugin::CardPlugin` и `LibreSCRS::SmartCard::CardSession`

Plugin покреће операције специфичне за картицу (APDU потписа, проналазак
кључа) и добија се из `CardPluginService`-а. Сесија енкапсулира отворени
PC/SC канал и добија се било преко монитора, било директно преко
`CardSession::open(readerName)`. Сервис за потписивање држи
дељено власништво над обоје за време трајања позива.

---

## PKCS#11 подршка

Engine за потписивање приступа приватним кључевима кроз `CardPlugin` /
`CardSession` апстракцију. Испод хаубе, слој додатака разговара са картицом
преко LibreSCRS PKCS#11 модула (`librescrs-pkcs11.so`) плус одговарајућих
драјвера специфичних за картицу — CardEdge, PKCS#15, PIV или OpenSC.

Спољни корисници који већ директно покрећу PKCS#11 модул могу то да раде
независно од `LibreSCRS::Signing`; јавни API за потписивање у 4.0
намерно је PKCS#11-агностичан на споју (plugin + session).

PIN никада не опстаје преко `sign()` позива — испоручује се картици преко
`CredentialProvider`-а (за који се очекује да хост обезбеди подршком за
нулирање при уништавању као што су `LibreSCRS::Secure::Buffer` /
`LibreSCRS::Secure::String`) и одмах одбацује после `C_Login`-а.

---

## Толеранција PDF улаза

За PAdES потписивање, engine прати Adobe Acrobat Implementation Notes §H.3
при обради PDF улаза, чиме се понаша исто као Acrobat, Foxit, qpdf и
pdfinfo:

- До **1024 бајта** не-PDF префикса пре `%PDF-` заглавља се толеришу и
  уклањају (нпр. `multipart/form-data` омотачи из веб форми).
- Пратећи подаци после последњег `%%EOF` се уклањају (опциони један CR/LF
  се задржава).
- Када `startxref` показује на offset на ком се не налази `xref` кључна
  реч (често након уклањања префикса или због грешке генератора), engine
  прелази на резервно скенирање последњих ~10 KB у потрази за самосталном
  `xref` кључном речју и поново покушава.

Ако првих 1024 бајта не садрже `%PDF-` заглавље, улаз се и даље одбија са
структурираним `InvalidRequest` резултатом. Нису потребне измене у позивном
коду — толеранција се примењује интерно током PAdES обраде.

---

## Руковање грешкама

`SigningService::sign()` враћа `SigningResult` уместо да баца изузетке.
Проверите `result.status` и `result.userMessage` у случају неуспеха:

```cpp
auto result = signingService->sign(request, pinProvider, cardPlugin, session);
if (result.status != LibreSCRS::Signing::SigningResult::Status::Ok) {
    using S = LibreSCRS::Signing::SigningResult::Status;
    switch (result.status) {
        case S::TrustStoreUnavailable:  /* TL преузимање / конфиг одбијен  */ break;
        case S::InvalidRequest:         /* null plugin/session, празан cb  */ break;
        case S::UserCancelled:          /* провајдер је вратио cancel      */ break;
        case S::PinVerificationFailed:  /* погрешан PIN                    */ break;
        case S::CardBlocked:            /* PIN за потписивање је блокиран  */ break;
        case S::TsaUnreachable:         /* B-T+ захтеван, TSA није успео   */ break;
        case S::SigningEngineError:     /* libresign / APDU цевовод        */ break;
        default: break;                 // append-only enum; задржите default
    }
    log(result.userMessage.defaultText);
    if (result.diagnosticDetail) {
        log(*result.diagnosticDetail);
    }
}
```

`TrustStoreService::create()` је слично `[[nodiscard]] noexcept` и враћа
`std::expected<…, CreateError>`. Провера резултата унапред чини путеве
грешке експлицитним; ниједан изузетак никада не пропагира преко јавне API
површине.
