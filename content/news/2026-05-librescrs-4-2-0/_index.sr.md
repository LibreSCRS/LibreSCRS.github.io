---
title: "LibreSCRS 4.2.0 — API за снимак листе читача и дељење сесије унутар процеса"
date: 2026-05-28
summary: "LibreMiddleware 4.2.0 + LibreCelik 4.2.0: Qt-free API за снимак листе читача, помоћни приступници за CardData, аутоматско дељење сесије унутар процеса које замењује 4.1 attach C ABI, подршка за AET SafeSign QSCD и fail-closed провера лиценци у пакету."
draft: false
---

LibreSCRS 4.2.0 је друго функционално издање у 4.x циклусу.
**LibreMiddleware 4.2.0** и **LibreCelik 4.2.0** носе GPG-потписане git
тагове и cosign-потписане артефакте издања. ABI је адитиван у односу на
4.1.0; потрошачи само за приказ који користе `LibreSCRS::Plugin`,
`LibreSCRS::Signing` и `LibreSCRS::Trust` граде се и раде непромењено.

## Истакнуто

- **API за снимак листе читача** — `MonitorService::subscribeReaderList`
  испоручује целу листу читача после промене као један Qt-free снимак
  (плус иницијално окидање за оне који се касно прикључе), па потрошачи
  више не преклапају појединачне догађаје у локални скуп.
- **Qt-free приступници за CardData** — `LibreSCRS::Plugin::textValue` /
  `textValueAt` сажимају плес `findGroup → groupAt → петља поља` у један
  позив који враћа `std::optional<std::string>`; GUI адаптери постају
  танки омотачи.
- **Дељење сесије унутар процеса замењује attach C ABI** — 4.1
  `AttachHook` / `SessionAttachment` PKCS#11 attach C ABI је **уклоњен**.
  Поседовање `CardSession`-а као `std::shared_ptr` сада аутоматски омогућава
  да путања потписивања унутар процеса поново користи живу сесију безбедне
  размене порука хоста без експлицитног attach позива.
- **AET SafeSign QSCD (Infineon)** — читање и потписивање сада раде на AET
  SafeSign QSCD картицама кроз откључавање софтверском атестацијом.
- **Очвршћавање конкурентности** — исправљено више трка у мониторовању
  читача, уз детерминистичке регресионе тестове без хардвера.
- **Fail-closed провера лиценци у пакету** — LibreCelik намеће, у CI-ју при
  сваком пушу, да се свака дељена библиотека у пакету пресликава на
  документовану лиценцу, за Linux `.so` и macOS `.dylib` распореде.

Погледајте [Шта је ново у 4.2](/sr/developer-guide/whats-new-in-4-2/) за
потпуне промене API-ја и напомене за прелазак са 4.1.

## Надоградња

- Хостови само за приказ: нису потребне промене.
- Хостови који су уграђивали `librescrs-pkcs11.so` унутар процеса: уклоните
  `SessionAttachment` / `AttachHook` инсталацију и поседујте живу сесију као
  `std::shared_ptr<CardSession>` — види
  [Дељење сесије унутар процеса](/sr/developer-guide/pkcs11-session-injection/).

## Преузимања

- [LibreMiddleware 4.2.0 издање](https://github.com/LibreSCRS/LibreMiddleware/releases/tag/4.2.0)
- [LibreCelik 4.2.0 издање](https://github.com/LibreSCRS/LibreCelik/releases/tag/4.2.0)

Сви артефакти долазе са `.sigstore.json` cosign потписима; провера:
`cosign verify-blob --bundle <name>.sigstore.json <name>`.
