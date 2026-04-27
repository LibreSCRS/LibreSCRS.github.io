---
title: "Bezbednost"
description: "LibreSCRS release bezbednost, kriptografska provenance i verifikacija"
weight: 50
---

# LibreSCRS Bezbednost

## Verifikacija release-a

Svi LibreSCRS release-i ≥ 4.0 su kriptografski potpisani koristeći dva
nezavisna trust anchor-a: GPG-potpisani git tagovi i Sigstore cosign-
potpisani release artefakti.

### Potpisivanje tagova — GPG

LibreSCRS git tagovi su potpisani projektnim release signing ključem
(Ed25519, primary [Certify] + signing subkey [Sign]).

**Fingerprint:** `6B05 889A C9A6 A718 8DF6  39B0 6F27 A989 C203 1D16`

**Javni ključ:**
- [librescrs-release.asc](/security/keys/librescrs-release.asc)
- `KEYS` fajl u [LibreMiddleware](https://github.com/LibreSCRS/LibreMiddleware/blob/main/KEYS) i [LibreCelik](https://github.com/LibreSCRS/LibreCelik/blob/main/KEYS) repoima
- Keyserver: `gpg --keyserver keys.openpgp.org --recv-keys 6B05889AC9A6A7188DF639B06F27A989C2031D16`

Da verifikuješ release tag:

```bash
git clone https://github.com/LibreSCRS/LibreCelik
cd LibreCelik
gpg --import KEYS
git verify-tag 4.0.0
```

### Potpisivanje artefakata — Sigstore (keyless)

LibreSCRS release artefakti (AppImage, DMG, pluginovi, …) su potpisani
Sigstore keyless metodom kroz GitHub Actions OIDC. Nije potrebno
importovati javni ključ; verifikacija koristi Sigstore Fulcio CA +
Rekor transparency log.

Da verifikuješ artefakt:

```bash
cosign verify-blob LibreCelik-4.0.0.AppImage \
  --bundle LibreCelik-4.0.0.AppImage.sigstore.json \
  --certificate-identity-regexp 'https://github\.com/LibreSCRS/LibreCelik/\.github/workflows/release\.yml@refs/tags/.*' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'
```

Transparency log entry javno je pretraživ na [search.sigstore.dev](https://search.sigstore.dev).

### Šta verifikacija dokazuje

Uspešan `git verify-tag` dokazuje da je tag kreiran LibreSCRS-ovim
projektnim release signing privatnim ključem i da nije izmenjen.

Uspešan `cosign verify-blob` dokazuje da je artefakt proizveden
LibreSCRS GitHub Actions release workflow-om na tag-u koji odgovara
release pattern-u, i da je potpis upisan u Rekor transparency log u
trenutku potpisivanja.

## Prijavljivanje bezbednosnih problema

Otvori privatni security advisory:
- [LibreMiddleware advisories](https://github.com/LibreSCRS/LibreMiddleware/security/advisories)
- [LibreCelik advisories](https://github.com/LibreSCRS/LibreCelik/security/advisories)

Ili email: [librescrs@proton.me](mailto:librescrs@proton.me).

## Politika rotacije ključeva

- **Primary ključ** (Certify-only) — Ed25519, 5-godišnji expiry, renewable
- **Signing subkey** — Ed25519, 2-godišnji expiry, proaktivna rotacija
- **KEYS** fajlovi u oba repoa i static asset na ovom sajtu se ažuriraju
  pri svakoj rotaciji.
