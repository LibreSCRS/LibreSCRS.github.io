---
layout: "simple"
title: "API за снимак листе читача"
description: "Пријем меродавног снимка листе читача после промене из MonitorService — уведено у LibreSCRS 4.2.0"
weight: 45
---

Уведено у **LibreSCRS 4.2.0**. Ова страница је намењена хост апликацијама
којима треба тренутни скуп PC/SC читача и ажурирање кад год се тај скуп
промени. Qt-free API `subscribeReaderList` испоручује целу листу читача
после промене као један снимак, па потрошачи више не морају да преклапају
појединачне `ReaderAdded` / `ReaderRemoved` догађаје у локални `std::set`
да би повратили чланство.

Сви симболи живе на јавној класи
`LibreSCRS::SmartCard::MonitorService` декларисаној у
`LibreMiddleware/include/LibreSCRS/SmartCard/MonitorService.h`.

## API

```cpp
using ReaderListCallback =
    std::function<void(const std::vector<std::string>&)>;          // @since 4.2

[[nodiscard]] SubscriptionId
subscribeReaderList(ReaderListCallback callback);                  // @since 4.2

void unsubscribeReaderList(
    SubscriptionId id,
    DrainPolicy policy = DrainPolicy::FireAndForget) noexcept;     // @since 4.2
```

| Члан | Сврха |
|---|---|
| `subscribeReaderList(cb)` | Региструј `cb` за цео снимак листе читача после промене. Враћа `SubscriptionId`. |
| `unsubscribeReaderList(id, policy)` | Одрегиструј претплату на листу читача. `noexcept`. |
| `ReaderListCallback` | `std::function<void(const std::vector<std::string>&)>` — прима имена читача. |

## Семантика

- **Иницијално окидање.** Повратни позив се окида једном при регистрацији
  са тренутним снимком (који може бити празан када ниједан читач није
  прикључен), а затим поново при свакој наредној промени са снимком после
  промене. Они који се прикључе касније тако виде почетни инвентар без
  ручног позивања `listReaders`.
- **Редослед у односу на `subscribe` по догађају.** Унутар једне промене
  листе читача, појединачни `MonitorEvent::Kind::ReaderAdded` /
  `ReaderRemoved` догађаји се испоручују **прво** кроз `subscribe`
  повратне позиве, а агрегирани снимак после промене **након тога** кроз
  сваки `subscribeReaderList` повратни позив. Потрошач који региструје обе
  врсте може се ослонити да сваки снимак види сваки претходни појединачни
  догађај за исту промену.
- **Дељени простор токена.** Хендлови које издају `subscribeReaderList` и
  `subscribe` међусобно су различити и морају се проследити одговарајућој
  верзији unsubscribe. Прослеђивање `subscribe` хендла ка
  `unsubscribeReaderList` (или обрнуто) сматра се непознатим и представља
  безоперацију.
- **Аутоматско покретање.** Први претплатник — рачунајући и `subscribe` и
  `subscribeReaderList` — покреће нит за испитивање. Кратак прозор у коме
  „`isRunning()` може вратити нетачно“ документован на `subscribe` важи и
  овде.
- **Гашење.** `unsubscribeReaderList(id, DrainPolicy::Drain)` блокира док
  тренутни циклус испоруке нити за ову претплату не заврши; након повратка
  повратни позив се гарантовано више не окида. Не позивајте га из самог
  повратног позива у `Drain` режиму (закључавање). Подразумевани
  `FireAndForget` се одмах враћа; испорука која је снимила скуп
  претплатника пре позива може још једном позвати повратни позив након
  тога, па повратни позиви који дирају стање које ускоро нестаје треба да
  користе `Drain` или слабо власништво.

## Пример

```cpp
LibreSCRS::SmartCard::MonitorService monitor;

// Прими меродавну листу читача после сваке промене без одржавања
// локалног std::set<std::string>.
auto id = monitor.subscribeReaderList(
    [](const std::vector<std::string>& readers) {
        // Пребаци на GUI нит, нпр. преко QMetaObject::invokeMethod.
        emitReaderListChanged(readers);
    });

// ... касније, при гашењу:
monitor.unsubscribeReaderList(id);
```

## Прелазак са 4.1

Пре 4.2, хост код се претплаћивао на ток по догађају и ручно поново
градио чланство:

```cpp
// 4.1: преклапање појединачних догађаја у локални скуп
std::set<std::string> readers;
monitor.subscribe([&](const MonitorEvent& ev) {
    if (ev.kind == MonitorEvent::Kind::ReaderAdded)   readers.insert(ev.reader);
    if (ev.kind == MonitorEvent::Kind::ReaderRemoved) readers.erase(ev.reader);
    publish(readers);  // такође је био потребан засебан listReaders() као почетак
});
```

У 4.2, уклоните локални скуп и ручни почетак — `subscribeReaderList` вам
даје снимак директно, укључујући почетни инвентар при првом окидању.
LibreCelik-ов `QSmartCardMonitor` је овако пребачен: сада свој Qt сигнал
`readerListChanged` води право из LM снимка.

## Погледајте такође

- [Шта је ново у 4.2](../whats-new-in-4-2/)
- [Преглед архитектуре](../architecture/)
