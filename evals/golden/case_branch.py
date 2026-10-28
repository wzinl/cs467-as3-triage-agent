#!/usr/bin/env python3
"""Make the branch a golden case runs on: eval/<case>, from the current commit, with the upstream files the
agent reads imported from the case's upstream_commit and, for a case with planted issues, those issues added
to evals/data/corpus.json.gz. Dispatching the workflow on this branch with the case's as_of shows the agent
the forms, labels, release notes, resource docs and earlier issues of the day the issue was opened.
The branch is committed, not pushed. CI does not run on eval/ branches.
Usage: python3 evals/golden/case_branch.py CASE_ID   (from a clean checkout of main)
"""
import gzip
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "evals/data/corpus.json.gz"


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    found = list((ROOT / "evals/golden/cases").glob(f"*/{sys.argv[1]}/input.json"))
    if not found:
        sys.exit(f"no case {sys.argv[1]}")
    case = json.loads(found[0].read_text())
    if git("status", "--porcelain"):
        sys.exit("the working tree has changes; commit or stash them first")
    branch = f"eval/{case['id']}"
    git("switch", "-c", branch)
    subprocess.run([str(ROOT / "sandbox/import_upstream.sh"), case["upstream_commit"]], check=True)
    if case["corpus_extra"]:
        corpus = json.loads(gzip.decompress(CORPUS.read_bytes()))
        corpus = sorted(corpus + case["corpus_extra"], key=lambda c: c["number"])
        # mtime=0 so the same case always gives the same file
        CORPUS.write_bytes(gzip.compress(json.dumps(corpus, separators=(",", ":")).encode(), mtime=0))
    git("add", "-A")
    git("commit", "-q", "-m", f"Evaluation branch for {case['id']}: upstream files at {case['upstream_commit'][:9]}"
        + (", planted issues in the corpus" if case["corpus_extra"] else ""))
    print(f"{branch} ready. Push it, post the case's `posted` title and body, then dispatch:\n"
          f"  gh workflow run issue-triage.lock.yml --ref {branch} -f issue_number=N -f as_of={case['as_of']}")


if __name__ == "__main__":
    main()
