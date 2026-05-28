---
layout: "simple"
title: "CardData Convenience Accessors"
description: "Qt-free textValue / textValueAt helpers over the CardData vocabulary — introduced in LibreSCRS 4.2.0"
weight: 47
---

Introduced in **LibreSCRS 4.2.0**. These two free functions collapse the
two-step `findGroup → groupAt → field-loop → textValue` dance that GUI
adapters previously hand-rolled on top of the raw
`LibreSCRS::Plugin::CardData` index API into a single call returning
`std::optional<std::string>`. They are Qt-free, so GUI adapters
(LibreCelik today; LibreMac / LibreKDE next) become thin `QString` wrappers
on top.

Both functions live in `LibreSCRS::Plugin`, declared in
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

| Function | Looks up by | Returns |
|---|---|---|
| `textValue(data, groupKey, fieldKey)` | well-known group **key** | engaged `optional` with the UTF-8 text when the group exists, the field exists, and it is a `FieldType::Text` field; `std::nullopt` otherwise |
| `textValueAt(data, groupIndex, fieldKey)` | explicit group **index** | same contract; index beyond `data.groups.size()` yields `std::nullopt` |

## Semantics

- **First-match on key.** When multiple groups share the same `groupKey`,
  `textValue` consults only the first (matching `CardData::findGroup`'s
  first-match semantics). Use `textValueAt` with an explicit index to target
  a second-or-later group.
- **Three failure modes collapse to `nullopt`.** A `nullopt` means *missing
  group*, *missing field*, **or** *non-textual field* — all three. Callers
  that must distinguish them should use the raw
  `CardData::findGroup` / `groupAt` / `CardField::textValue` triple directly.
- **`noexcept` value-aggregate access.** Both operate over plain value
  aggregates and are thread-compatible: concurrent reads of the same
  `CardData` are safe; concurrent read + mutate is not.

## Examples

By group key:

```cpp
const auto& data = plugin->readCard(...);
if (auto name = LibreSCRS::Plugin::textValue(data, "personal", "given_name")) {
    std::cout << "Given name: " << *name << '\n';
}
```

By explicit index (when the caller already located the group, or must target
a specific one among duplicates):

```cpp
if (auto idx = data.findGroup("personal")) {
    if (auto v = LibreSCRS::Plugin::textValueAt(data, *idx, "surname")) {
        std::cout << "Surname: " << *v << '\n';
    }
}
```

## GUI adapter pattern

A Qt host wraps the accessor in a one-line `QString` adapter:

```cpp
// librecelik::plugin::carddatautils — thin QString adapter
QString getFieldValue(const LibreSCRS::Plugin::CardData& data,
                      std::string_view groupKey, std::string_view fieldKey)
{
    if (auto v = LibreSCRS::Plugin::textValue(data, groupKey, fieldKey))
        return QString::fromStdString(*v);
    return {};
}
```

LibreCelik adopted exactly this in 4.2: the `(CardData&, groupKey, fieldKey)`
and `(CardData&, groupIndex, fieldKey)` overloads now delegate to the LM
accessors, with parity tests asserting the wrapper matches the engine.

## See also

- [What's new in 4.2](../whats-new-in-4-2/)
- [Architecture Overview](../architecture/)
