---
layout: "simple"
title: "Install the card agent"
description: "Why LibreSCRS uses a card agent, how to check that it is running, and what the authorization prompt is asking"
---

From 5.0 the **LibreSCRS card agent** is what actually talks to your card.
LibreCelik, LibreKDE, Firefox, Thunderbird and `ssh` are all clients of it. If
the agent is not installed, those applications start normally and then find no
card — so this is the first thing to install, before any of them.

Package names and the install order are on the
[downloads page](/downloads/).

## Why an agent at all

A smart card is a single-session device. Before 5.0, every application that
wanted your card opened it itself: a GUI, a browser through PKCS#11 and a
signing tool each held their own session, each asked for your PIN separately,
and whichever reached the reader first won. The other one got an opaque
failure.

One broker owns the card and its secrets, and everything else is a thin client
of it. That is one answer to three separate problems: no more races for the
reader, one place that knows whether your PIN has already been verified, and —
because the agent collects credentials through a separate prompter process —
your PIN never enters the address space of the browser that asked for the
signature.

The same shape is described from the developer's side under
[Architecture](/developer-guide/architecture/).

## Checking that it runs

The agent is a per-user systemd service on the session bus:

```
systemctl --user status librescrs-agent.service
```

It is **D-Bus activated on demand**: it does not run until the first card
operation asks for it, so `inactive (dead)` right after installing is normal
rather than a fault. Insert a card, open LibreCelik, and check again.

To confirm it has claimed the bus name:

```
busctl --user list | grep org.librescrs.Agent
```

## Starting it at every login

The agent is deliberately **not** enabled at login by default: on a machine
where you use a card twice a month, a service that starts with every session is
not what you want. If you use one daily, turn it on:

```
systemctl --user enable --now librescrs-agent.service
```

To go back to on-demand:

```
systemctl --user disable --now librescrs-agent.service
```

## The authorization prompt

Client requests are gated through **polkit**, and you will see a system
authorization dialog the first time an application asks the agent to do
something in a given class of action. The classes are separate on purpose, and
they do not all ask the same thing:

| Action | Default |
|---|---|
| Sign with a card | allowed for the active session — the PIN is the consent gate |
| Let a PKCS#11 application use your card | allowed for the active session — same reason |
| Manage card credentials (change a PIN, unblock) | allowed for the active session |
| Change signing settings | allowed for the active session |
| Change trust and timestamping settings | **asks you to authenticate**, in every session |

The last row is the one to read twice. Trust settings decide which
certificates a signature is checked against, so changing them is a
trust-elevation step and is treated as one; signing itself is guarded by the
PIN you are about to type, so a second dialog in front of it would train you to
click through both.

The prompt fires **once per class of action per session**, not once per
operation. If you see one before each signature, something is restarting the
agent between them.

## Prompts for PIN, CAN and MRZ

PINs, CANs and MRZs are never collected by the application you are using. A
separate prompter process (`librescrs-pinentry-kde`) asks for them and hands
them to the agent over a private session-bus interface. It is a distinct
package, and without it no PIN operation can happen at all — if you installed
the agent and PIN entry does nothing, that package is what is missing.

## Browsers, SSH and other PKCS#11 clients

The agent installs the PKCS#11 module those applications discover through
p11-kit. Browser setup, and the removal of a hand-made registration of the
older direct module, are on the [PKCS#11 guide](/user-guide/pkcs11/).
