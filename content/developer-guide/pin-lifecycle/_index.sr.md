---
layout: "simple"
title: "PIN и животни циклус акредитива"
description: "Записи животног циклуса по акредитиву из getPINList — врста, стање, бројачи и заставице способности са конзервативним подразумеваним вредностима — плус улазне тачке за активацију транспортног PIN-а и кључа за потписивање, уведено у LibreSCRS 4.x циклусу"
weight: 48
---

Ова страница је намењена хост апликацијама (LibreCelik, агенти,
интегратори трећих страна) и ауторима додатака који приказују или воде
стање животног циклуса PIN-а. `CardPlugin::getPINList` враћа по један
`LibreSCRS::Plugin::PinStatusEntry` за сваки акредитив који картица
излаже; запис носи класификацију животног циклуса, заставице
способности и бројаче, а свиме управља једно правило конзервативних
подразумеваних вредности. Две улазне тачке за активацију,
`activateTransportPin` и `activateSigningKey`, заокружују површину.

Запис је декларисан у
`LibreMiddleware/include/LibreSCRS/Plugin/PinStatusEntry.h`; улазне
тачке живе на `LibreSCRS::Plugin::CardPlugin`
(`LibreMiddleware/include/LibreSCRS/Plugin/CardPlugin.h`). Сви типови
су обични агрегати вредности — нит-компатибилни, са подразумеваном
једнакошћу по члановима на `PinStatusEntry`.

## Класификациони енуми

Четири `std::uint8_t` енума класификују сваки акредитив. Сва четири су
**append-only** (нове вредности се само додају на крај) када једном
слете, и сваки има прву вредност `Unknown` која је уједно и
конзервативна подразумевана вредност.

### `PinKind` — шта је акредитив

| Вредност | Значење |
|---|---|
| `Unknown` | Нема безбедног доказа за класификацију. |
| `UserPin` | PIN за општу аутентификацију. |
| `SignPin` | PIN за потпис/QSCD (локалан за DF потписа). |
| `Puk` | Кључ за деблокаду (PUK). |
| `Can` | PACE Card Access Number псеудо-акредитив. |

### `PinState` — објективно стање животног циклуса

| Вредност | Значење |
|---|---|
| `Unknown` | Није безбедно утврдиво. |
| `Transport` | Транспортна вредност постављена при издавању; још није персонализован. |
| `Operational` | Иницијализован и употребљив. |
| `NeedsChange` | Картица сигнализира да се PIN мора променити пре употребе. |
| `Blocked` | Бројач покушаја исцрпљен. |

Предност када важи више њих: `Blocked` > `NeedsChange` > `Transport` >
`Operational`. Две инваријанте везују стање за равне заставице:
`state == Blocked` ⇔ `blocked == true`, а `Transport` повлачи
`initialized == false` на фамилијама које подржавају транспортни
режим.

### `UnblockStyle` — како се понаша деблокада PUK-ом

Има значење само када је `unblockable` једнако `true`; иначе МОРА бити
`Unknown`.

| Вредност | Значење |
|---|---|
| `Unknown` | Није могућа деблокада, или стил није познат. |
| `ResetOnly` | Ресет бројача; стара вредност PIN-а се задржава. |
| `SetsNewPin` | Нови PIN је обавезан као део деблокаде. |
| `UnblockAndChange` | Ималац бира: само ресет или постављање нове вредности. |

### `PinRecovery` — ко може да опорави блокирани акредитив

| Вредност | Значење |
|---|---|
| `Unknown` | Нема доказа — клијенти приказују опште упутство „обратите се издаваоцу“. |
| `HolderViaPuk` | Ималац може да деблокира PUK-ом кроз овај софтвер. |
| `IssuerProcess` | Само издавалац може да опорави (нпр. изазов/одговор на шалтеру). |
| `None` | Терминално — једино замена картице. |

## Запис `PinStatusEntry`

Идентитет и ограничења:

| Поље | Тип | Подразумевано | Значење |
|---|---|---|---|
| `label` | `std::string` | — | Ознака коју дефинише додатак; користи се као селектор `pinLabel` у токовима промене/активације. |
| `reference` | `std::uint8_t` | `0` | Картична референца PIN-а (где је применљиво). |
| `retriesLeft` | `std::optional<int>` | `nullopt` | Преостали број покушаја PIN-а; `nullopt` када је непознат. |
| `initialized` | `bool` | `true` | PIN је иницијализован на картици. |
| `blocked` | `bool` | `false` | PIN је тренутно блокиран. |
| `minLength` / `maxLength` | `std::optional<std::size_t>` | `nullopt` | Наметнута ограничења дужине; `nullopt` када су непозната. |
| `canChange` | `bool` | `false` | Вредност PIN-а је кориснички променљива. Додаци који подржавају промену МОРАЈУ то експлицитно поставити. |
| `unblockable` | `bool` | `false` | Додатак подржава деблокаду овог PIN-а PUK-ом. |
| `blockedGuidance` | `std::optional<LocalizedText>` | `nullopt` | Порука приказана када је `blocked` тачно а деблокада недоступна. |

Класификација животног циклуса, бројачи и способности:

| Поље | Тип | Подразумевано | Значење |
|---|---|---|---|
| `kind` | `PinKind` | `Unknown` | Класификација акредитива изведена из доказа са картице. |
| `state` | `PinState` | `Unknown` | Објективно стање животног циклуса (видети инваријанте изнад). |
| `retriesMax` | `std::optional<int>` | `nullopt` | Максималан број покушаја (знање о фамилији). |
| `usesLeft` | `std::optional<int>` | `nullopt` | Преостали буџет употребе самог акредитива (бројач употребе PUK-а); `nullopt` када није изложен или није безбедно читљив. |
| `usesMax` | `std::optional<int>` | `nullopt` | Максималан буџет употребе акредитива (максималан број употреба PUK-а); `nullopt` када није изложен. |
| `unblocksLeft` | `std::optional<int>` | `nullopt` | Преостали број деблокада овог PIN-а. |
| `unblockStyle` | `UnblockStyle` | `Unknown` | Понашање деблокаде; `Unknown` осим када важи `unblockable`. |
| `activatable` | `bool` | `false` | Активација транспортни→оперативни је подржана **и** тренутно доступна. |
| `keyActivationPending` | `bool` | `false` | Придружени кључ за потписивање је још деактивиран (увођење у употребу није довршено). |
| `keyActivatable` | `bool` | `false` | Ималац може да активира тај кључ кроз овај софтвер (`false` тамо где је активација могућа само алатом издаваоца). |
| `recovery` | `PinRecovery` | `Unknown` | Ко може да опорави овај акредитив када је блокиран. |
| `probeSafe` | `bool` | `false` | Упити бројача су познато безбедни на овој фамилији. Само за приказ — видети испод. |
| `keyActivationGuidance` | `std::optional<LocalizedText>` | `nullopt` | Упутство приказано када активација кључа чека али је ималац не може обавити. |

## Конзервативне подразумеване вредности: нема доказа, нема понуде

Свака класификација подразумевано је `Unknown`, свака заставица
способности `false`, сваки бројач `nullopt`. Хост МОРА да третира
одсуство доказа као „не нуди операцију“:

- `canChange == false` → без акције промене PIN-а у интерфејсу.
- `activatable == false` → без тока активације транспортног PIN-а,
  чак и када је `state == Transport`.
- `keyActivatable == false` → без тока активације кључа; када је уз то
  `keyActivationPending` тачно, прикажите `keyActivationGuidance`.
- `blocked == true` уз `unblockable == false` → прикажите
  `blockedGuidance` уместо нуђења деблокаде PUK-ом.
- `recovery == Unknown` → прикажите опште упутство „обратите се
  издаваоцу“.

Разлог је одбрамбени: додатак који заборави да попуни заставицу не сме
случајно да огласи способност коју не имплементира. Само позитиван,
експлицитно постављен доказ омогућава акцију у корисничком
интерфејсу.

## Инваријанте

**`getPINList` никада не троши буџет покушаја нити употребе.** Додаци
прикупљају стање животног циклуса искључиво средствима која ништа не
троше. Хост зато може слободно да зове `getPINList` — при убацивању
картице, при освежавању приказа, после сваке операције — без нагризања
вредности `retriesLeft`, `usesLeft` или `unblocksLeft`.

**`probeSafe` служи само за приказ.** Када је `true`, упити бројача су
познато безбедни на овој фамилији картица, па одсутан бројач значи да
вредност заиста није доступна, а не да је намерно остала непрочитана.
Хостови користе заставицу искључиво за формулацију приказа бројача
(„није доступно на овој картици“ наспрам „није прочитано“). Клијенти
НЕ СМЕЈУ да је користе као окидач за сопствене упите ка картици — сва
интерогација картице остаје унутар додатка.

## Улазне тачке за активацију

Обе улазне тачке су `[[nodiscard]] virtual` чланови `CardPlugin`-а,
тајне примају као `LibreSCRS::Secure::String` (брише се при
уништењу) и враћају `PINResult`. Њихове базне имплементације враћају
`PINResultOutcome::Unsupported` — подршка се уводи по фамилији
картица, па позивалац увек може да разликује „овај додатак не
имплементира ток“ од стварног неуспеха на страни картице.

Релевантни исходи `PINResult`-а (`r.ok()` је еквивалентно са
`outcome == PINResultOutcome::Ok`):

| Исход | Значење |
|---|---|
| `Ok` | Операција успела. |
| `InvalidPin` | Картица је одбила предату вредност (`retriesLeft` ажуриран). |
| `Blocked` | Картица пријављује да је акредитив сада блокиран. |
| `KeyActivationFailed` | Провера PIN-а успела, али је корак ACTIVATE кључа неуспео. |
| `Unsupported` | Подразумевана базна имплементација — додатак не имплементира овај ток. |

### `activateTransportPin`

```cpp
[[nodiscard]] virtual PINResult
activateTransportPin(LibreSCRS::SmartCard::CardSession& session,
                     std::string_view pinLabel,
                     const LibreSCRS::Secure::String& transportValue,
                     const LibreSCRS::Secure::String& newPin) const;  // @since 4.x
```

Активира PIN у транспортном режиму: поставља вредност имаоца користећи
транспортну вредност из издавања (картична операција: CHANGE REFERENCE
DATA; тачан облик команде зависи од фамилије). Ток нудите само на
основу позитивног доказа из записа — `state == PinState::Transport`
**и** `activatable`:

```cpp
using namespace LibreSCRS::Plugin;
using LibreSCRS::Secure::String;

// Никада не троши буџет покушаја/употребе — безбедно при сваком освежавању.
const auto pins = plugin->getPINList(session);

for (const auto& entry : pins) {
    if (entry.state != PinState::Transport || !entry.activatable)
        continue; // нема позитивног доказа — не нуди активацију

    const String transportValue = promptForTransportPin();
    const String newPin         = promptForNewPin();

    const auto r = plugin->activateTransportPin(session, entry.label,
                                                transportValue, newPin);
    if (r.outcome == PINResultOutcome::Unsupported) {
        // Подршка за фамилију не постоји у овом издању — не понављати.
    } else if (r.ok()) {
        // Акредитив је сада оперативан; поново прочитати getPINList.
    }
}
```

### `activateSigningKey`

```cpp
[[nodiscard]] virtual PINResult
activateSigningKey(LibreSCRS::SmartCard::CardSession& session,
                   const LibreSCRS::Secure::String& signPin) const;   // @since 4.x
```

Активира још увек деактивиран кључ за потписивање: VERIFY оперативног
SIGN PIN-а и ACTIVATE кључа извршавају се самостално унутар једне
закључане сесије/трансакције (PIN-ALWAYS дисциплина закључавања). По
успеху додатак брише свако безбедносно стање које је успоставио пре
повратка. Код `InvalidPin`/`Blocked` неуспео је корак VERIFY и
`retriesLeft` се односи на SIGN PIN; `KeyActivationFailed` значи да је
VERIFY успео али ACTIVATE није. Услов: `keyActivationPending` **и**
`keyActivatable`:

```cpp
using namespace LibreSCRS::Plugin;
using LibreSCRS::Secure::String;

const auto pins = plugin->getPINList(session);
const auto it = std::ranges::find_if(pins, [](const PinStatusEntry& e) {
    return e.kind == PinKind::SignPin;
});
if (it == pins.end() || !it->keyActivationPending || !it->keyActivatable)
    return; // нема шта да се понуди (прикажите keyActivationGuidance ако чека)

const String signPin = promptForSignPin();
const auto r = plugin->activateSigningKey(session, signPin);

switch (r.outcome) {
case PINResultOutcome::Ok:                  /* кључ активан — потписивање ради */ break;
case PINResultOutcome::InvalidPin:          /* retriesLeft = покушаји SIGN PIN-а */ break;
case PINResultOutcome::Blocked:             /* SIGN PIN је сада блокиран */ break;
case PINResultOutcome::KeyActivationFailed: /* VERIFY успео, ACTIVATE није */ break;
case PINResultOutcome::Unsupported:         /* подршка за фамилију не постоји */ break;
default:                                    break;
}
```

## Доступност

У текућем инкременту обе улазне тачке испоручују се са својим
безбедним базним подразумеваним понашањем: сваки додатак наслеђује
`Unsupported`. Подршка се уводи по фамилији картица у наредним
издањима; заставице способности на страни записа (`activatable`,
`keyActivatable`) прате исти распоред по фамилијама и остају `false`
док их нека фамилија не попуни.

## Погледајте такође

- [CardSession Secure-Messaging API](../card-session-sm/)
- [Преглед архитектуре](../architecture/)
