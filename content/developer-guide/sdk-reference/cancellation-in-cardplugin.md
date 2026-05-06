---
title: "Cancellation in CardPlugin"
weight: 32
---

`LibreSCRS::Plugin::CardPlugin::readCard` and `sign` accept a `LibreSCRS::CancelToken`. Plugin implementations (`doReadCard`, `doSign`) **do not** receive a cancellation parameter.

## Why

PC/SC `SCardTransmit` cannot be aborted on Linux/pcsclite — `SCardCancel` only cancels `SCardGetStatusChange`. Each APDU exchange is therefore atomic from a cancellation standpoint. The base `CardPlugin` class observes `CancelToken` once, before dispatching to the virtual implementation:

```cpp
ReadResult CardPlugin::readCard(SmartCard::CardSession& session,
                                GroupCallback           onGroup,
                                CancelToken             token) const
{
    if (token.isCancelled()) return cancelledResult();
    return doReadCard(session, std::move(onGroup));
}
```

That is the only honest cancellation point, and it is handled in the base class so plugin authors never have to think about it.

## When mid-operation cancellation matters

Plugins targeting non-PC/SC transports (mock plugins for tests, future USB-CCID/NFC backends with native cancellation, network-attached card readers) MAY add an additive overload in 4.x:

```cpp
// hypothetical 4.x additive overload — NOT in 4.0
virtual ReadResult doReadCard(SmartCard::CardSession& session,
                              GroupCallback           onGroup,
                              CancelToken             token) const {
    return doReadCard(session, std::move(onGroup));  // default: ignores token
}
```

Adding this overload does not break ABI for existing plugins.
