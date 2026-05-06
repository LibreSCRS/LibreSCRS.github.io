---
title: "CancelToken with std::jthread (recipe)"
weight: 31
---

LibreMiddleware's public API uses `LibreSCRS::CancelToken` rather than `std::stop_token` directly, but third-party plugin authors often want `std::jthread` for its RAII join + automatic stop_token injection. The two integrate cleanly via a small bridge.

## Pattern

```cpp
#include <LibreSCRS/CancelToken.h>

#include <stop_token>
#include <thread>

class MyAsyncWorker {
public:
    void start(LibreSCRS::CancelToken token) {
        // Mirror cancellation into a private std::stop_source, owned by
        // the worker. std::jthread reads the matching stop_token directly.
        registration = token.registerCallback([this] {
            stopSource.request_stop();
        });

        worker = std::jthread([this](std::stop_token st) {
            while (!st.stop_requested()) {
                // do work; check st.stop_requested() between cooperatively
                // cancellable steps.
            }
        });

        // Note: re-use stopSource.get_token() inside the lambda above if you
        // need to share the same stop_token with non-jthread machinery.
    }

private:
    std::stop_source                  stopSource;
    LibreSCRS::CancelToken::Registration registration;
    std::jthread                      worker;  // RAII join
};
```

## Why bridge instead of expose `std::stop_token` directly

LibreMiddleware exposes `CancelToken` because:

- The pImpl-backed type keeps `<stop_token>` out of public include paths (avoids propagating the `-fexperimental-library` flag to consumers on Apple Clang).
- It gives LibreMiddleware ABI flexibility — the underlying primitive can change in 5.x without source-level fallout.

The bridge pattern above is stable: it relies only on C++20 standard library types and the public LibreSCRS API.
