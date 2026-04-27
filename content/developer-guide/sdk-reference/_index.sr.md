---
title: "SDK референца"
description: "Референца по просторима имена за 4.0 јавни API LibreSCRS-а"
weight: 30
---

LibreMiddleware испоручује C++20 SDK под `LibreSCRS::*` umbrella-ом. Површина је намерно уска — пет простора имена, ~27 јавних хедера — и стабилна је кроз 4.x линију по [API политици]({{< ref "developer-guide/sdk-reference/api-policy" >}}).

Ова страница је **наративна референца**: шта је сваки простор имена, када га користити, и по један идиоматски пример по компоненти. За ауто-генерисан списак свих ентитета (свака класа, сваки члан, сваки параметар) консултујте Doxygen излаз на GitHub Pages пројекта.

Минимални функционални пример потрошача је `examples/sdk-consumer/main.cpp` у изворном стаблу LibreMiddleware-а — програм од 70 линија који позива по једну методу из сваког јавног циља.

---

## `LibreSCRS::Auth` — упити за креденцијале

Описује **шта middleware тражи од корисника** (PIN, PUK, MRZ, CAN) и како домаћин одговара.

- `AuthRequirement` — захтев. Гради се кроз closed-set фабрике:
  - `forPreRead(PreReadAuthMethod::BacMrz | PaceCan | None)` — материјал за откључавање путног документа.
  - `forSigning(pinLabel, retriesLeft)` — један PIN за потписивање.
  - `forChangePin(pinLabel, retriesLeft)` — тренутни + нови + потврда (три поља).
  - `forUnblockPin(pinLabel)` — PUK + нови + потврда (три поља).
- `FieldDescriptor` — сваки улаз који провajдер мора да прикупи (по један `std::vector` ових по захтеву).
- `CredentialProvider` — `std::function<CredentialResult(const AuthRequirement&)>` који домаћин имплементира.
- `CredentialResult` — враћени bundle; вредности кључеване по `FieldDescriptor::id`-у, свака чувана као `Secure::String` који се нулира.
- `LocalizedText` — `{i18nKey, englishFallback, placeholders}` тројка која се користи за сваку корисничку поруку коју middleware производи.

```cpp
using namespace LibreSCRS;

auto req = Auth::AuthRequirement::forSigning("PIN", /*retriesLeft=*/3);
std::vector<Auth::CredentialResult::Entry> values;
for (const auto& field : req.fields()) {
    Secure::String pin = askUser(field.label.englishFallback);
    values.emplace_back(field.id, std::move(pin));
}
auto answer = Auth::CredentialResult::ok(std::move(values));
```

`CredentialResult` нема default конструктор — намерно се пролази кроз једну од именованих фабрика (`ok`, `cancelled`, `error`) тако да сваки произвођач експлицитно commit-ује `Status`. Ако корисник отказује упит, вратите `Auth::CredentialResult::cancelled()`.

Фабрике су преферирани избор овде (closed-shape захтев) у односу на Builder; видети класну Doxygen документацију за правило.

---

## `LibreSCRS::SmartCard` — PC/SC приступ

Два сервиса изнад PC/SC-а, оба pimpl-backed.

- `Monitor` — извор догађаја читача + картице. Non-copyable, non-movable (везан животни век са табелом претплата). Fan-out за више претплатника: polling нит се ауто-покреће на први `subscribe` и ауто-зауставља на последњи `unsubscribe`.
- `CardSession` — opaque сесијски handle. Конструише се преко noexcept `open(readerName)` фабрике која враћа `OpenSessionResult {optional<CardSession>, optional<OpenError>}`. Move-only.

```cpp
auto mon = std::make_shared<SmartCard::Monitor>();
auto readers = mon->listReaders();               // optional<vector<string>>
if (!readers) return;                            // PC/SC подсистем недоступан

auto token = mon->subscribe([](const SmartCard::MonitorEvent& e) {
    if (e.kind == SmartCard::MonitorEvent::Kind::CardInserted) {
        auto sessionResult = SmartCard::CardSession::open(e.readerName);
        if (sessionResult.session.has_value()) {
            handleCard(std::move(*sessionResult.session));
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
- `CardPluginRegistry` — учита-при-конструкцији, multi-directory. Враћа структурисан `LoadOutcome` по фајлу тако да домаћини приказују грешке додатака уместо да их тихо игноришу.
- `CardData` / `CardFieldGroup` / `CardField` — универзални payload тип који додатак производи.
- `ReadResult` — структурисан исход `readCard`-а (status enum + payload).
- `PinStatusEntry`, `SecurityCheck` / `SecurityStatus` — извештавање по PIN-у и по верификационој провери.
- `AutoReader` — wrapper који спаја `Monitor` са `CardPluginRegistry`-јем и даје `CardData` на insert догађаје.

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

LIBRESCRS_DECLARE_CARD_PLUGIN(MyPlugin, 6)  // ABI верзија закачена у compile-time
```

Изградите као `.so`, инсталирајте у директоријум прослеђен `CardPluginRegistry`-ју. Регистрарски ABI `static_assert` ће се окинути у compile-time ако циљате погрешну верзију. Изузеци НЕ СМЕЈУ да прелазе ABI границу додатка — макро обавија `new MyPlugin()` у noexcept try/catch; throw-ови стижу као `LoadOutcome::Status::FactoryThrew`.

### Коришћење регистра

```cpp
LibreSCRS::Plugin::CardPluginRegistry registry{std::filesystem::path{"/usr/lib/librescrs/plugins"}};

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

## `LibreSCRS::Signing` — PAdES / XAdES / JAdES / CAdES / ASiC-E

Дигитално потписивање против кључа на смарт картици.

- `SigningService` — улазна тачка. **Pure DI**: прима `TrustConfig` + `TsaProvider` у свом конструктору и никад се не мутира касније. Move-only. Конструишите једном по политици поверења/TSA; реиспользовајте кроз sign позиве.
- `SigningRequest` + `SigningRequest::Builder` — параметри једне sign операције (input/output путеве, формат, ниво, visual params, TSA override, contactInfo, reason, location). Builder валидира у `build() &&`.
- `VisualSignatureParams` + `VisualSignatureParams::Builder` — PAdES визуелни изглед анотације. Геометрија се валидира по setter-у. `kDefaultVisualSignatureRect` изложено за домаћине који само желе „дефолт”.
- `TsaProvider` — `std::function<TsaRequest(const TsaContext&)>`. Позива се по sign-у да добави URL + креденцијале (Basic / Bearer / mTLS / extra headers).
- `TrustConfig` — убацивање материјала поверења: offline TL cache, bundled anchors, TSA trust-root toggle-ови.
- `SigningResult` — status enum + `outputPath` (путања потписаног документа на успеху) + опциона translator-friendly порука + дијагностички детаљ.

```cpp
LibreSCRS::Signing::TrustConfig trust;
auto tsa = LibreSCRS::Signing::staticTsaChecked("https://tsa.example.com");  // валидира URL
LibreSCRS::Signing::SigningService service{std::move(trust), tsa};

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
| `smartcard::PCSCConnection`, `smartcard::Monitor` (јавно) | `LibreSCRS::SmartCard::CardSession`, `LibreSCRS::SmartCard::Monitor`; интерни транспорт остаје `smartcard::*` али више није у install stablu |
| `plugin::CardPlugin`, `plugin::CardData` | `LibreSCRS::Plugin::CardPlugin`, `LibreSCRS::Plugin::CardData` — видети промене по методи испод |
| `libresign::SigningService`, `libresign::SignRequest` | `LibreSCRS::Signing::SigningService`, `LibreSCRS::Signing::SigningRequest` + `Builder` |
| Јавни API `eidcard::`, `healthcard::`, `euvrc::`, `piv::` | Уклоњени — потрошачи сада воде све кроз `LibreSCRS::Plugin::CardPluginRegistry` + `CardData`. Поља по породици картица и даље постоје унутар додатака. |
| `smartcard::SecureBuffer` | `LibreSCRS::Secure::Buffer` (бинарно) + `LibreSCRS::Secure::String` (текст) |
| `readCard` баца на грешку | `readCard` враћа `LibreSCRS::Plugin::ReadResult` са status enum-ом (изузеци више не прелазе границу додатка) |
| `readCardStreaming` засебна метода | Спојено у `readCard` са опционом `GroupCallback` — имплементирате једну методу, streaming укључујете позивом callback-а |
| `canHandleConnection(PCSCConnection&)` | `canHandleConnection(const vector<uint8_t>& atr, CardSession&)` — ATR проследен унапред |
| `SigningService::instance()` / `configure*()` | Уклоњено — конструишите једном кроз `make_shared<SigningService>(trust, tsa)` по политици |
| Празан `SignResult` значио „додатак не потписује” | `SignResult::outcome == NotImplemented` — експлицитан сигнал |
| `PINResult.success` / `SignResult.success` bool | `bool ok() const noexcept` изведен из `.outcome` |
| `extraHeaders` био `std::map` | `std::vector<std::pair>` — чува ред уметања, дозвољава дупликате |
| `SigningResult::invalidRequest(std::string)` | `SigningResult::invalidRequestDiagnosticOnly(std::string)` — име оглашава „без корисничке LocalizedText” trade-off |

**Plugin ABI:** v5 (3.x) → **v6** (4.0). Third-party додаци МОРАЈУ бити поновно компилирани против 4.0 хедера. `static_assert` макроа `LIBRESCRS_DECLARE_CARD_PLUGIN(T, 6)` хвата mismatch верзије у compile-time.

**Дистрибуција дељене библиотеке:** LibreMiddleware-ов public static-link уговор је непромењен — статичке архиве, потрошач са конзистентним toolchain-ом, без ABI стабилности преко `libstdc++` верзија. Једина испоручена дељена библиотека је `librescrs-pkcs11.so` која носи сопствени C ABI за PKCS#11 потрошаче.

За комплетан списак уклоњених симбола и по-release миграционе напомене, видети LibreCelik release-notes у изворном стаблу.
