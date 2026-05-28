---
layout: "simple"
title: "Reader-List Snapshot API"
description: "Receiving the authoritative post-change reader-list snapshot from MonitorService — introduced in LibreSCRS 4.2.0"
weight: 45
---

Introduced in **LibreSCRS 4.2.0**. This page is for host applications that
need the current set of PC/SC readers and an update whenever that set
changes. The Qt-free `subscribeReaderList` API delivers the full post-change
reader list as one snapshot, so consumers no longer fold individual
`ReaderAdded` / `ReaderRemoved` events into a local `std::set` to recover the
membership.

All symbols live on the public
`LibreSCRS::SmartCard::MonitorService` class declared in
`LibreMiddleware/include/LibreSCRS/SmartCard/MonitorService.h`.

## API

```cpp
using ReaderListCallback =
    std::function<void(const std::vector<std::string>&)>;          // @since 4.2

[[nodiscard]] SubscriptionId
subscribeReaderList(ReaderListCallback callback);                  // @since 4.2

void unsubscribeReaderList(
    SubscriptionId id,
    DrainPolicy policy = DrainPolicy::FireAndForget) noexcept;     // @since 4.2
```

| Member | Purpose |
|---|---|
| `subscribeReaderList(cb)` | Register `cb` for the full post-change reader-list snapshot. Returns a `SubscriptionId`. |
| `unsubscribeReaderList(id, policy)` | Unregister a reader-list subscription. `noexcept`. |
| `ReaderListCallback` | `std::function<void(const std::vector<std::string>&)>` — receives the reader names. |

## Semantics

- **Bootstrap fire.** The callback fires once on registration with the
  current snapshot (which may be empty when no readers are plugged in), then
  again on every subsequent change with the post-change snapshot. Late
  joiners therefore observe the initial inventory without polling
  `listReaders` themselves.
- **Ordering vs per-event `subscribe`.** Within a single reader-list change,
  the per-reader `MonitorEvent::Kind::ReaderAdded` / `ReaderRemoved` events
  are dispatched **first** through any `subscribe` callbacks, and the
  aggregated post-change snapshot is dispatched **afterwards** through every
  `subscribeReaderList` callback. A consumer that registers both kinds can
  rely on each snapshot observing every prior per-reader event for the same
  change.
- **Shared token space.** Handles minted by `subscribeReaderList` and
  `subscribe` are pairwise distinct and must be passed to their matching
  unsubscribe overload. Passing a `subscribe` handle to
  `unsubscribeReaderList` (or vice versa) is treated as unknown and is a
  no-op.
- **Auto-start.** The first subscriber — counting both `subscribe` and
  `subscribeReaderList` — starts the polling thread. The brief
  "`isRunning()` may report false" window documented on `subscribe` applies
  here too.
- **Teardown.** `unsubscribeReaderList(id, DrainPolicy::Drain)` blocks until
  the poll thread's current dispatch cycle for this subscription has
  finished; after it returns the callback is guaranteed never to fire again.
  Do not call it from within the callback in `Drain` mode (deadlock). The
  default `FireAndForget` returns immediately; a dispatch that snapshotted
  the subscriber set before the call may still invoke the callback once
  afterwards, so callbacks touching soon-to-be-destroyed state should use
  `Drain` or weak ownership.

## Example

```cpp
LibreSCRS::SmartCard::MonitorService monitor;

// Receive the authoritative reader list after each change without
// maintaining a local std::set<std::string>.
auto id = monitor.subscribeReaderList(
    [](const std::vector<std::string>& readers) {
        // Marshal to the GUI thread, e.g. via QMetaObject::invokeMethod.
        emitReaderListChanged(readers);
    });

// ... later, on shutdown:
monitor.unsubscribeReaderList(id);
```

## Migration from 4.1

Before 4.2, host code subscribed to the per-event stream and rebuilt the
membership by hand:

```cpp
// 4.1: fold per-reader events into a local set
std::set<std::string> readers;
monitor.subscribe([&](const MonitorEvent& ev) {
    if (ev.kind == MonitorEvent::Kind::ReaderAdded)   readers.insert(ev.reader);
    if (ev.kind == MonitorEvent::Kind::ReaderRemoved) readers.erase(ev.reader);
    publish(readers);  // also needed a separate listReaders() bootstrap
});
```

In 4.2, drop the local set and the manual bootstrap — `subscribeReaderList`
hands you the snapshot directly, including the first-fire inventory.
LibreCelik's `QSmartCardMonitor` migrated this way: it now drives its Qt
`readerListChanged` signal straight from the LM snapshot.

## See also

- [What's new in 4.2](../whats-new-in-4-2/)
- [Architecture Overview](../architecture/)
