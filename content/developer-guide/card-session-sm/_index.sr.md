---
layout: "simple"
title: "API за безбедне канале CardSession-а"
description: "Активирање PACE/BAC/обичних канала из сесије картице, са преучитавањем акредитива и RAII животним веком канала — уведено у LibreSCRS 4.1.0"
weight: 50
---

Ова страница је намењена ауторима додатака и хост апликацијама које координирају безбедну размену порука кроз `LibreSCRS::SmartCard::CardSession`. Уведено у LibreSCRS 4.1.0, овај API премешта активацију канала, кеширање акредитива и животни век PC/SC трансакције на саму сесију, тако да додаци више не инсталирају `TransmitFilter` на голу PC/SC конекцију. За класе протокола испод канала, погледајте [Безбедни канали](../secure-channels/).

## Нове методе `CardSession`-а (4.1)

Методе испод проширују 4.0 површину `CardSession`-а. Све живе на јавној класи `LibreSCRS::SmartCard::CardSession` декларисаној у `LibreMiddleware/include/LibreSCRS/SmartCard/CardSession.h`.

| Метода | Потпис (скраћено) | Намена |
|---|---|---|
| `activateChannelFor` | `(AppletAid, CancelToken) → expected<ActiveChannelHolder, ChannelActivationError>` | Покреће трансакцију, SELECT-ује AID и инсталира `PlainChannel`. |
| `activateChannelWithSm` | `(AppletAid, SmProtocolRequest, CancelToken) → expected<ActiveChannelHolder, ChannelActivationError>` | Исти ток, али канал је `PaceChannel` или `BacChannel` изабран преко варијанте. |
| `setPaceSecret` | `(PaceSecretKind, Secure::String) → void` | Преучитава кеш PACE акредитива за ову сесију. |
| `setBacInput` | `(BacInput) → void` | Преучитава BAC MRZ тројку (број документа, датум рођења, датум истека). |
| `clearCachedPaceCredentials` | `() → void` | Брише сваки PACE слот кеша и BAC улаз. |
| `markDead` | `() noexcept → void` | Означава сесију мртвом после `CardRemoved` догађаја; накнадне активације враћају `CardRemoved`. |
| `isDead` | `() const noexcept → bool` | Предикат упарен са `markDead`-ом. |
| `setCredentialProvider` | `(LibreSCRS::Auth::CredentialProvider) → void` | Инсталира хост повратни позив који се користи при промашају кеша за тражење CAN-а/PIN-а/MRZ-а. Повратни позив се извршава **без** држања мутекса сесије; имплементације СМЕЈУ безбедно да поново уђу у исти `CardSession` (на пример `setPaceSecret` ради депоновања управо прикупљеног CAN-а). |

## Типови параметара и резултата

| Тип | Заглавље | Намена |
|---|---|---|
| `LibreSCRS::SmartCard::SmProtocolRequest` | `LibreSCRS/SmartCard/SmProtocolRequest.h` | `std::variant<BacRequest, PaceRequest>` — бира који SM протокол треба успоставити. |
| `LibreSCRS::SmartCard::BacRequest` | `LibreSCRS/SmartCard/SmProtocolRequest.h` | Празна ознака; BAC је увек кључен на MRZ. |
| `LibreSCRS::SmartCard::PaceRequest` | `LibreSCRS/SmartCard/SmProtocolRequest.h` | Носи `secretKind` (подразумевано `Can`). |
| `LibreSCRS::Auth::PaceSecretKind` | `LibreSCRS/Auth/PaceSecretKind.h` | Енумератор `Can` / `Mrz` / `Pin` / `Puk`; кардиналност изложена као `kPaceSecretKindCount`. |
| `LibreSCRS::SecureChannel::PACEParams` | `LibreSCRS/SecureChannel/PaceParams.h` | OID + paramId + тип лозинке + лозинка — попуњава се из EF.CardAccess и кеша акредитива. |
| `LibreSCRS::SecureChannel::BacInput` | `LibreSCRS/SecureChannel/BacParams.h` | MRZ-Z подскуп (`documentNumber`, `dateOfBirth`, `dateOfExpiry`) у `Secure::String`. |
| `LibreSCRS::SecureChannel::parsePaceOidsFromCardAccess` | `LibreSCRS/SecureChannel/PaceParams.h` | Слободни помоћник који враћа `(OID, paramId)` парове које картица оглашава у EF.CardAccess. Чиста функција, без I/O са картицом. |
| `LibreSCRS::Auth::CredentialProvider` | `LibreSCRS/Auth/CredentialProvider.h` | `SyncProvider<CredentialResult, AuthRequirement>` — повратни позив хост корисничког интерфејса. |
| `LibreSCRS::SecureChannel::ChannelActivationError` | `LibreSCRS/SecureChannel/ChannelErrors.h` | Енум грешака који се враћа у грани неуспеха `std::expected`-а (нпр. `PaceWrongSecret`, `CardRemoved`). |

## `ActiveChannelHolder` — RAII чувар канала

Обе улазне тачке активације враћају `ActiveChannelHolder` (декларисан у `LibreSCRS/SmartCard/ActiveChannelHolder.h`). Док је чувар жив, истовремено поседује три ресурса: мутекс на нивоу сесије који серијализује приступ унутар процеса, PC/SC трансакцију која даје атомичност између процеса, и активни `ISecureChannel` везан за један applet AID. Све APDU-је послате кроз `holder.transmit(cmd, token)` иду кроз тај канал; предикат `holder.isActive()` говори да ли чувар још увек поседује своју трансакцију и мутекс.

Може постојати само један чувар по сесији истовремено. Деструктор прво отпушта трансакцију, затим мутекс; позовите `holder.release()` да бисте оба завршили пре изласка из опсега. `release()` не брише кеширане SM кључеве — наредни `activateChannelFor` на истом AID-у може користити брзу путању. Користите `clearCachedPaceCredentials()` када је потребно експлицитно брисање.

## Пример: активирање PACE-а на аплету уз поновни покушај

```cpp
namespace SC = LibreSCRS::SmartCard;
namespace Sec = LibreSCRS::SecureChannel;
using LibreSCRS::Auth::PaceSecretKind;
using LibreSCRS::Secure::String;

const auto oids = Sec::parsePaceOidsFromCardAccess(cardAccess);
if (oids.empty()) { return; }

session.setPaceSecret(PaceSecretKind::Can, String{"123456"});

auto holder = session.activateChannelWithSm(
    aid, SC::PaceRequest{PaceSecretKind::Can}, token);

if (!holder && holder.error() == Sec::ChannelActivationError::PaceWrongSecret) {
    session.clearCachedPaceCredentials();
    session.setPaceSecret(PaceSecretKind::Can, promptForCan());
    holder = session.activateChannelWithSm(
        aid, SC::PaceRequest{PaceSecretKind::Can}, token);
}
if (!holder) { return; }

const auto rsp = holder->transmit(selectApdu, token);
// деструктор чувара отпушта трансакцију + мутекс на крају опсега
```

Покривеност овог тока живи у `LibreMiddleware/test/LibreSCRS_CardSessionTests.cpp`.

## Образац преучитавања акредитива

Када је хост већ прикупио CAN ван овог тока, преучитавање кеша преко `setPaceSecret`-а пре позива `activateChannelWithSm`-а избегава други UI упит. PKCS#11 модул користи ову путању: парсира хост-испоручени низ "CAN:PIN" из `C_Login`-а, депонује CAN у кеш сесије, затим активира SM канал и прослеђује голи PIN ка `VERIFY`-у. Погледајте [PKCS#11 убацивање сесије](../pkcs11-session-injection/) за повезивање на страни хоста.

## Погледајте такође

- [Безбедни канали](../secure-channels/)
- [PKCS#11 убацивање сесије](../pkcs11-session-injection/)
- [Шта је ново у 4.1](../whats-new-in-4-1/)
