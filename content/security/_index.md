---
title: "Security"
description: "LibreSCRS release security, cryptographic provenance, and verification"
weight: 50
---

# LibreSCRS Security

## Release verification

All LibreSCRS releases ≥ 4.0 are cryptographically signed using two
independent trust anchors: GPG-signed git tags and Sigstore cosign-signed
release artifacts.

### Tag signing — GPG

LibreSCRS git tags are signed with the project release signing key
(Ed25519, primary [Certify] + signing subkey [Sign]).

**Fingerprint:** `6B05 889A C9A6 A718 8DF6  39B0 6F27 A989 C203 1D16`

**Public key:**
- [librescrs-release.asc](/security/keys/librescrs-release.asc)
- `KEYS` file in [LibreMiddleware](https://github.com/LibreSCRS/LibreMiddleware/blob/main/KEYS) and [LibreCelik](https://github.com/LibreSCRS/LibreCelik/blob/main/KEYS) repos
- Keyserver: `gpg --keyserver keys.openpgp.org --recv-keys 6B05889AC9A6A7188DF639B06F27A989C2031D16`

To verify a release tag:

```bash
git clone https://github.com/LibreSCRS/LibreCelik
cd LibreCelik
gpg --import KEYS
git verify-tag 4.0.0
```

### Artifact signing — Sigstore (keyless)

LibreSCRS release artifacts (AppImage, DMG, plugins, …) are signed via
Sigstore keyless signing through GitHub Actions OIDC. No key import is
needed; verification uses the Sigstore Fulcio CA + Rekor transparency
log.

To verify an artifact:

```bash
cosign verify-blob LibreCelik-4.0.0.AppImage \
  --bundle LibreCelik-4.0.0.AppImage.sigstore.json \
  --certificate-identity-regexp 'https://github\.com/LibreSCRS/LibreCelik/\.github/workflows/release\.yml@refs/tags/.*' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'
```

The signature transparency log entry is publicly searchable at
[search.sigstore.dev](https://search.sigstore.dev).

### What verification proves

A successful `git verify-tag` proves the tag was created with the
LibreSCRS release signing private key and has not been altered.

A successful `cosign verify-blob` proves the artifact was produced by
the LibreSCRS GitHub Actions release workflow on a tag matching the
release pattern, and the signature was logged in Rekor at the time of
signing.

## Reporting security issues

Open a private security advisory:
- [LibreMiddleware advisories](https://github.com/LibreSCRS/LibreMiddleware/security/advisories)
- [LibreCelik advisories](https://github.com/LibreSCRS/LibreCelik/security/advisories)

Or email [librescrs@proton.me](mailto:librescrs@proton.me).

## Key rotation policy

- **Primary key** (Certify-only) — Ed25519, 5-year expiry, renewable
- **Signing subkey** — Ed25519, 2-year expiry, rotated proactively
- **KEYS** files in each repo and the static asset on this site are
  updated on every rotation.
