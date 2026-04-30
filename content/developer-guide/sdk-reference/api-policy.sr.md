---
title: "API политика"
description: "LibreSCRS правила за верзионисање, застаревање и стабилност јавног API-ја"
weight: 20
aliases:
  - /dev/api-policy/
---

# LibreSCRS API политика

**Опсег:** уређује површину `LibreSCRS::*` јавног API-ја који излаже LibreMiddleware и сваки други LibreSCRS repozitorijum.

## 1. Верзионисање (SemVer 2.0)

- **Major** (`X.0.0`) — намерне breaking промене; уклањање претходно застарелих симбола; промене потписа које нарушавају source compatibility.
- **Minor** (`X.Y.0`) — нови јавни симболи (backward-compatible); анотације застаревања на legacy симболима; еволуције build-системa које чувају public-link уговор.
- **Patch** (`X.Y.Z`) — само bug fix-ови. Без промена јавних потписа; без нових застаревања.

## 2. Јавна површина

```
Public API = све под LibreSCRS::{Auth,SmartCard,Secure,Plugin,Signing}::*,
             доступно преко јавних CMake target-а LibreSCRS::{Auth,SmartCard,
             Plugin,Signing,All}. Све остало — smartcard::, libresign::,
             internal header-и, сви не-LibreSCRS namespace-и — је имплементациони
             детаљ и може се мењати у било ком релизу без semver последица.
```

## 3. Правила застаревања (примењују се од 4.0 надаље)

### 3.1 Release-bridging застаревање (подразумевани облик)

Примењује се на сваки симбол који корисници ван овог repo-а могу видети — public headers, installed CMake targets, plugin ABI, било шта на шта third-party SDK consumer може да линкује.

1. Симбол означен `[[deprecated("<разлог>; use <замена> since <верзија>")]]` у релизу X.Y **мора остати callable** током целокупне X.* линије.
2. `@deprecated` Doxygen таг мора бити упарен са `@since` тагом на замени.
3. Застарели симболи се **уклањају** у следећем major-у (X+1.0). Ниједно застаревање не преживљава major version bump.
4. Release notes за сваки X.Y који уводи застаревања мора излистати свако ново застаревање под насловом „Deprecated in X.Y".
5. Миграциони водич у release notes сваког major-а документује сваки уклоњени симбол и његову pre-major замену.

### 3.2 Транзиционо in-repo застаревање (изузетак — само за interne рефакторе)

Примењује се када interni refactor треба да пребаци in-tree пазиваче са старог overload-а/потписа на нови КРОЗ ВИШЕ КОМИТА на ИСТОЈ грани, БЕЗ external consumer-а између првог и последњег комита. Пример: refactor у више комита који је заменио `TSAClient::timestamp(hash, url, timeout)` са `TSAClient::timestamp(hash, TSARequest)` кроз три комита на истој грани — први комит је додао нови overload поред старог, други је мигрирао све in-tree позиваче, трећи је уклонио стари overload.

Правила:

1. **Препоручени пут**: уради миграцију у ЈЕДНОМ комиту — додај нови overload, мигрирај позиваче, обриши стари overload. Без `[[deprecated]]` маркера. Чува `[[deprecated]]` за површине које end-корисници виде.
2. **Multi-commit пут** (када би један комит био превелики или мешао concerns): анотирај стари overload `[[deprecated(<разлог>)]]` са експлицитном напоменом да је ово транзиционо in-repo; мигрирај позиваче у наредним комитима; обриши стари overload у финалном комиту. Цео циклус МОРА да се обави на истој грани пре merge-а у `main`.
3. **Никад не мешај 3.1 и 3.2**: симбол намењен 3.2 транзиционом третману НЕ СМЕ да остане deprecated после branch merge-а. Ако грана носи release, симбол се брише пре tag-овања.
4. Commit message delete-commit-а мора да референцира intro-deprecate commit SHA како би review-ери могли да потврде да се циклус чисто затвара.

### 3.3 Разликовање два случаја

Ако `[[deprecated]]` преживи release-tagged commit на `main`: то је §3.1 — external consumers га сада виде, уклања се у следећем major-у.

Ако `[[deprecated]]` слети и нестане у потпуности на feature грани пре него што се та грана merge-ује: то је §3.2 — маркер је био refactoring конвенција, никада уговор.

## 4. Plugin ABI

ABI `CardPlugin` интерфејса је независно верзионисан (тренутно: **v6**, уведен 4.0 главним издањем). ABI верзија расте када се мења virtual table layout (нове non-default методе, уклоњене методе, реорганизоване методе, или се мења layout plugin-facing aggregate структуре). Non-ABI промене plugin-интерфејса (додавање virtual методе са безбедним default-ом, додавање вредности на крај enum-а затвореног default-arm-ом) НЕ bump-уjу ABI.

Аутори third-party plugin-а циљају специфичну ABI верзију. `LibreSCRS::Plugin::kCardPluginAbiVersion` излаже тренутни ABI integer, а `LIBRESCRS_DECLARE_CARD_PLUGIN(PluginType, AbiVersion)` макро `static_assert`-ује compile-time једнакост између plugin-ове декларисане верзије и тренутне хедерске константе — тако да се ABI drift појављује као plugin build failure, а не као runtime mismatch. Регистар додатно проверава верзију при load-у преко `card_plugin_abi_version()` extern "C" симбола и одбија mismatches као `LoadOutcome::Status::AbiMismatch`.

**Append-only дисциплина за plugin-facing enum-е.** `ReadResult::Status`, `PINResultOutcome`, `SignResultOutcome`, `SignMechanism`, `CardCapabilities`, и сваки будући plugin-facing enum морају бити третирани као append-only кроз ABI ревизије — старе вредности задржавају свој нумерички идентитет, нове вредности стижу на крај. Уклањање вредности захтева ABI bump. Consumer switch-еви на овим enum-има треба или да покрију сваку вредност (`-Wswitch-enum` compile-time check) или да укључе `default:` гранy тако да plugin који враћа post-version вредност против pre-version host-а degradirа предвидљиво.

Кандидати за будући рад за следећи plugin ABI bump праћени су као интерни roadmap који стиже уз release notes главне верзије која их уводи; аутори third-party plugin-а треба да се ослањају на објављени ABI integer (`kCardPluginAbiVersion`) као једини сигнал компатибилности уместо да форвард-предвиђају против необјављених кандидата.

## 5. Валидација vs. runtime руковање грешкама

Две различите врсте неуспеха чисто се разликују у LibreSCRS 4.0. Механизам извештавања о грешкама мора одговарати врсти неуспеха.

### 5.1 Неуспеси конструкције / валидације — throw

Builder-и, factory-је и конструктори који валидирају улазе које задаје позивалац бацају `std::invalid_argument` (или специфичнији подтип `std::logic_error`) са поруком која идентификује проблематично поље. То укључује:

- `SigningRequest::Builder::build() &&` — недостаје обавезно поље (улазни/излазни фајл, формат); неслагање на нивоу формата.
- `VisualSignatureParams::Builder::rect(x, y, w, h)` — непозитивна ширина или висина.
- `VisualSignatureParams::Builder::pageIndex(i)` — негативни индекс.
- `AuthRequirement::forSigning(...)`, `forChangePin(...)`, `forUnblockPin(...)` — празна PIN ознака.

Од позиваоца се очекује да руковање изузецима ограничи на фазу конструкције (нпр. клик „Next" у wizard страници, setup SDK consumer апликације), а затим третира конструисани објекат као валидан током runtime фазе.

### 5.2 Runtime / environmental неуспеси — status-code резултат

Методе које могу отказати из environmental разлога (картица није присутна, file I/O, network, одустајање корисника, итд.) враћају result тип који носи `Status` enum. Те методе НЕ бацају изузетке преко границе јавног API-ја LibreSCRS 4.0. То укључује:

- `SigningService::sign(...)` → `SigningResult` са `SigningResult::Status`.
- `CardPlugin::verifyPIN(...)`, `changePIN(...)`, `unblockPIN(...)` → `PINResult` (plugin ABI).
- `CardPluginService` (ктор) — хвата dlopen неуспехе, throw-ове из фабрике, и ABI mismatches интерно; сваки скенирани фајл производи `LoadOutcome` унос у `loadReport()`-у уместо пропагирања изузетка.

Engine-интерне грешке које заиста не могу да се класификују као нека од `Status` вредности пријављују се преко `SigningResult::Status::SigningEngineError` + `diagnosticDetail` стринга за логове. Позиваоци никада не примају бачене изузетке од `sign()`.

### 5.3 Чисти accessor-и — noexcept где је могуће

Getter-и (нпр. `SigningRequest::inputFile()`, `TrustConfig::trustedListFile`, pimpl-backed `operator==`) су `noexcept` и враћају по const референци или вредности, како је одговарајуће. Време живота враћених референци документовано је на сваком accessor-у.

### 5.4 Образложење

Бацање при конструкцији чини валидацију управљивом — позивалац може да ограничи руковање изузецима на фазу конструкције, а затим да третира конструисани објекат као валидан током целог његовог живота. Мешање throw + status-code унутар једне методе је анти-образац који LibreSCRS избегава.

SDK consumer-и пишу:
```cpp
// Фаза валидације — може да баци изузетак
try {
    auto request = std::move(SigningRequest::Builder{}
                     .inputFile(inPath)
                     .outputFile(outPath)
                     .format(SignatureFormat::Pades)
                     .level(SignatureLevel::B_LT))
                 .build();
    // Runtime фаза — status-code резултати
    auto result = signingService->sign(request, credProvider, plugin, session);
    switch (result.status) {
        case SigningResult::Status::Ok: ...
        case SigningResult::Status::UserCancelled: ...
        // ...
    }
} catch (const std::invalid_argument& e) {
    // Валидација у Builder-у неуспешна — UI порука о грешци
}
```

## 6. 3.0 → 4.0 прелаз (историјска белешка)

Сам пролаз за стабилизацију API границе је 4.0 major bump. 3.0 се испоручује без `[[deprecated]]` анотација; миграциони водич 4.0 документује комплетан сет уклоњених `smartcard::*` / `libresign::*` симбола са њиховим `LibreSCRS::*` заменама. Наредни циклуси (4.x → 5.0, 5.x → 6.0, ...) прате формални deprecate-in-minor → remove-in-major образац из §3 изнад.

## 7. Именовање enum вредности

LibreSCRS enum-ови користе **PascalCase** за идентификаторе вредности подразумевано:

- `SignatureFormat::Pades`, `Cades`, `Xades`, `Jades`, `AsicE`
- `Status::Ok`, `Cancelled`, `Error`

Два намерна изузетка:

1. **Стандардизовани акроними (3 слова или дужи) остају великим словима** када се појављују као самостални токени у идентификаторима: `PKI`, `EID`, `MRZ`, `CAN`, `PIN`, `PUK`. Сложене речи користе PascalCase: `EmrtdCrypto`, не `EMRTDCrypto`.
2. **ETSI-spec токени задржавају подвлаке**: `SignatureLevel::B_B`, `B_T`, `B_LT`, `B_LTA` пресликавају канонички облик из AdES стандарда. Подвлаке овде стоје за цртице из спецификације.

Када си у недоумици, користи PascalCase. Између акронима и PascalCase, приоритет иде на PascalCase ради читљивости.

## 8. Имплементациони детаљи на које consumer-и не треба да се ослањају

Библиотека чита неколико environment променљивих током извршавања. То су **интерни escape hatch-еви** — нису део public API-ја и подложни су промени без ABI bump-а:

| Променљива | Ефекат |
|---|---|
| `LIBRESCRS_SIGNING_BACKEND` | Пребацује између `native` (подразумевано) и `dss` (Java Digital Signature Services oracle, користи се за cross-validation у тестовима). |

Consumer-и не треба да их подешавају у production-у. Имена користе `LIBRESCRS_*` префикс; ако будући release изложи стабилну опцију, биће премештена у типизирано configuration поље на одговарајућем Builder-у.
