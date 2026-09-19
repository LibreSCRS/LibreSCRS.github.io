#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prove check_api_claims.py fails, and refuses, where it is supposed to.

    python3 tools/check_api_claims.selftest.py

A gate nobody has watched fail is a claim, not a check. Each case below is a
way this gate could have shipped green while proving nothing:

  * it passes a page that is honest and complete -- otherwise every later red
    is unreadable;
  * it catches a refuted sentence that WRAPS across two source lines. This is
    the whole reason the checker normalises whitespace instead of grepping:
    the sentences it was written for were wrapped on the published pages, and
    a line-oriented search over the same text found nothing. The case asserts
    both halves -- the gate sees it, and a line-oriented search does not;
  * it reads pages that are not section indexes. Rule 1 is a site-wide rule,
    and a leaf page carrying a refuted claim publishes exactly like an index
    one;
  * it catches the code examples the headers reject -- a builder chain
    finalised on the temporary it started from, and one finalised on a named
    builder, neither of which is the rvalue build() requires -- and leaves the
    idiomatic forms of the same call alone;
  * it catches a symbol documented in one language only, which is how a
    translated page pair drifts apart one symbol at a time, AND a symbol
    documented on an English page and on the Serbian side of a different one:
    counting the two languages separately would call that pair complete while
    a reader of either language finds nothing on the page their own language
    offers them;
  * it holds rule 2 to the scope its own list header states. A mention on the
    landing or security page does not document a symbol in the developer
    guide, and a gate whose message says "dev-guide page" while it searched
    the whole site is telling the reader something untrue;
  * it matches whole identifiers. Renaming a required symbol into a longer
    name that contains it is precisely the drift rule 2 exists to catch, so it
    must not satisfy it;
  * it opens the headers. Rules 1 and 2 read the site alone, and two pages that
    agree with each other say nothing about the code: a symbol renamed in the
    library and renamed on both pages would leave them both green. Rule 3
    resolves every listed symbol against the public headers, on identifier
    boundaries, and REFUSES where there is no header root to read rather than
    passing a run that opened nothing;
  * it keeps a '#' that belongs to an entry. This project's vocabulary is full
    of them, and truncating a pattern at the first '#' would either drop the
    rule or fire it on a prefix nobody wrote;
  * it REFUSES, with a distinct exit code, when either list is empty or
    missing, when there are no pages, and when there is no developer guide to
    judge. A deny-list gate over an empty deny-list passes every input; that
    is a vacuum, not a pass, and it must not be spelled the same as success;
  * its success line carries its denominators, so a later change that trims a
    list cannot produce a CI log indistinguishable from the full run;
  * it is actually wired into the workflow that deploys the site -- as a step
    that runs AND can fail its job, in a job the publish waits for, in a
    workflow a push to the published branch starts; not as a string that
    appears in the file. Deleting a step fails that case outright; nine
    further mutations of the real workflow are measured, because each of them
    leaves both commands in the file while stopping a red gate from stopping
    the publish: commenting them out, guarding them with a false condition,
    letting them fail with continue-on-error, switching off the job that owns
    them, forgiving that job's failure, writing that job's keys at another
    column and switching it off there, forgiving it there, cutting the `needs`
    that makes the publish wait for that job, and pointing the push trigger at
    a branch the site is not published from. Nothing else in this repository
    measures the workflow.

The cases that need no fixture of their own run against the lists this
repository actually ships, so the selftest measures the shipped regexes rather
than convenient stand-ins.
Exit: 0 every case behaved, 1 any case did not.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from fnmatch import fnmatch
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:      # the runner need not carry it
    yaml = None

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
GATE = TOOLS / "check_api_claims.py"
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
WIRED = [
    "python3 tools/check_api_claims.py content _middleware/include",
    "python3 tools/check_api_claims.selftest.py",
]
JOB = "::job"        # keys workflow_steps() adds; no workflow step declares them
JOB_IF = "::job-if"
JOB_COE = "::job-coe"
NOT_TRUE = {"false", "no", "off", "0"}
JOB_KEYS = ("if", "continue-on-error", "needs")
PUBLISHER = "actions/deploy-pages"   # the step that puts the built site online
PUBLISH_BRANCH = "main"              # the branch that publishing follows

# Set in main(): the stand-in header tree every case runs against, so the
# selftest needs no checkout of the library beside it and measures the gate's
# own behaviour rather than today's contents of somebody else's include tree.
HEADERS: Path | None = None


def entries(path: Path) -> list[str]:
    """Read a list the way the gate reads it (comment rule included)."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if not re.match(r"\s*#(\s|$)", line) and line.strip()
    ]


# Every symbol the shipped documented-api.txt requires, so a fixture page is
# complete without the selftest hard-coding a second copy of that list. Case 12
# asserts this count against the denominator the gate itself prints, which is
# what keeps the two readers of the file honest with each other.
SYMBOLS = entries(TOOLS / "documented-api.txt")

# One of the sentences the shipped refuted-claims.txt was written against,
# wrapped exactly where it was wrapped on the published page: inside a code
# comment, with the break falling between "no" and "byte-buffer".
WRAPPED_CLAIM = (
    "```cpp\n"
    "    // 4. Build the signing request. The engine reads from inputFile and\n"
    "    //    writes the signed payload to outputFile -- there is no\n"
    "    //    byte-buffer ingestion seam on the public API.\n"
    "```\n"
)
# What a search for that sentence in the source text would look for. It fails
# twice over: no single line carries it, and even over the whole file the gap
# between the two halves is "\n    //    ", which is not whitespace.
CLAIM_RE = re.compile(r"there is no\s+byte-buffer")

# A builder chain finalised on the temporary it started from. Every setter
# returns Builder&, and build() is rvalue-qualified, so this does not compile.
BROKEN_BUILDER = (
    "```cpp\n"
    "    auto request = lsc::Signing::SigningRequest::Builder{}\n"
    "                       .inputFile(\"document.pdf\")\n"
    "                       .format(lsc::Signing::SignatureFormat::Pades)\n"
    "                       .build();\n"
    "```\n"
)
# The other spelling the headers reject: the setters return Builder&, so a
# named builder is an lvalue too, and build() takes only an rvalue. The prose
# beside these examples calls this one idiomatic, which it is only with the
# move; the pattern has to catch it without the move all the same.
LVALUE_BUILDER = (
    "```cpp\n"
    "    lsc::Signing::SigningRequest::Builder builder;\n"
    "    builder.inputFile(\"document.pdf\");\n"
    "    auto request = builder.build();\n"
    "```\n"
)
# The two shapes that do compile, and that the same pattern must leave alone:
# a named builder moved into build(), and std::move() wrapped around the chain.
IDIOMATIC_BUILDER = (
    "```cpp\n"
    "    lsc::Signing::SigningRequest::Builder builder;\n"
    "    builder.inputFile(\"document.pdf\")\n"
    "        .format(lsc::Signing::SignatureFormat::Pades);\n"
    "    auto request = std::move(builder).build();\n"
    "\n"
    "    auto other = std::move(lsc::Signing::SigningRequest::Builder{}\n"
    "                     .inputFile(\"other.pdf\"))\n"
    "                 .build();\n"
    "```\n"
)


def write_page(path: Path, symbols: list[str], extra: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"`{symbol}` is documented here.\n\n" for symbol in symbols)
    path.write_text(
        "---\ntitle: \"Fixture\"\ndescription: \"Fixture\"\n---\n\n"
        "The engine takes the document from a file path or from a byte span.\n\n"
        + body
        + extra,
        encoding="utf-8",
    )


def pair(content: Path, section: str, en_symbols: list[str], sr_symbols: list[str],
         extra: str = "", name: str = "fixture") -> Path:
    page = content / section / name
    write_page(page / "_index.md", en_symbols, extra)
    write_page(page / "_index.sr.md", sr_symbols)
    return page


def fixture(root: Path, en_symbols: list[str], sr_symbols: list[str], extra: str = "",
            section: str = "developer-guide") -> Path:
    content = root / "content"
    pair(content, section, en_symbols, sr_symbols, extra)
    return content


def headers(root: Path, symbols: list[str], name: str = "Api.h") -> Path:
    """A stand-in for the public include tree, naming exactly these symbols.

    Rule 3 is a text search, so one line per symbol is all it needs. Writing a
    fixture instead of pointing at a real checkout is what keeps every case
    below a statement about the gate: the cases that must fail do so because
    the symbol is absent here, not because a library moved on.
    """
    tree = root / "include" / "LibreSCRS"
    tree.mkdir(parents=True, exist_ok=True)
    tree.joinpath(name).write_text(
        "#pragma once\n" + "".join(f"void {symbol}();\n" for symbol in symbols),
        encoding="utf-8",
    )
    return root / "include"


CASES = 0
RED = 0


def run(content: Path | None, **env_overrides: str) -> tuple[int, str]:
    """Run the gate once. Every invocation is one case, and a non-zero return
    over a perturbed input is a case that proved the gate red."""
    import os

    env = dict(os.environ)
    env.pop("REFUTED_FILE", None)
    env.pop("API_FILE", None)
    env.pop("API_HEADERS", None)
    if HEADERS is not None:
        env["API_HEADERS"] = str(HEADERS)
    env.update(env_overrides)
    argv = [sys.executable, str(GATE)]
    if content is not None:
        argv.append(str(content))
    done = subprocess.run(argv, capture_output=True, text=True, env=env)
    global CASES, RED
    CASES += 1
    if done.returncode != 0:
        RED += 1
    return done.returncode, done.stdout + done.stderr


def workflow_owners(lines: list[str]) -> tuple[list[str | None], dict[str, dict[str, str]]]:
    """The job each line belongs to, and the keys each job declares for itself.

    A step is only as live as the job around it, so the step walker below has
    to know which job it is inside, whether that job runs at all, and whether
    the run forgives its failure -- `continue-on-error` is a job key as well
    as a step key, and on a job it turns a red gate into a green run. `needs`
    is read in the same pass: a gate that fails a job nothing waits for stops
    no publication. All of them are collected over the whole file, because a
    job may declare a key after its steps and a reader that stopped at
    `steps:` would miss it.

    The keys are read at whatever column the job itself puts them. YAML fixes
    no indent, only agreement between siblings, so a job written four columns
    in is the same job -- and a reader that insisted on two would see a job
    with no keys at all and call the steps of a switched-off job wired.
    """
    owner: list[str | None] = [None] * len(lines)
    jobs: dict[str, dict[str, str]] = {}
    jobs_indent = job_indent = key_indent = None
    name: str | None = None
    listing: str | None = None      # a job key whose block sequence is still open
    for i, line in enumerate(lines):
        if not line.strip():
            owner[i] = name
            continue
        indent = len(line) - len(line.lstrip())
        if jobs_indent is None:
            if re.match(r"^(\s*)jobs:\s*$", line):
                jobs_indent = indent
            continue
        if indent <= jobs_indent:
            jobs_indent = job_indent = key_indent = name = listing = None
            continue
        header = re.match(r"^\s*([A-Za-z_][\w.-]*):\s*$", line)
        if header and job_indent in (None, indent) and header.group(1) != "steps":
            job_indent, key_indent, name, listing = indent, None, header.group(1), None
            jobs[name] = {}
        elif name is not None:
            if key_indent is None and indent > job_indent:
                key_indent = indent
            if indent == key_indent:
                listing = None
                field = re.match(r"^\s*([A-Za-z_][\w.-]*):\s*(.*?)\s*$", line)
                if field and field.group(1) in JOB_KEYS:
                    jobs[name][field.group(1)] = field.group(2)
                    listing = field.group(1) if not field.group(2) else None
            elif listing is not None and indent > key_indent:
                item = re.match(r"^\s*-\s*(.+?)\s*$", line)
                if item:
                    jobs[name][listing] = f"{jobs[name][listing]},{item.group(1)}".lstrip(",")
        owner[i] = name
    return owner, jobs


def workflow_jobs(workflow: str) -> dict[str, dict[str, str]]:
    """The keys each job declares for itself, comment lines out of the way."""
    lines = [line for line in workflow.splitlines() if not line.lstrip().startswith("#")]
    return workflow_owners(lines)[1]


def flow_list(value: str) -> list[str]:
    """The names in `[a, b]` or in `a`; empty when a block sequence follows."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [item.strip().strip("'\"") for item in value.split(",") if item.strip()]


def waited_for(jobs: dict[str, dict[str, str]], job: str) -> set[str]:
    """Every job `job` waits for, directly or through another job.

    A job the publishing job does not reach through `needs` runs beside it,
    not before it: its gate can go red while the publish, already started,
    puts the page online anyway.
    """
    reached: set[str] = set()
    queue = [job]
    while queue:
        for name in flow_list(jobs.get(queue.pop(), {}).get("needs", "")):
            if name not in reached:
                reached.add(name)
                queue.append(name)
    return reached


def push_filters(workflow: str) -> tuple[bool, dict[str, list[str]]]:
    """Whether the workflow triggers on push, and the branch filters on it.

    A gate that can fail the publishing job still measures nothing if the
    workflow never starts. Narrowing `on.push.branches` to a branch nobody
    pushes leaves every step, job and condition exactly as it is and takes
    the whole check off the path a published change travels.

    Only the block form (`on:` on a line of its own) is read; an `on: [push]`
    written inline reads here as no push trigger at all, which fails the case
    that calls this rather than passing it.
    """
    lines = [line for line in workflow.splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    on_indent = push_indent = None
    filters: dict[str, list[str]] = {}
    listing: str | None = None
    for line in lines:
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if on_indent is None:
            if re.match(r"""^["']?on["']?:\s*$""", stripped):
                on_indent = indent
            continue
        if indent <= on_indent:
            break
        if push_indent is None:
            if stripped == "push:":
                push_indent = indent
            continue
        if indent <= push_indent:
            break
        field = re.match(r"^([A-Za-z_][\w-]*):\s*(.*?)$", stripped)
        if field and field.group(1) in ("branches", "branches-ignore"):
            listing = field.group(1)
            filters[listing] = flow_list(field.group(2))
        elif listing is not None and stripped.startswith("- "):
            filters[listing].append(stripped[2:].strip().strip("'\""))
        elif field:
            listing = None
    return push_indent is not None, filters


def publishers(workflow: str) -> list[str]:
    """The jobs whose steps put the built site online."""
    return sorted({step[JOB] for step in workflow_steps(workflow)
                   if step.get("uses", "").startswith(PUBLISHER)})


def parses(text: str) -> tuple[bool, str]:
    """Whether a runner would accept this text, where there is a parser here.

    Every mutation below has to be a workflow GitHub would run, differing
    from the shipped one in exactly the thing being measured. One that plants
    a key where YAML allows none is rejected before any step runs, so a case
    it satisfies has measured its own mistake and not the workflow. Where
    PyYAML is absent the clause goes unmeasured, and main() says so in a line
    of its own rather than letting the omission read as a check.
    """
    if yaml is None:
        return True, "unchecked"
    try:
        yaml.safe_load(text)
    except Exception as rejected:   # noqa: BLE001 - any parse error is the answer
        return False, f"rejected ({type(rejected).__name__})"
    return True, "ok"


def job_key_indent(workflow: str, job: str) -> int:
    """The column the job's own keys sit at, read from the first of them.

    A mutation that plants a key anywhere else is not this workflow with one
    key added but a file the runner rejects, and a case measuring that would
    be measuring its own mistake.
    """
    lines = workflow.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != f"{job}:":
            continue
        header = len(line) - len(line.lstrip())
        for rest in lines[index + 1:]:
            if not rest.strip() or rest.lstrip().startswith("#"):
                continue
            indent = len(rest) - len(rest.lstrip())
            return indent if indent > header else header + 2
        return header + 2
    return 0


def workflow_steps(workflow: str) -> list[dict[str, str]]:
    """Steps the workflow declares, by indentation, each tagged with its job.

    Deliberately not a substring search over the file: a command that appears
    inside a comment, or on a step guarded by a condition, is text in a file
    and not a check that runs. The workflow this reads has no anchors, no flow
    mappings and no block scalars, so walking it by indentation needs no
    dependency the runner might not carry.

    Besides the fields it declares, every step carries the key of the job that
    owns it, that job's own condition and that job's continue-on-error, under
    three names no workflow step can use for itself.
    """
    lines = [line for line in workflow.splitlines() if not line.lstrip().startswith("#")]
    owner, jobs = workflow_owners(lines)
    steps: list[dict[str, str]] = []
    index = 0
    while index < len(lines):
        header = re.match(r"^(\s*)steps:\s*$", lines[index])
        job = owner[index]
        index += 1
        if not header:
            continue
        base = len(header.group(1))
        current: dict[str, str] | None = None
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                index += 1
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= base:
                break
            item = re.match(r"^(\s*)-\s+(.*)$", line)
            if item and len(item.group(1)) == base + 2:
                current = {JOB: job or ""}
                keys = jobs.get(job or "", {})
                if keys.get("if"):
                    current[JOB_IF] = keys["if"]
                if keys.get("continue-on-error"):
                    current[JOB_COE] = keys["continue-on-error"]
                steps.append(current)
                rest = item.group(2)
            else:
                rest = line.strip()
            field = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", rest)
            if field and current is not None:
                current[field.group(1)] = field.group(2).strip()
            index += 1
    return steps


def switched_off(value: str) -> bool:
    """True when continue-on-error takes the step out of the build.

    Only a literal false leaves the step able to fail the job. An expression
    cannot be settled by reading the file, and this assertion is that the step
    CAN fail the build -- so anything that is not provably false counts as the
    switch being on.
    """
    return value.strip().strip("'\"").lower() not in NOT_TRUE


def unconditional_runs(workflow: str) -> list[str]:
    """Commands that run, unconditionally, where they can still fail the run.

    Four shapes leave a command in the file while taking it out of the build,
    and all four are dropped here: a condition on the step, a condition on the
    job that owns it -- its steps never run -- and continue-on-error on either
    the step or the job, where the step runs, fails, and the result is
    reported green regardless. The job-level key is the one that reads most
    like wiring: the gate really does run, and really does exit 1, and nobody
    is ever told. A gate that cannot fail the build is documentation, not a
    check.
    """
    return [
        step["run"]
        for step in workflow_steps(workflow)
        if "run" in step
        and "if" not in step
        and not step.get(JOB_IF)
        and not switched_off(step.get("continue-on-error", "false"))
        and not switched_off(step.get(JOB_COE, "false"))
    ]


def comment_out(workflow: str, command: str) -> str:
    """Comment out the step that runs command, name line included."""
    out: list[str] = []
    for line in workflow.splitlines(keepends=True):
        if line.strip() == f"run: {command}":
            for i in range(len(out) - 1, -1, -1):
                if out[i].lstrip().startswith("- name:"):
                    out[i] = "#" + out[i]
                    break
            out.append("#" + line)
        else:
            out.append(line)
    return "".join(out)


def guard(workflow: str, command: str, expression: str = "false") -> str:
    """Attach a condition to the step that runs command."""
    out: list[str] = []
    for line in workflow.splitlines(keepends=True):
        if line.strip() == f"run: {command}":
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}if: {expression}\n")
        out.append(line)
    return "".join(out)


def allow_failure(workflow: str, command: str) -> str:
    """Let the step that runs command fail without failing the job."""
    out: list[str] = []
    for line in workflow.splitlines(keepends=True):
        if line.strip() == f"run: {command}":
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}continue-on-error: true\n")
        out.append(line)
    return "".join(out)


def job_key(workflow: str, job: str, key: str, value: str) -> str:
    """Declare `key: value` on the job, at the column its own keys sit at.

    Any key the job already declares under that name is dropped rather than
    shadowed: two copies of one key under one job is not what an author would
    write, every reader of it takes the last, and leaving the old one in
    place would let the mutation apply and change nothing.
    """
    out: list[str] = []
    indent = job_key_indent(workflow, job)
    inside = header_indent = 0
    for line in workflow.splitlines(keepends=True):
        current = len(line) - len(line.lstrip())
        if inside and line.strip() and current <= header_indent:
            inside = 0
        if inside and current == indent and line.strip().startswith(f"{key}:"):
            continue
        out.append(line)
        if line.strip() == f"{job}:":
            inside, header_indent = 1, current
            out.append(f"{' ' * indent}{key}: {value}\n")
    return "".join(out)


def disable_job(workflow: str, job: str, expression: str = "false") -> str:
    """Attach a condition to the job itself, so none of its steps run."""
    return job_key(workflow, job, "if", expression)


def allow_job_failure(workflow: str, job: str) -> str:
    """Let the job fail without the workflow run reporting a failure."""
    return job_key(workflow, job, "continue-on-error", "true")


def reindent_job(workflow: str, job: str) -> str:
    """Write the job's body two columns deeper than the file writes it.

    The same job, and the same steps, in a spelling YAML accepts just as
    readily. A reader that took the indent for granted instead of reading it
    would stop seeing this job's keys here -- including the ones the
    mutations above plant.
    """
    out: list[str] = []
    inside = header_indent = 0
    for line in workflow.splitlines(keepends=True):
        indent = len(line) - len(line.lstrip())
        if inside and line.strip() and indent <= header_indent:
            inside = 0
        out.append("  " + line if inside and line.strip() else line)
        if line.strip() == f"{job}:":
            inside, header_indent = 1, indent
    return "".join(out)


def drop_needs(workflow: str, job: str) -> str:
    """Cut the job's `needs`, so it no longer waits for anything.

    The gate keeps running, and keeps being able to fail its own job. What
    goes is the only thing that made a red gate hold the publish back.
    """
    out: list[str] = []
    indent = job_key_indent(workflow, job)
    inside = header_indent = dropping = 0
    for line in workflow.splitlines(keepends=True):
        current = len(line) - len(line.lstrip())
        if inside and line.strip() and current <= header_indent:
            inside = 0
        if inside and line.strip():
            if dropping and current > indent:
                continue
            dropping = 0
            if current == indent and line.strip().startswith("needs:"):
                dropping = 1
                continue
        out.append(line)
        if line.strip() == f"{job}:":
            inside, header_indent, dropping = 1, current, 0
    return "".join(out)


def narrow_push(workflow: str, branch: str = "no-such-branch") -> str:
    """Point the push trigger at a branch the site is not published from."""
    out: list[str] = []
    push_indent = None
    dropping = False
    for line in workflow.splitlines(keepends=True):
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if dropping and stripped.startswith("- "):
            continue
        dropping = False
        if push_indent is not None and stripped and indent <= push_indent:
            push_indent = None
        if push_indent is not None and re.match(r"^branches(-ignore)?:", stripped):
            out.append(f"{' ' * indent}branches: [{branch}]\n")
            dropping = True
            continue
        out.append(line)
        if stripped == "push:":
            push_indent = indent
    return "".join(out)


def main() -> int:
    global HEADERS
    failures = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        if ok:
            print(f"PASS  {name}")
        else:
            failures += 1
            print(f"FAIL  {name}{': ' + detail if detail else ''}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # Rule 3 resolves the list against a header tree, and refuses without
        # one. Every case below runs against this fixture, so the selftest
        # states what the gate does and not what some checkout happens to hold.
        HEADERS = headers(root / "shipped", SYMBOLS)

        # 1 -- an honest, complete page pair passes.
        clean = fixture(root / "clean", SYMBOLS, SYMBOLS)
        rc, clean_out = run(clean)
        check("clean fixture passes", rc == 0 and "OK: 2 pages" in clean_out,
              f"rc={rc} {clean_out.strip()}")

        # 2 -- a refuted sentence wrapped over two lines is caught, and a
        #      line-oriented search over the same file is not enough.
        wrapped = fixture(root / "wrapped", SYMBOLS, SYMBOLS, extra=WRAPPED_CLAIM)
        page_text = (wrapped / "developer-guide" / "fixture" / "_index.md").read_text(encoding="utf-8")
        line_hits = [line for line in page_text.splitlines() if CLAIM_RE.search(line)]
        check("wrapped claim hides from a line-oriented search", not line_hits, repr(line_hits))
        check(
            "wrapped claim hides from a whole-file search too",
            CLAIM_RE.search(page_text) is None,
            repr(page_text),
        )
        rc, out = run(wrapped)
        check(
            "wrapped claim fails the gate, named by file",
            rc == 1 and "carries a refuted claim" in out and "_index.md" in out,
            f"rc={rc} {out.strip()}",
        )

        # 3 -- rule 1 is site-wide. A leaf page is not a section index and is
        #      published all the same, so a refuted claim on one must fail.
        leaf = fixture(root / "leaf", SYMBOLS, SYMBOLS)
        write_page(leaf / "developer-guide" / "fixture" / "note.md", [], WRAPPED_CLAIM)
        rc, out = run(leaf)
        check(
            "refuted claim on a page that is not a section index fails",
            rc == 1 and "note.md" in out and "carries a refuted claim" in out,
            f"rc={rc} {out.strip()}",
        )

        # 4 -- a code example the headers reject is a refuted claim too, and
        #      the two idiomatic spellings of the same call are not.
        broken = fixture(root / "broken", SYMBOLS, SYMBOLS, extra=BROKEN_BUILDER)
        rc, out = run(broken)
        check(
            "a builder chain finalised on a temporary fails the gate",
            rc == 1 and "carries a refuted claim" in out and "Builder" in out,
            f"rc={rc} {out.strip()}",
        )
        lvalue = fixture(root / "lvalue", SYMBOLS, SYMBOLS, extra=LVALUE_BUILDER)
        rc, out = run(lvalue)
        check(
            "a builder chain finalised on a named builder fails the gate",
            rc == 1 and "carries a refuted claim" in out,
            f"rc={rc} {out.strip()}",
        )
        idiomatic = fixture(root / "idiomatic", SYMBOLS, SYMBOLS, extra=IDIOMATIC_BUILDER)
        rc, out = run(idiomatic)
        check(
            "the idiomatic builder spellings are left alone",
            rc == 0,
            f"rc={rc} {out.strip()}",
        )

        # 5 -- a symbol on the English page only is drift, not documentation.
        half = fixture(root / "half", SYMBOLS, SYMBOLS[:-1])
        rc, out = run(half)
        check(
            "symbol missing from the SR mirror fails",
            rc == 1 and f"public symbol {SYMBOLS[-1]} is documented on" in out
            and "but not on its SR mirror" in out and "(EN=1 SR=0)" in out,
            f"rc={rc} {out.strip()}",
        )

        # 6 -- documented on one English page and on the Serbian side of a
        #      DIFFERENT one. Both languages have it somewhere in the guide,
        #      and neither reader can find it on a page of their own language.
        split = root / "split" / "content"
        pair(split, "developer-guide", SYMBOLS, SYMBOLS[:-1], name="first")
        pair(split, "developer-guide", SYMBOLS[:-1], SYMBOLS, name="second")
        rc, out = run(split)
        check(
            "symbol whose SR hit is on another page's mirror fails",
            rc == 1 and f"public symbol {SYMBOLS[-1]} is documented on" in out
            and "but not on its SR mirror" in out and "(EN=1 SR=1)" in out,
            f"rc={rc} {out.strip()}",
        )

        # 7 -- a mention outside the developer guide does not discharge the
        #      requirement the list header states.
        elsewhere = fixture(root / "elsewhere", SYMBOLS[:-1], SYMBOLS[:-1])
        pair(elsewhere, "security", SYMBOLS[-1:], SYMBOLS[-1:])
        rc, out = run(elsewhere)
        check(
            "symbol documented only outside the developer guide fails",
            rc == 1 and f"public symbol {SYMBOLS[-1]} is on no dev-guide page (EN=0 SR=0)" in out,
            f"rc={rc} {out.strip()}",
        )

        # 8 -- a longer name containing the required one is a rename, not
        #      documentation of the required symbol.
        renamed = SYMBOLS[:-1] + [SYMBOLS[-1] + "Renamed"]
        superstring = fixture(root / "superstring", renamed, renamed)
        rc, out = run(superstring)
        check(
            "a superstring of the symbol does not document it",
            rc == 1 and f"public symbol {SYMBOLS[-1]} is on no dev-guide page (EN=0 SR=0)" in out,
            f"rc={rc} {out.strip()}",
        )

        # 9 -- a '#' inside an entry belongs to the entry. Truncating at the
        #      first one would fire /PKCS/ on every page naming PKCS#11, and
        #      an entry that begins with #include would vanish entirely.
        hashed = root / "hashed.txt"
        hashed.write_text(
            "# a whole-line comment, which IS stripped\n"
            "PKCS#11 has no session objects\n"
            "#include <LibreSCRS/Signing/SigningService.h> is not shipped\n",
            encoding="utf-8",
        )
        # Both sentences share one source line on purpose: normalise() strips a
        # leading '#' as a markdown heading marker, so a pattern beginning with
        # one matches where the '#' is not the first character of a line.
        hashclaims = fixture(
            root / "hashclaims", SYMBOLS, SYMBOLS,
            extra="The guide said PKCS#11 has no session objects, and that "
                  "#include <LibreSCRS/Signing/SigningService.h> is not shipped.\n",
        )
        rc, out = run(hashclaims, REFUTED_FILE=str(hashed))
        check(
            "a pattern carrying a '#' is neither truncated nor dropped",
            rc == 1
            and "2 refuted patterns" in out
            and "matched 'PKCS#11 has no session objects'" in out
            and "matched '#include <LibreSCRS/Signing/SigningService.h> is not shipped'" in out
            and "matched 'PKCS'" not in out,
            f"rc={rc} {out.strip()}",
        )

        # 10 -- an empty deny-list refuses; it must not read as a pass.
        empty = root / "empty.txt"
        empty.write_text("# only a comment, so no patterns at all\n", encoding="utf-8")
        rc, out = run(clean, REFUTED_FILE=str(empty))
        check(
            "empty refuted list refuses with rc=2",
            rc == 2 and "will not pass vacuously" in out,
            f"rc={rc} {out.strip()}",
        )
        rc, out = run(clean, API_FILE=str(empty))
        check(
            "empty documented-api list refuses with rc=2",
            rc == 2 and "will not pass vacuously" in out,
            f"rc={rc} {out.strip()}",
        )

        # 11 -- a missing list refuses too, and says which file.
        missing = root / "not-here.txt"
        rc, out = run(clean, REFUTED_FILE=str(missing))
        check(
            "missing refuted list refuses with rc=2",
            rc == 2 and f"{missing} is missing" in out,
            f"rc={rc} {out.strip()}",
        )

        # 12 -- no pages at all is a vacuum, not a clean site.
        bare = root / "bare" / "content"
        bare.mkdir(parents=True)
        rc, out = run(bare)
        check(
            "content directory with no pages refuses with rc=2",
            rc == 2 and "no pages under" in out,
            f"rc={rc} {out.strip()}",
        )

        # 13 -- pages but no developer guide is the same vacuum one level down:
        #       rule 2 would have nothing to search and would report every
        #       symbol missing, which reads as a content bug rather than as an
        #       unjudgeable tree.
        guideless = fixture(root / "guideless", SYMBOLS, SYMBOLS, section="security")
        rc, out = run(guideless)
        check(
            "content with no developer guide refuses with rc=2",
            rc == 2 and "developer-guide" in out and "vacuously" in out,
            f"rc={rc} {out.strip()}",
        )

        # 14 -- rule 3 opens the headers. The pages here are perfect and agree
        #       with each other in both languages; the library simply no longer
        #       carries the name they publish. Rules 1 and 2 cannot see that.
        rc, out = run(clean, API_HEADERS=str(headers(root / "dropped", SYMBOLS[:-1])))
        check(
            "a symbol no header names fails, however well the pages agree",
            rc == 1 and f"documented symbol {SYMBOLS[-1]} is named by no header" in out,
            f"rc={rc} {out.strip()}",
        )

        # 15 -- and on the header side too, a longer name that contains the
        #       symbol is the rename this rule exists to catch, not the symbol.
        widened = headers(root / "widened", SYMBOLS[:-1] + [SYMBOLS[-1] + "Renamed"])
        rc, out = run(clean, API_HEADERS=str(widened))
        check(
            "a header naming only a superstring does not carry the symbol",
            rc == 1 and f"documented symbol {SYMBOLS[-1]} is named by no header" in out,
            f"rc={rc} {out.strip()}",
        )

        # 16 -- no header root at all is the vacuum this rule is most likely to
        #       meet: a run beside no checkout of the library. It must refuse,
        #       or a check named for the headers goes green having read none.
        rc, out = run(clean, API_HEADERS=str(root / "not-checked-out" / "include"))
        check(
            "an absent header root refuses with rc=2",
            rc == 2 and "is not a directory" in out and "API_HEADERS" in out,
            f"rc={rc} {out.strip()}",
        )

        # 17 -- a header root that exists and holds no header is the same
        #       vacuum wearing the right shape, and reads as success unless it
        #       is spelled differently.
        empty_tree = root / "empty-tree" / "include"
        empty_tree.mkdir(parents=True)
        (empty_tree / "README.md").write_text("no headers here\n", encoding="utf-8")
        rc, out = run(clean, API_HEADERS=str(empty_tree))
        check(
            "a header root with no header refuses with rc=2",
            rc == 2 and "no header under" in out and "vacuously" in out,
            f"rc={rc} {out.strip()}",
        )

    # 18 -- the success line has to carry its denominators, or a later change
    #       that trims a list produces a log identical to the full run. The
    #       symbol count is also this file's agreement with the gate on how the
    #       shipped list is parsed.
    counts = re.search(
        r"OK: (\d+) pages \((\d+) in the developer guide\), (\d+) refuted patterns, "
        r"(\d+) symbols, (\d+) headers under (\S+), lists (\S+), (\S+)",
        clean_out,
    )
    check(
        "success line names pages, patterns, symbols, headers and both list files",
        counts is not None
        and int(counts.group(3)) > 0
        and int(counts.group(4)) == len(SYMBOLS)
        and int(counts.group(5)) > 0
        and counts.group(8).endswith("documented-api.txt"),
        clean_out.strip(),
    )

    # 19 -- a gate that is not wired deploys nothing. Nothing else in this
    #       repository measures the workflow, so this case does -- and it reads
    #       the steps, because a command sitting in a comment or on a step that
    #       never runs would satisfy a search of the file text.
    workflow = WORKFLOW.read_text(encoding="utf-8") if WORKFLOW.is_file() else ""
    live = unconditional_runs(workflow)
    check(
        "the gate and this selftest both run in the deploy workflow",
        all(command in live for command in WIRED),
        f"{WORKFLOW} runs {live}",
    )
    owners = sorted({s[JOB] for s in workflow_steps(workflow) if s.get("run") in WIRED})
    check(
        "both wired steps belong to one named job",
        len(owners) == 1 and owners[0] != "",
        f"jobs {owners}",
    )
    job = owners[0] if owners else ""

    # 20 -- and that job has to be one the publish waits for. A gate that goes
    #       red in a job running beside the publishing one marks the run
    #       failed after the page carrying the dead name is already online.
    def holds_the_publish(text: str) -> tuple[bool, str]:
        jobs = workflow_jobs(text)
        online = publishers(text)
        owner = sorted({s[JOB] for s in workflow_steps(text) if s.get("run") in WIRED})
        held = bool(online) and len(owner) == 1 and all(
            name == owner[0] or owner[0] in waited_for(jobs, name) for name in online
        )
        waits = sorted(set().union(*(waited_for(jobs, name) for name in online))) if online else []
        return held, f"gate in {owner}, publish {online} waits for {waits}"

    held, detail = holds_the_publish(workflow)
    check("the job that publishes waits for the job holding the gate", held, detail)

    # 21 -- and the workflow has to start on the push that publishes. Every
    #       condition above is about a run that happens; this one is about
    #       whether a push to the published branch starts one at all.
    def starts_on_publish(text: str) -> tuple[bool, str]:
        on_push, filters = push_filters(text)
        covered = on_push and (
            not filters.get("branches")
            or any(fnmatch(PUBLISH_BRANCH, pattern) for pattern in filters["branches"])
        ) and not any(
            fnmatch(PUBLISH_BRANCH, pattern) for pattern in filters.get("branches-ignore", [])
        )
        return covered, f"push={on_push} filters {filters}"

    covered, detail = starts_on_publish(workflow)
    check(f"a push to {PUBLISH_BRANCH} starts the workflow the gate sits in", covered, detail)

    # 22 -- and each way of leaving the commands in the file while stopping a
    #       red gate from stopping the publish has to read as unwired. All but
    #       the first two are shapes a search for a `run:` without an `if:`
    #       calls wired: a step that fails without failing the job, a job that
    #       never starts, a job whose failure the run forgives, either of those
    #       two written at the column the job itself uses rather than the one a
    #       reader assumed, a job the publish stops waiting for, and a trigger
    #       that no longer fires for a published change.
    def both(mutate):
        def apply(text: str) -> str:
            for command in WIRED:
                text = mutate(text, command)
            return text
        return apply

    def reindented(mutate):
        return lambda text: mutate(reindent_job(text, job), job)

    def runs_where_it_can_fail(text: str) -> tuple[bool, str]:
        live = unconditional_runs(text)
        return any(command in live for command in WIRED), f"runs {live}"

    # Each mutation is paired with the reading it has to break, so the loop
    # below asks the same question of every one of them: after this edit, does
    # the workflow still hold the publish to the gate?
    mutations = (
        (both(comment_out), "commented out", runs_where_it_can_fail),
        (both(guard), "guarded by a false condition", runs_where_it_can_fail),
        (both(allow_failure), "let through by continue-on-error", runs_where_it_can_fail),
        (lambda text: disable_job(text, job),
         "sitting in a job the workflow switched off", runs_where_it_can_fail),
        (lambda text: allow_job_failure(text, job),
         "in a job whose failure the run forgives", runs_where_it_can_fail),
        (reindented(disable_job),
         "in a job written at another column and switched off there", runs_where_it_can_fail),
        (reindented(allow_job_failure),
         "in a job written at another column and forgiven there", runs_where_it_can_fail),
        (lambda text: drop_needs(text, publishers(text)[0]),
         "in a job the publish no longer waits for", holds_the_publish),
        (narrow_push, "in a workflow no published change starts", starts_on_publish),
    )
    if yaml is None:
        print("note  PyYAML absent here: the mutations below go unchecked for YAML validity")
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "deploy.yml"
        for mutate, how, reading in mutations:
            copy.write_text(mutate(workflow), encoding="utf-8")
            broken_workflow = copy.read_text(encoding="utf-8")
            survives, detail = reading(broken_workflow)
            valid, why = parses(broken_workflow)
            check(
                f"a step {how} does not count as wired",
                broken_workflow != workflow and not survives and valid,
                f"changed={broken_workflow != workflow} {detail} yaml={why}",
            )

        # ...and the same reading must not go red on a spelling of `needs` the
        # workflow is free to use. A case that fails a workflow which does hold
        # the publish is as useless as one that passes a workflow that does not.
        listed = re.sub(rf"^(\s*)needs:\s*{re.escape(job)}\s*$",
                        rf"\g<1>needs: [{job}]", workflow, flags=re.M)
        copy.write_text(listed, encoding="utf-8")
        held_listed, detail = holds_the_publish(copy.read_text(encoding="utf-8"))
        check(
            "a `needs` written as a list still holds the publish",
            listed != workflow and held_listed,
            f"changed={listed != workflow} {detail}",
        )

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
