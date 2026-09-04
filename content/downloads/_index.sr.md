---
title: "Преузимања"
layout: "simple"
description: "Како инсталирати LibreSCRS 5.0.0 — прво картични агент, па клијент који вам треба"
---

LibreSCRS 5.0.0 је један производ кроз седам спремишта. Две ствари вреди знати
пре него што било шта одавде изаберете:

1. **Картични агент иде први.** Од 5.0 картицу држи агент по кориснику, а свака
   апликација — LibreCelik, LibreKDE, Firefox, Thunderbird, `ssh` — његов је
   клијент. Инсталирате ли GUI без агента, он ће се покренути, неће наћи
   картицу, и неће умети да вам каже зашто.
2. **Само LibreCelik у овом издању има унапред изграђен бинарни фајл.** Агент и
   Plasma клијент излазе као изворни код са рецептима за паковање у својим
   спремиштима; потписаног APT или DNF спремишта нема, а нема ни AUR пакета.
   Тамо где је тако, ова страница то каже, уместо да понуди дугме које не води
   никуда.

---

## LibreSCRS картични агент

Потребан пре него што LibreCelik, LibreKDE или било која PKCS#11 апликација
могу да виде вашу картицу. Њега инсталирајте прво.

### Arch / Manjaro

Свако спремиште носи Arch рецепт под `packaging/arch/`. Градите их редом по
зависностима — по један `makepkg` по спремишту, а једно покретање у спремишту
агента производи три пакета:

```
librescrs-middleware                                     (LibreMiddleware)
librescrs-agent-common, -core, -client-qt                (LibreAgent)
librescrs-agent, librescrs-pinentry-kde                  (LibreLinux)
```

`librescrs-agent` је демон; `librescrs-pinentry-kde` је засебан упитник који
прикупља PIN-ове, CAN-ове и MRZ-ове — без њега ниједна PIN операција није
могућа. `librescrs-agent-common` је `arch=any`, па се његово име фајла завршава
на `-any.pkg.tar.zst` док се остала завршавају на `-x86_64.pkg.tar.zst`;
команда која архитектуру испише дословно промашиће га.

```
sudo pacman -U librescrs-middleware-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-agent-common-5.0.0-1-any.pkg.tar.zst \
               librescrs-agent-core-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-agent-client-qt-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-agent-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-pinentry-kde-5.0.0-1-x86_64.pkg.tar.zst
```

{{< button href="https://github.com/LibreSCRS/LibreLinux/releases/tag/5.0.0" target="_blank" >}}LibreLinux 5.0.0 извор{{< /button >}}

### Debian, Ubuntu, Fedora

У овом издању нема `.deb` ни `.rpm` пакета. Градите из изворног кода — види
[Изградњу из изворног кода](/sr/developer-guide/building-from-source/) за пун
редослед, који је исти редослед зависности као горе.

### macOS

macOS домаћин агента је написан и покренут на стварном хардверу, али није део
овог издања: нема потписане и нотаризоване изградње, а macOS PKCS#11 посредник
није у 5.0.0. Корисник macOS-а коме данас треба приступ картици гради домаћина
из изворног кода.

### После инсталације

Агент се не покреће док прва картична радња то не затражи, и подразумевано није
укључен на сваком пријављивању. Види
[Инсталацију картичног агента](/sr/user-guide/install-agent/) за потврду да
ради и за то како се то мења.

---

## LibreCelik

GUI читач смарт картица за Linux и macOS. Чита пасоше, е-пасоше, личне карте,
саобраћајне и друге PKI картице преко додатака.

**Тражи LibreSCRS картични агент — види изнад.** LibreCelik не повезује
сопствени PC/SC слој; сав приступ картици иде кроз агента.

{{< button href="https://github.com/LibreSCRS/LibreCelik/releases/tag/5.0.0" target="_blank" >}}Преузми AppImage (Linux){{< /button >}}

{{< button href="https://github.com/LibreSCRS/LibreCelik/releases/tag/5.0.0" target="_blank" >}}Преузми DMG (macOS){{< /button >}}

---

## LibreKDE

Интеграција са Plasma 6: плазмоид за смарт картице, прозор за управљање
акредитивима, Purpose додатак „Потпиши“ и `card:/` KIO радник.

Излази као изворни код са Arch рецептом у `packaging/arch/` (име пакета
`librekde`). Зависи од `librescrs-agent`-а и `librescrs-agent-client-qt`-а, па
прво инсталирајте агента.

{{< button href="https://github.com/LibreSCRS/LibreKDE/releases/tag/5.0.0" target="_blank" >}}LibreKDE 5.0.0 извор{{< /button >}}

---

## PKCS#11 модул

Инсталира се аутоматски уз картични агент изнад — засебног преузимања нема.
Firefox, Chrome, Thunderbird и `ssh` откривају га кроз p11-kit чим је пакет
агента инсталиран.

Директан модул самог middleware-а више се не региструје подразумевано. Ако сте
га ручно инсталирали из 4.x архива издања, ту регистрацију не уклања ниједан
менаџер пакета; [водич за PKCS#11](/sr/user-guide/pkcs11/) носи једну команду
која је брише, уз подешавање прегледача и случај без интерфејса који и даље
користи директан модул.

---

## Провера онога што сте преузели

Тагови издања потписани су OpenPGP-ом, а артефакти издања cosign-ом. Кључ,
отисак и `cosign verify-blob` команда са закљученим идентитетом стоје на
[провери издања](/security/).
