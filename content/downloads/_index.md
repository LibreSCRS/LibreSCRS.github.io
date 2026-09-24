---
title: "Downloads"
layout: "simple"
description: "How to install LibreSCRS 5.0.0 — the card agent first, then the client you want"
---

LibreSCRS 5.0.0 is one product across seven repositories. Two things are worth
knowing before you pick anything from this page:

1. **The card agent comes first.** From 5.0 a per-user agent owns the card and
   every application — LibreCelik, LibreKDE, Firefox, Thunderbird, `ssh` — is a
   client of it. Install a GUI without the agent and it starts, finds no card,
   and cannot tell you why.
2. **Two components ship prebuilt binaries: LibreCelik and the middleware.**
   LibreCelik ships an AppImage and a DMG; LibreMiddleware ships `.deb`
   packages for Debian 13 and Ubuntu 26.04 LTS and `.rpm` packages for Fedora
   43. The agent host and the Plasma client ship as source with packaging
   recipes in their repositories. There is no signed APT, DNF or AUR
   repository, and **nothing installed from this release updates itself** —
   where that is the case, this page says so rather than offering a button that
   leads nowhere.

---

## LibreSCRS Card Agent

Required before LibreCelik, LibreKDE, or any PKCS#11-aware application can see
your card. Install this first.

### Arch / Manjaro

Each repository carries an Arch recipe under `packaging/arch/`. Build them in
dependency order — one `makepkg` run per repository, and the agent repository's
single run produces three packages:

```
librescrs-middleware                                     (LibreMiddleware)
librescrs-agent-common, -core, -client-qt                (LibreAgent)
librescrs-agent, librescrs-pinentry-kde                  (LibreLinux)
```

`librescrs-agent` is the daemon; `librescrs-pinentry-kde` is the separate
prompter that collects PINs, CANs and MRZs — without it no PIN operation is
possible. `librescrs-agent-common` is `arch=any`, so its file name ends in
`-any.pkg.tar.zst` while the others end in `-x86_64.pkg.tar.zst`; a command
that spells the architecture out will miss it.

All four Arch recipes on this page — middleware, agent libraries, agent and
the Plasma client — were built in a clean chroot for this release, in that
order.

```
sudo pacman -U librescrs-middleware-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-agent-common-5.0.0-1-any.pkg.tar.zst \
               librescrs-agent-core-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-agent-client-qt-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-agent-5.0.0-1-x86_64.pkg.tar.zst \
               librescrs-pinentry-kde-5.0.0-1-x86_64.pkg.tar.zst
```

The two agent repositories publish the source tarball those recipes fetch,
each with its signature:

{{< release-assets repo="LibreAgent" >}}

{{< release-assets repo="LibreLinux" >}}

{{< button href="https://github.com/LibreSCRS/LibreLinux/releases/tag/5.0.0" target="_blank" >}}LibreLinux 5.0.0 source{{< /button >}}

### Debian, Ubuntu, Fedora

Prebuilt middleware packages ship for Debian 13, Ubuntu 26.04 LTS and Fedora
43. Each asset names the distribution it was built for, so pick the one that
matches yours — a package built against another distribution's glibc will
install and then fail to load.

{{< release-assets repo="LibreMiddleware" >}}

These install the libraries, the card plugins and, if you choose it, the direct
PKCS#11 registration. **`librescrs-pkcs11-direct` conflicts with the card
agent.** On Debian and Ubuntu, installing it removes the agent; on Fedora, `dnf`
refuses the transaction until the agent is removed. Install it only on a
machine that deliberately has none.

The agent host and the Plasma client have no `.deb` or `.rpm` in this release —
build them from source, in the dependency order above; see
[Building from source](/developer-guide/building-from-source/).

### macOS

The macOS agent host is written and has run on real hardware, but it is not
part of this release: there is no signed, notarised build, and the macOS
PKCS#11 proxy is not in 5.0.0. A macOS user who needs card access today builds
the host from source.

### After installing

The agent does not start until the first card operation asks for it, and it is
not enabled at every login by default. See
[Install the card agent](/user-guide/install-agent/) for how to confirm it is
running and how to change that.

---

## LibreCelik

GUI smart card reader for Linux and macOS. Reads passports, ePassports, eID,
vehicle registration and other PKI cards through plugins.

**Requires the LibreSCRS card agent — see above.** LibreCelik links no PC/SC
stack of its own; all card access happens in the agent.

{{< button href="https://github.com/LibreSCRS/LibreCelik/releases/tag/5.0.0" target="_blank" >}}Download AppImage (Linux){{< /button >}}

{{< button href="https://github.com/LibreSCRS/LibreCelik/releases/tag/5.0.0" target="_blank" >}}Download DMG (macOS){{< /button >}}

{{< release-assets repo="LibreCelik" >}}

---

## LibreKDE

Plasma 6 integration: the smart-card plasmoid, the credential-management
window, a Purpose "Sign" plugin, and the `card:/` KIO worker.

Ships as source with an Arch recipe in `packaging/arch/` (package name
`librekde`). It depends on `librescrs-agent` and `librescrs-agent-client-qt`,
so install the agent first.

{{< release-assets repo="LibreKDE" >}}

{{< button href="https://github.com/LibreSCRS/LibreKDE/releases/tag/5.0.0" target="_blank" >}}LibreKDE 5.0.0 source{{< /button >}}

---

## PKCS#11 Module

Installed automatically with the card agent above — there is no separate
download. Firefox, Chrome, Thunderbird and `ssh` discover it through p11-kit
once the agent package is installed.

The middleware's own direct module is no longer registered by default. If you
installed it by hand from a 4.x release archive, that registration is not
removed by any package manager; the
[PKCS#11 guide](/user-guide/pkcs11/) has the one command that clears it, along
with browser setup and the headless case that still uses the direct module.

---

## Verifying what you downloaded

Release tags are signed with OpenPGP and release artifacts with cosign. The
key, the fingerprint and the identity-pinned `cosign verify-blob` command are
on [verifying a release](/security/).
