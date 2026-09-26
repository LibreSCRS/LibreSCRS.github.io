#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prove check_api_claims.py fails, and refuses, where it is supposed to.

    python3 tools/check_api_claims.selftest.py

One case per way the gate could ship green while proving nothing: a refuted
claim wrapped across lines or written as a code example the headers reject; a
symbol documented in one language only, or on the Serbian side of a different
page, or outside the developer guide, or only as a longer name; a symbol no
header names any more; and every vacuum (no list, an empty list, no pages, no
guide, no header root, a root with no header) as exit 2. Every case runs the
shipped gate against a stand-in header tree, so it states what the gate does
and not what a checkout of the library happens to hold today.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
GATE = TOOLS / "check_api_claims.py"
SYMBOLS = [l.strip() for l in (TOOLS / "documented-api.txt").read_text(encoding="utf-8").splitlines()
           if l.strip() and not re.match(r"\s*#(\s|$)", l)]

# A refuted sentence wrapped inside a code comment, as it was on the published
# page: no single line carries it, which is why the gate normalises whitespace.
WRAPPED_CLAIM = ("```cpp\n    // writes the signed payload to outputFile -- there is no\n"
                 "    //    byte-buffer ingestion seam on the public API.\n```\n")
# build() is rvalue-qualified and every setter returns Builder&: this does not compile.
BROKEN_BUILDER = ("```cpp\n    auto request = lsc::Signing::SigningRequest::Builder{}\n"
                  "                       .inputFile(\"document.pdf\")\n                       .build();\n```\n")
IDIOMATIC_BUILDER = ("```cpp\n    lsc::Signing::SigningRequest::Builder builder;\n"
                     "    builder.inputFile(\"document.pdf\");\n    auto request = std::move(builder).build();\n```\n")

CASES = RED = FAILED = 0


def page(path: Path, symbols, extra=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\ntitle: \"F\"\ndescription: \"F\"\n---\n\n"
                    + "".join(f"`{s}` is documented here.\n\n" for s in symbols) + extra,
                    encoding="utf-8")


def pair(content: Path, en, sr, extra="", section="developer-guide", name="fixture"):
    page(content / section / name / "_index.md", en, extra)
    page(content / section / name / "_index.sr.md", sr)
    return content


def headers(root: Path, symbols):
    (root / "LibreSCRS").mkdir(parents=True, exist_ok=True)
    (root / "LibreSCRS" / "Api.h").write_text(
        "#pragma once\n" + "".join(f"void {s}();\n" for s in symbols), encoding="utf-8")
    return root


def case(name, want, content, needle, **env_over):
    global CASES, RED, FAILED
    env = {k: v for k, v in os.environ.items() if k not in ("REFUTED_FILE", "API_FILE", "API_HEADERS")}
    env["API_HEADERS"] = str(SHIPPED)
    env.update(env_over)
    done = subprocess.run([sys.executable, str(GATE), str(content)],
                          capture_output=True, text=True, env=env)
    out = done.stdout + done.stderr
    CASES += 1
    RED += want != 0
    ok = done.returncode == want and needle in out
    FAILED += not ok
    print(f"{'ok  ' if ok else 'FAIL'}  {name} (rc={done.returncode}, want {want})")
    if not ok:
        print("\n".join("  | " + l for l in out.splitlines()[-8:]))


def main() -> int:
    global SHIPPED
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR", "/var/tmp")) as t:
        r = Path(t)
        SHIPPED = headers(r / "shipped", SYMBOLS)
        last, rest = SYMBOLS[-1], SYMBOLS[:-1]
        clean = pair(r / "clean", SYMBOLS, SYMBOLS)

        case("C1 an honest, complete pair passes", 0, clean, "OK:")
        leaf = pair(r / "leaf", SYMBOLS, SYMBOLS)
        page(leaf / "developer-guide" / "fixture" / "note.md", [], WRAPPED_CLAIM)
        case("C2 a wrapped refuted claim on a leaf page fails", 1, leaf, "carries a refuted claim")
        case("C3 a builder finalised on a temporary fails", 1,
             pair(r / "broken", SYMBOLS, SYMBOLS, BROKEN_BUILDER), "carries a refuted claim")
        case("C4 the idiomatic builder passes", 0,
             pair(r / "idiomatic", SYMBOLS, SYMBOLS, IDIOMATIC_BUILDER), "OK:")
        case("C5 a symbol missing from the SR mirror fails", 1,
             pair(r / "half", SYMBOLS, rest), "but not on its SR mirror")
        split = pair(r / "split", SYMBOLS, rest, name="first")
        pair(split, rest, SYMBOLS, name="second")
        case("C6 an SR hit on another page's mirror fails", 1, split, "(EN=1 SR=1)")
        elsewhere = pair(r / "elsewhere", rest, rest)
        pair(elsewhere, [last], [last], section="security")
        case("C7 a symbol documented only outside the guide fails", 1, elsewhere,
             f"public symbol {last} is on no dev-guide page")
        renamed = rest + [last + "Renamed"]
        case("C8 a longer name does not document the symbol", 1,
             pair(r / "super", renamed, renamed), f"public symbol {last} is on no dev-guide page")
        hashed = r / "hashed.txt"
        hashed.write_text("# comment\nPKCS#11 has no session objects\n", encoding="utf-8")
        case("C9 a '#' inside a pattern belongs to the pattern", 1,
             pair(r / "hash", SYMBOLS, SYMBOLS, "Here PKCS#11 has no session objects.\n"),
             "matched 'PKCS#11 has no session objects'", REFUTED_FILE=str(hashed))
        empty = r / "empty.txt"
        empty.write_text("# nothing\n", encoding="utf-8")
        case("C10 an empty refuted list refuses", 2, clean, "vacuously", REFUTED_FILE=str(empty))
        case("C11 an empty documented-api list refuses", 2, clean, "vacuously", API_FILE=str(empty))
        case("C12 a missing list refuses", 2, clean, "is missing", REFUTED_FILE=str(r / "none.txt"))
        (r / "bare").mkdir()
        case("C13 no pages refuses", 2, r / "bare", "no pages under")
        case("C14 no developer guide refuses", 2,
             pair(r / "guideless", SYMBOLS, SYMBOLS, section="security"), "vacuously")
        case("C15 a symbol no header names fails", 1, clean, "is named by no header",
             API_HEADERS=str(headers(r / "dropped", rest)))
        case("C16 a header naming only a longer name fails", 1, clean, "is named by no header",
             API_HEADERS=str(headers(r / "widened", renamed)))
        case("C17 an absent header root refuses", 2, clean, "is not a directory",
             API_HEADERS=str(r / "absent"))
        (r / "no-headers").mkdir()
        case("C18 a header root with no header refuses", 2, clean, "no header under",
             API_HEADERS=str(r / "no-headers"))

    print("---")
    print(f"{FAILED} case(s) did not behave as required" if FAILED
          else "OK: the gate passes what it should and refuses what it must")
    print(f"selftest: {CASES} cases, {RED} red-proved")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
