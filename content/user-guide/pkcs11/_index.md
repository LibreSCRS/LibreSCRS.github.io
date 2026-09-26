---
layout: "simple"
title: "PKCS#11 Module"
description: "Using the LibreSCRS card agent's PKCS#11 module with Firefox, Chrome, Thunderbird and SSH, and removing an older direct-module registration"
---

Any PKCS#11-aware application — Firefox, Chrome, Thunderbird, `ssh`, Kleopatra
— can use your smart card through LibreSCRS, with LibreCelik closed.

From 5.0 the module those applications load is the **card agent's client
module**, `librescrs-pkcs11-agent.so`. It performs no cryptography itself and
holds no card secret: it maps the PKCS#11 `C_*` calls onto the per-user agent,
which owns the card, the prompter and the authorization policy.

The practical consequence is worth stating before anything else. The token
advertises a **protected authentication path**, so your PIN is typed into the
agent's own prompter and never reaches the application. An application that
passes a PIN to `C_Login` has it ignored.

**Card types recognized automatically:**

- **CardEdge** — Serbian eID Gemalto (2014+), IF2020 Foreigner, PKS Chamber of
  Commerce
- **PKCS#15** — any PKCS#15-compliant smart card
- **PIV** — US federal ID cards (NIST SP 800-73)

## Installation

There is nothing to download. The module is installed by the card agent
package — see [Install the card agent](/user-guide/install-agent/) and the
[downloads page](/downloads/) — and registered with p11-kit by that same
package. Applications wired into p11-kit find it with no per-application
configuration at all.

Confirm the registration:

```
p11-kit list-modules
```

The LibreSCRS entry must be listed, and its token must show
`protected authentication path`. That line is the check that matters: without
it, the application would try to collect the PIN itself.

The same command prints the module's absolute path, which the sections below
call `<module>`. On a stock Linux install it is
`/usr/lib/pkcs11/librescrs-pkcs11-agent.so`.

## OpenSC's module beside this one

If your distribution's OpenSC package is installed, `p11-kit list-modules`
lists its module too, and together with p11-kit's own trust module three
entries is the normal count on a desktop. OpenSC is a separate provider, not
part of LibreSCRS: an OpenSC release that carries the Serbian eID driver (see
[OpenSC integration](/user-guide/opensc-integration/)) offers the same card a
second time, and through it the application collects the PIN itself.

A browser that lists two devices for one card is showing you exactly that.
The LibreSCRS one is the device whose token shows `protected authentication
path`. The packages do not conflict with OpenSC on purpose — that would remove
it for every other card it serves. If you do not need it, removing OpenSC's
PKCS#11 package (`opensc-pkcs11` on Debian and Ubuntu, `opensc` elsewhere)
leaves one provider.

## If you installed a PKCS#11 module before 5.0

Up to 4.x the middleware shipped its own direct module and told you to register
it by hand. That module is no longer the registered provider, and one card
offering two providers with two different PIN-entry models is exactly the
situation this release exists to end. Three populations, and a package manager
cleans only one of them:

- **You installed a distribution package.** Nothing to do. `pacman`, `dpkg` and
  `rpm` remove files that leave the manifest.
- **You installed from source with `cmake --install`.** Not cleaned:
  `install()` overwrites and never deletes. Remove the old library and any
  registration you added by hand.
- **You installed from a release archive**, following the instructions that
  release shipped. Not cleaned either, and this is the install base that
  actually exists, because the published archive is what created it. Remove the
  registration:

  ```
  rm ~/.config/pkcs11/modules/librescrs.module
  ```

Then re-run `p11-kit list-modules` and confirm exactly one LibreSCRS provider
is listed. If a browser still offers two devices for one card, an NSS database
registration is left over as well — see
[Firefox and Thunderbird](#firefox-and-thunderbird) below and remove the entry
you added.

## Firefox and Thunderbird

Firefox and Thunderbird consume p11-kit on most Linux distributions and need no
setup. If yours does not:

1. **Settings** → **Privacy & Security** → **Security** → **Security Devices**
2. **Load**
3. Name it `LibreSCRS` and give the module path from `p11-kit list-modules`
4. **OK**

Insert your card and refresh. When a service asks for a client certificate —
Serbian eUprava, for instance — the agent's prompter asks for the PIN.

To remove a stale entry, select it in the same dialog and choose **Unload**.

## Chrome and Chromium

Chrome on Linux uses the NSS database rather than p11-kit. Register once:

```
# modutil, if not already present
sudo apt install libnss3-tools     # Debian/Ubuntu
sudo dnf install nss-tools         # Fedora

modutil -dbdir sql:$HOME/.pki/nssdb -add librescrs -libfile <module>
```

Restart Chrome. The card's certificates appear under **Settings** → **Privacy
and security** → **Manage certificates**.

## OpenSSH

List the public keys on the card:

```
ssh-keygen -D <module>
```

Authenticate with it:

```
ssh -I <module> user@host
```

Or, in `~/.ssh/config`:

```
Host myserver
    PKCS11Provider <module>
```

## Checking it from the command line

```
pkcs11-tool --module <module> -T
```

The token must list `protected authentication path`. PKCS#11 URI selection
(`pkcs11:token=…`) works across p11-kit modules once the agent is running.

## Out-of-process isolation

By default the module runs in the calling application's process, where it holds
no secret and does no cryptography. If you would rather it did not run there at
all, p11-kit can host it out of process — either one short-lived child per
consumer, or a long-lived per-user server over a socket. Both are configuration
changes to the installed `.module` file, which documents the two forms inline;
the library itself is the same either way.

## macOS

**There is no agent PKCS#11 provider on macOS in 5.0.0.** The agent ships in
[LibreMac](/user-guide/install-libremac/), and Keychain clients such as Safari
and Mail reach a present card's signing certificates through its CryptoTokenKit
extension; a proxy module that other PKCS#11 applications could load is not
part of this release.

A macOS user who needs a PKCS#11 provider today builds the middleware's direct
module from source and registers it explicitly. It is the same module Linux
used up to 4.x, with the same property this page otherwise argues against: the
application collects the PIN.

## Headless Linux hosts

A machine that runs no agent — a build server signing artifacts, say — can
still use the middleware's direct module. It is built and installed as before;
only its p11-kit declaration is gone, and
`-DLIBREMIDDLEWARE_INSTALL_P11KIT_MODULE=ON` restores that:

```
cmake -S /path/to/LibreMiddleware -B build \
      -DLIBREMIDDLEWARE_INSTALL_P11KIT_MODULE=ON
cmake --build build --target librescrs-pkcs11
```

On such a host there is no prompter, so the application supplies the PIN — which
is why this is the headless case and not the default one.
