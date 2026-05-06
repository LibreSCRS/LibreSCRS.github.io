---
title: "Korišćenje CancelToken-a"
weight: 30
---

`LibreSCRS::CancelToken` je primitiv za kooperativno otkazivanje koji koriste sve asinkrone LibreMiddleware API-je. Koristi se zajedno sa `LibreSCRS::CancelSource` (kontrolerom) i `LibreSCRS::Completion<T>` (pozivnim rezultatom asinkronog poziva).

## Osnovno korišćenje

```cpp
#include <LibreSCRS/CancelToken.h>
#include <LibreSCRS/Trust/TrustStoreService.h>

auto source = LibreSCRS::CancelSource{};
service->waitForEagerFetches(std::chrono::seconds{30}, source.token());

// kasnije, iz druge niti:
source.requestCancel();  // sinhrono; odmah pokreće sve registrovane callback-ove
```

## Podrazumevani token = bez otkazivanja

`LibreSCRS::CancelToken{}` (podrazumevano konstruisan) nije moguće otkazati. Ne alocira ništa i predstavlja siguran podrazumevani izbor za pozivaoce koji nemaju izvor otkazivanja. `isCancellable()` vraća `false`.

## Registrovanje callback-a

```cpp
auto registration = token.registerCallback([] {
    std::cerr << "zahtev za otkazivanje\n";
});
// registration je RAII; izlazak iz opsega odjavljuje callback.
```

Callback se izvršava sinhrono na niti koja zove `requestCancel`. Ne pozivajte `registerCallback` iz callback-a koji se već izvršava — to dovodi do mrtve petlje u `std::stop_callback` semantici.

## Životni vek

Tokeni kopirani iz istog izvora dele stanje preko `std::shared_ptr`. Uništavanje izvora dok su tokeni (ili registracije) još aktivni je sigurno — stanje otkazivanja preživljava izvor.
