---
title: "Допринесите"
layout: "simple"
description: "Како допринети LibreSCRS пројекту"
---

Пројекат је отвореног кода. Ево како можете да допринесете.

---

## Начини доприноса

- **Пријавите грешку** — у спремишту у коме грешка и јесте: [LibreMiddleware](https://github.com/LibreSCRS/LibreMiddleware/issues) (комуникација са картицом, додаци, потписивање), [LibreAgent](https://github.com/LibreSCRS/LibreAgent/issues) (језгро агента, жичани протокол, Qt клијентска библиотека), [LibreLinux](https://github.com/LibreSCRS/LibreLinux/issues) (демон, упитник, PKCS#11 модул), [LibreCelik](https://github.com/LibreSCRS/LibreCelik/issues) (Qt GUI), [LibreKDE](https://github.com/LibreSCRS/LibreKDE/issues) (Plasma). Ако нисте сигурни, клијент који сте користили сасвим је добро полазиште.
- **Предложите функционалност** — отворите issue на одговарајућем репозиторијуму
- **Пошаљите Pull Request** — погледајте упутства испод

---

## Развојно окружење

Свако спремиште се гради помоћу CMake 3.24+ и C++23 преводиоца (GCC 13+ /
Clang 17+). Граде се редом по зависностима, и свако после првог троши претходно
као инсталиран пакет, уместо да га довлачи:

```bash
PREFIX=$PWD/prefix

git clone https://github.com/LibreSCRS/LibreMiddleware.git
git clone https://github.com/LibreSCRS/LibreAgent.git
git clone https://github.com/LibreSCRS/LibreLinux.git
git clone https://github.com/LibreSCRS/LibreCelik.git

# 1. middleware
cmake -S LibreMiddleware -B LibreMiddleware/build \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX"
cmake --build LibreMiddleware/build && cmake --install LibreMiddleware/build

# 2. агент — ClientQt је подразумевано OFF; Qt клијенту је потребан
cmake -S LibreAgent -B LibreAgent/build \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" \
      -DCMAKE_PREFIX_PATH="$PREFIX" \
      -DLIBREAGENT_BUILD_CLIENT_QT=ON -DLIBREAGENT_BUILD_PKCS11_FACADE=ON
cmake --build LibreAgent/build && cmake --install LibreAgent/build

# 3. Linux домаћин — демон, упитник, PKCS#11 модул
cmake -S LibreLinux -B LibreLinux/build \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$PREFIX" \
      -DLIBRELINUX_USE_INSTALLED_AGENT_CORE=ON -DLIBRELINUX_USER_INSTALL=ON
cmake --build LibreLinux/build && cmake --install LibreLinux/build

# 4. GUI, према радном checkout-у агента
cmake -S LibreCelik -B LibreCelik/build -DCMAKE_BUILD_TYPE=Release \
      -DFETCHCONTENT_SOURCE_DIR_LIBREAGENT=$PWD/LibreAgent
cmake --build LibreCelik/build
```

LibreCelik троши **LibreAgent**, не middleware: не повезује сопствени PC/SC
слој, јер приступ картици иде кроз агента.

За детаље, погледајте [Изградња из изворног кода](/sr/developer-guide/building-from-source/).

---

## Стандарди кодирања

- C++23 свуда. Користите `std::span`, `std::format`, `std::expected`, паметне показиваче. Јавна фабрика која може да омане враћа `std::expected` — види [Обраду очекиваног исхода](/sr/developer-guide/sdk-reference/expected-result-handling/).
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

2. **Middleware плагин** — имплементирајте `CardPlugin` интерфејс у LibreMiddleware-у. Ово обрађује детекцију картице (ATR подударање или провера на живој конекцији) и читање података. Верзију плагин ABI-ја пријавите макроом `LIBRESCRS_DECLARE_CARD_PLUGIN`; правила су у [API политици](/sr/developer-guide/sdk-reference/api-policy/).

3. **GUI плагин** — имплементирајте `CardWidgetPlugin` интерфејс у LibreCelik-у. Ово обезбеђује Qt6 widget који приказује податке са картице.

Погледајте [Преглед архитектуре](/sr/developer-guide/architecture/) за детаље о систему плагинова и интерфејсима.

---

## Развојни процес

- Развој уз помоћ вештачке интелигенције — користимо AI алате као део развојног процеса
- Развој вођен тестовима (TDD)
- Code review на сваком pull request-у
- CI pipeline покреће тестове на свим подржаним платформама
