---
layout: "simple"
title: "Преглед архитектуре"
description: "Компоненте система, површина јавног API-ја, модел додатака и ток података"
---

LibreSCRS су два пројекта која заједно читају, обрађују и приказују податке српских државних смарт картица. Јавна површина 4.0 API-ја је стабилан C++20 + LGPL у LibreMiddleware-у; Qt десктоп GUI седи изнад, под GPL-3.0.

## Пројекти

### LibreMiddleware (LGPL-2.1)

Колекција C++20 статичких библиотека без Qt зависности. Сав PC/SC и код протокола картице живи овде. Потрошачи линкују на јавне циљеве и приступају свему кроз `LibreSCRS::*` просторе имена.

### LibreCelik (GPL-3.0)

Qt6 десктоп апликација која користи LibreMiddleware. **Чист презентацијски слој** — без PC/SC-а, без APDU-а, без знања о криптографским протоколима. Прима `LibreSCRS::Plugin::CardData` од middleware додатака и приказује га кроз GUI додатке.

LibreCelik преузима LibreMiddleware преко CMake `FetchContent`. За локални развој, усмерите га на локалну копију кроз `FETCHCONTENT_SOURCE_DIR_LIBREMIDDLEWARE`.

---

## Површина јавног API-ја

Све што се очекује да потрошачи користе живи у једном од пет простора имена.

| Простор имена | Намена |
|---|---|
| `LibreSCRS::Auth` | Речник за прикупљање креденцијала — `AuthRequirement` са `forPreRead` / `forSigning` / `forChangePin` / `forUnblockPin` фабрикама, `FieldDescriptor`, `CredentialProvider` callback псеудоним, `CredentialResult`, `LocalizedText` i18n пакет |
| `LibreSCRS::SmartCard` | Приступ PC/SC читачу — `MonitorService` (fan-out догађаја читача/картице за више претплатника), `CardSession` (pimpl сесијски handle отворен преко noexcept `open()` фабрике која враћа `OpenSessionResult`) |
| `LibreSCRS::Plugin` | Плугин оквир — `CardPlugin` апстрактна база, `CardPluginService`, `CardData` / `CardFieldGroup` / `CardField`, `ReadResult`, `PinStatusEntry`, `SecurityCheck` / `SecurityStatus`, `AutoReaderService` |
| `LibreSCRS::Signing` | PAdES / XAdES / JAdES / CAdES / ASiC-E потписивање — `SigningService` (pure-DI, move-only), `SigningRequest::Builder`, `VisualSignatureParams::Builder`, `TsaProvider` runtime-secret callback, `TrustConfig`, `SigningResult` |
| `LibreSCRS::Secure` | Типови који нулирају бајтове, за краткотрајне тајне — `Secure::String` (PIN/токен текст; нулиран при destrukciji и move-from), `Secure::Buffer` (бинарни кључеви / APDU бајтови) |

Све ван ових простора имена — `smartcard::*`, `libresign::*`, `pkcs11::*`, `pkcs15::*`, интерни `detail::*` хедери — је детаљ имплементације. Може се мењати у било ком издању без semver утицаја.

---

## Модел додатака

Систем има два независна слоја додатака: **middleware додаци** обрађују комуникацију са картицом, **GUI додаци** обрађују приказ. Срећу се на `CardData`-и, универзалном моделу података који производи middleware додатак, а конзумира GUI додатак.

```
┌───────────────────────────────────────────────────────────┐
│                      LibreCelik (GUI)                     │
│                                                           │
│  ┌──────────────────────────┐ ┌───────────────────────┐   │
│  │ QSmartCardMonitor        │ │ CardWidgetPluginReg.  │   │
│  │ (Qt адаптер за MonitorService)  │ │ (QPluginLoader)       │   │
│  └──────────────────────────┘ └──────────┬────────────┘   │
│           ▲                              │ учитава         │
│           │ обавија               ┌──────▼──────────────┐  │
│           │                       │  GUI додаци (.so)    │  │
│           │                       └─────────────────────┘  │
│           │                              ▲                 │
│           │                              │ CardData        │
├───────────┼──────────────────────────────┼─────────────────┤
│           │         LibreMiddleware      │                 │
│           │                              │                 │
│  ┌────────┴────────────┐  ┌──────────────┴───────────┐     │
│  │ LibreSCRS::SmartCard│  │ LibreSCRS::Plugin::       │     │
│  │          ::MonitorService  │  │   CardPluginService     │     │
│  │ (PC/SC event poll)  │  │ (dlopen + ABI v6 static  │     │
│  └─────────────────────┘  │  assert + ATR/AID probe) │     │
│                           └──────────┬───────────────┘     │
│                                      │ учитава              │
│  ┌───────────────────────────────────▼─────────────────┐   │
│  │         Middleware додаци (.so)                      │   │
│  │   cardedge, emrtd, pkcs15, piv, opensc, …           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                      │                     │
│                                      │ APDU (ISO 7816-4)   │
│                                      ▼                     │
│                               ┌────────────┐               │
│                               │ PC/SC      │               │
│                               └─────┬──────┘               │
└─────────────────────────────────────┼─────────────────────┘
                                      │
                               ┌──────▼──────┐
                               │ Смарт картица│
                               └─────────────┘
```

### Middleware додаци — `LibreSCRS::Plugin::CardPlugin`

Middleware додатак је дељена библиотека (`.so` / `.dylib`) коју `CardPluginService` учитава преко `dlopen` у време извршавања. Сваки додатак је подкласа `CardPlugin`-а која у свом конструктору позива `setIdentity(id, displayName, probePriority)` и прегласава виртуелне методе релевантне за породицу картица коју подржава. Декларативна површина:

- **`CardCapabilities capabilities() const`** — битфилд који оглашава које категорије додатак имплементира: `None`, `PKI`, `IdentityData`, `EmrtdCrypto`, `PinManagement`. Домаћин чита ову вредност при учитавању; методе ван оглашеног скупа по подразумеваном враћају `NotImplemented`.
- **`bool canHandle(const std::vector<uint8_t>& atr) const`** — брз тест само по ATR-у. Без I/O картице.
- **`bool canHandleConnection(const std::vector<uint8_t>& atr, CardSession& session) const`** — проба на живој вези за додатке који нису прошли сам ATR. ATR сесије се прослеђује унапред да додаци не би морали поново да га читају.
- **`ReadResult readCard(CardSession& session, GroupCallback onGroup = {}) const`** — екстрахује податке картице. Враћа status-coded `ReadResult`; опциони callback прима сваку `CardFieldGroup` како постане доступна, тако да домаћини могу прогресивно да рендерују (замењује ранију одвојену `readCardStreaming` методу).
- **Signing методе** (када се оглашава `CardCapabilities::PKI`) — `discoverKeyReferences`, `sign`, `getPINList`, `verifyPIN`, `changePIN`, `unblockPIN`. Враћају структуриране `SignResult` / `PINResult` са `bool ok()` предикатом.

ABI додатка је независно верзионисан као integer константа `LibreSCRS::Plugin::kCardPluginAbiVersion` (тренутно: **v6**). Макро у једној линији `LIBRESCRS_DECLARE_CARD_PLUGIN(MyPlugin, 6)` емитује три C-linkage фабричка симбола (`create_card_plugin`, `destroy_card_plugin`, `card_plugin_abi_version`) и фиксира верзију кроз compile-time `static_assert`. Изузеци НЕ СМЕЈУ да прелазе ABI границу додатка — макро обавија `new MyPlugin()` у `noexcept` try/catch; неуспеси стижу као `LoadOutcome::Status::FactoryThrew`.

**Двофазна провера.** `CardPluginService::findAllCandidates(atr, session)` прво позива `canHandle(atr)` на сваком учитаном додатку. Додаци који врате `true` одмах улазе у листу кандидата, сортирану по `probePriority` (мањи број побеђује). Додаци који су вратили `false` добијају другу шансу кроз `canHandleConnection(atr, session)` — дозвољавајући генеричким драјверима (OpenSC, PKCS#15) да преузму картицу кроз живу AID пробу.

**Fallback ланац.** Ако `readCard` најбоље рангираног кандидата не успе, следећи се покушава аутоматски. Додаци за податке (еИД, саобраћајна, здравствена) читају демографске податке; PKI додаци (CardEdge, PKCS#15, OpenSC) се покрећу засебно за потписивање и операције са сертификатима. Раздвајање значи да додатак за податке никад не мора да зна за PKI и обрнуто.

### GUI додаци — `CardWidgetPlugin`

GUI додатак је Qt MODULE библиотека коју `CardWidgetPluginRegistry` учитава преко `QPluginLoader`. Сваки додатак декларише `cardType()` стринг (који одговара `LibreSCRS::Plugin::CardData::cardType`-у који његов парни middleware додатак емитује) и имплементира `createWidget(const CardData&, QWidget* parent)` враћајући потпуно изграђен Qt виџет. Додавање новог приказа не захтева поновну компилацију језгра — испустите `.so`, регистар га открива.

---

## Модел власништва

Документ Export.h на врху стабла изричито наводи пројектно-општу конвенцију: **сваки јавни сервис који зависи од другог сервиса узима зависност кроз `std::shared_ptr`**. Ово елиминише „must outlive” класу greshaka у редоследу уништавања која је мучила код пре 4.0 приликом гашења процеса.

Конкретне последице:

- `LibreSCRS::Signing::SigningService::sign(request, credProvider, plugin, session)` — `plugin` и `session` су `shared_ptr`; интерни радници промовишу из `weak_ptr`-а при употреби.
- `LibreSCRS::Plugin::AutoReaderService` конструктор — `monitor` и `registry` су `shared_ptr`.
- `LibreSCRS::Plugin::CardPluginService::plugins()` — враћа `vector<shared_ptr<CardPlugin>>`; custom deleter покреће destruktor додатка и затим позива `dlclose`, тако да основни `.so` остаје mapped док се последња спољна референца не пусти.

**Само-move** где би дупликација била погрешна: `SigningRequest` (две конкурентне sign операције над истим I/O фајлом су footgun), `Secure::Buffer` (без случајне дупликације тајни), `CardSession` (хардверски handle), `SigningService` (објекат *је* конфигурисан пипелајн), `MonitorService` (поседује живу poll нит и табелу претплата оквирену стабилним токенима).

**Копирљив** где је вредносна семантика природан избор: `AuthRequirement` (обичан податак + `std::vector<FieldDescriptor>`), `VisualSignatureParams` (pimpl deep-copies small-data), `CredentialResult` и `SigningResult` (свака копија носи сопствено нулирано `Secure::String` складиште), `LocalizedText`.

---

## Модел руковања грешкама

API-POLICY §5 дели грешке у три облика, униформно примењена на целу јавну површину:

1. **Грешке конструкције / валидације — throw.** Builder-и, фабрике и конструктори који валидирају корисничке улазе бацају `std::invalid_argument` идентификујући лоше поље. Примери: `VisualSignatureParams::Builder::rect(r)` са непозитивним димензијама, `SigningRequest::Builder::build()` са недостајућим обавезним пољима, `AuthRequirement::forSigning(label, retries)` са празним label-ом. Позиваоци обавијају руковање изузецима око фазе конструкције.

2. **Runtime / environmental грешке — структурисан статус.** Методе које могу неуспешно завршити из environmental разлога (картица одсутна, мрежа, отказивање корисника, mismatch протокола) враћају result тип који носи `Status` enum + опциони payload + опциону поруку прилагођену преводиоцу. Ове методе **не бацају** преко 4.0 јавне границе. Примери: `SigningService::sign` → `SigningResult`, `CardPlugin::readCard` → `ReadResult`, `CardSession::open` → `OpenSessionResult (std::variant<CardSession, OpenError>)`, `MonitorService::listReaders` → `optional<vector<string>>`.

3. **Чисти accessor-и — `noexcept`.** Getter-и враћају по `const&` или по вредности без бацања. Accessor-и на moved-from pimpl објекту су неодређено понашање; `explicit operator bool()` на сваком pimpl-backed типу дозвољава позиваоцима да безбедно провере без изазивања UB-а.

ABI граница додатка је тврда баријера за изузетке: `readCard` и плугин фабрика су `noexcept`; интерни throw-ови се преводе у `ReadResult::Status::CommunicationError` / `ParseError` и `LoadOutcome::Status::FactoryThrew` на граници.

---

## Ток података

Комплетан пут од убацивања картице до приказа:

```
1. Картица убачена у читач

2. LibreSCRS::SmartCard::MonitorService (LibreMiddleware, PC/SC поллинг нит)
   └─ детектује присуство картице преко SCardGetStatusChange
   └─ креира MonitorEvent { CardInserted, readerName, atr }
   └─ fan-out-ује до сваке subscriber callback-е (thread-safe табела претплата)

3. QSmartCardMonitor (LibreCelik, Qt адаптер)
   └─ прима MonitorEvent на нити монитора
   └─ marshal-ира на Qt главну нит преко QMetaObject::invokeMethod
   └─ емитује Qt сигнал

4. Главни прозор почиње двофазно откривање додатака:
   Фаза 1 — ATR филтар (без I/O-а картице):
   └─ CardPluginService::findAllCandidates(atr, session)
      ├─ cardedge-plugin::canHandle(atr)  → true
      ├─ emrtd-plugin::canHandle(atr)     → false
      └─ pkcs15-plugin::canHandle(atr)    → false
      Кандидати: [cardedge (приоритет 840)]
   Фаза 2 — провера на вези (само додаци који су вратили false):
      ├─ emrtd-plugin::canHandleConnection(atr, session)  → false
      └─ pkcs15-plugin::canHandleConnection(atr, session) → true (нађен EF.ODF)
      Коначно: [cardedge (840), pkcs15 (2000)]  — мањи побеђује

5. AsyncCardReader::requestData(topCandidate)
   └─ std::async → позадинска нит
   └─ cardedge-plugin::readCard(session, options, groupCallback)
      ├─ SELECT AID, SM постављање ако је потребно
      ├─ парсирање BER-TLV одговора
      └─ прогресивно емитује CardFieldGroups преко callback-е
      └─ враћа ReadResult::Status::Ok

6. Главна нит враћа резултате преко QMetaObject::invokeMethod

7. CardWidgetPluginRegistry::findByCardType(cardData.cardType)
   └─ cardedge-gui-plugin одговара

8. createWidget(cardData, parent) → рендерован Qt виџет

9. Виџет приказан у главном прозору
```

---

## Стандарди

Јавни API интероперише са или цитира ове стандарде:

| Стандард | Употреба |
|---|---|
| ISO 7816-4 | Комуникација са смарт картицом — APDU команда/одговор, TLV / BER-TLV кодирање |
| PC/SC | Слој приступа читачу — детекција картице, управљање везом |
| PKCS#11 | Интерфејс криптографског токена — `librescrs-pkcs11.so` за прегледаче и PKI клијенте |
| PKCS#15 / ISO 7816-15 | Апликација криптографских информација — откривање сертификата и кључева |
| ICAO 9303 | eMRTD — Basic Access Control, PACE, Secure Messaging, структура група података |
| NIST SP 800-73 | PIV интерфејс картице — откривање сертификата, аутентификација, потписивање |
| BSI TR-03110 | PACE протокол — договарање кључева аутентификованих лозинком |
| ISO 32000-1 | PDF потписни dictionary поља (reason, location, contactInfo) |
| ETSI EN 319 412 / 319 102 | AdES профили — CAdES / PAdES / XAdES / JAdES / ASiC-E нивои потписивања |
| RFC 3161 / 7617 / 6750 / 7230 | TSA timestamping + HTTP auth + семантика хедера |

---

## Проширивање SDK-а

4.0 површина је намерно уска. Додавање нове функционалности генерално захтева мењање N независних фајлова усклађено — секције испод су упутства за уобичајене случајеве.

### Додавање новог формата потписа

Нпр. додавање PKCS#7-enveloping или хипотетичке CAdES-Enveloping варијанте:

1. Додајте формат у `LibreSCRS::Signing::SignatureFormat` enum (`include/LibreSCRS/Signing/Enums.h`).
2. Додајте одговарајући backend модул у `lib/libresign/src/native/`, по узору на `pades_module.{h,cpp}` (типизована `Module` класа, `sign()` која враћа `SigningResult`).
3. Додајте dispatch грану за формат у `lib/LibreSCRS/Signing/detail/RequestBridge.cpp::mapFormat()`.
4. Додајте тест путању у `test/native_*_test.cpp` (нови фајл или нова fixture у постојећем).
5. Ажурирајте секцију „Signing" у [SDK Референци]({{< ref "developer-guide/sdk-reference" >}}) да помиње нови формат.

Дизајн затвореног enum-а чини корак 4 ухватљивим — сваки `switch` по `SignatureFormat`-у којем недостаје нова вредност ће издати упозорење под `-Wswitch-enum`.

### Додавање нове `SigningResult::Status` вредности

1. Додајте у `LibreSCRS::Signing::SigningResult::Status` enum.
2. Додајте именовану фабрику (`SigningResult::myNewStatus(...)`) у `SigningResult.h`.
3. Додајте libresign-интерно → јавно мапирање у `lib/LibreSCRS/Signing/detail/ErrorClassifier.h::classify()`.
4. Ажурирајте табелу статуса у [SDK Референци]({{< ref "developer-guide/sdk-reference" >}}).

### Додавање новог типа картице (Plugin)

Plugin ABI је `kCardPluginAbiVersion = 6` (видети `include/LibreSCRS/Plugin/PluginTypes.h`). Нови типови картица се испоручују као засебне дељене библиотеке у `LIBRESCRS_PLUGIN_PATH`. Аутори додатака:

1. Изводе класу из `LibreSCRS::Plugin::CardPlugin`.
2. У конструктору позивају `setIdentity(id, displayName, probePriority)`.
3. Override-ују `capabilities()` да оглашавају bitfield подржаних могућности (`PKI`, `IdentityData`, `EmrtdCrypto`, итд.).
4. Override-ују одговарајуће виртуелне методе по оглашеној могућности.
5. Извозе entry-point преко `LIBRESCRS_DECLARE_CARD_PLUGIN(MyType, 6)`.

`LIBRESCRS_DECLARE_CARD_PLUGIN` макро `static_assert`-ује на compile-time да додатак одговара тренутној ABI верзији.

Видети `lib/cardedge/`, `lib/pkcs15/` и `lib/piv/` за production примере.
