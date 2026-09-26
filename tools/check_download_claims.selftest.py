#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prove check_download_claims.py fails, and refuses, where it is supposed to.

    python3 tools/check_download_claims.selftest.py

Each case builds seven throwaway repositories, each tagged, each declaring a
release-asset set; data/artifacts.json is written by the real generator over
them, so the gate is judged against the data it will really be given. The
most likely failure of a gate like this is a vacuum pass, so the refusals are
asserted as exit 2 and the green case comes first.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUBJECT = HERE / "check_download_claims.py"
GENERATOR = HERE / "gen-artifacts-data.py"
REPOS = ["LibreMiddleware", "LibreAgent", "LibreLinux", "LibreCelik",
         "LibreKDE", "LibreDarwin", "LibreMac"]
DECL = {
    "LibreMiddleware": "*.debian13.deb   packages for Debian 13\nSHA256SUMS   checksums\n",
    "LibreAgent": "libreagent_*.orig.tar.gz   the source tarball\n",
    "LibreLinux": "librelinux_*.orig.tar.gz   the source tarball\n",
    "LibreCelik": "LibreCelik-*-x86_64.AppImage   the Linux build\n",
    "LibreKDE": "librekde_*.orig.tar.gz   the source tarball\n",
    "LibreDarwin": "",
    "LibreMac": "",
}
PAGE = """---
title: "Downloads"
description: "d"
---

{{< release-assets repo="LibreMiddleware" >}}

Agent: {{< release-assets repo="LibreAgent" >}} {{< release-assets repo="LibreLinux" >}}

{{< release-assets repo="LibreKDE" >}}

Run `./LibreCelik-*.AppImage` after `chmod +x LibreCelik-*.AppImage`.
{{< release-assets repo="LibreCelik" >}}

A `.deb` is a generic word, not an asset name.
"""

CASES = 0
RED = 0
failures = 0


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t",
                    "-c", "commit.gpgSign=false", "-c", "tag.gpgSign=false", *args],
                   check=True, capture_output=True)


def world(root, tag="5.0.0", data_ref=None):
    """Seven tagged repositories, a content tree, and generated data."""
    repos = root / "repos"
    for name in REPOS:
        r = repos / name
        (r / "ci").mkdir(parents=True)
        (r / "ci" / "release-assets.txt").write_text(
            "# SPDX-License-Identifier: LGPL-2.1-or-later\n" + DECL[name], encoding="utf-8")
        git(r, "init", "-q", ".")
        git(r, "add", "-A")
        git(r, "commit", "-q", "-m", "t")
        git(r, "tag", tag)
    content = root / "content" / "downloads"
    content.mkdir(parents=True)
    (content / "_index.md").write_text(PAGE, encoding="utf-8")
    data = root / "artifacts.json"
    subprocess.run([sys.executable, str(GENERATOR), "--repos-root", str(repos),
                    "--ref", data_ref or tag, "--out", str(data)], check=True, capture_output=True)
    return repos, root / "content", data


def run(repos, content, data, ref="5.0.0", github_ref=None):
    # The runner's own GITHUB_REF never reaches the subject: the branch mode
    # follows from it, so each case sets it, or leaves it unset, on purpose.
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_REF"}
    if github_ref is not None:
        env["GITHUB_REF"] = github_ref
    p = subprocess.run([sys.executable, str(SUBJECT), str(content), str(data),
                        "--repos-root", str(repos), "--ref", ref],
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def case(name, want, got, out, needle=None):
    global CASES, RED, failures
    CASES += 1
    if want != 0:
        RED += 1
    ok = got == want and (needle is None or needle in out)
    print(f"{'ok  ' if ok else 'FAIL'}  {name} (rc={got}, want {want})")
    if not ok:
        failures += 1
        print("\n".join("  | " + l for l in out.splitlines()))


def main():
    if not SUBJECT.exists():
        print(f"FAIL  subject missing: {SUBJECT} does not exist -- nothing to prove")
        return 1
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR", "/var/tmp")) as t:
        base = Path(t)

        def fresh(n, data_ref=None):
            d = base / n
            d.mkdir()
            return world(d, data_ref=data_ref)

        # D0 -- everything agrees: the page renders every repository that
        # publishes, names only assets that exist, and the data is fresh.
        repos, content, data = fresh("d0")
        rc, out = run(repos, content, data)
        case("D0 consistent page, data and sources", 0, rc, out)

        # D1 -- the page names an asset nobody publishes.
        repos, content, data = fresh("d1")
        page = content / "downloads" / "_index.md"
        before = page.read_text(encoding="utf-8")
        page.write_text(before + "\nGet `librescrs-agent_5.0.0-1_amd64.deb` too.\n", encoding="utf-8")
        assert page.read_text(encoding="utf-8") != before
        rc, out = run(repos, content, data)
        case("D1 page names an asset no repository declares", 1, rc, out,
             "librescrs-agent_5.0.0-1_amd64.deb")

        # D2 -- a repository publishes and no page renders it.
        repos, content, data = fresh("d2")
        page = content / "downloads" / "_index.md"
        before = page.read_text(encoding="utf-8")
        page.write_text(before.replace('{{< release-assets repo="LibreKDE" >}}', ""), encoding="utf-8")
        assert page.read_text(encoding="utf-8") != before
        rc, out = run(repos, content, data)
        case("D2 declared assets rendered on no page", 1, rc, out, "librekde_*.orig.tar.gz")

        # D3 -- fewer than seven sources: nothing to hold the data against.
        repos, content, data = fresh("d3")
        shutil.rmtree(repos / "LibreMac")
        rc, out = run(repos, content, data)
        case("D3 fewer than seven sources", 2, rc, out, "LibreMac")

        # D4 -- a source changed after the data was generated.
        repos, content, data = fresh("d4")
        f = repos / "LibreAgent" / "ci" / "release-assets.txt"
        f.write_text(f.read_text(encoding="utf-8") + "*.sigstore.json   bundle\n", encoding="utf-8")
        rc, out = run(repos, content, data)
        case("D4 source_sha256 does not match the source", 1, rc, out, "LibreAgent")

        # D5 -- the data names a tag the repository does not have.
        repos, content, data = fresh("d5")
        doc = json.loads(data.read_text(encoding="utf-8"))
        doc["repos"][2]["tag"] = "9.9.9"
        data.write_text(json.dumps(doc), encoding="utf-8")
        rc, out = run(repos, content, data)
        case("D5 the data's tag does not exist in the repository", 2, rc, out, "9.9.9")

        # D6 -- a ref that is not a tag: the release does not exist yet. This
        # is the answer on every local run before the tags are pushed.
        repos, content, data = fresh("d6")
        rc, out = run(repos, content, data, ref="HEAD")
        case("D6 a ref that is not a tag is unjudged", 2, rc, out,
             "cannot judge a page about a release that does not exist yet")

        # D7 -- no data file at all.
        repos, content, data = fresh("d7")
        data.unlink()
        rc, out = run(repos, content, data)
        case("D7 no data file", 2, rc, out)

        # D8 -- no page in scope: a vacuum, not a pass.
        repos, content, data = fresh("d8")
        shutil.rmtree(content / "downloads")
        rc, out = run(repos, content, data)
        case("D8 no page in scope", 2, rc, out)

        # D9 -- data generated over a ref that was not a tag, then judged as
        # if it were the release.
        repos, content, data = fresh("d9")
        doc = json.loads(data.read_text(encoding="utf-8"))
        doc["provisional"] = True
        data.write_text(json.dumps(doc), encoding="utf-8")
        rc, out = run(repos, content, data)
        case("D9 provisional data judged against a release", 1, rc, out, "provisional")

        # --- provisional data (generated over HEAD), by the ref that runs it --
        branch = "refs/heads/ci/5.0"

        # D10 -- on a branch the claims are judged against the lists checked
        # out, and a consistent page passes.
        repos, content, data = fresh("d10", data_ref="HEAD")
        rc, out = run(repos, content, data, ref="HEAD", github_ref=branch)
        case("D10 provisional data on a branch: consistent claims pass", 0, rc, out,
             "rules 1 and 2 hold")

        # D11 -- ... and a wrong claim fails there, not "cannot judge".
        repos, content, data = fresh("d11", data_ref="HEAD")
        page = content / "downloads" / "_index.md"
        before = page.read_text(encoding="utf-8")
        page.write_text(before + "\nGet `librescrs-agent_5.0.0-1_amd64.deb` too.\n", encoding="utf-8")
        assert page.read_text(encoding="utf-8") != before
        rc, out = run(repos, content, data, ref="HEAD", github_ref=branch)
        case("D11 provisional data on a branch: a wrong claim fails", 1, rc, out,
             "librescrs-agent_5.0.0-1_amd64.deb")

        # D12 -- the lists, not the data, are what a branch run judges: a glob
        # a repository declares on its checkout and no page renders fails.
        repos, content, data = fresh("d12", data_ref="HEAD")
        f = repos / "LibreDarwin" / "ci" / "release-assets.txt"
        f.write_text(f.read_text(encoding="utf-8") + "LibreDarwin-*.dmg   the build\n",
                     encoding="utf-8")
        rc, out = run(repos, content, data, ref="HEAD", github_ref=branch)
        case("D12 provisional data on a branch: an unrendered declared glob fails", 1, rc, out,
             "LibreDarwin-*.dmg")

        # D13 -- the deploy path: on main provisional data stays unjudged.
        repos, content, data = fresh("d13", data_ref="HEAD")
        rc, out = run(repos, content, data, ref="HEAD", github_ref="refs/heads/main")
        case("D13 provisional data on main is unjudged", 2, rc, out,
             "cannot judge a page about a release that does not exist yet")

        # D14 -- and so is every run the runner did not start on a branch: a
        # pull request, or a local run with no GITHUB_REF at all.
        repos, content, data = fresh("d14", data_ref="HEAD")
        rc, out = run(repos, content, data, ref="HEAD", github_ref="refs/pull/1/merge")
        case("D14 provisional data on a pull request is unjudged", 2, rc, out)
        rc, out = run(repos, content, data, ref="HEAD")
        case("D14 provisional data with no GITHUB_REF is unjudged", 2, rc, out)

        # D15 -- tagged data on a branch is judged in full, freshness included.
        repos, content, data = fresh("d15")
        rc, out = run(repos, content, data, github_ref=branch)
        case("D15 tagged data on a branch judges normally", 0, rc, out, "all hold")
        f = repos / "LibreAgent" / "ci" / "release-assets.txt"
        f.write_text(f.read_text(encoding="utf-8") + "*.sigstore.json   bundle\n", encoding="utf-8")
        rc, out = run(repos, content, data, github_ref=branch)
        case("D15 tagged data on a branch: a stale source still fails", 1, rc, out, "LibreAgent")

        # D16 -- only PROVISIONAL data earns the branch mode: tagged data run
        # over a ref that is not a tag is still a release not judged.
        repos, content, data = fresh("d16")
        rc, out = run(repos, content, data, ref="HEAD", github_ref=branch)
        case("D16 tagged data over a non-tag ref on a branch is unjudged", 2, rc, out,
             "cannot judge a page about a release that does not exist yet")

        # D17 -- and only before the release exists: provisional data once the
        # tags are there fails on a branch exactly as it does on main.
        repos, content, data = fresh("d17")
        doc = json.loads(data.read_text(encoding="utf-8"))
        doc["provisional"] = True
        data.write_text(json.dumps(doc), encoding="utf-8")
        rc, out = run(repos, content, data, github_ref=branch)
        case("D17 provisional data after the tags fails on a branch", 1, rc, out, "provisional")

    print("---")
    if failures:
        print(f"{failures} case(s) did not behave as required")
        print(f"selftest: {CASES} cases, {RED} red-proved")
        return 1
    print("OK: the gate passes what it should and refuses what it must")
    print(f"selftest: {CASES} cases, {RED} red-proved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
