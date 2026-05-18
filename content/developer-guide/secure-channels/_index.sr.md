---
layout: "simple"
title: "Безбедни канали"
description: "Безбедна размена порука између додатака преко LibreSCRS::SecureChannel API-ја (PACE, BAC, plain) — уведено у LibreSCRS 4.1.0"
weight: 40
---

Именски простор `LibreSCRS::SecureChannel` излаже површину за безбедну размену порука између додатака уведену у **LibreSCRS 4.1.0** као део рада на координацији безбедних канала између додатака. Намењен је ауторима додатака и имплементаторима SM протокола који граде директно на `LibreMiddleware`-у. Већина корисника не позива ове типове директно — предају захтев класи `LibreSCRS::SmartCard::CardSession`, која поседује животни век канала и кроз њега рутира APDU-ове додатка; за тај интеграциони слој погледајте [`card-session-sm/`](../card-session-sm/).

## Именски простор `LibreSCRS::SecureChannel`

Сва доле наведена заглавља живе испод `include/LibreSCRS/SecureChannel/` и део су подржане корисничке површине.

| Тип | Заглавље | Намена |
|---|---|---|
| `ISecureChannel` | `SecureChannel/ISecureChannel.h` | Апстрактна површина безбедног канала за један аплет; `transmit`, `close`, `currentApplet`, `state`, `replaceKeys` |
| `PaceChannel` | `SecureChannel/PaceChannel.h` | SM канал изведен из PACE-а (BSI TR-03110); кључеви на нивоу сесије, статичка фабрика `establish()` |
| `BacChannel` | `SecureChannel/BacChannel.h` | SM канал изведен из BAC-а (ICAO Doc 9303 Part 11); 3DES + ISO 9797-1 MAC algorithm 3 |
| `PlainChannel` | `SecureChannel/PlainChannel.h` | Пропуштајући канал за картице без SM-а (RS eID, AET, Здравствена, класични PKCS#15) |
| `SessionKeys` | `SecureChannel/SessionKeys.h` | Кључ за шифровање, MAC кључ и бројач секвенце; нулирани кроз `OPENSSL_cleanse` при уништавању |
| `SmCipher` | `SecureChannel/SessionKeys.h` | Енум фамилије шифре: `Des3` (BAC) или `Aes` (PACE) |
| `ChannelState` | `SecureChannel/ChannelErrors.h` | Енум животног циклуса: `Open`, `Closed`, `Failed` |
| `ChannelActivationError` | `SecureChannel/ChannelErrors.h` | Таксономија грешака при handshake-у |
| `ChannelOperationError` | `SecureChannel/ChannelErrors.h` | Таксономија грешака `transmit` позива након успостављања |
| `PACEParams` | `SecureChannel/PaceParams.h` | Улази PACE handshake-а: OID, тип лозинке, лозинка, paramId |
| `BacInput` | `SecureChannel/BacParams.h` | MRZ-Z подскуп (број документа, датум рођења, датум истека) |
| `parsePaceOidsFromCardAccess` | `SecureChannel/PaceParams.h` | Чист ASN.1 парсер над бајтовима EF.CardAccess-а |

## Животни циклус и кључни материјал

Канал отвара конкретна протоколска класа (`PaceChannel::establish`, `BacChannel::establish` или директна конструкција `PlainChannel`-а), прослеђује увијене APDU-ове кроз `ISecureChannel::transmit` и затвара се при уништавању или експлицитним позивом `close()`. Метод `close()` је идемпотентан и преводи канал у `ChannelState::Closed`.

`SessionKeys` носи кључ за шифровање, MAC кључ и бројач секвенце; његов деструктор нулира сваки непразан бафер кроз `OPENSSL_cleanse` пре него што `std::vector` ослободи алокацију. Пресељење оставља изворне векторе празне, па је пост-пресељење нулирање без ефекта — живи кључни материјал прати власништво у одредишту пресељења, које носи исти уговор о нулирању.

PACE и BAC сесијски кључеви су **на нивоу сесије** (опсег целе картице, не по аплету). PACE handshake тече на MF-у и везује сесијске кључеве за SM тунел картице за читав животни век сесије; пребацивање аплета се обавља увијеним `SELECT`-ом кроз сам канал, након чега `CardSession` позива `PaceChannel::setCurrentApplet` ради бележења новог AID-а. **Немојте** поново покретати PACE при сваком пребацивању аплета — то је протоколска грешка на нивоу OS-а картице и принципијелно је нетачно (мемориjска ставка `feedback_pace_sm_per_session_not_per_applet`, емпиријски потврђено на NAM и GEO contactless-у од 4.0.0).

## Пример: активирање PACE канала преко `CardSession`-а

Исечак испод приказује јавну, идиоматску путању: отворите `CardSession`, унапред упишите CAN и затражите од сесије да активира applet под PACE заштитом. Сесија поседује животни циклус канала и серијализује додатачке APDU-е кроз њега. Извршна end-to-end верзија живи у `LibreMiddleware/test/LibreSCRS_SmChannelTests.cpp`.

```cpp
#include <LibreSCRS/SmartCard/CardSession.h>
#include <LibreSCRS/SmartCard/SmProtocolRequest.h>
#include <LibreSCRS/Auth/PaceSecretKind.h>
#include <LibreSCRS/Secure/String.h>

using namespace LibreSCRS;

auto session = SmartCard::CardSession::open(readerName).value();

// Унапред уписујемо CAN који је корисник унео у PACE кеш по процесу.
session.setPaceSecret(Auth::PaceSecretKind::Can, Secure::String{can});

SmartCard::SmProtocolRequest protocol = SmartCard::PaceRequest{
    .secretKind = Auth::PaceSecretKind::Can,
};

auto active = session.activateChannelWithSm(appletAid, protocol, token);
if (!active) {
    // active.error() је ChannelActivationError; PaceWrongSecret је
    // подобан за поновни покушај током активације, остали су терминални.
    return;
}

// ActiveChannelHolder поседује PC/SC трансакцију и канал.
// Додатачки APDU-и иду кроз њега; уништавање завршава трансакцију.
auto response = active->transmit(commandApdu, token);
```

Аутори додатака у самом стаблу који имају приступ интерном bucket-B заглављу `IConnection` могу директно конструисати канале преко `PaceChannel::establish` итд.; клијенти на страни корисника треба да користе јавни `CardSession::activateChannelWithSm` API.

## Модел грешака

Грешке канала се деле у два енума према фази животног циклуса. Грешке при handshake-у се појављују као `ChannelActivationError` из статичких `establish()` фабрика (и из `CardSession::activateChannelWithSm` у ширем току SM активације); грешке након успостављања се појављују као `ChannelOperationError` из `transmit`-а и његових позивалаца.

### `ChannelActivationError` — грешке при handshake-у

| Енумератор | Значење | Поновљиво? |
|---|---|---|
| `None` | Успех | — |
| `SelectAppletFailed` | Аплет одсутан или SELECT одбијен | Терминално |
| `PaceWrongSecret` | Погрешан CAN / MRZ / PIN / PUK | Поновљиво унутар активације |
| `PacePinBlocked` | Бројач PIN-као-PACE исцрпљен (резервисано за 4.x) | Терминално |
| `PaceProtocolFailure` | Криптографски или протоколски пад током handshake-а | Терминално |
| `PaceUnsupported` | Картица не подржава тражени PACE режим | Терминално |
| `UserCancelled` | Кориснички отказ из провајдера креденцијала | Терминално (поновљиво ако домаћин жели поновни упит) |
| `Cancelled` | `LibreSCRS::CancelToken` активиран | Терминално |
| `CardRemoved` | Уклањање картице током handshake-а | Терминално |
| `ReaderError` | Грешка на PC/SC нивоу | Терминално (углавном) |
| `CredentialsRequired` | Промашај у кешу и нема конфигурисаног провајдера креденцијала; мапира се у `CKR_USER_NOT_LOGGED_IN` на PKCS#11 путањи | Терминално |
| `Internal` | Бубица видљива позиваоцу | Терминално |

### `ChannelOperationError` — грешке `transmit` позива

| Енумератор | Значење |
|---|---|
| `None` | Успех |
| `ChannelFailed` | Канал је прешао у `ChannelState::Failed`; одбаците и реактивирајте |
| `ChannelClosed` | Канал је био затворен пре овог позива; реактивирајте |
| `CardRemoved` | Уклањање картице током операције |
| `Cancelled` | `LibreSCRS::CancelToken` активиран |
| `ReaderError` | Грешка на PC/SC нивоу |
| `Sw6987Or6988` | Картица вратила SW 6987 или 6988 (SM подаци недостају или су нетачни); одбаците и реактивирајте |
| `MacVerificationFailed` | MAC одговора није прошао верификацију (PACE/BAC канали); одбаците и реактивирајте |
| `Internal` | Бубица видљива позиваоцу |

`ChannelFailed`, `MacVerificationFailed` и `Sw6987Or6988` сви значе да се SM тунел десинхронизовао — канал на домаћину се мора одбацити и реактивирати кроз `CardSession`; његово даље коришћење неће се опоравити.

## Погледајте такође

- [SM активација на сесији картице](../card-session-sm/)
- [Убацивање сесије у PKCS#11](../pkcs11-session-injection/)
- [Шта је ново у 4.1](../whats-new-in-4-1/)
