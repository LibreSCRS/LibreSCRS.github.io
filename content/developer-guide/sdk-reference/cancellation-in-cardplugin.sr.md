---
title: "Otkazivanje u CardPlugin-u"
weight: 32
---

`LibreSCRS::Plugin::CardPlugin::readCard` i `sign` primaju `LibreSCRS::CancelToken`. Implementacije plugina (`doReadCard`, `doSign`) **ne** dobijaju parametar otkazivanja.

## Razlog

PC/SC `SCardTransmit` ne može biti prekinut na Linux-u/pcsclite — `SCardCancel` otkazuje samo `SCardGetStatusChange`. Svaka APDU razmena je stoga atomska sa stanovišta otkazivanja. Bazna klasa `CardPlugin` posmatra `CancelToken` jednom, pre dispatch-a virtuelnoj implementaciji:

```cpp
ReadResult CardPlugin::readCard(SmartCard::CardSession& session,
                                GroupCallback           onGroup,
                                CancelToken             token) const
{
    if (token.isCancelled()) return cancelledResult();
    return doReadCard(session, std::move(onGroup));
}
```

To je jedina iskrena tačka otkazivanja, i obrađuje se u baznoj klasi tako da autori plugina ne moraju o tome da brinu.

## Kada otkazivanje tokom operacije ima smisla

Plugini koji ciljaju ne-PC/SC transporte (mock plugini za testove, budući USB-CCID/NFC sa nativnim otkazivanjem, mrežno povezani čitači kartica) MOGU dodati additivnu varijantu u 4.x:

```cpp
// hipotetička 4.x additivna varijanta — NIJE deo 4.0
virtual ReadResult doReadCard(SmartCard::CardSession& session,
                              GroupCallback           onGroup,
                              CancelToken             token) const {
    return doReadCard(session, std::move(onGroup));  // podrazumevano: ignoriše token
}
```

Dodavanje ove varijante ne narušava ABI postojećim pluginima.
