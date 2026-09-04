---
layout: "simple"
title: "OpenSC Integration"
description: "Native OpenSC support for Serbian cards, and what replaced the withdrawn external driver"
aliases:
  - /user-guide/cardedge-opensc-driver/
---

## Native OpenSC support

The [srbeid driver](https://github.com/OpenSC/OpenSC/pull/3595) for Serbian
smart cards is merged into OpenSC mainline. Serbian eID (Gemalto 2014+, IF2020
Foreigner) and PKS Chamber of Commerce cards are supported out of the box in an
OpenSC release that carries it, and in any build from OpenSC's main branch — no
external driver and no configuration.

**Supported cards**

- Serbian eID Gemalto (2014+) — matched by ATR `3B:FF:94`
- Serbian eID IF2020 Foreigner — matched by AID
- PKS Chamber of Commerce card — matched by AID

**Not supported**: Apollo 2008 eID — the card carries no CardEdge applet.

## The external driver is withdrawn

Up to 4.x, LibreSCRS shipped a separate OpenSC card-driver module for OpenSC
releases that predated the merge, together with a `cmake` flag to build it and
an `opensc.conf` fragment to register it. The driver, the flag and the build
target are all gone in 5.0: what they existed to backport is upstream.

If you still carry an `opensc.conf` entry for it, remove it. A `card_driver`
or `emulate` block naming a module that is no longer installed makes OpenSC log
a load failure on every card operation:

```
app default {
    card_drivers = librescrs, internal;      # <- remove
    card_driver librescrs { ... }            # <- remove the whole block
    framework pkcs15 {
        emulate librescrs { ... }            # <- and this one
    }
}
```

Nothing replaces those blocks; the stock configuration is what you want.

## LibreSCRS does not go through OpenSC's PKCS#11

Worth separating, because the two are easy to conflate. OpenSC is the PKI
engine LibreSCRS uses to talk to these cards, but a PKCS#11 application does
**not** reach a LibreSCRS card through `opensc-pkcs11.so`. From 5.0 it goes
through the card agent's own module, which routes operations to the agent that
owns the card — see the [PKCS#11 guide](/user-guide/pkcs11/).

Both can be installed at once. They are separate providers over separate paths,
and a browser that lists two devices for one card is showing you exactly that.

## Verification

Card detection:

```bash
opensc-tool --list-readers
# Gemalto USB SmartCard Reader  Slot 0  ATR: 3B FF ...
```

PKCS#15 objects:

```bash
pkcs15-tool --list-certificates
pkcs15-tool --list-keys
pkcs15-tool --list-pins          # shows tries remaining
```

`opensc-tool` caches the ATR it saw for a reader, so an inserted card that
changed since the last run can be reported from the cache rather than from the
card. If a result surprises you, re-run after a fresh insert.

For signing and verifying files, see the
[Digital Signing]({{< ref "user-guide/digital-signing" >}}) page.

## Debugging

Enable OpenSC debug logging in `opensc.conf`:

```
app default {
    debug = 3;
    debug_file = /tmp/opensc-debug.txt;
    ...
}
```

Inspect `/tmp/opensc-debug.txt` after running any `pkcs15-tool` or
`pkcs11-tool` command.
