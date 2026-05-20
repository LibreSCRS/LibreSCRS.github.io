---
title: "LibreSCRS 4.0.0 — прво стабилно издање 4.0 циклуса"
date: 2026-05-11
summary: "LibreMiddleware 4.0.0 + LibreCelik 4.0.0 објављени. C++23 језгро, ABI v6, нативно PAdES/XAdES/JAdES/CAdES/ASiC-E потписивање, RFC 5280 ланац поверења, eMRTD PACE, лична карта Србије + AET SafeSign + PIV + генеричке PKCS#15 картице."
draft: false
---

LibreSCRS 4.0.0 је данас објављен. Након два кандидата за издање и
опсежног тестирања у заједници на Linux, macOS и Windows платформама, и
**LibreMiddleware 4.0.0** и **LibreCelik 4.0.0** носе GPG-потписане git
тагове и cosign-потписане артефакте издања.

## Шта 4.0 доноси

- **C++23 језгро** са `std::expected` API-јем за фабрике које могу да
  омане, `LocalizedText` i18n метаподацима, и `CancelToken`-ом за
  кооперативно отказивање.
- **Нативно PAdES / XAdES / JAdES / CAdES / ASiC-E потписивање** кроз
  `LibreSCRS::Signing::SigningService` — без екстерног демона.
- **Аутоматско прилагођавање визуелног потписа** (`layoutVisualSignature`)
  — преглед у чаробњаку се пиксел-тачно поклапа са уграђеним PAdES
  излазом.
- **RFC 5280 ланац поверења** са eIDAS qcStatements конформацијом.
- **eMRTD PACE** за безконтактно читање пасоша; **CardEdge, PKCS#15,
  PIV** провајдери; **OpenSC фолбек** у card-plugin путу.
- **Уграђени CardEdge OpenSC спољни драјвер** за OpenSC 0.26.1 и
  0.27.1, у одвојеном tarball-у, док upstream OpenSC не угради srbeid
  драјвер у нумерисано издање.

## Познат проблем — рутирање PIN-а између вишеструких картица

Када су више српских паметних картица истовремено убачене и корисник
покрене ток потписивања, PIN захтев може бити асоциран са другачијим
слотом од оног који поседује изабрани сертификат. Конфигурације са
једном картицом нису погођене. Поправка је архитектурална — Card+Slot
модел — и главна је новина 4.1.0, већ имплементирана на развојној
грани.

## Преузимања

- [LibreMiddleware 4.0.0 издање](https://github.com/LibreSCRS/LibreMiddleware/releases/tag/4.0.0)
- [LibreCelik 4.0.0 издање](https://github.com/LibreSCRS/LibreCelik/releases/tag/4.0.0)

Сви артефакти долазе са `.sigstore.json` cosign потписима; провера:
`cosign verify-blob --bundle <name>.sigstore.json <name>`.
