#!/usr/bin/env python3
"""Collect the inputs the triage agent needs, before the agent starts.

Runs as a deterministic `steps:` entry of .github/workflows/issue-triage.md, outside the agent's
sandbox. The agent itself has no GitHub API access; everything it reads comes from the files written here:

  issue.json      the issue: number, url, repo, title, body, author, labels, created_at, and as_of (= created_at)
  corpus.json     issues opened before as_of, for the duplicate check, each with its state at as_of
  resources.txt   `aws_<name>` for each resource and `data.aws_<name>` for each data source in website/docs/{r,d}
  plan.json       an empty plan the agent fills in (it may edit files under /tmp only)

Usage: prepare_context.py --issue ISSUE.json --corpus CORPUS.json.gz --out /tmp/gh-aw/agent
  --issue   the issue as the REST API returns it (GET /repos/{owner}/{repo}/issues/{number})
  --corpus  a gzipped JSON list like evals/data/corpus.json.gz (upstream issues, labels removed)
"""
import argparse
import glob
import gzip
import json
import os
import re
import sys
from datetime import datetime

EMPTY_PLAN = {"decision": None, "labels": [], "comment": None, "duplicate_of": [], "reason": None}


def when(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def corpus_as_of(issues, as_of):
    out = []
    for i in issues:
        if when(i["created_at"]) >= as_of:
            continue
        closed = i.get("closed_at") and when(i["closed_at"]) <= as_of
        out.append({"number": i["number"], "url": i["url"], "title": i["title"], "body": i.get("body") or "",
                    "state": "closed" if closed else "open",
                    "state_reason": ((i.get("state_reason") or "").lower() or None) if closed else None,
                    "created_at": i["created_at"]})
    return out


def resources(repo_root="."):
    names = set()
    for kind, prefix in (("r", ""), ("d", "data.")):
        for path in glob.glob(os.path.join(repo_root, f"website/docs/{kind}/*.html.markdown")):
            names.add(prefix + "aws_" + os.path.basename(path).split(".")[0])
    return sorted(names)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.issue, encoding="utf-8") as f:
        raw = json.load(f)
    # The issue text is untrusted. It is stored verbatim for the scripts; the skill tells the agent to
    # treat it as data. Only NUL bytes are removed, because they break some JSON consumers.
    issue = {"number": raw["number"], "url": raw["html_url"],
             "repo": re.sub(r"^https://api\.github\.com/repos/", "", raw["repository_url"]),
             "title": (raw.get("title") or "").replace("\x00", ""), "body": (raw.get("body") or "").replace("\x00", ""),
             "author": (raw.get("user") or {}).get("login"), "author_association": raw.get("author_association"),
             "labels": [l["name"] for l in raw.get("labels") or []],
             "created_at": raw["created_at"], "as_of": raw["created_at"]}
    with gzip.open(args.corpus, "rt", encoding="utf-8") as f:
        corpus = corpus_as_of(json.load(f), when(issue["as_of"]))
    names = resources()

    os.makedirs(args.out, exist_ok=True)

    def write(name, obj):
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
            f.write(obj if isinstance(obj, str) else json.dumps(obj, indent=2))

    write("issue.json", issue)
    write("corpus.json", {"source": os.path.basename(args.corpus), "issues": corpus})
    write("resources.txt", "\n".join(names) + "\n")
    write("plan.json", EMPTY_PLAN)
    print(f"prepared {issue['repo']}#{issue['number']}: corpus={len(corpus)} issues before {issue['as_of']}, "
          f"resources={len(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
