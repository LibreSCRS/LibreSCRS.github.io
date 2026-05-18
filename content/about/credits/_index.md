---
title: "Third-Party Credits"
layout: "simple"
weight: 50
---

LibreSCRS would not be possible without the open-source ecosystem.
This page lists every third-party component bundled in our binary
releases, with attribution and license terms.

---

## Statically linked components

### OpenSC (LGPL-2.1-or-later)

[OpenSC](https://github.com/OpenSC/OpenSC) — the open-source smart card
library. We ship a modified fork; see our
[LibreMiddleware thirdparty/patches/](https://github.com/LibreSCRS/LibreMiddleware/tree/main/thirdparty/patches)
directory for downstream patches.

### OpenSSL (Apache-2.0)

[OpenSSL](https://www.openssl.org/) 3.5.5 — cryptographic library,
statically vendored.

---

## Vendored libraries

### nlohmann/json (MIT)

[json](https://github.com/nlohmann/json) — JSON for Modern C++.

### miniz (MIT/zlib-style)

[miniz](https://github.com/richgel999/miniz) — lossless compression.

### zlib (zlib license)

[zlib](https://zlib.net) — transitive dependency through OpenSC.

### Liberation Sans (SIL-OFL-1.1)

[Liberation Fonts](https://github.com/liberationfonts/liberation-fonts)
— bundled subset.

---

## Source code availability

The complete corresponding source code for LibreSCRS, including all
LGPL-licensed components and our downstream modifications to them, is
publicly available:

- **LibreMiddleware:** <https://github.com/LibreSCRS/LibreMiddleware>
- **LibreCelik:** <https://github.com/LibreSCRS/LibreCelik>

This offer is valid for as long as we distribute LibreSCRS.
