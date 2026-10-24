#!/usr/bin/env python3
"""Independent cross-check of results.md, from the same frozen snapshot. Writes crosscheck.md next to this file.

Written separately from compute_metrics.py: a maintainer here is ONLY a comment author whose association is
OWNER/MEMBER/COLLABORATOR, so where the two methods agree the result does not depend on either inference.
It also measures what results.md does not: the weekend effect, how concentrated triage is, and how often a
reporter gets a written reply at all.

Usage: python3 evals/metrics/crosscheck_metrics.py
"""
import collections
import gzip
import json
import statistics
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE.parent / "data"
FETCHED = datetime.fromisoformat(json.loads((DATA / "fetch_meta.json").read_text())["started_at"])
MAINT = {"OWNER", "MEMBER", "COLLABORATOR"}
BOTS = {"github-actions", "dosubot", "hashicorp-cla", "hashicorp-tsccr"}


def t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def days(a, b):
    return (b - a).total_seconds() / 86400


def who(node, key):
    return ((node.get(key) or {}).get("login")) or ""


def is_bot(login):
    return not login or login.endswith("[bot]") or login in BOTS


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def weekend(created):
    # Friday noon UTC to Sunday midnight UTC: roughly when the US-based maintainers stop for the weekend.
    return created.weekday() >= 5 or (created.weekday() == 4 and created.hour >= 12)


issues = json.load(gzip.open(DATA / "window_issues.json.gz"))
rep = [i for i in issues if i["authorAssociation"] in {"NONE", "CONTRIBUTOR"}]

first_comment, removed, removers = {}, {}, collections.Counter()
for i in rep:
    author, created = who(i, "author"), t(i["createdAt"])
    ts = [t(c["createdAt"]) for c in i["comments"]["nodes"]
          if c["authorAssociation"] in MAINT and not is_bot(who(c, "author")) and who(c, "author") != author]
    if ts:
        first_comment[i["number"]] = days(created, min(ts))
    un = [e for e in i["timelineItems"]["nodes"]
          if e["__typename"] == "UnlabeledEvent" and e["label"]["name"] == "needs-triage"]
    if un:
        removed[i["number"]] = days(created, min(t(e["createdAt"]) for e in un))
        removers.update(who(e, "actor") for e in un)

split = collections.defaultdict(list)
for i in rep:
    if i["number"] in removed:
        split["Friday noon to Sunday" if weekend(t(i["createdAt"])) else "Monday to Friday noon"].append(removed[i["number"]])
assert sum(len(v) for v in split.values()) == len(removed)

out = []
w = out.append
fc = list(first_comment.values())
w("# Cross-check: reporter waits, from comment author association only\n")
w(f"Snapshot fetched {FETCHED:%Y-%m-%d %H:%M} UTC; {len(rep)} reporter issues of {len(issues)} opened 2026-06-01 to "
  f"2026-10-20. Regenerate with `python3 evals/metrics/crosscheck_metrics.py`.\n")
w("## 1. Time until `needs-triage` is removed, by when the issue was opened (UTC)\n")
w("| opened | issues | median days | 90th percentile days |")
w("|---|---|---|---|")
w(f"| any time | {len(removed)} | {statistics.median(removed.values()):.2f} | {q(removed.values(), .9):.1f} |")
for k in ("Monday to Friday noon", "Friday noon to Sunday"):
    w(f"| {k} | {len(split[k])} | {statistics.median(split[k]):.2f} | {q(split[k], .9):.1f} |")
w("\n## 2. Who removes `needs-triage`\n")
total = sum(removers.values())
for login, n in removers.most_common():
    w(f"- `{login}`: {n}/{total} ({100 * n / total:.0f}%)")
w(f"\n## 3. Written replies from a maintainer\n")
w(f"- Reporter issues with at least one maintainer comment: {len(fc)}/{len(rep)} ({100 * len(fc) / len(rep):.0f}%).")
w(f"- Days to the first one, where it happened: median {statistics.median(fc):.2f}, 75th percentile "
  f"{q(fc, .75):.1f}, 90th percentile {q(fc, .9):.1f}.")
silent = sum(1 for n in removed if not (n in first_comment and first_comment[n] <= 7))
w(f"- Triaged (`needs-triage` removed) with no maintainer comment within 7 days: {silent}/{len(removed)}.\n")
w("## 4. Limits\n")
w("- Association depends on what the API shows the fetching account. Eight accounts commented as MEMBER or "
  "COLLABORATOR, including every person who removed `needs-triage`, but a maintainer shown as CONTRIBUTOR is missed.")
w("- The weekend cut is in UTC; the maintainers' own time zones are not known.")
w("- Comments beyond the first 30 per issue were not fetched (2 issues had more).")

(HERE / "crosscheck.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
