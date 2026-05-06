---
title: "Using CancelToken"
weight: 30
---

`LibreSCRS::CancelToken` is the cooperative cancellation primitive for every async LibreMiddleware API. Pair it with `LibreSCRS::CancelSource` (the controller) and `LibreSCRS::Completion<T>` (the async result callback).

## Basic usage

```cpp
#include <LibreSCRS/CancelToken.h>
#include <LibreSCRS/Trust/TrustStoreService.h>

auto source = LibreSCRS::CancelSource{};
service->waitForEagerFetches(std::chrono::seconds{30}, source.token());

// later, from another thread:
source.requestCancel();  // synchronous; fires registered callbacks immediately
```

## Default token = no cancellation

`LibreSCRS::CancelToken{}` (default-constructed) is *never-cancellable*. It allocates nothing and is the safe default for callers that have no cancellation source. `isCancellable()` returns `false`.

## Registering a callback

```cpp
auto registration = token.registerCallback([] {
    std::cerr << "cancellation requested\n";
});
// registration is RAII; let it go out of scope to unregister.
```

The callback fires synchronously on the thread that calls `requestCancel`. Do not call `registerCallback` from within an already-firing callback — it deadlocks `std::stop_callback` semantics.

## Lifetime

Tokens copied from the same source share state via `std::shared_ptr`. Destroying the source while tokens (or registrations) are still alive is safe — the cancellation state outlives the source.
