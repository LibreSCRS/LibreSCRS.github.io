---
title: "Допринесите"
layout: "simple"
description: "Како допринети LibreSCRS пројекту"
---

Пројекат је отвореног кода. Ево како можете да допринесете.

---

## Начини доприноса

- **Пријавите грешку** — [LibreCelik пријаве](https://github.com/LibreSCRS/LibreCelik/issues), [LibreMiddleware пријаве](https://github.com/LibreSCRS/LibreMiddleware/issues)
- **Предложите функционалност** — отворите issue на одговарајућем репозиторијуму
- **Пошаљите Pull Request** — погледајте упутства испод

---

## Развојно окружење

Оба пројекта се граде помоћу CMake 3.24+ и C++20 компајлера.

```bash
# Клонирајте оба репозиторијума
git clone https://github.com/LibreSCRS/LibreCelik.git
git clone https://github.com/LibreSCRS/LibreMiddleware.git

# Изградња LibreMiddleware
cd LibreMiddleware
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build

# Изградња LibreCelik са локалним LibreMiddleware
cd ../LibreCelik
cmake -B build -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_LIBREMIDDLEWARE=../LibreMiddleware
cmake --build build
```

За детаље, погледајте [Изградња из изворног кода](/sr/developer-guide/building-from-source/).

---

## Стандарди кодирања

- C++20. Користите `std::span`, `std::format`, паметне показиваче.
- Упозорења компајлера: `-Wall -Wextra -Wpedantic`
- Именовање: `camelCase` за променљиве, `PascalCase` за типове. Без завршних доњих црта на члановима класе.
- SPDX заглавља лиценце на свим изворним фајловима.
- Свака промена мора да укључује тестове.

---

## Процес за Pull Request

1. Fork-ујте репозиторијум
2. Направите feature грану
3. Направите промене са тестовима
4. Push-ујте и отворите Pull Request
5. Опишите шта промена ради и зашто
6. CI мора да прође
7. Code review пре merge-а

---

## Додавање подршке за нову картицу

Ако желите да додате подршку за нови тип смарт картице:

1. **Анализирајте картицу** — користите `card_mapper` CLI алат (део LibreMiddleware-а) за истраживање фајл система картице и APDU одговора. Ово је корисан први корак за разумевање садржаја картице.

2. **Middleware плагин** — имплементирајте `CardPlugin` интерфејс у LibreMiddleware-у. Ово обрађује детекцију картице (ATR подударање или провера на живој конекцији) и читање података.

3. **GUI плагин** — имплементирајте `CardWidgetPlugin` интерфејс у LibreCelik-у. Ово обезбеђује Qt6 widget који приказује податке са картице.

Погледајте [Преглед архитектуре](/sr/developer-guide/architecture/) за детаље о систему плагинова и интерфејсима.

---

## Развојни процес

- Развој уз помоћ вештачке интелигенције — користимо AI алате као део развојног процеса
- Развој вођен тестовима (TDD)
- Code review на сваком pull request-у
- CI pipeline покреће тестове на свим подржаним платформама
