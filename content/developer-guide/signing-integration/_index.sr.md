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
#include <LibreSCRS/Signing/SigningRequest.h>
#include <LibreSCRS/Signing/SigningResult.h>
#include <LibreSCRS/Signing/SigningService.h>
#include <LibreSCRS/SmartCard/CardSession.h>
#include <LibreSCRS/SmartCard/MonitorService.h>
#include <LibreSCRS/Trust/TrustConfig.h>
#include <LibreSCRS/Trust/TrustStoreService.h>

#include <fstream>
#include <iostream>
#include <vector>

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

    // 2. Конструишите SigningService. TsaProvider{} = празан std::function;
    //    B-B потписивање и даље ради, B-T / B-LT / B-LTA захтевају
    //    callback који враћа TSA URL за дати ниво.
    lsc::Signing::TsaProvider tsa = [](lsc::Signing::SignatureLevel) {
        return std::string{"http://timestamp.digicert.com"};
    };
    auto signingService = std::make_shared<lsc::Signing::SigningService>(trust, std::move(tsa));

    // 3. Откријте card plugin + отворите сесију. CardPluginService скенира
    //    конфигурисани директоријум додатака; MonitorService прати PC/SC
    //    догађаје. Праве апликације се претплаћују на MonitorService;
    //    исечак испод само отвара прву картицу видљиву регистру.
    lsc::Plugin::CardPluginService plugins{"/usr/local/lib/librescrs/plugins"};
    lsc::SmartCard::MonitorService monitor;
    auto session = openFirstSession(monitor, plugins);  // помоћник специфичан за апликацију
    if (!session) {
        std::cerr << "No card available\n";
        return 1;
    }
    auto cardPlugin = plugins.pluginFor(*session);

    // 4. Прочитајте документ.
    std::ifstream file("document.pdf", std::ios::binary);
    std::vector<std::uint8_t> content(
        std::istreambuf_iterator<char>(file), {});

    // 5. Изградите захтев за потписивање.
    auto request = lsc::Signing::SigningRequest::Builder{}
                       .document(std::move(content), "document.pdf")
                       .format(lsc::Signing::SignatureFormat::PAdES)
                       .level(lsc::Signing::SignatureLevel::B_T)
                       .build();

    // 6. PIN провајдер — позива га сервис када картица захтева PIN.
    //    Провајдер прима AuthRequirement који описује шта да прикупи и
    //    враћа CredentialResult. У GUI хосту ово обично отвара PIN
    //    дијалог; у batch алатима чита из env променљиве / сигурног
    //    upita.
    lsc::Auth::CredentialProvider pinProvider =
        [](const lsc::Auth::AuthRequirement&) {
            return lsc::Auth::CredentialResult::withPin(/* безбедни бајтови PIN-а */);
        };

    // 7. Потпишите. Позив блокира за време трајања операције (PIN
    //    верификација + APDU потпис на картици + опционо TSA повратно
    //    путовање). GUI хостови ово покрећу на радној нити.
    auto result = signingService->sign(request, std::move(pinProvider), cardPlugin, session);

    if (result.status != lsc::Signing::SigningResult::Status::Success) {
        std::cerr << "Signing failed: "
                  << result.errorMessage.defaultText << '\n';
        return 1;
    }

    // 8. Запишите потписан документ.
    std::ofstream out("document-signed.pdf", std::ios::binary);
    out.write(reinterpret_cast<const char*>(result.signedDocument.data()),
              static_cast<std::streamsize>(result.signedDocument.size()));
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
Кључна поља:

| Метода builder-а | Опис |
|---|---|
| `document(bytes, fileName)` | Сирови бајтови документа и оригинално име фајла |
| `format(SignatureFormat)` | PAdES / CAdES / XAdES / JAdES / ASiC-E |
| `level(SignatureLevel)` | B-B / B-T / B-LT / B-LTA |
| `visualSignature(VisualSignatureParams)` | PAdES визуелни потпис |
| `tsaOverride(std::string url)` | TSA override по захтеву |
| `allowExpiredCertificate(bool)` | Тест exception — задржите `false` у продукцији |

### `LibreSCRS::Signing::SigningResult`

| Поље | Тип | Опис |
|---|---|---|
| `status` | `Status` enum | Увек постављен; проверите пре читања payload-а |
| `signedDocument` | `std::vector<std::uint8_t>` | Бајтови потписаног излаза при успеху |
| `errorMessage` | `LocalizedText` | Локализован опис грешке |
| `signerCertificate` | опциони сертификат | Сертификат који је потписао |

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
`CardSession::open(readerName, plugin)`. Сервис за потписивање држи
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
Проверите `result.status` и `result.errorMessage` у случају неуспеха:

```cpp
auto result = signingService->sign(request, pinProvider, cardPlugin, session);
if (result.status != LibreSCRS::Signing::SigningResult::Status::Success) {
    using S = LibreSCRS::Signing::SigningResult::Status;
    switch (result.status) {
        case S::TrustStoreUnavailable:  /* TL преузимање / конфиг одбијен */ break;
        case S::InvalidRequest:         /* null plugin/session, празан PIN cb */ break;
        case S::UserCancelled:          /* CredentialProvider вратио cancel */ break;
        case S::PinVerificationFailed:  /* погрешан PIN */ break;
        case S::CardCommunicationError: /* APDU / PC/SC слој */ break;
        case S::TsaUnavailable:         /* B-T или виши захтеван, TSA није успео */ break;
        case S::CertificateExpired:     /* сертификат потписника истекао */ break;
        default: break;
    }
    log(result.errorMessage.defaultText);
}
```

`TrustStoreService::create()` је слично `[[nodiscard]] noexcept` и враћа
`std::expected<…, CreateError>`. Провера резултата унапред чини путеве
грешке експлицитним; ниједан изузетак никада не пропагира преко јавне API
површине.
