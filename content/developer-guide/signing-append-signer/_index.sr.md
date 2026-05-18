---
layout: "simple"
title: "Више потписника: appendSigner"
description: "Како додати додатне потписнике на већ потписан документ"
weight: 35
---

`LibreSCRS::Signing::SigningService::appendSigner` проширује већ
потписан документ једним додатним потписником, чувајући бајтове и
атрибуте сваког претходног потписника. Ово је API који треба користити
када је потребан проток за заједничко потписивање, контра-потписивање
или паралелно више-потписивање — никада не позивајте поново `sign()`
над већ потписаним садржајем.

## Јавни потпис

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

Формат се **закључује из `priorSignature`** (PDF / XML / JSON / CMS
SEQUENCE / ZIP magic) и поништава било коју вредност постављену у
`request.format`. Параметри потписника из `request` (ниво, TSA
конфигурација, визуелни изглед, contactInfo) односе се само на
**новог** потписника; атрибуте претходних потписника не дира.

`originalDocument` је обавезан за DETACHED претходнике (CAdES, XAdES
detached, JAdES) — спецификација не уграђује оригинални садржај у
detached контејнер, па мотор не може да га опорави. За ENVELOPED
претходнике (PAdES, XAdES enveloped) `originalDocument` може бити
празан; проследите непразан span да бисте укључили tamper-check
провереру у односу на опорављени садржај.

## Када користити

| Сценарио | Позив |
|---|---|
| Први / једини потписник | `sign(...)` |
| Додавање ко-потписника на постојећи PDF / XML / итд. | `appendSigner(...)` |
| Поновно потписивање другим кључем | `appendSigner(...)` |
| Масовно потписивање N независних докумената | N × `sign(...)` |

Диспечер у `sign()` ће детектовати претходно потписан улаз преко
`looksSignedAlready` и одбити захтев са
`SigningResult::Status::InvalidRequest`. Намера је експлицитна: бирате
`appendSigner` свесно када проширујете, `sign` свесно када креирате.

## Семантика по формату

| Формат | Ефекат `appendSigner` на контејнер |
|---|---|
| PAdES | Нови инкрементални update додат након претходног `%%EOF`; нови `/Sig` dict + xref/trailer ланац преко `/Prev` |
| XAdES (enveloped) | Нови `<ds:Signature>` сибling уметнут под кореном документа; референце re-anchored |
| XAdES (detached) | Нови `<ds:Signature>` спојен у `asic:Signatures` омотач; Id-јеви re-minted |
| CAdES | Нови `SignerInfo` додат у постојећи `SignedData` `signerInfos` SET |
| JAdES | Нови JWS додат у JSON серијализацију `signatures` низ |
| ASiC-E | Нови XAdES потпис додат унутар `META-INF/` постојећег контејнера |

## Пример

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
    // (trust + signingService + plugin + session подешени као у
    //  Signing Integration Guide; изостављено ради сажетости)

    // 1. Први потписник — Alice потписује нов PDF са sign().
    auto firstReq = lsc::Signing::SigningRequest::Builder{}
                        .inputFile("contract.pdf")
                        .outputFile("contract-alice.pdf")
                        .format(lsc::Signing::SignatureFormat::Pades)
                        .level(lsc::Signing::SignatureLevel::B_T)
                        .build();
    auto first = signingService->sign(firstReq, alicePinProvider,
                                      cardPlugin, session);

    // 2. Други потписник — Bob проширује исти PDF са appendSigner.
    //    inputFile/outputFile у захтеву НИСУ коришћени од стране
    //    appendSigner за priorSignature/originalDocument (API је
    //    span-based) али ЈЕСУ коришћени за поља која builder захтева
    //    и за циљ писања излаза. Поставите оба ради будуће
    //    компатибилности.
    auto secondReq = lsc::Signing::SigningRequest::Builder{}
                         .inputFile("contract-alice.pdf")
                         .outputFile("contract-alice-bob.pdf")
                         .format(lsc::Signing::SignatureFormat::Pades)
                         .level(lsc::Signing::SignatureLevel::B_T)
                         .reason("Одобрено од стране Bob-а")
                         .build();

    const auto prior = readBytes("contract-alice.pdf");
    auto second = signingService->appendSigner(
        secondReq,
        std::span<const std::uint8_t>{prior},
        std::span<const std::uint8_t>{},      // празно: enveloped
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

За DETACHED претходника (CAdES `.p7s`, detached XAdES), проследите
бајтове оригиналног садржаја у `originalDocument`:

```cpp
const auto prior    = readBytes("contract.pdf.p7s");
const auto original = readBytes("contract.pdf");           // обавезно
auto result = signingService->appendSigner(
    request, prior, original, pinProvider, cardPlugin, session);
```

## Позната ограничења

- **PAdES и XAdES више-потписивање су валидирани end-to-end за B-B**;
  више-потписивање на вишим нивоима (B-T / B-LT / B-LTA) је у активном
  развоју и за сада се не препоручује за продукционе B-LTA
  документе. Конкретно, интеракција више-потписивања са
  `/DocTimeStamp` и архивским временским ознакама се ојачава у односу
  на строге валидаторе.
- **CAdES `appendSigner` са PKCS#11 кључевима** је у редизајну ради
  усклађивања `CMS_final` са PKCS#11-омотаним `EVP_PKEY` цевоводом
  мотора; очекујте привремене грешке `error:17000085:CMS routines::no
  private key`.
- **XAdES detached више-потписивање** још не re-mint-ује Id-јеве током
  спајања, што активира строге DSS валидаторе са "duplicate
  occurrences of the signature"; третирати као рад у току.
- **ASiC-E више-потписивање** кроз DSS oracle мост је погођено
  отвореним багом око препознавања content-type-а на страни oracle-а;
  нативна валидација није погођена.

Ова ограничења се прате у пројектном 4.2-track регистру багова;
основни `sign()` путеви (један потписник) остају у потпуности
подржани end-to-end. Корисници који интегришу `appendSigner` за
продукционо више-потписивање треба да валидирају произведене документе
кроз свој циљни валидатор (Adobe Acrobat, EU DSS, валидатор са Adobe
Approved Trust List-а) пре него што прогласе прихватање.
