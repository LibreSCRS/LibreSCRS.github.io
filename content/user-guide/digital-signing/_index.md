---
title: "Digital Signing"
description: "Sign documents and files using your smart card"
layout: "simple"
---

Smart cards with private keys can be used for digital signatures. This page covers how to sign files from the command line and mentions other applications that support PKCS#11 signing. The examples below use Serbian eID and PKS cards, but the same workflow applies to any card supported by OpenSC or the LibreSCRS PKCS#11 module.

## Prerequisites

You need one of the following:

1. **OpenSC with built-in Serbian card support** — just install OpenSC, nothing else needed. *(Not yet released — a built-in driver has been approved and is pending inclusion in the next OpenSC release.)*
2. **OpenSC + LibreSCRS external driver** — use this until the built-in driver is released. Gives you full OpenSC CLI tools (`pkcs15-crypt`, `pkcs11-tool`, etc.). See [OpenSC driver setup]({{< ref "user-guide/cardedge-opensc-driver" >}}).
3. **LibreSCRS PKCS#11 module** — works without OpenSC. For browser authentication and signing via any PKCS#11 application. See [PKCS#11 setup]({{< ref "user-guide/cardedge-pkcs11" >}}).

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
pkcs11-tool --module /usr/local/lib/librescrs-cardedge-pkcs11.so \
    --sign --mechanism RSA-PKCS --id 02 \
    --input-file /tmp/hash.bin --output-file /tmp/sig.bin
```

---

## Browser authentication (eUprava)

For authenticating to government services like eUprava, set up the PKCS#11 module in Firefox. See the [PKCS#11 Firefox setup guide]({{< ref "user-guide/cardedge-pkcs11" >}}).

When you visit a site that requires client certificate authentication, Firefox will prompt you to select a certificate and enter your PIN.

---

## PDF signing

PDF readers that support PKCS#11 security devices should be able to use your smart card for signing. This includes:

- **Okular** (KDE) — supports PKCS#11 via NSS
- **Adobe Reader** (if available on your platform)

This functionality has not been extensively tested. If you have experience with PDF signing using smart cards, please [report your findings](https://github.com/LibreSCRS/LibreMiddleware/issues).

---

## Email signing (S/MIME)

Thunderbird and other email clients that support PKCS#11 security devices can use your smart card certificates for S/MIME email signing and encryption. Load the PKCS#11 module in Thunderbird the same way as in Firefox — see [PKCS#11 setup]({{< ref "user-guide/cardedge-pkcs11" >}}).

Whether the certificates on your card are suitable for S/MIME depends on their key usage extensions. If you have tested this, please [share your results](https://github.com/LibreSCRS/LibreMiddleware/issues).
