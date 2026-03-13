---
title: "Преузимања"
description: "Преузмите LibreCelik и LibreMiddleware пакете"
layout: "simple"
---

Сва издања су објављена на GitHub-у. Изаберите пакет за вашу платформу.

---

## LibreCelik

Десктоп апликација за читање и приказивање српских смарт картица — лична карта, саобраћајна дозвола, здравствена картица и ПКС картица.

| Платформа | Пакет |
|-----------|-------|
| Linux (x86_64) | `.AppImage` |
| macOS (Apple Silicon) | `.dmg` |

[LibreCelik издања на GitHub-у](https://github.com/LibreSCRS/LibreCelik/releases)

---

## LibreMiddleware — PKCS#11 модул

> **Напомена:** Када OpenSC укључи уграђену подршку за српске картице, моћи ћете да користите OpenSC-ов PKCS#11 модул уместо овог. Овај модул остаје доступан као алтернатива.

Користите смарт картицу за аутентификацију у прегледачу (нпр. пријава на еУправу) и дигиталне потписе у Firefox-у, Chrome-у, Thunderbird-у или OpenSSH-у.

| Платформа | Пакет |
|-----------|-------|
| Linux (x86_64) | `.tar.gz` |
| macOS (Apple Silicon) | `.zip` |

[LibreMiddleware издања на GitHub-у](https://github.com/LibreSCRS/LibreMiddleware/releases)

Погледајте [PKCS#11 упутство](/sr/docs/pkcs11/) за подешавање Firefox-а, Chrome-а и Thunderbird-а.

---

## LibreMiddleware — OpenSC драјвер

> **Застарело.** Уграђени драјвер за српске картице је предложен за OpenSC и чека укључивање у следеће издање. Када буде доступан, инсталирајте OpenSC директно — без додатног драјвера.

OpenSC екстерни драјвер за CLI алате (`pkcs15-tool`, `pkcs11-tool`, `pkcs15-crypt`) и PKCS#11 апликације.

| Платформа | Пакет |
|-----------|-------|
| Linux (x86_64, OpenSC 0.26.x) | `.tar.gz` |
| macOS (Apple Silicon, OpenSC 0.26.x) | `.zip` |

[LibreMiddleware издања на GitHub-у](https://github.com/LibreSCRS/LibreMiddleware/releases)

Погледајте [OpenSC драјвер упутство](/sr/docs/opensc-driver/) за инсталацију и конфигурацију.
