#!/usr/bin/env python3
"""Fetch read-only issue data from hashicorp/terraform-provider-aws for the CS467 triage-agent study.

Uses the GitHub GraphQL API through an authenticated `gh` CLI (GET-equivalent queries only;
nothing is written to GitHub). Output goes to ./raw/ next to this script's working directory.

Usage: python3 fetch_upstream.py [--only window|backlog|corpus]
"""
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

OWNER, REPO = "hashicorp", "terraform-provider-aws"
OUT = Path("raw")
WINDOW = ("2026-06-01", "2026-10-20")   # issues studied for metrics + golden-case selection
CORPUS_FROM = "2022-01-01"              # duplicate-search corpus start

ISSUE_FIELDS = """
  number title body createdAt closedAt state stateReason lastEditedAt includesCreatedEdit url
  author { login } authorAssociation
  labels(first: 30) { nodes { name } }
  comments(first: 30) { totalCount nodes { author { login } authorAssociation createdAt body } }
  timelineItems(first: 60, itemTypes: [LABELED_EVENT, UNLABELED_EVENT, CLOSED_EVENT, REOPENED_EVENT, MARKED_AS_DUPLICATE_EVENT]) {
    nodes {
      __typename
      ... on LabeledEvent { createdAt actor { login } label { name } }
      ... on UnlabeledEvent { createdAt actor { login } label { name } }
      ... on ClosedEvent { createdAt actor { login } stateReason }
      ... on ReopenedEvent { createdAt actor { login } }
      ... on MarkedAsDuplicateEvent { createdAt actor { login } canonical { ... on Issue { number } } }
    }
  }
  userContentEdits(first: 20) { nodes { editedAt createdAt diff editor { login } } }
"""

SEARCH_Q = """query($q: String!, $cursor: String) {
  rateLimit { remaining resetAt cost }
  search(query: $q, type: ISSUE, first: %d, after: $cursor) {
    issueCount pageInfo { hasNextPage endCursor }
    nodes { ... on Issue { %s } }
  }
}"""

BACKLOG_Q = """query($cursor: String) {
  rateLimit { remaining resetAt cost }
  repository(owner: "%s", name: "%s") {
    open: issues(states: OPEN) { totalCount }
    issues(states: OPEN, labels: ["needs-triage"], first: 100, after: $cursor) {
      totalCount pageInfo { hasNextPage endCursor }
      nodes { number createdAt authorAssociation labels(first: 30) { nodes { name } } }
    }
  }
}""" % (OWNER, REPO)


def gql(query, variables):
    for attempt in range(5):
        p = subprocess.run(["gh", "api", "graphql", "--input", "-"],
                           input=json.dumps({"query": query, "variables": variables}),
                           capture_output=True, text=True)
        if p.returncode == 0:
            data = json.loads(p.stdout)
            if "errors" not in data:
                rl = data["data"].get("rateLimit") or {}
                if rl.get("remaining", 9999) < 200:
                    reset = dt.datetime.fromisoformat(rl["resetAt"].replace("Z", "+00:00"))
                    wait = max(0, (reset - dt.datetime.now(dt.timezone.utc)).total_seconds()) + 5
                    print(f"  rate limit low ({rl}); sleeping {wait:.0f}s", flush=True)
                    time.sleep(wait)
                return data["data"]
            print(f"  graphql errors: {data['errors']}", file=sys.stderr)
        else:
            print(f"  gh failed ({p.returncode}): {p.stderr.strip()[:500]}", file=sys.stderr)
        time.sleep(10 * (attempt + 1))
    raise SystemExit("giving up after 5 attempts")


def search_all(q, fields, page_size):
    out, cursor = [], None
    while True:
        d = gql(SEARCH_Q % (page_size, fields), {"q": q, "cursor": cursor})["search"]
        out += [n for n in d["nodes"] if n]
        if d["issueCount"] > 1000:
            print(f"  WARNING: {q!r} has {d['issueCount']} results (>1000 search cap); narrow the range", file=sys.stderr)
        if not d["pageInfo"]["hasNextPage"]:
            return out
        cursor = d["pageInfo"]["endCursor"]
        time.sleep(1)


def date_ranges(start, end, days):
    s, e = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    while s <= e:
        t = min(s + dt.timedelta(days=days - 1), e)
        yield s.isoformat(), t.isoformat()
        s = t + dt.timedelta(days=1)


def fetch_window():
    issues = []
    for a, b in date_ranges(*WINDOW, 7):
        q = f"repo:{OWNER}/{REPO} is:issue created:{a}..{b}"
        got = search_all(q, ISSUE_FIELDS, 25)
        print(f"window {a}..{b}: {len(got)} issues", flush=True)
        issues += got
    (OUT / "window_issues.json").write_text(json.dumps(issues))


def fetch_backlog():
    nodes, cursor, totals = [], None, {}
    while True:
        r = gql(BACKLOG_Q, {"cursor": cursor})["repository"]
        totals = {"open_issues": r["open"]["totalCount"], "open_needs_triage": r["issues"]["totalCount"]}
        nodes += r["issues"]["nodes"]
        if not r["issues"]["pageInfo"]["hasNextPage"]:
            break
        cursor = r["issues"]["pageInfo"]["endCursor"]
        time.sleep(1)
    print(f"backlog: {totals}, fetched {len(nodes)}", flush=True)
    (OUT / "backlog_needs_triage.json").write_text(json.dumps({"totals": totals, "issues": nodes}))


def fetch_corpus():
    fields = "number title body createdAt closedAt stateReason"
    corpus = []
    today = dt.date.today().isoformat()
    for a, b in date_ranges(CORPUS_FROM, today, 14):
        got = search_all(f"repo:{OWNER}/{REPO} is:issue created:{a}..{b}", fields, 100)
        for n in got:
            n["body"] = (n.get("body") or "")[:2000]
        corpus += got
        print(f"corpus {a}..{b}: {len(got)} (total {len(corpus)})", flush=True)
    (OUT / "corpus_issues.json").write_text(json.dumps(corpus))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    only = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--only" else None
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    if only in (None, "backlog"):
        fetch_backlog()
    if only in (None, "window"):
        fetch_window()
    if only in (None, "corpus"):
        fetch_corpus()
    (OUT / f"meta-{only or 'all'}.json").write_text(json.dumps({
        "repo": f"{OWNER}/{REPO}", "started_at": started,
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "window": WINDOW, "corpus_from": CORPUS_FROM,
        "gh_version": subprocess.run(["gh", "--version"], capture_output=True, text=True).stdout.splitlines()[0],
    }, indent=2))
    print("done", flush=True)
