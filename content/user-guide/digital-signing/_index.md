---
title: "Digital Signing"
description: "Sign documents and files using your smart card"
layout: "simple"
---

Smart cards with private keys can be used for digital signatures. The fastest way to sign a document is the **built-in signing wizard in LibreCelik**. This page also covers command-line signing and third-party PKCS#11 clients. The examples below use Serbian eID and PKS cards, but the same workflow applies to any card supported by LibreCelik, OpenSC, or the LibreSCRS PKCS#11 module.

## Signing in LibreCelik (recommended)

LibreCelik ships a native signing wizard that produces EU eIDAS / ETSI
baseline signatures directly from your smart card — no external signing
service, no PDF tooling, no manual hash-and-sign dance. The wizard handles
PAdES (PDF), CAdES (`.p7s`), XAdES (`.xml`), JAdES (`.json`), and ASiC-E
(`.asice`) containers at the four conformance levels (B-B, B-T, B-LT,
B-LTA).

To sign a document:

1. Insert your signing card and open LibreCelik. Wait until the card appears
   in the main window.
2. Open **File → Sign document…** (or the "Sign" action on the card view).
3. **Pick the document.** Drag a file into the drop zone, or click *Browse*.
4. **Choose the signature format** (PAdES for PDFs, ASiC-E for any other
   file type, CAdES / XAdES / JAdES if you have a specific requirement) and
   the **conformance level** (B-B for offline signing, B-T for a trusted
   timestamp, B-LT / B-LTA for long-term archive signatures — these
   additionally require an internet connection to fetch revocation data
   from CRL / OCSP).
5. *(PAdES only)* **Place the visual signature.** Pick a page, drag the
   placement rectangle, and the wizard auto-fits the text. The preview
   is pixel-exact against the final embedded PDF.
6. **Select the signing certificate** — the wizard lists all signing
   certificates discovered on the card. PIN status (good / blocked /
   retries-left) is shown next to each.
7. **Enter your PIN** when prompted, then choose the output path.
8. The wizard produces the signed file and shows the verification
   summary (signer, chain, timestamps).

The wizard uses the LibreSCRS PKCS#11 module under the hood, so the same
trust anchors and revocation behaviour apply whether you sign through the
GUI or one of the command-line workflows below.

---

## Prerequisites

You need one of the following:

1. **OpenSC with built-in Serbian card support** — just install OpenSC, nothing else needed. *(The srbeid driver has been [merged into OpenSC mainline](https://github.com/OpenSC/OpenSC/pull/3595) but is not yet included in a release. If you build OpenSC from source, it works now.)*
2. **OpenSC + LibreSCRS external driver** — use this until the built-in driver is released. Gives you full OpenSC CLI tools (`pkcs15-crypt`, `pkcs11-tool`, etc.). See [OpenSC integration]({{< ref "user-guide/opensc-integration" >}}).
3. **LibreSCRS PKCS#11 module** — works without OpenSC. For browser authentication and signing via any PKCS#11 application. See [PKCS#11 setup]({{< ref "user-guide/pkcs11" >}}).

---

## Command-line signing with OpenSC

### Sign a file

`pkcs15-crypt --sha-256` expects a **pre-computed binary hash** as input, not the raw message.

```bash
# Compute the hash
openssl dgst -sha256 -binary /path/to/message.txt > /tmp/hash.bin

# Sign with key 02 (Digital Signature)
pkcs15-crypt --sign --pkcs1 --sha-256 --key 02 \
    --input /tmp/hash.bin --output /tmp/sig.bin
```

### Verify the signature

```bash
# Extract the public key from the certificate
# Note: pkcs15-tool outputs PEM on Linux, DER on macOS
pkcs15-tool --read-certificate 02 --output /tmp/cert.pem
openssl x509 -in /tmp/cert.pem -pubkey -noout > /tmp/pubkey.pem

# Verify
openssl dgst -sha256 -verify /tmp/pubkey.pem \
    -signature /tmp/sig.bin /path/to/message.txt
# Verified OK
```

### Using pkcs11-tool

You can also sign using `pkcs11-tool` with either the LibreSCRS PKCS#11 module or OpenSC's module:

```bash
pkcs11-tool --module /usr/local/lib/librescrs-pkcs11.so \
    --sign --mechanism RSA-PKCS --id 02 \
    --input-file /tmp/hash.bin --output-file /tmp/sig.bin
```

---

## Browser authentication (eUprava)

For authenticating to government services like eUprava, set up the PKCS#11 module in Firefox. See the [PKCS#11 Firefox setup guide]({{< ref "user-guide/pkcs11" >}}).

When you visit a site that requires client certificate authentication, Firefox will prompt you to select a certificate and enter your PIN.

---

## PDF signing in third-party readers

If you prefer a different PDF reader, most PKCS#11-aware readers can use
your smart card via the LibreSCRS PKCS#11 module. Examples:

- **Okular** (KDE) — supports PKCS#11 via NSS
- **Adobe Reader** (if available on your platform)

These paths are useful when you need a viewer-integrated signing flow that
isn't covered by LibreCelik's wizard. If you test one of them with a
specific card and have feedback, please [share your findings](https://github.com/LibreSCRS/LibreMiddleware/issues).

---

## Email signing (S/MIME)

Thunderbird and other email clients that support PKCS#11 security devices can use your smart card certificates for S/MIME email signing and encryption. Load the PKCS#11 module in Thunderbird the same way as in Firefox — see [PKCS#11 setup]({{< ref "user-guide/pkcs11" >}}).

Whether the certificates on your card are suitable for S/MIME depends on their key usage extensions. If you have tested this, please [share your results](https://github.com/LibreSCRS/LibreMiddleware/issues).
