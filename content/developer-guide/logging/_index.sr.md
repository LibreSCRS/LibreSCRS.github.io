---
layout: "simple"
title: "Фасада за евидентирање"
description: "Преусмеравање дијагностике LibreMiddleware-а у лог ваше апликације — API LibreSCRS::log са уметнутим одводом, уведен у LibreSCRS 5.0"
weight: 49
---

Уведено у **LibreSCRS 5.0**. Ова страница је намењена хост апликацијама које
желе да дијагностика LibreMiddleware-а стигне тамо где већ иду и њихове
сопствене поруке — у journald, у ротирајући фајл, у Qt категорију, у конзолу
унутар апликације — уместо на `stderr` процеса.

Сви симболи живе у јавном заглављу
`LibreMiddleware/include/LibreSCRS/Logging.h`, простор имена `LibreSCRS::log`.

## Зашто постоји

Пре 5.0 LibreMiddleware овде није имао никакав шав. Када би повратни позив
претплатника који сте предали `MonitorService::subscribe` бацио изузетак,
библиотека га је хватала — и мора да га хвата, јер изузетак који побегне из
улазне тачке нити `std::thread` позива `std::terminate` — па га пријављивала
преко `std::fprintf(stderr, ...)`. То је и писало у коментару у извору:
резервно решење *„зато што SDK тренутно не уметне логер преко границе јавног
ABI-ја”*.

Библиотека која пише у ток који није њен, без икаквог начина да се то
преусмери, јесте кварна сама по себи, а не ствар укуса. `LibreSCRS::log` је
та граница.

## API

```cpp
namespace LibreSCRS::log {

enum class Level : std::uint8_t { Info, Warn, Error };

using LogSink = std::function<void(Level level, std::string_view line)>;

void init(LogSink sink, std::string category = "rs.librescrs");
void resetForTest() noexcept;

void info(std::string_view message);
void warn(std::string_view message);
void error(std::string_view message);

template <class... Args> void infof(std::format_string<Args...>, Args&&...);
template <class... Args> void warnf(std::format_string<Args...>, Args&&...);
template <class... Args> void errorf(std::format_string<Args...>, Args&&...);

} // namespace LibreSCRS::log
```

Исти облик излаже и LibreSCRS агент (`LibreSCRS::Agent::log`), па једно
претраживање дијагностике чита слој хоста и језгро на исти начин.

## Уметање одвода

`init` се позива једном, током једнонитног покретања, пре него што било која
LibreSCRS услуга крене:

```cpp
#include <LibreSCRS/Logging.h>
#include <LibreSCRS/SmartCard/MonitorService.h>

int main()
{
    LibreSCRS::log::init(
        [](LibreSCRS::log::Level level, std::string_view line) {
            switch (level) {
            case LibreSCRS::log::Level::Info:  myLog().info(line);  break;
            case LibreSCRS::log::Level::Warn:  myLog().warn(line);  break;
            case LibreSCRS::log::Level::Error: myLog().error(line); break;
            }
        },
        "com.example.myapp");

    LibreSCRS::SmartCard::MonitorService monitor;
    // ...
}
```

Прослеђивање **празног** `LogSink`-а враћа уграђени одвод.

## Облик реда

Сваки ред стиже у одвод већ форматиран и завршен новим редом:

```
<N>категорија ниво: порука\n
```

`<N>` је syslog приоритет који journald чита са почетка реда и уклања —
`<6>` за info, `<4>` за warning, `<3>` за error. Свуда другде је то само
инертан текст. На пример:

```
<3>com.example.myapp error: MonitorService: subscriber callback threw: bad allocation
```

Уграђени одвод исписује исти ред на `std::clog`.

## Шта ово хвата, а шта не

`LibreSCRS::log` носи дијагностику коју LibreMiddleware емитује **а да га
нико није питао** — данас су то четири штита око изузетака из повратних
позива потрошача у `MonitorService`-у.

То није канал за трагове. LibreMiddleware и даље има око 150 дијагностичких
места иза пет независних прекидача окружења — `LIBRESCRS_SIGN_TRACE`,
`LIBRESCRS_PCSC_TRACE`, `LIBRESCRS_PROBE_TRACE`, `LIBRESCRS_OPENSC_DEBUG` и
`PKCS11_DEBUG` — која пишу директно на `stderr` и на која уметнути одвод не
утиче. Она се налазе у PC/SC преносу, читању PKCS#15 профила и потписном
мотору; у 5.0 су непромењена. Немојте „уметнуо сам одвод” читати као
„ухватио сам све што LibreMiddleware уме да испише”.

## Правила којих одвод мора да се држи

**Не зовите фасаду из одвода.** Један процесни мутекс држи се преко и
форматирања и позива одвода, тако да се редови никада не преплићу и да `init`
не може да се тркa са емисијом у лету. Позив `LibreSCRS::log::info` изнутра
одвода закључава процес.

**Очекујте позиве са било које нити.** Анкетна нит `MonitorService`-а емитује
на сопственој нити; ваш одвод мора бити безбедан за конкурентни приступ.

**Нека буде јефтин и без изузетака.** Изузетак који изађе из одвода
пропагира се у код LibreSCRS-а који је емитовао — укључујући и `catch` блок
чији је цео посао био да спречи изузетак да стигне до улазне тачке нити.

**Мора да надживи употребу.** Одвод је `std::function` који се чува до краја
процеса. Хватање локалне променљиве са стека, па повратак из функције која га
је уметнула, јесте приступ ослобођеној меморији при следећој емисији.

## Тестирање

`resetForTest()` уклања уметнути одвод и враћа подразумевану категорију. Тест
који уметне одвод што хвата стање локално за тај тест, а не врати га,
оставља тај одвод постављен за сваки следећи случај у истом бинару. Позив
иде у `TearDown()` фикстуре, а не на крај тела теста — тврдња која падне
враћа се раније и прескочи све после себе.

## Глобално стање, намерно

LibreSCRS је иначе грађен на уметању зависности кроз конструктор: без
`instance()`, без Мајерсових синглтона. Фасада за евидентирање је једини
документован изузетак. Провлачење референце на логер кроз сваки унутрашњи тип,
све до `catch` блока у анкетној нити, коштало би целу површину а не би
донело ништа; изузетак је ограничен на ово заглавље, а `resetForTest()` је
обавеза која уз њега иде.
