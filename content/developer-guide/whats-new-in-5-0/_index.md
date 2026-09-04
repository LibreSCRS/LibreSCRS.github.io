---
layout: "simple"
title: "What's new in LibreSCRS 5.0"
description: "The card agent becomes the product, country-signing anchors verify passport chips, the shared objects move to .so.5, and the plugin ABI reaches version 9"
weight: 1
aliases:
  - /developer-guide/whats-new-in-4-3/
---

LibreSCRS 5.0.0 is a major release across seven repositories, tagged together.
Three things make it a major rather than a feature release: a **card agent**
now owns the card and every application is a client of it, the shared objects
move to `.so.5`, and a release that removes the last deprecation in the tree
also removes the transitional code around it.

If you are reading this to find out what breaks, skip to
[Breaking changes](#breaking-changes).

## One broker owns the card

Until 4.x every application that wanted a card opened it itself. A GUI, a
browser through PKCS#11 and a signing tool each held their own session, each
collected their own PIN, and whichever got to the reader first won.

From 5.0 a per-user **card agent** is the single owner of the card and its
secrets. It is headless and Qt-free; on Linux it is a D-Bus session service
that publishes the live reader and card tree through the standard
`ObjectManager` interface, so a client sees readers appear and cards come and
go in real time. PINs, CANs and MRZs are collected by a separate prompter
process, kept isolated from the agent, and every client request is gated
through **polkit**.

The pieces are now separate published libraries rather than one repository's
internals:

| Target | Links | For |
| --- | --- | --- |
| `LibreAgent::Core` | LibreMiddleware, OpenSSL | platform hosts |
| `LibreAgent::Wire` | nothing first-party | anything speaking the agent wire |
| `LibreAgent::ClientQt` | Qt6 | Qt and KDE desktop clients |

The wire layer deliberately links nothing of ours: it is Qt-free, middleware-
free and OpenSSL-free, so the same protocol serves a D-Bus transport and a
plain socket transport without dragging a desktop stack behind it. See
[the agent's architecture](/developer-guide/agent-architecture/),
[its operation catalogue](/developer-guide/agent-operations/) and
[the wire protocol](/developer-guide/agent-wire-protocol/); to build a client
of your own, see
[building a Qt client](/developer-guide/agent-client-qt/).

**One card, one PKCS#11 provider.** The middleware's in-tree PKCS#11 module is
no longer registered with p11-kit and no longer published as a release
artefact. Standard PKCS#11 applications reach the card through the agent's
client module instead, which forwards operations rather than touching the card
itself: it performs no cryptography of its own, offers a raw RSA sign and
decrypt surface with per-operation re-authorization, and supports cards that
compute the digest on-card. The PIN is collected by the prompter behind an
authorization prompt and a lease, and never enters the browser's address
space.

Shipping both modules meant offering two devices for the same card with two
different security models, and letting the choice fall to whichever dialog a
user happened to type into. The direct module is still built and installed for
a headless host that runs no agent —
`-DLIBREMIDDLEWARE_INSTALL_P11KIT_MODULE=ON` restores its declaration — but it
is no longer what a desktop install gets. The
[PKCS#11 guide](/user-guide/pkcs11/) covers browser setup and how to remove a
hand-made registration of the old module, which no package manager will clean
up for you.

## Country-signing anchors for ePassports

An electronic passport's chip data is now checked against a locally imported
**CSCA master list**, not merely parsed. The import accepts what the ICAO
Public Key Directory actually publishes — a directory export carrying dozens of
master lists, each signed by a different country — rather than one list at a
time.

Every list in a collection is verified on its own, against its own signer, and
the anchors installed are the union of those that survived. The rules that
governed a single list now apply per publisher: each publisher is remembered
separately, a lawful key rotation is followed on its own evidence, and a list
is refused as a replay when it is not strictly newer than the one already
accepted *from that publisher* — so a country that publishes rarely no longer
looks like a rollback. A signer with no record behind it must additionally beat
the newest publisher the import displaces, which is what stops a rotation from
becoming a way to carry an old list in.

An import takes what verifies rather than refusing everything: two stale lists
among twenty-eight no longer deny you the other twenty-six, and nothing is
installed that was not verified. What did not make it is reported alongside
what did. An import that admits no list at all is still a refusal, and still
leaves the stored anchors untouched.

The trust surfaces this rides on are documented in
[Trust, certificates and secure values](/developer-guide/trust-and-certificates/).

## On-card RSA decryption

OpenSC-backed cards — for example the Serbian PKS / Gemalto eID — can perform
on-card RSA decryption. The middleware exposes this through the public plugin
entry point `LibreSCRS::Plugin::CardPlugin::decipher`, which takes a
`LibreSCRS::Plugin::DecipherMechanism` (currently
`DecipherMechanism::RSA_PKCS1_V15`, the only padding those cards support). The
card performs the RSA operation with its on-card private key; the backend
strips the PKCS#1 v1.5 padding and returns the recovered plaintext in a
`DecipherResult`. That plaintext is sensitive, and the caller owns cleansing
the returned bytes.

The capability is per card. The OpenSC-family plugin implements decipher
against the card's RSA key; the generic PKCS#15 plugin reports the operation as
not implemented for cards that expose no decrypt primitive.

## Hash-on-card SHA-256 RSA signing

Hash-on-card IAS-ECC cards — the Serbian NAM eID — can produce RSA PKCS#1 v1.5
signatures over SHA-256 where the **card computes the digest itself**. These
cards reject a caller-supplied DigestInfo, so the middleware sends the raw
message and lets the card hash it internally. The mechanism is
`LibreSCRS::Plugin::SignMechanism::RSA_SHA256`; across the PKCS#11 surface it
maps to the standard `CKM_SHA256_RSA_PKCS`, so a client signs exactly as it
would against any combined hash-and-sign token. The result is a standard
PKCS#1 v1.5 signature, verified end to end against the card's public key.

`RSA_SHA256` is offered only by cards that really hash on-card. For an ordinary
PKCS#15 card that expects a caller-built DigestInfo, the plugin reports the
mechanism as not implemented, so callers fall back to the existing `RSA_PKCS`
DigestInfo path.

## Plugin ABI version 9

The card-plugin ABI is now version 9
(`LibreSCRS::Plugin::kCardPluginAbiVersion == 9`). Plugins must be rebuilt
against the 5.0 headers; the loader rejects any plugin whose
`card_plugin_abi_version()` does not equal `kCardPluginAbiVersion`. Declare the
version with the convenience macro, whose compile-time check fails if the
headers later move to a newer ABI:

```cpp
LIBRESCRS_DECLARE_CARD_PLUGIN(MyPlugin, 9);
```

**This page previously claimed the decipher virtual was appended as the final
vtable slot, so the change was additive. That was not true, and it is worth
saying plainly rather than quietly deleting.** Read off the current vtable,
`doDecipher` sits at slot 23 with `activateTransportPin` and
`activateSigningKey` behind it at 24 and 25, and `readCounters` sits at slot
**12** — in the middle, ahead of `doSign` — because it was inserted rather than
appended. Every slot behind it moved. A plugin author who believed the old
sentence would have concluded that a rebuild was optional; it never was.

That is also why ABI 9 is described as covering the shape changes
*retroactively*: for a period the same integer, 8, named two mutually
incompatible layouts. Raising it to 9 does not rescue an artefact built in
that window — nothing can — which is why the
[API policy](/developer-guide/sdk-reference/api-policy/) records the correction
rather than only the new row. For the published 4.2 → 5.0 step the collision is
harmless by accident: 6 ≠ 9 rejects everything from the previous release, and
no artefact carrying the intermediate shape was ever published.

The signing and decrypt mechanisms (`SignMechanism::RSA_SHA256`,
`DecipherMechanism::RSA_PKCS1_V15`) are appended enumerators, so a plugin built
against an older header simply never receives those values.

## Breaking changes

**`CardPlugin::getPINTriesLeft` is removed.** It was never marked
`[[deprecated]]` in a released version, so it goes straight from present to
gone at the major boundary. Callers migrate to `readCounters`:

```cpp
// Before (4.x):
std::optional<int> tries = plugin.getPINTriesLeft(session);

// After (5.0):
const auto counters = plugin.readCounters(session);   // default user PIN
if (counters.retriesLeft) { /* ... */ }
```

`Plugin::CredentialCounters` carries `retriesLeft`, `retriesMax`, `usesLeft`,
`usesMax` and `unblocksLeft`, each absent unless the card exposed it — so a
plugin that does not implement the call reports "nothing known" rather than a
wrong zero. Details are in
[the plugin ABI section of the API policy](/developer-guide/sdk-reference/api-policy/).

**The installed CMake package exports one target namespace, `LibreSCRS::`.**
Up to 4.x the export carried `LibreMiddleware::` and the config file mirrored
every target under `LibreSCRS::`, while the mirror's own comment called
`LibreSCRS::` the preferred spelling for new code. The preferred spelling is
now the export, and the mirror is gone. `LibreMiddleware` still names the
package you ask `find_package` for; it no longer names the targets inside it.
Consumers linking `LibreMiddleware::Auth` and friends move to
`LibreSCRS::Auth`.

**The shared objects move to `.so.5`.** The SONAME integer is independent of
the release version and is bumped whenever the layout gate reports a
non-additive change; in this release the two happen to coincide at 5. Anything
that links `libLibreSCRS_*.so.4` or
`liblibrescrs-agentclient-qt.so.4` needs a rebuild and a repackage.

**LibreLinux and LibreKDE leave their own 0.x numbering** and tag `5.0.0` with
everyone else, so that a version number means the same thing across the whole
product.

**LibreKDE no longer configures with a bare `cmake -B build`.** It needs
LibreAgent 5.0 or newer, installed with its `ClientQt` component, either where
CMake already looks or named through `CMAKE_PREFIX_PATH`.

**The PKCS#11 module is no longer registered with p11-kit.** See
[one broker owns the card](#one-broker-owns-the-card) above; a hand-made
registration from a published archive is not removed by any package manager
and has to go by hand.

## Migration from 4.2

- **Display-only hosts** that consume `LibreSCRS::Plugin`,
  `LibreSCRS::Signing` and `LibreSCRS::Trust`: change the target namespace to
  `LibreSCRS::`, rebuild against `.so.5`. No source changes otherwise.
- **Signing consumers**: as above. `RSA_SHA256` and decipher are additive;
  adopt `SignMechanism::RSA_SHA256` to sign through a hash-on-card card, or
  `CardPlugin::decipher` to recover RSA-decrypted plaintext.
- **Plugin authors**: rebuild against the 5.0 headers (ABI 9), and replace any
  `getPINTriesLeft` override or call with `readCounters`. A plugin that needs
  on-card decrypt overrides `doDecipher`; one that does not leaves the base
  default, which reports `NotImplemented`.
- **PKCS#11 consumers**: install the agent, and remove any hand-made
  registration of the old direct module. See the
  [PKCS#11 guide](/user-guide/pkcs11/).

## Developer notes

A plugin implementation surfaces decipher by overriding the protected
`doDecipher` virtual, mirroring `doSign`; callers invoke the public NVI
wrapper, which observes the cancellation token before dispatch:

```cpp
// On-card RSA decrypt with a live session and an on-card key reference.
LibreSCRS::Plugin::DecipherResult d =
    plugin.decipher(session, keyReference, ciphertext,
                    LibreSCRS::Plugin::DecipherMechanism::RSA_PKCS1_V15);
if (d.ok()) {
    // d.plaintext holds the recovered bytes — cleanse after use.
}

// Hash-on-card SHA-256 RSA signature over the RAW message.
LibreSCRS::Plugin::SignResult s =
    plugin.sign(session, keyReference, message,
                LibreSCRS::Plugin::SignMechanism::RSA_SHA256);
```

Both wrappers return their structured outcome (`DecipherResultOutcome` /
`SignResultOutcome`): `NotImplemented` when the plugin does not support the
mechanism, `Cancelled` for the pre-dispatch short-circuit, and `PluginError`
for a card-side or plugin-internal failure.

## References

- [Architecture overview](/developer-guide/architecture/)
- [API policy](/developer-guide/sdk-reference/api-policy/)
- [Signing architecture](/developer-guide/signing-architecture/)
- [Install the card agent](/user-guide/install-agent/)
- [What's new in 4.2](/developer-guide/whats-new-in-4-2/)
