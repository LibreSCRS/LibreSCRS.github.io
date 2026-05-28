---
layout: "simple"
title: "Помоћни приступници за CardData"
description: "Qt-free помоћници textValue / textValueAt над CardData вокабуларом — уведено у LibreSCRS 4.2.0"
weight: 47
---

Уведено у **LibreSCRS 4.2.0**. Ове две слободне функције сажимају
двокорачни плес `findGroup → groupAt → петља поља → textValue` који су GUI
адаптери раније ручно писали над сировим индексним API-јем
`LibreSCRS::Plugin::CardData` у један позив који враћа
`std::optional<std::string>`. Qt-free су, па GUI адаптери (LibreCelik данас;
LibreMac / LibreKDE следећи) постају танки `QString` омотачи изнад њих.

Обе функције живе у `LibreSCRS::Plugin`, декларисане у
`LibreMiddleware/include/LibreSCRS/Plugin/CardDataAccess.h`.

## API

```cpp
[[nodiscard]] std::optional<std::string>
textValue(const CardData& data,
          std::string_view groupKey,
          std::string_view fieldKey) noexcept;          // @since 4.2

[[nodiscard]] std::optional<std::string>
textValueAt(const CardData& data,
            std::size_t      groupIndex,
            std::string_view fieldKey) noexcept;         // @since 4.2
```

| Функција | Тражи по | Враћа |
|---|---|---|
| `textValue(data, groupKey, fieldKey)` | познатом **кључу** групе | попуњен `optional` са UTF-8 текстом када група постоји, поље постоји и оно је `FieldType::Text` поље; иначе `std::nullopt` |
| `textValueAt(data, groupIndex, fieldKey)` | експлицитном **индексу** групе | исти уговор; индекс изван `data.groups.size()` даје `std::nullopt` |

## Семантика

- **Прво поклапање по кључу.** Када више група дели исти `groupKey`,
  `textValue` консултује само прву (у складу са first-match семантиком
  `CardData::findGroup`). Користите `textValueAt` са експлицитним индексом
  да циљате другу или каснију групу.
- **Три начина неуспеха сажимају се у `nullopt`.** `nullopt` значи *група
  недостаје*, *поље недостаје*, **или** *поље није текстуално* — све троје.
  Позиваоци који морају да их разликују треба да користе сирову тројку
  `CardData::findGroup` / `groupAt` / `CardField::textValue` директно.
- **`noexcept` приступ агрегату вредности.** Обе раде над обичним
  агрегатима вредности и нит-компатибилне су: истовремена читања исте
  `CardData` су безбедна; истовремено читање + измена нису.

## Примери

По кључу групе:

```cpp
const auto& data = plugin->readCard(...);
if (auto name = LibreSCRS::Plugin::textValue(data, "personal", "given_name")) {
    std::cout << "Given name: " << *name << '\n';
}
```

По експлицитном индексу (када је позивалац већ пронашао групу, или мора да
циља одређену међу дупликатима):

```cpp
if (auto idx = data.findGroup("personal")) {
    if (auto v = LibreSCRS::Plugin::textValueAt(data, *idx, "surname")) {
        std::cout << "Surname: " << *v << '\n';
    }
}
```

## Образац GUI адаптера

Qt хост обмотава приступник у једнолинијски `QString` адаптер:

```cpp
// librecelik::plugin::carddatautils — танак QString адаптер
QString getFieldValue(const LibreSCRS::Plugin::CardData& data,
                      std::string_view groupKey, std::string_view fieldKey)
{
    if (auto v = LibreSCRS::Plugin::textValue(data, groupKey, fieldKey))
        return QString::fromStdString(*v);
    return {};
}
```

LibreCelik је управо ово усвојио у 4.2: верзије `(CardData&, groupKey,
fieldKey)` и `(CardData&, groupIndex, fieldKey)` сада делегирају LM
приступницима, уз тестове једнакости који тврде да се омотач поклапа са
мотором.

## Погледајте такође

- [Шта је ново у 4.2](../whats-new-in-4-2/)
- [Преглед архитектуре](../architecture/)
