---
layout: "simple"
title: "Arhitektura potpisivanja"
description: "Interna arhitektura LibreMiddleware engine-a za digitalno potpisivanje"
weight: 40
---

Ova stranica opisuje internu arhitekturu LibreMiddleware engine-a za potpisivanje za kontributore koji žele da razumeju kako sistem funkcioniše, dodaju nove formate potpisa ili debaguju probleme sa potpisivanjem.

## Tok potpisivanja od početka do kraja

Kompletan tok od korisničke akcije do potpisanog dokumenta:

```
1. Korisnik klikne "Potpiši" u LibreCelik-u
   └─ SignPage čarobnjak prikuplja: dokument, format, nivo, TSA, vizuelne parametre

2. LibreCelik kreira SigningRequest i poziva SigningService::sign()
   └─ PIN prosleđen kao span<const uint8_t> iz SecureBuffer-a

3. NativeSigningService::sign()
   ├─ Otvara Pkcs11Token (učitava PKCS#11 modul, prijavljuje se PIN-om)
   ├─ Čita sertifikat za potpisivanje + lanac sa tokena
   └─ Prosleđuje format modulu na osnovu request.format

4. Format modul (npr. PAdESModule::sign())
   ├─ Priprema kontejner potpisa (PDF inkrementalno čuvanje, CMS, XML, JSON ili ZIP)
   ├─ Računa digest dokumenta (SHA-256)
   ├─ Poziva Pkcs11Token::sign(hash) → sirovi bajtovi potpisa sa kartice
   ├─ Ugrađuje potpis + lanac sertifikata u kontejner
   └─ Ako je nivo >= B-T: poziva TSAClient::timestamp(hash)
      └─ Šalje RFC 3161 zahtev TSA serveru
      └─ Ugrađuje TimeStampToken u potpis

5. Ako je nivo >= B-LT:
   ├─ RevocationClient preuzima CRL + OCSP odgovore za lanac sertifikata
   └─ Format modul ugrađuje podatke o opozivu u potpis

6. Ako je nivo == B-LTA:
   └─ Arhivski vremenski pečat dodat preko celokupnog potpisa + podataka o opozivu

7. NativeSigningService vraća SigningResult { success, signedDocument }

8. LibreCelik čuva potpisani dokument na disk
```

---

## Struktura modula

Engine za potpisivanje se nalazi u `lib/libresign/` unutar LibreMiddleware-a. Organizovan je u tri sloja:

Javna zaglavlja se nalaze u `include/libresign/` (tipovi najvišeg nivoa) i `include/libresign/native/` (klase native backend-a). Implementacije i interni helperi backend-a žive u `src/`.

### Sloj osnovnog servisa

| Fajl | Namena |
|---|---|
| `include/libresign/signing_service.h` | `SigningService` apstraktni interfejs — `configure()`, `sign()`, `isAvailable()` |
| `include/libresign/signing_service_factory.h` | Fabrička funkcija `createSigningService(Backend)` |
| `include/libresign/types.h` | Tipovi podataka: `SigningRequest`, `SigningResult`, `TrustConfig`, `TSAConfig`, enumeracije |
| `include/libresign/trust_store_manager.h` | `TrustStoreManager` — agregira sistemske, ugrađene i TL-izvedene sertifikate za različite potrošače, i one koji potpisuju i one koji ne |

### Format moduli

Svaki format potpisa je implementiran kao nezavisan modul. Svi moduli prate isti obrazac: primaju dokument + sertifikat + callback za potpisivanje, proizvode potpisane izlazne bajtove.

| Modul | Fajl | Standard |
|---|---|---|
| PAdES | `src/native/pades_module.cpp` | PDF inkrementalno čuvanje sa CMS potpisom |
| CAdES | `src/native/cades_module.cpp` | Detached CMS/PKCS#7 potpis |
| XAdES | `src/native/xades_module.cpp` | XML Digital Signature sa XAdES svojstvima |
| JAdES | `src/native/jades_module.cpp` | JSON Web Signature sa JAdES zaglavljem |
| ASiC-E | `src/native/asic_module.cpp` | ZIP kontejner sa XAdES potpisom (koristi miniz) |

Format moduli primaju `Pkcs11Token&` referencu za operacije potpisivanja. Token interno upravlja PKCS#11 sesijom, pretragom ključeva i sirovim potpisivanjem.

### Infrastruktura

| Komponenta | Fajlovi | Namena |
|---|---|---|
| `Pkcs11Token` | `include/libresign/native/pkcs11_token.h` + `src/native/pkcs11_token.cpp` | Upravljanje PKCS#11 sesijom — učitavanje modula, prijava, pretraga ključeva, sirovo potpisivanje, ekstrakcija sertifikata |
| `TSAClient` | `include/libresign/native/tsa_client.h` + `src/native/tsa_client.cpp` | RFC 3161 zahtevi za vremenske pečate putem HTTP-a (libcurl) |
| `RevocationClient` | `include/libresign/native/revocation_client.h` + `src/native/revocation_client.cpp` | Preuzimanje CRL-ova i OCSP-a za B-LT/B-LTA nivoe |
| `SigningProvider` | `include/libresign/native/signing_provider.h` + `src/native/signing_provider.cpp` | Apstrakcija nad Pkcs11Token za spoljne korisnike |
| `TrustedListParser` | `include/libresign/native/trusted_list_parser.h` + `src/native/trusted_list_parser.cpp` | XML parser za EU Trusted Lists (LOTL i TL) |
| `TlCache` | (interni) `src/native/tl_cache.h/.cpp` | Keš na disku za preuzete Trusted List XML fajlove |
| `TlSignatureVerifier` | (interni) `src/native/tl_signature_verifier.h/.cpp` | XML-DSIG verifikacija potpisa Trusted List-a |
| `PinnedTlCerts` | (interni) `src/native/pinned_tl_certs.h/.cpp` | Kompajlirani LOTL sertifikati za potpis koji služe kao koren poverenja |
| PDF parser | (interni) `src/native/pdf_parser.h/.cpp` | Minimalan PDF parser za PAdES inkrementalno čuvanje — pronalazi xref, dodaje rečnik potpisa |
| OpenSSL RAII | (interni) `src/native/openssl_raii.h` | RAII omotači za OpenSSL tipove (`BIO`, `X509`, `EVP_PKEY`, itd.) |

---

## Model poverenja

Engine za potpisivanje koristi model poverenja sa tri nivoa za validaciju sertifikata:

### Nivo 1: Sistemski sertifikati

Podrazumevano skladište sertifikata operativnog sistema. Koristi se kao koren poverenja za TLS konekcije (TSA, CRL/OCSP krajnje tačke) i kao rezervna opcija za izgradnju lanca sertifikata.

### Nivo 2: Ugrađeni sertifikati

Sertifikati isporučeni sa LibreMiddleware-om u `thirdparty/certs/`. Uključuju korenaste CA sertifikate za srpsku državnu PKI infrastrukturu koji možda nisu u sistemskim skladištima. Koriste se za verifikaciju lanca sertifikata sa kartice.

### Nivo 3: Sertifikati izvedeni iz lista poverenja

Sertifikati ekstraktovani iz EU Trusted Lists (TL/LOTL). Engine preuzima i parsira EU List of Trusted Lists, prati linkove ka nacionalnim listama poverenja i ekstraktuje CA sertifikate za potpisivanje. Koriste se za B-LT i B-LTA validaciju — obezbeđuju sidra poverenja koja povezuju sertifikat potpisnika sa EU-priznatim pružaocem usluga poverenja.

**Lanac autentifikacije:** Sam LOTL je potpisan. Engine verifikuje potpis LOTL-a koristeći prikvačene sertifikate (`pinned_tl_certs.cpp`) koji su kompajlirani u biblioteku. Nacionalni TL-ovi se verifikuju koristeći sertifikate pronađene u LOTL-u. Ovo stvara lanac: prikvačeni sertifikat verifikuje potpis LOTL-a, LOTL obezbeđuje sertifikate koji verifikuju potpise nacionalnih TL-ova, nacionalni TL-ovi obezbeđuju sertifikate pružalaca usluga poverenja.

```
Prikvačeni LOTL sertifikati za potpisivanje (kompajlirani)
  └─ verifikuju → potpis EU LOTL XML-a
       └─ sadrži → sertifikate za potpisivanje nacionalnih TL-ova
             └─ verifikuju → potpise nacionalnih TL XML-ova
                   └─ sadrže → sertifikate pružalaca usluga poverenja
                         └─ validiraju → lanac sertifikata potpisnika
```

---

## DSS oracle za validaciju

Projekat uključuje DSS (Digital Signature Services) backend koji se može koristiti kao **oracle za validaciju** u testovima. DSS je EU referentna implementacija za kreiranje i validaciju potpisa, koju održava Evropska komisija.

**Šta radi:** DSS backend delegira potpisivanje pokrenutom DSS serveru putem REST API-ja. Ovo je korisno za unakrsnu validaciju da su potpisi proizvedeni nativnim engine-om prihvaćeni od strane EU referentne implementacije.

**Korišćenje u testovima:** Kada je postavljeno `SIGNING_BACKEND=both`, testovi mogu kreirati potpis nativnim backend-om i validirati ga DSS-om, ili obrnuto. Ovo otkriva suptilne probleme usklađenosti formata koje sami unit testovi ne bi uhvatili.

**Napomena:** DSS backend je zastareo za produkcionu upotrebu. Postoji isključivo kao test oracle. Nativni backend je produkcioni engine za potpisivanje.

---

## Tok podataka: LibreCelik ka LibreMiddleware

LibreCelik (GUI) i LibreMiddleware (engine) su odvojeni projekti sa čistom granicom. Evo kako podaci za potpisivanje prelaze tu granicu:

```
┌─────────────────────────────────────────────────┐
│                 LibreCelik (GUI)                 │
│                                                  │
│  ┌────────────┐    ┌──────────────────────────┐ │
│  │  SignPage   │───▶│ SigningRequest            │ │
│  │  (čarobnjak)│    │ ┌─ bajtovi dokumenta     │ │
│  │             │    │ ├─ format (PAdES/CAdES/..)│ │
│  │ Prikuplja:  │    │ ├─ nivo (B-B/B-T/..)     │ │
│  │ - putanja   │    │ ├─ TSA URL               │ │
│  │ - format    │    │ ├─ parametri viz. potpisa │ │
│  │ - nivo      │    │ └─ PIN (SecureBuffer)     │ │
│  │ - PIN       │    └──────────┬───────────────┘ │
│  └────────────┘               │                  │
│                               ▼                  │
├───────────────────────────────┬──────────────────┤
│              LibreMiddleware  │                   │
│                               │                  │
│  ┌────────────────────────────▼───────────────┐  │
│  │         NativeSigningService               │  │
│  │                                            │  │
│  │  ┌──────────────┐  ┌───────────────────┐   │  │
│  │  │ Pkcs11Token  │  │  Format modul     │   │  │
│  │  │ (I/O kartice)│  │  (PAdES/CAdES/..) │   │  │
│  │  └──────┬───────┘  └────────┬──────────┘   │  │
│  │         │ sirov potpis      │ potpisan dok. │  │
│  │         ▼                   ▼               │  │
│  │  ┌──────────────────────────────────────┐   │  │
│  │  │ SigningResult { success, bytes, err } │   │  │
│  │  └──────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

**Ključne projektne odluke:**

- **Bez Qt zavisnosti** — celokupan engine za potpisivanje je čist C++20 bez Qt tipova. LibreCelik konvertuje između Qt tipova (`QString`, `QByteArray`) i standardnih tipova (`std::string`, `std::vector<uint8_t>`) na granici.
- **Bez poznavanja protokola kartice** — engine za potpisivanje ne šalje APDU komande i ne zna za tipove kartica. Sav pristup kartici ide kroz PKCS#11, koji je standardni interfejs koji svaki kompatibilan token može zadovoljiti.
- **PIN se nikada ne čuva** — PIN putuje kao `span<const uint8_t>` koji ne poseduje memoriju, od `SecureBuffer`-a GUI-ja kroz `C_Login` poziv PKCS#11. Nijedna međukopija ne opstaje nakon povratka iz poziva.
- **Format moduli su bez stanja** — svaki `sign()` poziv je samosadržan. Nema stanja sesije između poziva, što engine čini bezbednim za konkurentno korišćenje iz više niti.

---

## Dodavanje novog formata potpisa

Za dodavanje novog format modula:

1. Kreirajte `include/libresign/native/newformat_module.h` i `src/native/newformat_module.cpp`
2. Implementirajte `sign()` funkciju koja prima dokument, `Pkcs11Token&` i parametre specifične za format
3. Registrujte format u `NativeSigningService::sign()` dodavanjem slučaja za novu `SignatureFormat` enum vrednost
4. Dodajte novu enum vrednost u `SignatureFormat` u `types.h`
5. Dodajte izvorne fajlove u `lib/libresign/CMakeLists.txt`
6. Napišite testove — koristite DSS oracle (`SIGNING_BACKEND=both`) za validaciju usklađenosti formata
