#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Hold the developer guide against the headers it describes.

Three rules, because the site's existing gate cannot see any of these failures:
check_translation_completeness.py compares EN with SR, so a claim that is
equally false in both languages passes it perfectly.

  1. Refuted claims       a claim the code has disproved -- a sentence, or a
                          code example the headers reject -- may not appear on
                          any page of the site. tools/refuted-claims.txt
                          carries one regex per line, with the header that
                          disproved it.
  2. Documented API       every symbol in tools/documented-api.txt must appear
                          on at least one EN page under content/developer-guide/
                          AND on that page's own SR mirror. "No public API
                          ships without documentation" was a project rule
                          nobody could fail; this list is what makes it fail.
  3. Symbols that exist   every symbol in tools/documented-api.txt must also be
                          named by the public headers of the library the guide
                          describes. Rules 1 and 2 read the site alone: rename
                          a symbol in the library, rename it on both pages, and
                          they stay green while the guide publishes a name no
                          header carries any more. Rule 3 is a text search over
                          the headers, not a parse -- it catches a name that
                          has left the tree, not one that has retreated into a
                          comment.

Rules 1 and 2 have deliberately different scopes: a refuted claim is false
wherever it stands, so rule 1 reads every markdown file under the content
directory, not only the section index pages; documentation is a promise about
the guide, so rule 2 reads only pages under content/developer-guide/ and a
mention on the landing or security page does not discharge it.

Rule 2 pairs page by page. Counting EN hits and SR hits separately would let a
symbol documented on one English page and on the Serbian side of a different
one pass, which is how a translated pair drifts apart while both totals stay
non-zero: the reader of either language would have to find the symbol on a
page its own language never names.

Rule 2 matches on identifier boundaries, not as a substring: renaming a
required symbol to a longer name that contains it is exactly the drift the
rule exists to catch, so it must not satisfy it.

Prose wraps across lines, so rule 1 matches against a whitespace-normalised
copy of the file (markdown/code comment prefixes stripped) and reports the
line the match starts on.

Usage: tools/check_api_claims.py [content-dir] [header-root]
       header-root defaults to ../LibreMiddleware/include next to this
       checkout, which is where a workspace holding both repositories puts it.
Env:   REFUTED_FILE / API_FILE relocate the two lists. They exist so the
       selftest can drive the refusal paths -- a list that is missing, and one
       that is present but empty -- against THIS file rather than against a
       copy of it placed in a temporary tree, where the copy would be the
       thing under test and the shipped script would go unmeasured.
       API_HEADERS relocates the header root the same way, for a checkout that
       puts the library beside this repository rather than above it.
Exit:  0 all rules hold; 1 a rule broke; 2 a list file is missing/empty, the
       header root is absent or holds no header, or there is nothing to judge.
       Rule 3 refuses rather than skipping: a check named for the headers must
       not pass green where it opened none.
"""
import os
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
CONTENT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "content"
GUIDE = "developer-guide"
EN, SR = "_index.md", "_index.sr.md"
OVERRIDES = {
    "refuted-claims.txt": os.environ.get("REFUTED_FILE"),
    "documented-api.txt": os.environ.get("API_FILE"),
}
HEADERS = Path(
    sys.argv[2] if len(sys.argv) > 2
    else os.environ.get("API_HEADERS") or ROOT.parent / "LibreMiddleware" / "include"
)
HEADER_SUFFIXES = (".h", ".hh", ".hpp", ".hxx")


def label(path):
    """Name a file the way a reader of the CI log can act on."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_list(name):
    """Return (entries, path). Refuses rather than passing over an empty list.

    A line is a comment only when its '#' is followed by whitespace or ends
    the line. Everywhere else a '#' belongs to the entry: this project's
    vocabulary is full of them -- PKCS#11, PKCS#15, #include -- and stripping
    from the first '#' would silently truncate such a pattern to a prefix that
    fires on every page naming PKCS, or drop it altogether.
    """
    override = OVERRIDES.get(name)
    p = Path(override) if override else TOOLS / name
    if not p.is_file():
        print(f"REFUSING: {p} is missing", file=sys.stderr)
        sys.exit(2)
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if re.match(r"\s*#(\s|$)", line):
            continue
        line = line.strip()
        if line:
            out.append(line)
    if not out:
        print(f"REFUSING: {p} is empty -- this gate will not pass vacuously", file=sys.stderr)
        sys.exit(2)
    return out, p


def read_headers():
    """Return (all header text, header paths). Refuses over an empty tree.

    Rule 3 exists because the list is otherwise a promise the site makes to
    itself. Refusing when the root is absent is the point: skipping would make
    the rule disappear exactly where nobody is looking -- a run with no library
    beside it -- and the log would read the same as a run that checked.
    """
    if not HEADERS.is_dir():
        print(f"REFUSING: {HEADERS} is not a directory -- rule 3 needs the public "
              f"headers this guide describes; pass them as the second argument or "
              f"in API_HEADERS", file=sys.stderr)
        sys.exit(2)
    files = sorted(p for p in HEADERS.rglob("*") if p.suffix in HEADER_SUFFIXES)
    if not files:
        print(f"REFUSING: no header under {HEADERS} -- rule 3 will not pass vacuously",
              file=sys.stderr)
        sys.exit(2)
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files), files


def normalise(text):
    """Collapse wrapping so a sentence split over lines still matches.

    Returns (flat, offsets) where offsets[i] is the 1-based source line of
    flat[i], so a match can be reported at its real line.
    """
    flat, offsets = [], []
    for lineno, raw in enumerate(text.splitlines(), 1):
        s = re.sub(r"^\s*(//+|#+|>|\*)\s*", "", raw)
        s = s.strip()
        if flat and flat[-1] != " ":
            flat.append(" ")
            offsets.append(lineno)
        for ch in s:
            flat.append(ch)
            offsets.append(lineno)
    return "".join(flat), offsets


def mentions(text, symbol):
    """True when text names symbol as a whole identifier.

    A substring test would let `setAnchorDirectory` discharge the requirement
    for `setAnchor`, so a rename into a longer name would pass unnoticed.
    """
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])", text) is not None


def main():
    pages = sorted(CONTENT.rglob("*.md"))
    if not pages:
        print(f"REFUSING: no pages under {CONTENT}", file=sys.stderr)
        return 2
    guide = [p for p in pages if p.relative_to(CONTENT).parts[0] == GUIDE]
    guide_en = [p for p in guide if p.name == EN]
    if not guide_en:
        print(f"REFUSING: no {EN} pages under {CONTENT}/{GUIDE} -- rule 2 would "
              f"pass vacuously over an empty guide", file=sys.stderr)
        return 2
    guide_sr = [p for p in guide if p.name == SR]

    text = {p: p.read_text(encoding="utf-8") for p in pages}
    flattened = {p: normalise(body) for p, body in text.items()}

    patterns, refuted_path = read_list("refuted-claims.txt")
    symbols, api_path = read_list("documented-api.txt")
    lists = f"{label(refuted_path)}, {label(api_path)}"
    header_text, header_files = read_headers()
    failed = 0

    for pattern in patterns:
        rx = re.compile(pattern)
        for page in pages:
            flat, offsets = flattened[page]
            for m in rx.finditer(flat):
                line = offsets[m.start()]
                print(f"FAIL: {page.relative_to(CONTENT.parent)}:{line} carries a refuted claim "
                      f"-- /{pattern}/ matched {m.group(0)!r}", file=sys.stderr)
                failed += 1

    for symbol in symbols:
        en = [p for p in guide_en if mentions(text[p], symbol)]
        sr = [p for p in guide_sr if mentions(text[p], symbol)]
        mirrored = [p for p in en if mentions(text.get(p.with_name(SR), ""), symbol)]
        if not mirrored:
            where = f"EN={len(en)} SR={len(sr)}"
            if en:
                print(f"FAIL: public symbol {symbol} is documented on "
                      f"{en[0].relative_to(CONTENT.parent)} but not on its SR mirror "
                      f"({where})", file=sys.stderr)
            else:
                print(f"FAIL: public symbol {symbol} is on no dev-guide page ({where})",
                      file=sys.stderr)
            failed += 1

    for symbol in symbols:
        if not mentions(header_text, symbol):
            print(f"FAIL: documented symbol {symbol} is named by no header under "
                  f"{HEADERS} -- the guide publishes a name the library does not carry",
                  file=sys.stderr)
            failed += 1

    scope = (f"{len(pages)} pages ({len(guide_en) + len(guide_sr)} in the developer guide), "
             f"{len(patterns)} refuted patterns, {len(symbols)} symbols, "
             f"{len(header_files)} headers under {label(HEADERS)}, lists {lists}")
    if failed:
        print(f"{failed} claim/documentation failure(s) over {scope}", file=sys.stderr)
        return 1
    print(f"OK: {scope} -- no refuted claim, every listed symbol documented EN+SR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
