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
2. **Linux packages ship for five distributions:** `.deb` for Debian 13 and
   Ubuntu 26.04 LTS, `.rpm` for Fedora 43, Fedora 44 and openSUSE Tumbleweed —
   for the middleware, the agent, LibreCelik and LibreKDE (LibreKDE on all of
   them except openSUSE Tumbleweed). LibreCelik also ships an AppImage and a
   DMG; Arch and Manjaro build from the recipes in each repository. There is no
   signed APT, DNF, zypper or AUR repository, and **nothing installed from
   this release updates itself** — where that is the case, this page says so
   rather than offering a button that leads nowhere.

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

The source tarballs those recipes fetch are listed, each with its signature,
among the assets of each repository below.

{{< button href="https://github.com/LibreSCRS/LibreLinux/releases/tag/5.0.0" target="_blank" >}}LibreLinux 5.0.0 source{{< /button >}}

### Debian, Ubuntu, Fedora, openSUSE

Packages ship for Debian 13, Ubuntu 26.04 LTS, Fedora 43, Fedora 44 and
openSUSE Tumbleweed. Each asset names the distribution it was built for, so
pick the ones that match yours — a package built against another
distribution's libraries will install and then fail to load.

The card agent is three repositories' worth of packages — the middleware's
libraries and card plugins, the agent's client library, and the agent with
its PIN prompter:

| | Debian 13, Ubuntu 26.04 | Fedora 43, 44, openSUSE Tumbleweed |
|---|---|---|
| LibreMiddleware | `liblibrescrs5`, `librescrs-card-plugins` | `librescrs-middleware`, `librescrs-card-plugins` |
| LibreAgent | `liblibrescrs-agentclient-qt5` | `librescrs-agent-client-qt` |
| LibreLinux | `librescrs-agent`, `librescrs-pinentry-kde` | `librescrs-agent`, `librescrs-pinentry-kde` |

Download them into one otherwise empty directory and install them in one
transaction, so the package manager orders them itself:

```
sudo apt install ./*.deb                                  # Debian, Ubuntu
sudo dnf install ./*.rpm                                  # Fedora
sudo zypper install --allow-unsigned-rpm ./*.rpm          # openSUSE Tumbleweed
```

The packages are not signed with a distribution key — there is no repository
to carry one — so `zypper` needs `--allow-unsigned-rpm`; what proves where they
came from is the release signature described under
[Verifying what you downloaded](#verifying-what-you-downloaded). The `-dev` and
`-devel` packages are for building against the libraries; a desktop needs none
of them.

{{< release-assets repo="LibreMiddleware" >}}

{{< release-assets repo="LibreAgent" >}}

{{< release-assets repo="LibreLinux" >}}

**`librescrs-pkcs11-direct` conflicts with the card agent.** It registers the
middleware's own PKCS#11 module for a machine that deliberately runs no agent,
and exactly one of the two can be installed. What switching between them takes
depends on the package manager, in both directions:

| | plain install of the other package | the command that switches |
|---|---|---|
| `apt` | switches: removes the installed one | `sudo apt install ./<package>.deb` |
| `dnf` | refuses, and changes nothing | `sudo dnf install --allowerasing ./<package>.rpm` |
| `zypper` | refuses, and changes nothing | `sudo zypper install --allow-unsigned-rpm --force-resolution ./<package>.rpm` — or run it interactively and choose the solution that removes the installed one |

**Not in this release:** Ubuntu 24.04 LTS and openSUSE Leap 16.0. The agent
needs sdbus-c++ 2, and Ubuntu 24.04 ships 1.4 and Leap 16.0 ships 1.6; Ubuntu
24.04 has no KDE Frameworks 6 either, which the PIN prompter is built on.
Without the agent no client has card access, so neither distribution gets
packages. Arm64 is not built either.

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
stack of its own; all card access happens in the agent. **The AppImage does not
contain the agent** and cannot: the agent is a per-user systemd service on the
session bus behind polkit, and only a system package can install those.
Install the agent packages above first, whichever form of LibreCelik you run.

On the distributions above, LibreCelik is also a package, `librecelik`,
installed the same way as the agent's.

{{< button href="https://github.com/LibreSCRS/LibreCelik/releases/tag/5.0.0" target="_blank" >}}Download AppImage (Linux){{< /button >}}

{{< button href="https://github.com/LibreSCRS/LibreCelik/releases/tag/5.0.0" target="_blank" >}}Download DMG (macOS){{< /button >}}

{{< release-assets repo="LibreCelik" >}}

---

## LibreKDE

Plasma 6 integration: the smart-card plasmoid, the credential-management
window, a Purpose "Sign" plugin, and the `card:/` KIO worker.

Ships as five packages — `librekde-common`, `librekde-plasmoid`,
`librekde-kio`, `librekde-purpose` and `librekde-credentials` — for Debian 13,
Ubuntu 26.04 LTS, Fedora 43 and Fedora 44, and as an Arch recipe in
`packaging/arch/` (package name `librekde`). There is no openSUSE Tumbleweed
build: a rolling distribution moves Plasma's libraries under a prebuilt
package faster than a release can follow. It depends on the agent and its
client library, so install the agent first.

{{< release-assets repo="LibreKDE" >}}

{{< button href="https://github.com/LibreSCRS/LibreKDE/releases/tag/5.0.0" target="_blank" >}}LibreKDE 5.0.0 source{{< /button >}}

---

## PKCS#11 Module

Installed automatically with the card agent above — there is no separate
download. Firefox, Chrome, Thunderbird and `ssh` discover it through p11-kit
once the agent package is installed.

If your distribution's OpenSC package is installed too, `p11-kit list-modules`
shows its module beside ours — together with p11-kit's own trust module, three
entries is the normal count. They are separate providers: an OpenSC that
carries the Serbian eID driver offers the same card a second time, with the PIN
typed into the application instead of the agent's prompter. Our packages do
not conflict with OpenSC on purpose — that would remove it for every other
card it serves. The [PKCS#11 guide](/user-guide/pkcs11/) says how to tell the
two apart.

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
