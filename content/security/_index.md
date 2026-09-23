---
layout: "simple"
title: "Verifying a Release"
description: "The OpenPGP key that signs LibreSCRS release tags, and the identity-pinned cosign command that verifies a release artifact"
---

Every LibreSCRS release is signed twice: the **git tag** with an OpenPGP key,
and each **release artifact** with cosign in keyless mode. The two answer
different questions — the tag proves which commit the maintainer released, the
artifact signature proves which build workflow produced the file you
downloaded — so a careful verification does both.

The same information ships in the `KEYS` file at the root of every LibreSCRS
repository. This page exists so that a `SECURITY.md` or a README can link to
it, and so that the commands below stay in one place when they change.

## Verifying a release tag

```
gpg --import KEYS
git verify-tag <TAG>
```

The project release signing key, valid from 4.0 onwards:

```
pub   ed25519 2026-04-27 [C] [expires: 2031-04-26]
      6B05889AC9A6A7188DF639B06F27A989C2031D16
uid           [ultimate] LibreSCRS Release Signing <librescrs@proton.me>
sub   ed25519 2026-04-27 [S] [expires: 2028-04-26]
      D95BE325E2EC2E90E1DC750422941CECE07A5167
```

The first fingerprint is the **primary** key; the second is the signing
subkey, and it is the subkey that actually appears in a tag signature. When
you read `gpg --verify --status-fd=1` output rather than the human-readable
form, the `VALIDSIG` line's *first* field is the signing subkey and the
*last* is the primary — compare the right one.

## Verifying a release artifact

Release artifacts carry a `<artifact>.sigstore.json` cosign bundle. The
complete command is:

```
cosign verify-blob <artifact> \
  --bundle <artifact>.sigstore.json \
  --certificate-identity-regexp 'https://github\.com/LibreSCRS/.*\.github/workflows/release\.yml@refs/tags/.*' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'
```

### Why the two `--certificate-*` flags are not optional

`cosign verify-blob --bundle <bundle> <artifact>` on its own proves only that
the artifact matches the bundle that came with it. It says nothing about
**who** produced either. In keyless mode there is no long-lived public key to
recognise; the identity lives in a short-lived certificate, and the two flags
above are what pin it:

- `--certificate-identity-regexp` requires the signature to come from a
  release workflow in the `LibreSCRS` GitHub organisation, running on a tag;
- `--certificate-oidc-issuer` requires that identity to have been asserted by
  GitHub's own OIDC issuer, not by some other identity provider that also
  happens to be able to mint Sigstore certificates.

Without them, an attacker who replaces both the artifact and its bundle
passes the check. With them, they would additionally have to sign as a
LibreSCRS release workflow.

**What the signature does and does not prove.** A cosign bundle proves which
release workflow, on which tag, produced the exact bytes you downloaded. It
does not prove that an independent rebuild would produce the same bytes: the
source tarball is built to be byte-reproducible — and for LibreLinux,
LibreCelik and LibreKDE that is measured on every push — but the binary
packages, the AppImage and the DMG are not yet. Until they are, the identity in
the certificate is the claim — not a rebuild you can repeat.

## Reporting a vulnerability

Each repository carries a `SECURITY.md` with the current reporting address
and the supported-version table for that component.
