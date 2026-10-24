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
    # Friday noon UTC to the end of Sunday UTC. The maintainers' time zones are unknown, so this cut is a convention.
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

dup = sum(1 for i in rep if i["stateReason"] == "DUPLICATE"
          or any(e["__typename"] == "MarkedAsDuplicateEvent" for e in i["timelineItems"]["nodes"]))
svc_had, svc_hit, svc_removed, svc_adders = 0, 0, 0, collections.Counter()
for i in rep:
    ev = i["timelineItems"]["nodes"]
    if any(e["__typename"] == "LabeledEvent" and e["label"]["name"].startswith("service/") for e in ev):
        svc_had += 1
        gone = [e for e in ev if e["__typename"] == "UnlabeledEvent" and e["label"]["name"].startswith("service/")
                and not is_bot(who(e, "actor")) and who(e, "actor") != who(i, "author")]
        svc_hit, svc_removed = svc_hit + bool(gone), svc_removed + len(gone)
        for g in gone:   # who had added the label that a person then removed
            added = [e for e in ev if e["__typename"] == "LabeledEvent" and e["label"]["name"] == g["label"]["name"]
                     and e["createdAt"] <= g["createdAt"]]
            svc_adders[who(added[-1], "actor") if added else "(not in the fetched events)"] += 1

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
w("Author association of all issues in the window: "
  + ", ".join(f"{k} {v}" for k, v in collections.Counter(i["authorAssociation"] for i in issues).most_common()) + ".\n")
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
w(f"\n{len(removers)} accounts removed `needs-triage`, {sum(map(is_bot, removers))} of them a bot.")
w(f"\n## 3. Written replies from a maintainer\n")
w(f"- Reporter issues with at least one maintainer comment: {len(fc)}/{len(rep)} ({100 * len(fc) / len(rep):.0f}%).")
w(f"- Days to the first one, where it happened: median {statistics.median(fc):.2f}, 75th percentile "
  f"{q(fc, .75):.1f}, 90th percentile {q(fc, .9):.1f}.")
silent = sum(1 for n in removed if not (n in first_comment and first_comment[n] <= 7))
w(f"- Triaged (`needs-triage` removed) with no maintainer comment within 7 days: {silent}/{len(removed)}.\n")
w("## 4. Figures results.md also reports, recomputed with separate code\n")
w(f"- Closed as duplicate or marked duplicate: {dup}/{len(rep)} ({100 * dup / len(rep):.0f}%).")
w(f"- Issues that ever had a `service/*` label: {svc_had}. A person other than the author removed {svc_removed} of "
  f"those labels, on {svc_hit}/{svc_had} ({100 * svc_hit / svc_had:.0f}%) of them.")
w("- Who had added the removed labels: " + ", ".join(f"`{k}` {v}" for k, v in svc_adders.most_common())
  + ". `github-actions` is the account upstream's regex labeler (`triage.yml`) runs as.\n")
w("## 5. Limits\n")
commenters = {who(c, "author") for i in issues for c in i["comments"]["nodes"]
              if c["authorAssociation"] in MAINT and not is_bot(who(c, "author"))}
people = {r for r in removers if not is_bot(r)}
truncated = sum(1 for i in issues if i["comments"]["totalCount"] > len(i["comments"]["nodes"]))
newest = days(max(t(i["createdAt"]) for i in issues), FETCHED)
w(f"- {len(commenters)} accounts commented as OWNER, MEMBER or COLLABORATOR. "
  f"{len(people & commenters)} of the {len(people)} people who removed `needs-triage` are among them. A maintainer "
  "the API reports with another association would be missed here.")
w("- The weekend cut is in UTC; the maintainers' own time zones are not known.")
w(f"- Only the first 30 comments per issue were fetched; {truncated} issues had more.")
w(f"- The newest issue was opened {newest:.1f} days before the fetch, so the last issues had little time to be triaged.")

(HERE / "crosscheck.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
