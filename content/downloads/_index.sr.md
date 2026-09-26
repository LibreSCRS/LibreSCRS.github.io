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
2. **Linux пакети излазе за пет дистрибуција:** `.deb` за Debian 13 и Ubuntu
   26.04 LTS, `.rpm` за Fedora 43, Fedora 44 и openSUSE Tumbleweed — за
   међуслој, агента, LibreCelik и LibreKDE (LibreKDE за све осим openSUSE
   Tumbleweed-а). LibreCelik даје и AppImage и DMG; Arch и Manjaro граде из
   рецепата у сваком спремишту. Нема потписаног APT, DNF, zypper ни AUR
   спремишта, и **ништа инсталирано из овог издања не ажурира само себе** —
   тамо где је тако, ова страница то каже, уместо да понуди дугме које не води
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

Сва четири Arch рецепта са ове странице — међуслој, библиотеке агента, агент и
Plasma клијент — за ово издање изграђена су у чистом chroot-у, тим редом.

```
sudo pacman -U librescrs-middleware-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-agent-common-5.0.0-1-any.pkg.tar.zst \
               librescrs-agent-core-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-agent-client-qt-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-agent-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-pinentry-kde-5.0.0-1-x86_64.pkg.tar.zst
```

Изворне архиве које ти рецепти преузимају, свака са својим потписом, наведене
су међу фајловима сваког спремишта испод.

{{< button href="https://github.com/LibreSCRS/LibreLinux/releases/tag/5.0.0" target="_blank" >}}LibreLinux 5.0.0 извор{{< /button >}}

### Debian, Ubuntu, Fedora, openSUSE

Пакети излазе за Debian 13, Ubuntu 26.04 LTS, Fedora 43, Fedora 44 и openSUSE
Tumbleweed. Свако име носи дистрибуцију за коју је изграђено, па изаберите она
која одговарају вашој — пакет изграђен наспрам библиотека друге дистрибуције ће
се инсталирати, а затим неће моћи да се учита.

Картични агент чине пакети из три спремишта — библиотеке и додаци за картице
међуслоја, клијентска библиотека агента, и агент са својим упитником за PIN:

| | Debian 13, Ubuntu 26.04 | Fedora 43, 44, openSUSE Tumbleweed |
|---|---|---|
| LibreMiddleware | `liblibrescrs5`, `librescrs-card-plugins` | `librescrs-middleware`, `librescrs-card-plugins` |
| LibreAgent | `liblibrescrs-agentclient-qt5` | `librescrs-agent-client-qt` |
| LibreLinux | `librescrs-agent`, `librescrs-pinentry-kde` | `librescrs-agent`, `librescrs-pinentry-kde` |

Преузмите их у један иначе празан директоријум и инсталирајте у једној
трансакцији, да их менаџер пакета сам поређа:

```
sudo apt install ./*.deb                                  # Debian, Ubuntu
sudo dnf install ./*.rpm                                  # Fedora
sudo zypper install --allow-unsigned-rpm ./*.rpm          # openSUSE Tumbleweed
```

Пакети нису потписани кључем дистрибуције — нема спремишта које би га носило —
па `zypper` тражи `--allow-unsigned-rpm`; порекло доказује потпис издања
описан под [Провером онога што сте преузели](#провера-онога-што-сте-преузели).
Пакети `-dev` и `-devel` служе за изградњу наспрам библиотека; радној површини
ниједан од њих не треба.

{{< release-assets repo="LibreMiddleware" >}}

{{< release-assets repo="LibreAgent" >}}

{{< release-assets repo="LibreLinux" >}}

**`librescrs-pkcs11-direct` је у конфликту са картичним агентом.** Он
региструје сопствени PKCS#11 модул међуслоја за машину која агента свесно нема,
и од та два може бити инсталиран тачно један. Шта прелаз између њих тражи
зависи од менаџера пакета, у оба смера:

| | обична инсталација другог пакета | команда која прелази |
|---|---|---|
| `apt` | прелази: уклања инсталирани | `sudo apt install ./<package>.deb` |
| `dnf` | одбија, и ништа не мења | `sudo dnf install --allowerasing ./<package>.rpm` |
| `zypper` | одбија, и ништа не мења | `sudo zypper install --allow-unsigned-rpm --force-resolution ./<package>.rpm` — или га покрените интерактивно и изаберите решење које уклања инсталирани |

**Нису у овом издању:** Ubuntu 24.04 LTS и openSUSE Leap 16.0. Агенту треба
sdbus-c++ 2, а Ubuntu 24.04 испоручује 1.4 и Leap 16.0 испоручује 1.6; Ubuntu
24.04 нема ни KDE Frameworks 6, на којем је изграђен упитник за PIN. Без агента
ниједан клијент нема приступ картици, па ниједна од те две дистрибуције не
добија пакете. Ни arm64 се не гради.

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
сопствени PC/SC слој; сав приступ картици иде кроз агента. **AppImage не садржи
агента** и не може: агент је systemd сервис по кориснику на сесијској
магистрали иза polkit-а, а њих може да инсталира само системски пакет. Прво
инсталирајте пакете агента изнад, у ком год облику покрећете LibreCelik.

На дистрибуцијама изнад LibreCelik је и пакет, `librecelik`, који се
инсталира исто као пакети агента.

{{< button href="https://github.com/LibreSCRS/LibreCelik/releases/tag/5.0.0" target="_blank" >}}Преузми AppImage (Linux){{< /button >}}

{{< button href="https://github.com/LibreSCRS/LibreCelik/releases/tag/5.0.0" target="_blank" >}}Преузми DMG (macOS){{< /button >}}

{{< release-assets repo="LibreCelik" >}}

---

## LibreKDE

Интеграција са Plasma 6: плазмоид за смарт картице, прозор за управљање
акредитивима, Purpose додатак „Потпиши“ и `card:/` KIO радник.

Излази као пет пакета — `librekde-common`, `librekde-plasmoid`,
`librekde-kio`, `librekde-purpose` и `librekde-credentials` — за Debian 13,
Ubuntu 26.04 LTS, Fedora 43 и Fedora 44, и као Arch рецепт у `packaging/arch/`
(име пакета `librekde`). Изградње за openSUSE Tumbleweed нема: дистрибуција са
сталним ажурирањем помера Plasma библиотеке испод унапред изграђеног пакета
брже него што издање може да прати. Зависи од агента и његове клијентске
библиотеке, па прво инсталирајте агента.

{{< release-assets repo="LibreKDE" >}}

{{< button href="https://github.com/LibreSCRS/LibreKDE/releases/tag/5.0.0" target="_blank" >}}LibreKDE 5.0.0 извор{{< /button >}}

---

## PKCS#11 модул

Инсталира се аутоматски уз картични агент изнад — засебног преузимања нема.
Firefox, Chrome, Thunderbird и `ssh` откривају га кроз p11-kit чим је пакет
агента инсталиран.

Ако је инсталиран и OpenSC пакет ваше дистрибуције, `p11-kit list-modules`
приказује његов модул поред нашег — заједно са p11-kit-овим сопственим модулом
поверења, три уноса су уобичајен број. То су засебни добављачи: OpenSC који
носи драјвер за српску личну карту нуди исту картицу по други пут, са PIN-ом
који се куца у апликацију уместо у упитник агента. Наши пакети намерно нису у
конфликту са OpenSC-ом — то би га уклонило за сваку другу картицу коју
опслужује. [Водич за PKCS#11](/sr/user-guide/pkcs11/) каже како да их
разликујете.

Директан модул самог middleware-а више се не региструје подразумевано. Ако сте
га ручно инсталирали из 4.x архива издања, ту регистрацију не уклања ниједан
менаџер пакета; [водич за PKCS#11](/sr/user-guide/pkcs11/) носи једну команду
која је брише, уз подешавање прегледача и случај без интерфејса који и даље
користи директан модул.

---

## Провера онога што сте преузели

Тагови издања потписани су OpenPGP-ом, а артефакти издања cosign-ом. Кључ,
отисак и `cosign verify-blob` команда са закљученим идентитетом стоје на
[провери издања](/sr/security/).
