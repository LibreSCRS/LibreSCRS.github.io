#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Generate data/artifacts.json from what each repository declares it publishes.

The downloads page used to list asset names by hand, in two languages, and said
the release ships no Debian or RPM packages while the middleware publishes them
for three distributions. The list is now generated from ci/release-assets.txt,
the one file per repository that says what a tag of it publishes, and rendered
by the release-assets shortcode.

It reads each file AT THE REF the page documents, never from a branch: the site
documents a release, and the first commit on a default branch after a tag that
changes the asset set would otherwise rewrite the download page of the release
before it. Each entry carries the sha256 of the bytes it was read from, so
tools/check_download_claims.py can tell a stale data file from a fresh one by
content rather than by timestamp -- a checkout does not preserve mtimes.

  gen-artifacts-data.py --repos-root <dir> --ref <tag> [--out data/artifacts.json]

<dir> holds the seven repositories side by side, each under its own name. A ref
that is not a tag in every one of them is recorded, and the file is marked
provisional: it has to be regenerated over the real tags before the site that
renders it is published.

Exit: 0 written; 2 could not generate -- a repository missing, the ref or the
file absent from one, or a malformed declaration. Nothing is written then.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPOS = ["LibreMiddleware", "LibreAgent", "LibreLinux", "LibreCelik",
         "LibreKDE", "LibreDarwin", "LibreMac"]
DECLARATION = "ci/release-assets.txt"


def fatal(msg):
    print(f"FATAL: {msg} -- nothing written", file=sys.stderr)
    sys.exit(2)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, check=False)


def parse(text, where):
    assets, seen = [], set()
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split(None, 1)
        if len(fields) != 2:
            fatal(f"{where}:{n} has a glob and no description: {line}")
        glob, description = fields[0], fields[1].strip()
        if glob in seen:
            fatal(f"{where}:{n} declares {glob} twice")
        seen.add(glob)
        assets.append({"glob": glob, "description": description})
    return assets


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repos-root", required=True, type=Path)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parent.parent / "data" / "artifacts.json")
    args = ap.parse_args()

    entries, provisional = [], False
    for name in REPOS:
        repo = args.repos_root / name
        if not repo.exists() or git(repo, "rev-parse", "--git-dir").returncode != 0:
            fatal(f"{repo} is not a checkout of {name}")
        if git(repo, "rev-parse", "--verify", "--quiet", f"refs/tags/{args.ref}").returncode != 0:
            provisional = True
        shown = git(repo, "show", f"{args.ref}:{DECLARATION}")
        if shown.returncode != 0:
            fatal(f"{name} has no {DECLARATION} at {args.ref}: "
                  f"{shown.stderr.decode(errors='replace').strip()}")
        data = shown.stdout
        entries.append({
            "repo": name,
            "tag": args.ref,
            "assets": parse(data.decode("utf-8"), f"{name}@{args.ref}:{DECLARATION}"),
            "source_sha256": hashlib.sha256(data).hexdigest(),
        })

    doc = {
        "generated_by": "tools/gen-artifacts-data.py -- do not edit",
        "provisional": provisional,
        "repos": entries,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    note = " (PROVISIONAL: the ref is not a tag everywhere -- regenerate over the release tags)" if provisional else ""
    print(f"gen-artifacts-data: {len(entries)} repositories at {args.ref} -> {args.out}{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
