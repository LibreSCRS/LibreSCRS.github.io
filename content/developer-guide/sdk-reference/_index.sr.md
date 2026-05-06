---
title: "SDK референца"
description: "Референца по просторима имена за 4.0 јавни API LibreSCRS-а"
weight: 30
---

LibreMiddleware испоручује C++20 SDK под `LibreSCRS::*` umbrella-ом. Површина је намерно уска — шест простора имена, ~28 јавних хедера — и стабилна је кроз 4.x линију по [API политици]({{< ref "developer-guide/sdk-reference/api-policy" >}}).

Ова страница је **наративна референца**: шта је сваки простор имена, када га користити, и по један идиоматски пример по компоненти. За ауто-генерисан списак свих ентитета (свака класа, сваки члан, сваки параметар) консултујте Doxygen излаз на GitHub Pages пројекта.

Минимални функционални пример потрошача је `examples/sdk-consumer/main.cpp` у изворном стаблу LibreMiddleware-а — програм од 70 линија који позива по једну методу из сваког јавног циља.

---

## `LibreSCRS::Auth` — упити за креденцијале

Описује **шта middleware тражи од корисника** (PIN, PUK, MRZ, CAN) и како домаћин одговара.

- `AuthRequirement` — захтев. Гради се кроз closed-set фабрике:
  - `forPreRead(PreReadAuthMethod::BacMrz | PaceCan | None)` — материјал за откључавање путног документа.
  - `forSigning(pinLabel, retriesLeft)` — један PIN за потписивање.
  - `forSigning(LocalizedText pinLabel, retriesLeft)` — преводива варијанта (4.0); чува `key` од почетка до краја.
  - `forChangePin(pinLabel, retriesLeft)` — тренутни + нови + потврда (три поља).
  - `forChangePin(LocalizedText pinLabel, retriesLeft)` — преводива варијанта (4.0); исти bundle на сва три поља, улога се разликује преко идентификатора поља.
  - `forUnblockPin(pinLabel)` — PUK + нови + потврда (три поља).
  - `forUnblockPin(LocalizedText pinLabel)` — преводива варијанта (4.0).
- `FieldDescriptor` — сваки улаз који провajдер мора да прикупи (по један `std::vector` ових по захтеву).
- `CredentialProvider` — `std::function<CredentialResult(const AuthRequirement&)>` који домаћин имплементира.
- `CredentialResult` — враћени bundle; вредности кључеване по `FieldDescriptor::id`-у, свака чувана као `Secure::String` који се нулира.
- `LocalizedText` — `{key, defaultText, placeholders}` тројка која се користи за сваку корисничку поруку коју middleware производи.

```cpp
using namespace LibreSCRS;

auto req = Auth::AuthRequirement::forSigning("PIN", /*retriesLeft=*/3);
std::vector<Auth::CredentialResult::Entry> values;
for (const auto& field : req.fields()) {
    Secure::String pin = askUser(field.label.defaultText);
    values.emplace_back(field.id, std::move(pin));
}
auto answer = Auth::CredentialResult::ok(std::move(values));
```

`CredentialResult` нема default конструктор — намерно се пролази кроз једну од именованих фабрика (`ok`, `cancelled`, `error`) тако да сваки произвођач експлицитно commit-ује `Status`. Ако корисник отказује упит, вратите `Auth::CredentialResult::cancelled()`.

Фабрике су преферирани избор овде (closed-shape захтев) у односу на Builder; видети класну Doxygen документацију за правило.

---

## `LibreSCRS::SmartCard` — PC/SC приступ

Два сервиса изнад PC/SC-а, оба pimpl-backed.

- `MonitorService` — извор догађаја читача + картице. Non-copyable, non-movable (везан животни век са табелом претплата). Fan-out за више претплатника: polling нит се ауто-покреће на први `subscribe` и ауто-зауставља на последњи `unsubscribe`.
- `CardSession` — opaque сесијски handle. Конструише се преко noexcept `open(readerName)` фабрике која враћа `std::expected<CardSession, OpenError>`. Move-only.

```cpp
auto mon = std::make_shared<SmartCard::MonitorService>();
auto readers = mon->listReaders();               // optional<vector<string>>
if (!readers) return;                            // PC/SC подсистем недоступан

auto token = mon->subscribe([](const SmartCard::MonitorEvent& e) {
    if (e.kind == SmartCard::MonitorEvent::Kind::CardInserted) {
        auto sessionResult = SmartCard::CardSession::open(e.readerName);
        if (sessionResult) {
            handleCard(std::move(*sessionResult));
        }
    }
});
// ... mon->unsubscribe(token); када је готово
```

`listReaders`, `open`, и `subscribe` су thread-safe; callback-ови се позивају на poll нити — marshal-ирајте на своју UI нит.

---

## `LibreSCRS::Plugin` — оквир за драјвере картица

Све око проширења подршке за нове типове картица.

- `CardPlugin` — апстрактна база. Сваки `.so` додатак имплементира подкласу, зове `setIdentity(id, displayName, probePriority)` у ктору и прегласава виртуелне методе које његови `CardCapabilities` флагови оглашавају.
- `CardPluginService` — учита-при-конструкцији, multi-directory. Враћа структурисан `LoadOutcome` по фајлу тако да домаћини приказују грешке додатака уместо да их тихо игноришу.
- `CardData` / `CardFieldGroup` / `CardField` — универзални payload тип који додатак производи.
- `ReadResult` — структурисан исход `readCard`-а (status enum + payload).
- `PinStatusEntry`, `SecurityCheck` / `SecurityStatus` — извештавање по PIN-у и по верификационој провери.
- `AutoReaderService` — wrapper који спаја `MonitorService` са `CardPluginService`-јем и даје `CardData` на insert догађаје.

### Писање додатка

```cpp
// my_plugin.cpp
#include <LibreSCRS/Plugin/CardPlugin.h>
#include <LibreSCRS/Plugin/PluginExport.h>
#include <LibreSCRS/Plugin/ReadResult.h>

class MyPlugin final : public LibreSCRS::Plugin::CardPlugin {
public:
    MyPlugin() {
        setIdentity("example.my-card", "Example card", /*probePriority=*/1000);
    }
    LibreSCRS::Plugin::CardCapabilities capabilities() const override {
        return LibreSCRS::Plugin::CardCapabilities::IdentityData;
    }
    bool canHandle(const std::vector<uint8_t>& atr) const override {
        return atr == std::vector<uint8_t>{0x3B, 0x80, /* ... */};
    }
    LibreSCRS::Plugin::ReadResult readCard(
        LibreSCRS::SmartCard::CardSession& session,
        GroupCallback onGroup = {}) const override   // GroupCallback је угнежден унутар CardPlugin-а
    {
        // ...слање APDU-а кроз session, емитовање CardFieldGroups преко onGroup callback-е...
        return LibreSCRS::Plugin::ReadResult::ok({});
    }
};

LIBRESCRS_DECLARE_CARD_PLUGIN(MyPlugin, 7)  // ABI верзија закачена у compile-time
```

Изградите као `.so`, инсталирајте у директоријум прослеђен `CardPluginService`-ју. Регистрарски ABI `static_assert` ће се окинути у compile-time ако циљате погрешну верзију. Изузеци НЕ СМЕЈУ да прелазе ABI границу додатка — макро обавија `new MyPlugin()` у noexcept try/catch; throw-ови стижу као `LoadOutcome::Status::FactoryThrew`.

### Коришћење регистра

```cpp
LibreSCRS::Plugin::CardPluginService registry{std::filesystem::path{"/usr/lib/librescrs/plugins"}};

for (const auto& outcome : registry.loadReport()) {
    if (outcome.status != LibreSCRS::Plugin::LoadOutcome::Status::Loaded) {
        log("плугин {} неуспех: {}", outcome.soPath, outcome.diagnostic);
    }
}

auto candidates = registry.findAllCandidates(atr, session);   // сортирано по приоритету
for (const auto& plugin : candidates) {
    auto result = plugin->readCard(session);   // GroupCallback default-ован — без streaming-а
    if (result.status == LibreSCRS::Plugin::ReadResult::Status::Ok)
        break;
}
```

---

## `LibreSCRS::Trust` — анкери поверења и асинхрони TL fetch

Власник животног циклуса унифицираног trust store-а: bundled CA анкери, опциони OS root store, и било који број асинхроно-преузетих eIDAS Trusted List-а.

- `TrustStore` — read-only композитни скуп анкера. Расте монотоно како eager и lazy TL преузимања завршавају; безбедан за конкурентно читање.
- `TrustConfig` — декларативни улази: TL извори, cache директоријум, system-trust toggle, опциони локални TL фајл.
- `TrustStoreService` — власник животног циклуса. **Асинхрона, не-throwing factory.** `create(TrustConfig)` одмах враћа усабатан сервис са bundled + system анкерима; eager TL преузимања раде на интерним worker нитима и спајају се у јавни store како завршавају. Потрошачи посматрају завршетак кроз `status()`, `addObserver(...)`, или opt-in `waitForEagerFetches(deadline, stop_token)`.

```cpp
namespace Trust = LibreSCRS::Trust;

Trust::TrustConfig config;
config.trustedListSources.push_back({
    "https://www.mit.gov.rs/TrustedList/TSL-RS.xml", /*lazy=*/false, /*verify=*/true});
config.includeSystemTrustStore = true;

// create() никад не блокира на network IO и никад не throw-ује.
auto trustService = Trust::TrustStoreService::create(std::move(config));

// Render-ујте UI одмах са bundled + system анкерима; нови TL анкери стижу
// асинхроно. GUI потрошачи треба да се претплате кроз addObserver:
auto handle = trustService->addObserver(
    [](std::string_view url, Trust::TrustStoreService::SourceStatus s) {
        // marshal на UI нит (нпр. QMetaObject::invokeMethod) и
        // освежи било шта што зависи од резолуције ланца.
    });

// Тестови / CLI алати који легитимно желе синхрони wait:
auto status = trustService->waitForEagerFetches(std::chrono::seconds(5));

// Read-only приступ композитном store-у:
std::shared_ptr<const Trust::TrustStore> store = trustService->trustStore();
```

`TrustStoreService` се конструише кроз приватни ctor + factory; власништво је увек `std::shared_ptr` зато што интерне worker нити држе weak референце на његов `Impl`. Дeстructor отказује fetchewe у току кроз `std::stop_source` и спаја worker-е са ограниченим grace периодом.

**Threading.** Све јавне методе су thread-safe. Observer callback-ови се позивају на интерним worker нитима — UI потрошачи морају да marshal-ују на свој main thread кроз queued-invocation примитив платформе.

**Бихејвиорална напомена.** TL анкери стижу асинхроно. Потрошачи којима је апсолутно потребна синхрона доступност (ретко — типично само test fixture-и) позивају `waitForEagerFetches`. GUI потрошачи толеришу eventual consistency: render-ују са оним што store има у моменту отварања и освежавају се на observer догађаје.

---

## `LibreSCRS::Signing` — PAdES / XAdES / JAdES / CAdES / ASiC-E

Дигитално потписивање против кључа на смарт картици.

- `SigningService` — улазна тачка. **Pure DI**: прима `shared_ptr<Trust::TrustStoreService>` + `TsaProvider` у свом конструктору и никад се не мутира касније. Move-only. Конструишите једном по политици поверења/TSA; реиспользовајте кроз sign позиве.
- `SigningRequest` + `SigningRequest::Builder` — параметри једне sign операције (input/output путеве, формат, ниво, visual params, TSA override, contactInfo, reason, location). Builder валидира у `build() &&`.
- `VisualSignatureParams` + `VisualSignatureParams::Builder` — PAdES визуелни изглед анотације. Геометрија се валидира по setter-у. `kDefaultVisualSignatureRect` изложено за домаћине који само желе „дефолт”.
- `TsaProvider` — `std::function<TsaRequest(const TsaContext&)>`. Позива се по sign-у да добави URL + креденцијале (Basic / Bearer / mTLS / extra headers).
- `SigningResult` — status enum + `outputPath` (путања потписаног документа на успеху) + опциона translator-friendly порука + дијагностички детаљ.

Материјал поверења се убацује кроз `Trust::TrustStoreService` (видети `LibreSCRS::Trust` секцију изнад) — `SigningService` више не поседује животни циклус поверења.

```cpp
LibreSCRS::Trust::TrustConfig trust;
trust.includeSystemTrustStore = true;
auto trustService = LibreSCRS::Trust::TrustStoreService::create(std::move(trust));

auto tsa = LibreSCRS::Signing::staticTsaChecked("https://tsa.example.com");  // валидира URL
LibreSCRS::Signing::SigningService service{trustService, tsa};

LibreSCRS::Signing::SigningRequest::Builder sb;
sb.inputFile("/tmp/document.pdf");
sb.outputFile("/tmp/document.signed.pdf");
sb.format(LibreSCRS::Signing::SignatureFormat::Pades);
sb.level(LibreSCRS::Signing::SignatureLevel::B_LT);
sb.reason("Одобрење");
sb.contactInfo("signer@example.com");
auto request = std::move(sb).build();  // баца invalid_argument ако недостаје обавезно поље

// cardPlugin и cardSession су std::shared_ptr<...> — sign() преузима делиоче
// власништво за време позива.
auto result = service.sign(request, credentialProvider, cardPlugin, cardSession);
switch (result.status) {
    case LibreSCRS::Signing::SigningResult::Status::Ok:
        log("потписано: {}", result.outputPath->string());
        break;
    case LibreSCRS::Signing::SigningResult::Status::UserCancelled:
    case LibreSCRS::Signing::SigningResult::Status::PinVerificationFailed:
    case LibreSCRS::Signing::SigningResult::Status::TsaUnreachable:
        if (result.userMessage) showUserMessage(*result.userMessage);
        break;
    // ... остали Status-и ...
}
```

`build()` је rvalue-qualified. Канонска форма је именовани builder:

```cpp
LibreSCRS::Signing::SigningRequest::Builder b;
b.inputFile(...).outputFile(...);    // setter-и враћају Builder&
auto request = std::move(b).build(); // експлицитни rvalue cast
```

Чисто једно-изразни ланац над привременим builder-ом ради јер темпорари живи до краја целог израза — `auto p = SigningRequest::Builder{}.inputFile(...).outputFile(...).build();` је well-formed (rvalue темпорари задовољава `build() &&`). НЕ компајлира се мешана форма: *именован lvalue* builder без експлицитног `std::move`-а не може да задовољи `build() &&`. У пракси је именована форма пожељнија — error путеви се читљивије мапирају кад је сваки setter сопствена линија, а дијагностике на пропуштени `std::move` су пријатељскије од оних на заглушени ланац.

### Unicode визуелни потпис — 4.0+

Текст видљивог потписа на PAdES PDF-овима сад исправно ренderује све
карактере из Latin-Extended и ћириличног опсега. Engine уграђује и сечује
(subsets) програм Liberation Sans фонта по сваком потписаном документу, са
пратећим `/ToUnicode` CMap-ом тако да је renderовани текст претражив,
копирајући и доступан асистивним технологијама. Пре 4.0 визуелни потписи су
користили Helvetica Type1 фонт са једнобајтним StandardEncoding-ом — non-ASCII
имена потписника су се ренderовала као искривљене глифе (нпр. `Hiršl` као
`Hir¯¡l`).

Исправка је у потпуности испод public API-ја: исти `VisualSignatureParams`
облик (геометрија + `textTemplate`) носи видљив текст — позивајући код се
не мења.

```cpp
// 4.0: било који Unicode текст у визуелним потписима ренderује исправно.
LibreSCRS::Signing::VisualSignatureParams::Builder vb;
vb.pageIndex(0);
vb.rect({50, 50, 250, 60});
vb.textTemplate("Potpisao: Hiršl Ćirković\nDatum: 2026-04-25");
auto visual = std::move(vb).build();
```

Фонт subset је по потпису: сваки потписани PDF носи само глифе које користи
(~5-10 KB типично). Liberation Sans 2.1.5 је укључен под SIL Open Font
License 1.1; engine-ов TTF subsetter је имплементиран from-scratch без
спољних font-dependency-ја.

---

## `LibreSCRS::Secure` — нулирајуће тајне

Краткотрајан тајни материјал нулиран при destrukciji и при move-from. Позадина: `OPENSSL_cleanse`.

- `Secure::String` — PIN / PUK / токен текст. Move-only по подразумеваном али **копирљив** уз нулирање по копији, тако да се уклапа са `std::function`-captured `CredentialProvider` closure-има и са `std::optional<CredentialResult>`-ом. Намерно подложен `std::vector<char>`-у (не `std::string`-у) да избегне Small-String-Optimisation цурење.
- `Secure::Buffer` — бинарни материјал (APDU одговори, бајтови кључа). Move-only. Четири конструктора: default (празан, без алокације), `(size, fill)` (фиксна величина унапред попуњена), `std::string_view` (текстуални фрагменти), и `std::span<const std::uint8_t>` (бинарни).

```cpp
LibreSCRS::Secure::String pin{"1234"};
// ... користити pin.view() са PKCS#11 verify-јем ...
// destruktor OPENSSL_cleanse нулира бајтове; оригинални std::string литерал се копира, не референцира

auto b = LibreSCRS::Secure::Buffer{std::span<const std::uint8_t>{apduBytes.data(), apduBytes.size()}};
// b.data() важи за b.size() бајтова; брише се при ~Buffer() или move-assign
```

**Једнакост на `Secure::String`-у НИЈЕ constant-time** — намерно, документовано у хедеру. Позиваоци којима је потребно constant-time поређење треба да узму `view()` и прослеђују га свом примитиву.

---

## Миграција 3.x → 4.0

4.0 umbrella refactor уклонио је сваки не-`LibreSCRS::*` јавни простор имена. Ако одржавате код према 3.x издању, ево миграционе мапе у једном реду:

| 3.x | 4.0 |
|---|---|
| `smartcard::PCSCConnection`, `smartcard::MonitorService` (јавно) | `LibreSCRS::SmartCard::CardSession`, `LibreSCRS::SmartCard::MonitorService`; интерни транспорт остаје `smartcard::*` али више није у install stablu |
| `plugin::CardPlugin`, `plugin::CardData` | `LibreSCRS::Plugin::CardPlugin`, `LibreSCRS::Plugin::CardData` — видети промене по методи испод |
| `libresign::SigningService`, `libresign::SignRequest` | `LibreSCRS::Signing::SigningService`, `LibreSCRS::Signing::SigningRequest` + `Builder` |
| Јавни API `eidcard::`, `healthcard::`, `euvrc::`, `piv::` | Уклоњени — потрошачи сада воде све кроз `LibreSCRS::Plugin::CardPluginService` + `CardData`. Поља по породици картица и даље постоје унутар додатака. |
| `smartcard::SecureBuffer` | `LibreSCRS::Secure::Buffer` (бинарно) + `LibreSCRS::Secure::String` (текст) |
| `readCard` баца на грешку | `readCard` враћа `LibreSCRS::Plugin::ReadResult` са status enum-ом (изузеци више не прелазе границу додатка) |
| `readCardStreaming` засебна метода | Спојено у `readCard` са опционом `GroupCallback` — имплементирате једну методу, streaming укључујете позивом callback-а |
| `canHandleConnection(PCSCConnection&)` | `canHandleConnection(const vector<uint8_t>& atr, CardSession&)` — ATR проследен унапред |
| `SigningService::instance()` / `configure*()` | Уклоњено — конструишите једном кроз `make_shared<SigningService>(trustService, tsa)` по политици |
| `SigningService(TrustConfig, TsaProvider)` (3.x preview) | `SigningService(shared_ptr<Trust::TrustStoreService>, TsaProvider)` — животни циклус поверења је померен у засебан first-class сервис. Миграција: замените `SigningService(trustConfig, tsa)` са `Trust::TrustStoreService::create(trustConfig)` па онда `SigningService(trustService, tsa)`. |
| `Signing::SigningService::trustStore()` getter | Уклоњено — читајте store из сервиса који га поседује: `trustService->trustStore()` |
| `Signing::TrustStoreManager` | Уклоњено — `Trust::TrustStoreService` је јединствени власник животног циклуса |
| Празан `SignResult` значио „додатак не потписује” | `SignResult::outcome == NotImplemented` — експлицитан сигнал |
| `PINResult.success` / `SignResult.success` bool | `bool ok() const noexcept` изведен из `.outcome` |
| `extraHeaders` био `std::map` | `std::vector<std::pair>` — чува ред уметања, дозвољава дупликате |
| `SigningResult::invalidRequest(std::string)` | `SigningResult::invalidRequestDiagnosticOnly(std::string)` — име оглашава „без корисничке LocalizedText” trade-off |
| `PCSCConnection::Pcsc(reader)` (баца изузетак на грешци) | `CardSession::open(reader)` враћа `std::expected<CardSession, OpenError>` (`noexcept`) |
| `CredentialResult::errorMessage` | `CredentialResult::userMessage` (преименовано ради конзистентности преко result типова) |
| `OpenError::message` | `OpenError::userMessage` (преименовано ради конзистентности преко result типова) |
| `MonitorEvent::errorDetail` | `MonitorEvent::diagnosticDetail` (преименовано ради конзистентности преко result типова) |

**Plugin ABI:** v5 (3.x) → **v6** (4.0). Third-party додаци МОРАЈУ бити поновно компилирани против 4.0 хедера. `static_assert` макроа `LIBRESCRS_DECLARE_CARD_PLUGIN(T, 6)` хвата mismatch верзије у compile-time.

**Дистрибуција дељене библиотеке:** LibreMiddleware-ов public static-link уговор је непромењен — статичке архиве, потрошач са конзистентним toolchain-ом, без ABI стабилности преко `libstdc++` верзија. Једина испоручена дељена библиотека је `librescrs-pkcs11.so` која носи сопствени C ABI за PKCS#11 потрошаче.

За комплетан списак уклоњених симбола и по-release миграционе напомене, видети LibreCelik release-notes у изворном стаблу.
