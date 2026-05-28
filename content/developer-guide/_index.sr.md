---
title: "Водич за програмере"
description: "Техничка документација за програмере који проширују LibreSCRS"
layout: "simple"
---

Овај водич је намењен програмерима који желе да разумеју унутрашњост LibreSCRS-а, изграде пројекат из изворног кода или прошире систем новим додацима за картице.

## Напомене о издањима

- [Шта је ново у 4.2](/sr/developer-guide/whats-new-in-4-2/) — API за снимак листе читача, приступници за CardData, дељење сесије унутар процеса и прелазак са 4.1
- [Шта је ново у 4.1](/sr/developer-guide/whats-new-in-4-1/) — безбедни канали и (сада замењена) PKCS#11 attach површина

## Почетак

- [Преглед архитектуре](/sr/developer-guide/architecture/) — компоненте система, ток података, систем додатака и пројектни обрасци
- [Изградња из изворног кода](/sr/developer-guide/building-from-source/) — предуслови, упутства за изградњу и покретање тестова

## Потписивање

- [Архитектура потписивања](/sr/developer-guide/signing-architecture/) — нативни механизам потписивања, подржани формати и руковање сертификатима
- [Водич за интеграцију потписивања](/sr/developer-guide/signing-integration/) — интеграција дигиталног потписивања у апликације користећи LibreMiddleware
- [Вишеструко потписивање: appendSigner](/sr/developer-guide/signing-append-signer/) — додавање потписа у већ потписан контејнер

## Паметна картица и безбедна размена порука

- [Безбедни канали](/sr/developer-guide/secure-channels/) — класе протокола PACE / BAC / обичан канал
- [CardSession API за безбедну размену порука](/sr/developer-guide/card-session-sm/) — активирање канала и управљање акредитивима из сесије
- [API за снимак листе читача](/sr/developer-guide/monitor-reader-list/) — 4.2 ток снимка `MonitorService::subscribeReaderList`
- [Помоћни приступници за CardData](/sr/developer-guide/card-data-access/) — 4.2 Qt-free помоћници `textValue` / `textValueAt`
- [Дељење сесије унутар процеса](/sr/developer-guide/pkcs11-session-injection/) — поновна употреба живе `CardSession` кроз PKCS#11 путању потписивања унутар процеса

За детаље о плагин API-јима, погледајте `CardPlugin` и `CardWidgetPlugin` интерфејсе у [Прегледу архитектуре](/sr/developer-guide/architecture/).
