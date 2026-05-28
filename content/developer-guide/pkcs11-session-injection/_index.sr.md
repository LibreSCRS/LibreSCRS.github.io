---
layout: "simple"
title: "Дељење сесије унутар процеса"
description: "Дељење живе CardSession између приказа и PKCS#11 путање потписивања унутар процеса преко SessionPresence регистра — преправљено у LibreSCRS 4.2.0"
weight: 60
---

Ова страница је намењена хост апликацијама (LibreCelik, алати за
потписивање трећих страна, интегратори у стилу прегледача) које воде
PKCS#11 путању потписивања **унутар процеса** и желе да модул поново
користи живу `CardSession` хоста уместо да отвара другу PC/SC конекцију ка
истом читачу. Отварање паралелне конекције уништило би стање безбедне
размене порука (PACE/BAC, SM) које је хост успоставио, па LibreSCRS
координира то двоје кроз процес-локални регистар.

## Шта је промењено у 4.2

> **4.1 attach C ABI је уклоњен.** `extern "C"` површина из
> `AttachHook.h` (`librescrs_pkcs11_attach_session` /
> `_detach_session`, токен `LibrescrsPkcs11AttachTokenV1`, кодови
> `LIBRESCRS_PKCS11_ATTACH_*`) и C++ омотач
> `LibreSCRS::Pkcs11::SessionAttachment` **више не постоје**. У 4.2 нема
> експлицитног attach/detach позива. Ако имате 4.1 код који зове
> `SessionAttachment::attach(...)`, погледајте
> [Прелазак са 4.1](#прелазак-са-41) испод.

У 4.2 је координација **аутоматска**. `CardSession` наслеђује
`std::enable_shared_from_this`, па у тренутку када сесију поседујете кроз
`std::shared_ptr<CardSession>` она региструје `weak_ptr` у интерном,
процес-локалном `SessionPresence` регистру. opensc-pkcs11 провајдер унутар
процеса консултује тај регистар: када на читачу већ постоји жив SM канал,
провајдер **одустаје** — одбија да отвори паралелну PC/SC конекцију уместо
да руши SM тунел везан за сесију хоста. Ваш позив потписивања унутар
процеса тако поново користи аутентификовану сесију хоста и њену живу
безбедну размену порука.

Регистрација је RAII: када власнички `shared_ptr` нестане, `weak_ptr` се
сам брише, па нема ничега што треба ручно одрегистровати.

## Одговорност хоста: поседујте сесију као `shared_ptr`

Цео уговор на страни хоста је „држите сесију у
`std::shared_ptr<CardSession>` и предајте тај показивач потрошачу унутар
процеса“. `LibreSCRS::Signing::SigningService::sign(...)` већ прима сесију
као `std::shared_ptr` по вредности, па уобичајен случај не захтева додатни
код.

```cpp
#include <LibreSCRS/SmartCard/CardSession.h>
#include <LibreSCRS/Signing/SigningService.h>

namespace ls = LibreSCRS::SmartCard;

void run_signing(const std::string& readerName)
{
    auto opened = ls::CardSession::open(readerName);
    if (!opened) { return; }

    // Поседовање сесије кроз shared_ptr је аутоматски региструје у
    // процес-локалном SessionPresence регистру (weak_ptr, RAII).
    auto session = std::make_shared<ls::CardSession>(std::move(*opened));

    // ... активирајте PACE/BAC канал који картица захтева (види Card-Session SM) ...

    // Потписивање унутар процеса поново користи `session` и њену живу SM.
    // opensc-pkcs11 провајдер види живо присуство и одустаје уместо да
    // отвори другу PC/SC конекцију ка `readerName`.
    signingService.sign(request, session, token);

    // Нестанак `session` на крају опсега брише њен weak_ptr из регистра.
}
```

Ово прати оно што LibreCelik ради:
`std::make_shared<LibreSCRS::SmartCard::CardSession>(std::move(*opened))`
у `src/librecelik.cpp`, са истим `shared_ptr`-ом који тече у чаробњак за
потписивање и `SigningService::sign()`.

### Сесије чуване по вредности

Аутоматска `SessionPresence` регистрација ослања се на
`shared_from_this()`, што важи само када сесију поседује `std::shared_ptr`.
Сесија чувана **по вредности** (на пример `BridgeSession` SwiftUI хоста,
који чува `CardSession` уграђено) прескаче регистрацију као документована
безоперација — иначе би `shared_from_this()` бацио `std::bad_weak_ptr`.
Такви хостови ионако држе једну PC/SC конекцију, па нема конфликта
паралелне конекције који би требало координисати.

## CardMap и вишеструки PIN

PKCS#11 расподела вишеструких PIN-ова ослоњена је на
`LibreSCRS::SmartCard::CardMap`
(`include/LibreSCRS/SmartCard/CardMap.h`), нит-безбедан процес-локални кеш
кључеван торком `(reader, atrHex, serial)` који се пресликава у
`CardMapEntry` са разрешеном PKCS#15 путањом, радним SELECT FILE P2 бајтом
(`0x0C` подразумевано, `0x00` за картице које то захтевају) и PIN ознакама
пронађеним у AODF-у. Кеш омогућава да се PKCS#15 распоред сваке картице
испита једном и поново користи кроз набрајање слотова, тако да картица са
више акредитива излаже један слот по PIN-у без поновног покретања EF.DIR
резерве на сваком улазу.

| Метода | Сврха |
|---|---|
| `get(key)` | Потражи кеширани унос; враћа `std::nullopt` ако не постоји. |
| `put(key, entry)` | Постави или препиши унос. |
| `invalidate(key)` | Уклони унос за једну картицу (нпр. на `cardRemoved`). |
| `invalidateAll()` | Уклони сваки унос, обично у време `C_Finalize`. |

Све јавне методе су `noexcept` и интерно синхронизоване. Хост апликације
углавном не дирају `CardMap` директно — користи га PKCS#11 модул — али је
тип јаван да би PKCS#11 провајдери изграђени на LibreMiddleware могли да се
интегришу са истим кешом уместо да воде паралелни.

## Прелазак са 4.1

| 4.1 (уклоњено) | 4.2 (замена) |
|---|---|
| C позив `librescrs_pkcs11_attach_session(reader, token)` | ништа — поседујте сесију као `std::shared_ptr<CardSession>` |
| `LibreSCRS::Pkcs11::SessionAttachment::attach(modulePath, reader, session)` | ништа — аутоматска регистрација преко `enable_shared_from_this` |
| Експлицитан `detach()` / рушење у деструктору пре `C_Finalize` | ништа — `weak_ptr` регистра се брише када `shared_ptr` нестане |
| `#include <LibreSCRS/Pkcs11/SessionInjection.h>` / `AttachHook.h` | заглавља уклоњена; укључите `<LibreSCRS/SmartCard/CardSession.h>` |

Практично: обришите `SessionAttachment` инсталацију, уверите се да живу
сесију поседује `std::shared_ptr<CardSession>`, и предајте тај показивач
потрошачу унутар процеса. Понашање поновне употребе SM које сте раније
добијали успешним `attach`-ом сада се дешава аутоматски.

## Погледајте такође

- [`../card-session-sm/`](../card-session-sm/) — отварање `CardSession`-а
  и активирање стања безбедног канала.
- [`../secure-channels/`](../secure-channels/) — протоколи (PACE, BAC,
  обичан) чије се стање чува преко границе унутар процеса.
- [`../whats-new-in-4-2/`](../whats-new-in-4-2/) — преглед промена API-ја
  у 4.2 и напомене за прелазак.
