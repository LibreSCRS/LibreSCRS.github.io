---
layout: "simple"
title: "Logging Facade"
description: "Redirecting LibreMiddleware's diagnostics into your application's log — the sink-injected LibreSCRS::log API introduced in LibreSCRS 5.0"
weight: 49
---

Introduced in **LibreSCRS 5.0**. This page is for host applications that want
LibreMiddleware's diagnostics to land wherever their own log lines already go
— journald, a rotating file, a Qt category, an in-app console — instead of on
the process's `stderr`.

All symbols live in the public header
`LibreMiddleware/include/LibreSCRS/Logging.h`, namespace `LibreSCRS::log`.

## Why it exists

Before 5.0, LibreMiddleware had no seam here. When a subscriber callback you
passed to `MonitorService::subscribe` threw, the library caught the exception
— it has to, an exception escaping a `std::thread` entry point calls
`std::terminate` — and reported it with `std::fprintf(stderr, ...)`. The
source said as much in a comment: a fallback *"because the SDK does not
currently inject a logger across the public ABI boundary"*.

A library writing to a stream it does not own, with no way to redirect it, is
a defect on its own terms rather than a matter of taste. `LibreSCRS::log` is
that boundary.

## API

```cpp
namespace LibreSCRS::log {

enum class Level : std::uint8_t { Info, Warn, Error };

using LogSink = std::function<void(Level level, std::string_view line)>;

void init(LogSink sink, std::string category = "rs.librescrs");
void resetForTest() noexcept;

void info(std::string_view message);
void warn(std::string_view message);
void error(std::string_view message);

template <class... Args> void infof(std::format_string<Args...>, Args&&...);
template <class... Args> void warnf(std::format_string<Args...>, Args&&...);
template <class... Args> void errorf(std::format_string<Args...>, Args&&...);

} // namespace LibreSCRS::log
```

The same shape is exposed by the LibreSCRS agent
(`LibreSCRS::Agent::log`), so a diagnostic grep reads the host layer and the
core identically.

## Installing a sink

Call `init` once, during single-threaded startup, before any LibreSCRS
service runs:

```cpp
#include <LibreSCRS/Logging.h>
#include <LibreSCRS/SmartCard/MonitorService.h>

int main()
{
    LibreSCRS::log::init(
        [](LibreSCRS::log::Level level, std::string_view line) {
            switch (level) {
            case LibreSCRS::log::Level::Info:  myLog().info(line);  break;
            case LibreSCRS::log::Level::Warn:  myLog().warn(line);  break;
            case LibreSCRS::log::Level::Error: myLog().error(line); break;
            }
        },
        "com.example.myapp");

    LibreSCRS::SmartCard::MonitorService monitor;
    // ...
}
```

Passing an **empty** `LogSink` restores the built-in sink.

## Line format

Each line arrives at the sink already formatted and newline terminated:

```
<N>category level: message\n
```

`<N>` is the syslog priority journald reads off the front of a line and
strips — `<6>` for info, `<4>` for warning, `<3>` for error. Anywhere else it
is inert text. For example:

```
<3>com.example.myapp error: MonitorService: subscriber callback threw: bad allocation
```

The built-in sink writes the same line to `std::clog`.

## What this does and does not capture

`LibreSCRS::log` carries the diagnostics LibreMiddleware emits **without
being asked** — today, the four exception shields around consumer callbacks
in `MonitorService`.

It is not a trace channel. LibreMiddleware still has roughly 150 diagnostic
sites gated behind five environment switches — `LIBRESCRS_SIGN_TRACE`,
`LIBRESCRS_PCSC_TRACE`, `LIBRESCRS_PROBE_TRACE`, `LIBRESCRS_OPENSC_DEBUG` and
`PKCS11_DEBUG` — which write to `stderr` directly and are unaffected by an
installed sink. Those sit in PC/SC transmit, PKCS#15 profile reading and the
signing engine; they are unchanged in 5.0. Do not read *"I installed a sink"*
as *"I captured everything LibreMiddleware can print"*.

## Rules the sink has to follow

**Do not call back into the facade.** A single process-wide mutex is held
across the format and the sink call, so lines never interleave and `init`
cannot race an in-flight emit. Calling `LibreSCRS::log::info` from inside a
sink deadlocks.

**Expect calls from any thread.** The `MonitorService` poll thread emits on
its own thread; your sink must be thread-safe.

**Keep it cheap and non-throwing.** An exception thrown out of a sink
propagates into whatever LibreSCRS code was emitting — including a `catch`
block whose whole job was to stop an exception from reaching a thread entry
point.

**Outlive the library's use of it.** The sink is a `std::function` held for
the process's lifetime. Capturing a stack local, then returning from the
function that installed it, is a use-after-free on the next emit.

## Testing

`resetForTest()` drops the injected sink and restores the default category. A
test that installs a sink capturing test-local state and does not reset it
leaves that sink installed for every following case in the same binary. Put
the call in the fixture's `TearDown()`, not at the end of the test body — a
failing assertion returns early and skips whatever comes after it.

## Global state, deliberately

LibreSCRS is otherwise built on constructor dependency injection: no
`instance()`, no Meyers singletons. The logging facade is the one documented
exception. Threading a logger reference through every internal type, down to
a `catch` block inside a poll thread, would cost the entire surface and buy
nothing; the exception is confined to this header, and `resetForTest()` is
the obligation that comes with it.
