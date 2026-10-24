#!/usr/bin/env python3
"""Pack the raw output of fetch_upstream.py (and the docs history) into the committed data files.

Usage: python3 evals/data/pack.py <raw dir>

  window_issues.json.gz   issues opened 2026-06-01..2026-10-20 with comments, label/close timeline, edits
  corpus.json.gz          every issue opened since 2022-01-01: number, url, title, body[:1000],
                          created/closed time and close reason. Labels are dropped on purpose:
                          they were applied after the fact and would leak triage decisions.
  backlog_needs_triage.json  open issues labelled needs-triage on the fetch date (2026-10-24)
  resource_docs.json.gz   {resource name: first commit date of its website/docs page on main},
                          from `git log --no-renames --diff-filter=A --name-only -- website/docs/r website/docs/d`
                          (a renamed page counts as added on the rename date)
"""
import gzip
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

raw = Path(sys.argv[1])
out = Path(__file__).parent


def dump_gz(obj, name):
    with gzip.open(out / name, "wt", encoding="utf-8") as f:
        json.dump(obj, f, separators=(",", ":"))


dump_gz(json.load(open(raw / "window_issues.json")), "window_issues.json.gz")

corpus = [{"number": i["number"], "url": f"https://github.com/hashicorp/terraform-provider-aws/issues/{i['number']}", "title": i["title"], "body": (i.get("body") or "")[:1000],
           "created_at": i["createdAt"], "closed_at": i.get("closedAt"), "state_reason": i.get("stateReason")}
          for i in json.load(open(raw / "corpus_issues.json"))]
dump_gz(sorted(corpus, key=lambda c: c["number"]), "corpus.json.gz")

shutil.copy(raw / "backlog_needs_triage.json", out / "backlog_needs_triage.json")

docs, when = {}, None
for line in open(raw / "docs_added.txt", encoding="utf-8"):
    line = line.strip()
    if line.startswith("COMMIT "):
        when = datetime.fromisoformat(line[7:]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    m = re.match(r"website/docs/([rd])/(.+?)\.html\.(?:markdown|md)$", line)
    if m and when:
        name = ("data." if m.group(1) == "d" else "") + "aws_" + m.group(2)
        docs[name] = min(docs.get(name, when), when)   # git log is newest first; keep the oldest
dump_gz(docs, "resource_docs.json.gz")
print(f"window={len(json.load(open(raw / 'window_issues.json')))} corpus={len(corpus)} resource_docs={len(docs)}")
