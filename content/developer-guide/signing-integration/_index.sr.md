---
layout: "simple"
title: "Vodič za integraciju potpisivanja"
description: "Kako integrisati mogućnosti digitalnog potpisivanja LibreMiddleware-a u vašu aplikaciju"
weight: 30
---

LibreMiddleware uključuje nativni C++ engine za digitalno potpisivanje koji podržava pet formata potpisa, četiri nivoa usklađenosti i hardversko potpisivanje putem PKCS#11. Ovaj vodič objašnjava kako integrisati potpisivanje u vašu aplikaciju.

## Formati i nivoi potpisa

Engine proizvodi potpise u skladu sa EU eIDAS/ETSI baseline profilima:

| Format | Standard | Ulaz | Izlaz | Pakovanje |
|---|---|---|---|---|
| PAdES | ETSI EN 319 142 | PDF | Potpisan PDF | Enveloped |
| CAdES | ETSI EN 319 122 | Bilo koji fajl | `.p7s` (PKCS#7/CMS) | Detached |
| XAdES | ETSI EN 319 132 | Bilo koji fajl | `.xml` (XML-DSIG) | Enveloped ili detached |
| JAdES | ETSI EN 319 182 | Bilo koji fajl | `.json` (JWS) | Detached |
| ASiC-E | ETSI EN 319 162 | Bilo koji fajl(ovi) | `.asice` (ZIP kontejner) | Detached (XAdES unutra) |

Svaki format podržava četiri nivoa rastućeg poverenja:

| Nivo | Sadržaj | Zahteva |
|---|---|---|
| B-B | Osnovni potpis | Samo sertifikat za potpisivanje |
| B-T | B-B + vremenski pečat | TSA server |
| B-LT | B-T + podaci o opozivu (CRL/OCSP) | TSA + izvori opoziva |
| B-LTA | B-LT + arhivski vremenski pečat | TSA + izvori opoziva |

---

## CMake integracija

LibreMiddleware je dizajniran za korišćenje putem CMake `FetchContent`. Podrška za potpisivanje je podrazumevano uključena.

```cmake
include(FetchContent)
FetchContent_Declare(
    LibreMiddleware
    GIT_REPOSITORY https://github.com/LibreSCRS/LibreMiddleware.git
    GIT_TAG        v2.0.2
)
FetchContent_MakeAvailable(LibreMiddleware)

target_link_libraries(MyApp PRIVATE LibreSign)
```

Za lokalni razvoj, usmerite na lokalnu kopiju umesto preuzimanja sa Git-a:

```bash
cmake -B build -DFETCHCONTENT_SOURCE_DIR_LIBREMIDDLEWARE=/path/to/LibreMiddleware
```

### Opcije izgradnje

| Opcija | Podrazumevano | Opis |
|---|---|---|
| `BUILD_SIGNING` | `ON` | Uključi podršku za digitalno potpisivanje (LibreSign biblioteka) |
| `SIGNING_BACKEND` | `native` | Izbor backend-a: `native`, `dss` ili `both`. DSS backend je zastareo |

Izgradnja izvozi `LIBREMIDDLEWARE_HAS_SIGNING` tako da projekti koji koriste biblioteku mogu uslovno kompajlirati funkcionalnosti potpisivanja.

---

## Minimalan primer potpisivanja

```cpp
#include <libresign/signing_service_factory.h>
#include <libresign/types.h>

#include <fstream>
#include <vector>

int main()
{
    // 1. Kreiranje servisa za potpisivanje (native backend)
    auto service = libresign::createSigningService(libresign::Backend::Native);
    if (!service || !service->isAvailable()) {
        return 1;
    }

    // 2. Opciono konfigurisanje poverenja (EU Trusted Lists za B-LT/B-LTA)
    libresign::TrustConfig trust;
    trust.cacheDirectory = "/tmp/tl-cache";
    trust.trustedLists.push_back({
        .url = "https://ec.europa.eu/tools/lotl/eu-lotl.xml",
        .isLotl = true,
        .eager = true
    });
    service->configure(trust);

    // 3. Učitavanje dokumenta za potpisivanje
    std::ifstream file("document.pdf", std::ios::binary);
    std::vector<uint8_t> content(
        (std::istreambuf_iterator<char>(file)),
        std::istreambuf_iterator<char>()
    );

    // 4. Kreiranje zahteva za potpisivanje
    libresign::SigningRequest request;
    request.document = std::move(content);
    request.fileName = "document.pdf";
    request.format = libresign::SignatureFormat::PAdES;
    request.level = libresign::SignatureLevel::B_T;
    request.tsa.url = "http://timestamp.digicert.com";

    // 5. Potpisivanje putem PKCS#11 tokena
    std::string pin = "1234";  // u produkciji koristite SecureBuffer
    auto result = service->sign(
        request,
        "/usr/lib/opensc-pkcs11.so",     // putanja do bilo kog PKCS#11 modula
        libresign::as_pin(pin),          // PIN kao span bajtova
        "SIGN"                           // alias ključa na kartici
    );

    if (!result.success) {
        // result.errorMessage sadrži razlog greške
        return 1;
    }

    // 6. Zapisivanje potpisanog dokumenta
    std::ofstream out("document-signed.pdf", std::ios::binary);
    out.write(reinterpret_cast<const char*>(result.signedDocument.data()),
              result.signedDocument.size());
    return 0;
}
```

---

## Referenca API-ja

Svi tipovi se nalaze u `libresign` prostoru imena. Zaglavlja su u `libresign/`.

### SigningService

Apstraktni interfejs za sve operacije potpisivanja. Dobija se putem fabričke funkcije.

```cpp
// Fabrika — kreira konkretnu instancu servisa
std::unique_ptr<SigningService> createSigningService(Backend backend);

enum class Backend { Native, DSS };
```

**Metode:**

| Metoda | Opis |
|---|---|
| `configure(const TrustConfig&)` | Učitavanje lista poverenja i konfiguracija opoziva. Opciono za B-B/B-T, obavezno za B-LT/B-LTA |
| `sign(request, pkcs11Path, pin, keyAlias, tokenLabel)` | Potpisivanje dokumenta. Vraća `SigningResult` |
| `isAvailable()` | Provera da li je backend funkcionalan |

### SigningRequest

Opisuje šta se potpisuje i kako.

| Polje | Tip | Podrazumevano | Opis |
|---|---|---|---|
| `document` | `vector<uint8_t>` | — | Sirovi bajtovi dokumenta |
| `fileName` | `string` | — | Originalno ime fajla (koristi se za detekciju formata u ASiC-E) |
| `format` | `SignatureFormat` | `PAdES` | Ciljni format potpisa |
| `packaging` | `SignaturePackaging` | `ENVELOPED` | Enveloped ili detached |
| `level` | `SignatureLevel` | `B_T` | Nivo usklađenosti |
| `tsa` | `TSAConfig` | — | Konfiguracija servera za vremenske pečate |
| `visual` | `VisualSignatureParams` | onemogućeno | Vizuelni potpis (samo PAdES) |
| `allowExpiredCertificate` | `bool` | `false` | Dozvoli potpisivanje isteklim sertifikatima (samo za testiranje) |

### SigningResult

| Polje | Tip | Opis |
|---|---|---|
| `success` | `bool` | Da li je potpisivanje uspelo |
| `signedDocument` | `vector<uint8_t>` | Bajtovi potpisanog izlaza |
| `errorMessage` | `string` | Poruka o grešci u slučaju neuspeha |

### TrustConfig

Konfiguracija za EU Trusted Lists, koristi se za B-LT i B-LTA nivoe.

| Polje | Tip | Podrazumevano | Opis |
|---|---|---|---|
| `trustedLists` | `vector<TrustedListEntry>` | — | Izvori lista poverenja |
| `cacheDirectory` | `string` | — | Keš na disku za preuzete liste |
| `crlEnabled` | `bool` | `true` | Preuzimanje CRL-ova za proveru opoziva |
| `ocspEnabled` | `bool` | `true` | Korišćenje OCSP-a za proveru opoziva |

### TSAConfig

| Polje | Tip | Podrazumevano | Opis |
|---|---|---|---|
| `url` | `string` | — | URL RFC 3161 servera za vremenske pečate |
| `timeoutSeconds` | `int` | `10` | HTTP vremensko ograničenje za TSA zahteve |
| `crlEnabled` | `bool` | `true` | CRL provera za B-LT/B-LTA |
| `ocspEnabled` | `bool` | `true` | OCSP provera za B-LT/B-LTA |

---

## Podrška za PKCS#11 tokene

Engine za potpisivanje pristupa privatnim ključevima putem PKCS#11. Ne komunicira direktno sa smart karticama — sav I/O sa karticom prolazi kroz PKCS#11 modul.

Engine za potpisivanje radi sa bilo kojim PKCS#11 modulom. Možete koristiti OpenSC-ov `opensc-pkcs11.so` ili bilo koji drugi kompatibilan modul koji podržava vaš tip kartice.

**Izbor tokena:** Prosledite `tokenLabel` string metodi `sign()` za izbor specifičnog PKCS#11 slota po oznaci. Ako je prazan, servis automatski detektuje prvi dostupan token.

**Izbor ključa:** Parametar `keyAlias` se poklapa sa `CKA_LABEL` atributom na objektu privatnog ključa. Za srpske eID kartice, oznaka ključa za potpisivanje je obično `"SIGN"`.

**Rukovanje PIN-om:** Parametar `pin` je `std::span<const uint8_t>` — pogled koji ne poseduje memoriju i koji upućuje na memoriju kojom upravlja pozivalac. U produkcionom kodu, čuvajte PIN u `smartcard::SecureBuffer` koji automatski briše memoriju pri destrukciji. Servis za potpisivanje ne zadržava PIN nakon povratka iz `sign()` poziva.

---

## Rukovanje greškama

Metoda `sign()` vraća `SigningResult` umesto da baca izuzetke. Proverite `result.success` i pročitajte `result.errorMessage` u slučaju neuspeha:

```cpp
auto result = service->sign(request, pkcs11Path, pin, keyAlias);
if (!result.success) {
    // Uobičajene greške:
    // - "PKCS#11 module not found"
    // - "PIN verification failed"
    // - "TSA server unreachable"
    // - "Certificate has expired"
    log(result.errorMessage);
}
```

Metoda `configure()` vraća `false` ako učitavanje liste poverenja ne uspe. Ovo nije fatalno za B-B i B-T nivoe (koji ne zahtevaju liste poverenja), ali će kasnije uzrokovati neuspeh potpisivanja na B-LT i B-LTA nivoima.
