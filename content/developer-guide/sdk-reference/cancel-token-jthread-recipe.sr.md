---
title: "CancelToken sa std::jthread (recept)"
weight: 31
---

Javni LibreMiddleware API koristi `LibreSCRS::CancelToken` umesto direktnog `std::stop_token`-a, ali autori plugina iz trećih ruku često žele `std::jthread` zbog RAII join-a i automatskog ubrizgavanja stop_token-a. Oba se čisto integrišu preko malog mosta.

## Šablon

```cpp
#include <LibreSCRS/CancelToken.h>

#include <stop_token>
#include <thread>

class MyAsyncWorker {
public:
    void start(LibreSCRS::CancelToken token) {
        // Preslikavanje otkazivanja u privatni std::stop_source koji vlasi
        // worker. std::jthread čita odgovarajući stop_token direktno.
        registration = token.registerCallback([this] {
            stopSource.request_stop();
        });

        worker = std::jthread([this](std::stop_token st) {
            while (!st.stop_requested()) {
                // posao; proveravajte st.stop_requested() između
                // kooperativno otkazivih koraka.
            }
        });
    }

private:
    std::stop_source                  stopSource;
    LibreSCRS::CancelToken::Registration registration;
    std::jthread                      worker;  // RAII join
};
```

## Zašto most umesto direktnog izlaganja `std::stop_token`-a

LibreMiddleware izlaže `CancelToken` jer:

- pImpl-tip drži `<stop_token>` van javnih include putanja (sprečava propagaciju `-fexperimental-library` flag-a konzumentima na Apple Clang-u).
- Daje LibreMiddleware-u ABI fleksibilnost — interni primitiv može da se promeni u 5.x bez source-level posledica.

Šablon mosta je stabilan: oslanja se samo na C++20 standardne tipove i javni LibreSCRS API.
