#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Hold the download pages to the generated data, and the data to its sources.

    check_download_claims.py <content-dir> <data/artifacts.json> \
        --repos-root <dir> --ref <tag>

Two pages that agree with each other say nothing about what is published: a
claim equally wrong in both languages passes the translation check perfectly.
That is how the downloads page came to say this release ships no Debian or RPM
packages while the middleware publishes them for three distributions. So:

  1. Every asset NAME a page in scope prints -- a file name ending in .deb,
     .rpm, .AppImage, .dmg, .orig.tar.gz, .cdx.json, .sigstore.json, or
     SHA256SUMS -- must fall under a glob some repository declares. A bare
     extension (`.deb`) is a word, not an asset name, and is not judged.
  2. Every glob a repository declares must be rendered on a page in scope:
     by the release-assets shortcode for that repository, or by a literal it
     covers. A published asset the pages never mention is the other half of
     the same lie.
  3. The data is fresh: each of the seven ci/release-assets.txt files under
     <repos-root>/<Repository>/ hashes to the source_sha256 recorded for it --
     by content, never by timestamp, since a checkout keeps no mtime -- and
     the tag the data names is the tag being judged.

Scope: pages under content/downloads/ and content/user-guide/, both languages.
News posts describe the releases they announce and are not held to this one.

Exit: 0 all three hold; 1 one does not; 2 cannot judge -- no data file, no page
in scope, fewer than seven sources, a tag the data names that its repository
does not have, or a ref that is not a tag at all ("cannot judge a page about a
release that does not exist yet", which is the expected answer on every local
run before the release is tagged). 2 is never a pass.
"""
import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPOS = ["LibreMiddleware", "LibreAgent", "LibreLinux", "LibreCelik",
         "LibreKDE", "LibreDarwin", "LibreMac"]
SCOPE = ["downloads", "user-guide"]
SHORTCODE = re.compile(r'\{\{<\s*release-assets\s+repo="([^"]+)"\s*>\}\}')
ASSET = re.compile(
    r"(?<![\w.-])([A-Za-z0-9_+~*.-]*?(?:\.deb|\.rpm|\.AppImage|\.dmg|\.orig\.tar\.gz"
    r"|\.cdx\.json|\.sigstore\.json)|SHA256SUMS)(?![\w.])")

fails = []
unjudged = []


def fail(msg):
    fails.append(msg)
    print(f"FAIL: {msg}")


def cannot(msg):
    unjudged.append(msg)
    print(f"CANNOT JUDGE: {msg}")


def overlaps(literal, glob):
    return fnmatch.fnmatchcase(literal, glob) or fnmatch.fnmatchcase(glob, literal)


def is_tag(repo, ref):
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet",
                           f"refs/tags/{ref}"], capture_output=True).returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("content", type=Path)
    ap.add_argument("data", type=Path)
    ap.add_argument("--repos-root", required=True, type=Path)
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()

    try:
        doc = json.loads(a.data.read_text(encoding="utf-8"))
        entries = {e["repo"]: e for e in doc["repos"]}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FATAL: {a.data} is not the generated data file ({exc}) -- cannot judge",
              file=sys.stderr)
        return 2

    pages = sorted(p for d in SCOPE for p in (a.content / d).rglob("*.md")) \
        if a.content.is_dir() else []
    if not pages:
        print(f"FATAL: no page under {', '.join(a.content.as_posix() + '/' + d for d in SCOPE)}"
              " -- a scan that read nothing is unmeasured, not clean", file=sys.stderr)
        return 2

    # --- rules 1 and 2: the pages against the data --------------------------
    rendered, literals = set(), []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        rendered.update(SHORTCODE.findall(text))
        for n, line in enumerate(text.splitlines(), 1):
            for m in ASSET.finditer(line):
                if not m.group(1).startswith("."):
                    literals.append((page, n, m.group(1)))
    for name in rendered - set(entries):
        fail(f"a page renders release-assets for {name}, which the data does not carry")
    all_globs = [(r, g["glob"]) for r, e in entries.items() for g in e.get("assets", [])]
    for page, n, lit in literals:
        if not any(overlaps(lit, g) for _, g in all_globs):
            fail(f"{page}:{n} names {lit}, which no repository declares it publishes")
    for repo, glob in all_globs:
        if repo in rendered:
            continue
        if not any(overlaps(lit, glob) for _, _, lit in literals):
            fail(f"{repo} publishes {glob}, and no page in scope renders it")

    # --- rule 3: the data against its sources --------------------------------
    missing = [r for r in REPOS if not (a.repos_root / r / "ci" / "release-assets.txt").is_file()]
    if missing:
        cannot(f"{len(REPOS) - len(missing)} of {len(REPOS)} sources under {a.repos_root}; "
               f"missing: {', '.join(missing)}")
    present = [r for r in REPOS if r not in missing]
    if present and not all(is_tag(a.repos_root / r, a.ref) for r in present):
        cannot(f"{a.ref} is not a tag in every repository -- cannot judge a page about "
               f"a release that does not exist yet")
    else:
        if doc.get("provisional"):
            fail("the data is provisional (generated over a ref that is not a tag); "
                 "regenerate it over the release tags")
        for r in present:
            e = entries.get(r)
            if e is None:
                fail(f"the data carries no entry for {r}")
                continue
            if not is_tag(a.repos_root / r, e["tag"]):
                cannot(f"the data names tag {e['tag']} for {r}, which that repository does not have")
                continue
            if e["tag"] != a.ref:
                fail(f"the data documents {r} at {e['tag']}, and this run judges {a.ref}")
            got = hashlib.sha256((a.repos_root / r / "ci" / "release-assets.txt")
                                 .read_bytes()).hexdigest()
            if got != e.get("source_sha256"):
                fail(f"{r}: ci/release-assets.txt hashes to {got[:12]}, the data records "
                     f"{str(e.get('source_sha256'))[:12]} -- the data is stale; run "
                     f"tools/gen-artifacts-data.py")

    if fails:
        return 1
    if unjudged:
        return 2
    print(f"check_download_claims: {len(pages)} page(s), {len(literals)} asset name(s), "
          f"{len(all_globs)} declared glob(s), {len(present)} source(s) at {a.ref} -- all hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
