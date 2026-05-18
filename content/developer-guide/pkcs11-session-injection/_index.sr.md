---
layout: "simple"
title: "PKCS#11 убацивање сесије"
description: "Уграђивање librescrs-pkcs11.so у процес и дељење CardSession између приказа и потписивања — уведено у LibreSCRS 4.1.0"
weight: 60
---

Уведено у **LibreSCRS 4.1.0**. Ова страница се обраћа апликацијама-домаћинима
(LibreCelik, потписни алати трећих страна, прегледачки интегратори) које
учитавају `librescrs-pkcs11.so` **унутар свог процеса** и желе да једну
`CardSession` сесију деле између нити за приказ и PKCS#11 путање за
потписивање. Отварање друге PC/SC ручке ка истом читачу из модула укинуло би
стање PACE заштићених порука које је домаћин већ успоставио, па модул
излаже верзионисану куку за убацивање коју домаћин позива да би уместо тога
делио своју живу сесију.

## C ABI: `AttachHook.h`

C-позивна површина живи у
`include/LibreSCRS/Pkcs11/AttachHook.h` и означена је као `extern "C"` —
безбедна за разрешавање преко `dlsym` из било ког језика са C FFI-јем.

### Магични колачић

```c
#define LIBRESCRS_PKCS11_ATTACH_MAGIC_V1 0x4C53435253415431ULL
```

Низ бајтова исписује `LSCRSAT1` у ASCII запису. v1 магија је **замрзнута**:
будуће несагласне организације токена ће бити испоручене као нова структура
`LibrescrsPkcs11AttachTokenV2` уз одговарајућу константу
`LIBRESCRS_PKCS11_ATTACH_MAGIC_V2`, а v1 површина остаје подржана.

### Структура токена

```c
typedef struct LibrescrsPkcs11AttachTokenV1
{
    unsigned long long magic;
    void*              session_ptr;
    unsigned long      flags;
} LibrescrsPkcs11AttachTokenV1;
```

Позивалац је власник токена. `session_ptr` је непрозиран за C ABI; модул га
интерно претвара у свој познати тип паметног показивача на `CardSession`, и
позивалац мора одржати референцирани објекат живим све до подударног
позива за откачињање. `flags` је резервисано и мора бити нула у v1.

### Улазне тачке

| Функција | Сврха |
|---|---|
| `int librescrs_pkcs11_attach_session(const char* reader_name, const LibrescrsPkcs11AttachTokenV1* token)` | Паркира `session_ptr` уз `reader_name` за следеће пробно очитавање `C_GetSlotList`. Поновно качење за исти читач замењује претходни унос. Безбедно за нити. |
| `int librescrs_pkcs11_detach_session(const char* reader_name)` | Идемпотентно уклањање. Ослобађа референцу на `shared_ptr` са стране модула. Без ефекта ако унос не постоји. |

Ниједна функција никад не баца изузетке преко C границе.

### Кодови повратка

| Код | Макро | Значење |
|---|---|---|
| 0 | `LIBRESCRS_PKCS11_ATTACH_OK` | Успех. |
| 1 | `LIBRESCRS_PKCS11_ATTACH_BAD_MAGIC` | Неподударно `token->magic`. |
| 2 | `LIBRESCRS_PKCS11_ATTACH_BAD_FLAGS` | `token->flags` различито од нуле. |
| 3 | `LIBRESCRS_PKCS11_ATTACH_NULL_PTR` | `reader_name`, `token`, или `token->session_ptr` је `NULL`. |
| 4 | `LIBRESCRS_PKCS11_ATTACH_NOT_INITIALIZED` | `C_Initialize` још није позвано. |
| 5 | `LIBRESCRS_PKCS11_ATTACH_OUT_OF_MEMORY` | Унутрашњи неуспех алокације (такође мапирано из ухваћених изузетака). |

## C++ RAII омотач: `SessionAttachment`

`include/LibreSCRS/Pkcs11/SessionInjection.h` додаје померљиву (move-only)
`final` класу `LibreSCRS::Pkcs11::SessionAttachment` која умотава C ABI у
идиоматски C++23. Конструкција иде преко статичке фабрике:

```cpp
[[nodiscard]] static std::expected<SessionAttachment, Error>
attach(const std::filesystem::path& modulePath,
       std::string                  readerName,
       std::shared_ptr<LibreSCRS::SmartCard::CardSession> session) noexcept;
```

Фабрика прибија модул преко `RTLD_NOLOAD` тако да већ учитани
`librescrs-pkcs11.so` не буде истоварен испод домаћина, затим разрешава
куку за убацивање по имену. Фабрика је `noexcept`: било који `std::bad_alloc`
или неочекивани изузетак преводи се у `Error::OutOfMemory` и излаже се
кроз `std::expected`.

| Енумератор `Error` | Узрок |
|---|---|
| `ModuleNotLoaded` | `modulePath` није могао бити отворен од стране динамичког учитавача. |
| `DlsymFailed` | Модул је учитан, али не извози куку за убацивање (старији модул). |
| `InvalidArguments` | Празан `modulePath` / празан `readerName` / `null` сесија. |
| `Rejected` | Модул је вратио ненулти нумерички статус из куке за убацивање. |
| `OutOfMemory` | `std::bad_alloc` који је испливао из унутрашње копије / алокације. |

Деструктор позива одговарајућу куку за откачињање и ослобађа мапирање
модула; `detach()` је такође доступан за експлицитно рано раздуживање и
идемпотентан је. `readerName()` враћа везано име читача (празно након
откачињања). Операције померања су `noexcept`; померени објекат је у
одвезаном стању и његов деструктор нема ефекта.

## Редослед животног циклуса

1. Домаћин позива `C_Initialize` над учитаним модулом.
2. Домаћин отвара `CardSession` за активни читач на својој нити за приказ.
3. Домаћин позива `SessionAttachment::attach(modulePath, readerName, session)`
   — **после** `C_Initialize`, **пре** `C_GetSlotList`.
4. Домаћин позива `C_GetSlotList` / `C_OpenSession` / `C_Login` / `C_Sign` —
   пробна путања модула усваја убачену сесију уместо да отвара сопствену
   PC/SC ручку ка истом читачу.
5. Домаћин уништава `SessionAttachment` (или експлицитно позива `detach()`)
   пре `C_Finalize`.

Поновно качење за исти читач замењује претходни унос; претходна референца
са стране модула отпада.

## CardMap и расподела више ПИН-ова

PKCS#11 расподелу више ПИН-ова подупире `LibreSCRS::SmartCard::CardMap`
(`include/LibreSCRS/SmartCard/CardMap.h`), процеска кеш безбедна за нити,
кључана торком `(reader, atrHex, serial)` која се мапира у `CardMapEntry`
који носи разрешену PKCS#15 путању, радни SELECT FILE P2 бајт (`0x0C`
подразумевано, `0x00` за картице које то захтевају), и ПИН ознаке откривене
у AODF-у. Кеш омогућава да се распоред PKCS#15 једне картице испита
једном и поново користи кроз набрајање слотова, тако да картица са више
акредитива излаже један слот по ПИН-у без поновног покретања резервне
EF.DIR логике на свакој улазној тачки.

| Метод | Сврха |
|---|---|
| `get(key)` | Тражи кеширани унос; враћа `std::nullopt` ако не постоји. |
| `put(key, entry)` | Уписује или преписује унос. |
| `invalidate(key)` | Уклања унос за једну картицу (нпр. на `cardRemoved`). |
| `invalidateAll()` | Уклања све уносе, обично у време `C_Finalize`. |

Све јавне методе су `noexcept` и интерно синхронизоване. Апликације
домаћини углавном не дотичу `CardMap` директно — њега користи PKCS#11
модул — али је тип јаван како би PKCS#11 пружаоци изграђени на
LibreMiddleware могли да се интегришу са истим кешом уместо да воде
паралелни.

## Пример: минимални домаћин качи сесију

```cpp
#include <LibreSCRS/Pkcs11/SessionInjection.h>
#include <LibreSCRS/SmartCard/CardSession.h>

namespace lp = LibreSCRS::Pkcs11;
namespace ls = LibreSCRS::SmartCard;

void run_signing(const std::string& readerName)
{
    auto session = ls::CardSession::open(readerName).value();

    // C_Initialize над librescrs-pkcs11.so је овде већ успео
    // (илустративно — домаћин поседује PKCS#11 init/finalize пар).

    auto attached = lp::SessionAttachment::attach(
        "/usr/lib/librescrs-pkcs11.so", readerName, session);
    if (!attached) {
        // Прелаз на самосталну PKCS#11 путању; потпис може и даље успети
        // за картице без PACE-а. Уписати структуирани Error и одустати.
        return;
    }

    // C_GetSlotList / C_OpenSession / C_Login / C_Sign поново користе
    // `session`. На изласку из опсега аутоматски се откачиње, потом
    // домаћин позива C_Finalize.
}
```

Извршна референца је
`LibreMiddleware/lib/pkcs11_inject/test/SessionAttachmentTests.cpp`, која
проверава фабрику, путеве за грешке и идемпотентан деструктор.

## Видети још

- [`../card-session-sm/`](../card-session-sm/) — отварање `CardSession` и
  активирање стања заштићеног канала пре качења.
- [`../secure-channels/`](../secure-channels/) — протоколи (PACE, BAC,
  обичан) чије стање преживљава прелазак границе убацивања.
- [`../whats-new-in-4-1/`](../whats-new-in-4-1/) — преглед свих
  4.1.0 површина и напомене за прелазак са 4.0.
