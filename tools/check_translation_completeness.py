#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""check_translation_completeness.py — every page exists twice, and says the same thing twice.

    usage: python3 tools/check_translation_completeness.py <content-dir>

Three independent assertions per EN/SR page pair:

  1. both files exist — an English page with no Serbian counterpart is a gap,
     not a draft, and the reverse is just as true;
  2. both carry a non-empty ``title`` and ``description`` in front matter —
     ``description`` is what a search result and a social card show, so a page
     without one is published half-blind;
  3. both cite the same set of outbound links. Absolute URLs are compared
     literally; site-relative links are compared with the language prefix
     stripped, so ``/downloads/`` and ``/sr/downloads/`` are the same link and
     a link one language carries alone is drift. Hugo's ``ref``/``relref``
     shortcodes are resolved to the path they name first, so that a page
     linking with a shortcode and its translation linking with a bare path
     are compared on where they point, not on how they spell it.

Exit status: 0 when clean, 1 on any violation, 2 when the checker could not
run at all (a bad argument), so that "could not measure" never reads as "OK".
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SR_SUFFIX = ".sr.md"
LINK_RE = re.compile(r"""(?:\]\(|href=["']|\bhref=|<)\s*((?:https?://|/)[^)\s"'<>]+)""")
FRONT_MATTER_FIELD = re.compile(r"^(title|description)\s*:\s*(.*?)\s*$")
REF_SHORTCODE = re.compile(r"""\{\{<\s*(?:rel)?ref\s+["']?([^"'>]+?)["']?\s*>\}\}""")


def front_matter(text: str) -> dict[str, str]:
    """Return the title/description fields of a YAML front-matter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = FRONT_MATTER_FIELD.match(line)
        if match:
            value = match.group(2).strip().strip("\"'").strip()
            fields[match.group(1)] = value
    return fields


def body(text: str) -> str:
    """The page below its front matter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :])
    return text


def resolve_shortcodes(text: str) -> str:
    """Rewrite {{< ref "a/b" >}} to /a/b/ so both link spellings compare equal."""

    def replace(match: re.Match[str]) -> str:
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "#")):
            return target
        target = target.split("#", 1)[0].strip("/")
        return "/" + target + "/" if target else "/"

    return REF_SHORTCODE.sub(replace, text)


def outbound_links(text: str) -> set[str]:
    text = resolve_shortcodes(text)
    links: set[str] = set()
    for raw in LINK_RE.findall(text):
        link = raw.rstrip(".,;:!?")
        if link.startswith("/"):
            # /sr/downloads/ and /downloads/ are the same link in two languages.
            if link == "/sr" or link.startswith("/sr/"):
                link = link[3:] or "/"
            link = link if link.endswith("/") or "." in link.rsplit("/", 1)[-1] else link + "/"
        links.add(link)
    return links


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <content-dir>", file=sys.stderr)
        return 2
    content = Path(argv[1])
    if not content.is_dir():
        print(f"content directory is not a directory: {content}", file=sys.stderr)
        return 2

    english = sorted(
        path
        for path in content.rglob("*.md")
        if not path.name.endswith(SR_SUFFIX)
    )
    serbian_only = sorted(
        path
        for path in content.rglob("*" + SR_SUFFIX)
        if not path.with_name(path.name[: -len(SR_SUFFIX)] + ".md").exists()
    )

    violations = 0
    pairs = 0

    for en in english:
        rel = en.relative_to(content)
        sr = en.with_name(en.name[: -len(".md")] + SR_SUFFIX)
        if not sr.exists():
            print(f"MISSING translation: {rel} has no {sr.name}")
            violations += 1
            continue
        pairs += 1

        en_text = en.read_text(encoding="utf-8")
        sr_text = sr.read_text(encoding="utf-8")

        for path, text in ((en, en_text), (sr, sr_text)):
            fields = front_matter(text)
            for field in ("title", "description"):
                if not fields.get(field):
                    print(
                        f"MISSING front-matter '{field}': "
                        f"{path.relative_to(content)}"
                    )
                    violations += 1

        en_links = outbound_links(body(en_text))
        sr_links = outbound_links(body(sr_text))
        only_en = sorted(en_links - sr_links)
        only_sr = sorted(sr_links - en_links)
        if only_en:
            print(f"LINK DRIFT {rel}: EN has, SR lacks: {only_en}")
            violations += 1
        if only_sr:
            print(f"LINK DRIFT {rel}: SR has, EN lacks: {only_sr}")
            violations += 1

    for sr in serbian_only:
        print(f"MISSING translation: {sr.relative_to(content)} has no English page")
        violations += 1

    print("---")
    if violations:
        print(f"{violations} violation(s) across {pairs} page pairs")
        return 1
    print(f"OK — {pairs} page pairs, all paired, all described, no link drift")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
