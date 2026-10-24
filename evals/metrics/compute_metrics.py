#!/usr/bin/env python3
"""Repository metrics that justify (and size) the triage agent. Writes results.md next to this file.

Input: the frozen upstream data in evals/data (fetched 2026-10-24, see fetch_meta.json).
Window: issues opened 2026-06-01..2026-10-20 in hashicorp/terraform-provider-aws.

Definitions used below:
  reporter    a non-maintainer issue author (association NONE or CONTRIBUTOR). The agent only runs for these.
  maintainer  a person (not a bot) who commented with association OWNER/MEMBER/COLLABORATOR, or who
              labelled, unlabelled or closed an issue somebody else opened (that needs triage permission).
  first touch the first label change, comment or close on an issue by a maintainer other than its author.

Usage: python3 evals/metrics/compute_metrics.py
"""
import collections
import gzip
import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE.parent / "data"
FETCHED = datetime.fromisoformat(json.loads((DATA / "fetch_meta.json").read_text())["started_at"])
MAINT_ASSOC = {"OWNER", "MEMBER", "COLLABORATOR"}
REPORTER_ASSOC = {"NONE", "CONTRIBUTOR"}
TYPE_LABELS = ["bug", "enhancement", "documentation", "new-resource", "new-data-source", "new-service",
               "regression", "crash", "question", "upstream-terraform", "waiting-response"]


def t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def is_bot(login):
    return not login or login.endswith("[bot]") or login.endswith("bot") or login == "github-actions"


def login(node, key):
    return ((node.get(key) or {}).get("login")) or ""


def days(td):
    return td.total_seconds() / 86400


def median(xs):
    return f"{statistics.median(xs):.1f}" if xs else "n/a"


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else f"{a}/0"


def within(issues, delays, limit_days):
    """Share of issues with an event within limit_days, counting only issues at least that old at fetch time."""
    eligible = [i for i in issues if days(FETCHED - t(i["createdAt"])) >= limit_days]
    hit = [i for i in eligible if delays.get(i["number"]) is not None and delays[i["number"]] <= limit_days]
    return pct(len(hit), len(eligible))


issues = json.load(gzip.open(DATA / "window_issues.json.gz"))
backlog = json.loads((DATA / "backlog_needs_triage.json").read_text())

maintainers = set()
for i in issues:
    author = login(i, "author")
    for c in i["comments"]["nodes"]:
        if c["authorAssociation"] in MAINT_ASSOC and not is_bot(login(c, "author")):
            maintainers.add(login(c, "author"))
    for e in i["timelineItems"]["nodes"]:
        a = login(e, "actor")
        if e["__typename"] in ("LabeledEvent", "UnlabeledEvent", "ClosedEvent") and a != author and not is_bot(a):
            maintainers.add(a)

reporters = [i for i in issues if i["authorAssociation"] in REPORTER_ASSOC]
out = []
w = out.append

# 1. Volume
weeks = collections.Counter(t(i["createdAt"]).date().isocalendar()[:2] for i in issues)
rweeks = collections.Counter(t(i["createdAt"]).date().isocalendar()[:2] for i in reporters)
full = sorted(weeks)[1:-1]   # the first and last ISO weeks are partial
w("# Repository metrics: hashicorp/terraform-provider-aws issues\n")
w(f"Data fetched {FETCHED:%Y-%m-%d %H:%M} UTC with `evals/data/fetch_upstream.py`. Window: issues opened "
  f"2026-06-01 to 2026-10-20 ({len(issues)} issues). Regenerate with `python3 evals/metrics/compute_metrics.py`.\n")
w("## 1. Volume\n")
w(f"- Issues opened: {len(issues)}, of which {pct(len(reporters), len(issues))} by reporters (non-maintainers).")
w(f"- Full ISO weeks: {len(full)}. Issues per week: median {statistics.median(weeks[k] for k in full):.0f}, "
  f"max {max(weeks[k] for k in full)} (week {max(full, key=lambda k: weeks[k])[1]}). "
  f"Reporter issues per week: median {statistics.median(rweeks[k] for k in full):.0f}, max {max(rweeks[k] for k in full)}.")
w(f"- Maintainers identified: {len(maintainers)}.\n")

# 2. Time to first maintainer touch, and to needs-triage removal
first_touch, triage_removed, type_by_maint, waiting_added, svc_removed, svc_events, svc_had = {}, {}, collections.Counter(), 0, 0, 0, 0
dup, dosu_issues, dosu_comments, bot_comments = 0, 0, 0, 0
for i in reporters:
    author, created = login(i, "author"), t(i["createdAt"])
    touches = [t(c["createdAt"]) for c in i["comments"]["nodes"]
               if login(c, "author") in maintainers and login(c, "author") != author]
    touches += [t(e["createdAt"]) for e in i["timelineItems"]["nodes"]
                if e["__typename"] in ("LabeledEvent", "UnlabeledEvent", "ClosedEvent")
                and login(e, "actor") in maintainers and login(e, "actor") != author]
    if touches:
        first_touch[i["number"]] = days(min(touches) - created)
    removed = [t(e["createdAt"]) for e in i["timelineItems"]["nodes"]
               if e["__typename"] == "UnlabeledEvent" and e["label"]["name"] == "needs-triage"]
    if removed:
        triage_removed[i["number"]] = days(min(removed) - created)
    seen_waiting = False
    for e in i["timelineItems"]["nodes"]:
        a = login(e, "actor")
        if a not in maintainers or a == author:
            continue
        name = e["label"]["name"] if "label" in e else None
        if e["__typename"] == "LabeledEvent" and name in TYPE_LABELS:
            type_by_maint[name] += 1
            if name == "waiting-response" and not seen_waiting:
                waiting_added, seen_waiting = waiting_added + 1, True
    events = i["timelineItems"]["nodes"]
    if any(e["__typename"] == "LabeledEvent" and e["label"]["name"].startswith("service/") for e in events):
        svc_had += 1
        n = sum(1 for e in events if e["__typename"] == "UnlabeledEvent" and e["label"]["name"].startswith("service/")
                and login(e, "actor") in maintainers)
        svc_removed, svc_events = svc_removed + bool(n), svc_events + n
    if i["stateReason"] == "DUPLICATE" or any(e["__typename"] == "MarkedAsDuplicateEvent" for e in events):
        dup += 1
    dosu = [c for c in i["comments"]["nodes"] if login(c, "author") == "dosubot"]
    dosu_issues += bool(dosu)
    dosu_comments += len(dosu)
    bot_comments += sum(1 for c in i["comments"]["nodes"] if is_bot(login(c, "author")))

w("## 2. How long reporters wait\n")
w(f"Over the {len(reporters)} reporter issues. A share \"within N days\" counts only issues that were at least N days "
  f"old at fetch time, so recent issues do not count as misses.\n")
w("| | median days (issues where it happened) | happened at all | within 1 day | within 7 days | within 30 days |")
w("|---|---|---|---|---|---|")
for name, d in (("first maintainer touch", first_touch), ("`needs-triage` removed", triage_removed)):
    w(f"| {name} | {median(list(d.values()))} | {pct(len(d), len(reporters))} | {within(reporters, d, 1)} | "
      f"{within(reporters, d, 7)} | {within(reporters, d, 30)} |")
w("")

# 3. Backlog on the fetch date
ages = [days(FETCHED - t(b["createdAt"])) for b in backlog["issues"]]
in_window = sum(1 for b in backlog["issues"] if b["createdAt"] >= "2026-06-01")
w("## 3. Untriaged backlog on the fetch date\n")
w(f"- Open issues: {backlog['totals']['open_issues']}. Open with `needs-triage`: {backlog['totals']['open_needs_triage']} "
  f"(fetched {len(ages)}), {in_window} of them opened in the window.")
w(f"- Age of those {len(ages)}: median {median(ages)} days, oldest {max(ages):.0f} days.\n")

# 4. What maintainers did that the agent could prepare
w("## 4. What maintainers do during triage (reporter issues)\n")
w(f"- Closed as duplicate or marked duplicate: {pct(dup, len(reporters))}.")
w(f"- `waiting-response` added by a maintainer at least once: {pct(waiting_added, len(reporters))}.")
w(f"- Had a `service/*` label at some point: {svc_had}. Maintainers removed {svc_events} `service/*` labels, on "
  f"{pct(svc_removed, svc_had)} of them (the regex labeler over-labels).")
w("- Type labels added by maintainers (events): " + ", ".join(f"`{k}` {v}" for k, v in type_by_maint.most_common()) + ".")
w(f"- Bot comments: {bot_comments}. `dosubot` (an AI assistant upstream already runs) commented on "
  f"{pct(dosu_issues, len(reporters))} reporter issues ({dosu_comments} comments).\n")

# 5. Limits
trunc = sum(1 for i in issues if i["comments"]["totalCount"] > len(i["comments"]["nodes"]))
w("## 5. Limits of these metrics\n")
w("- One repository, one 20-week window. Summer releases and the provider's v6 cadence may not be typical.")
w("- \"Maintainer\" is inferred from comment association and from permission-gated actions. A maintainer who only "
  "reacted, or who triaged in a linked PR, is missed, so first-touch times are upper bounds.")
w("- \"First touch\" is not \"resolved\". A label change can be a one-second regex fix; a comment may be a question.")
w(f"- The fetch kept the first 30 comments ({trunc} issues had more) and the first 60 timeline events (none reached it).")
w("- The backlog is one snapshot on the fetch date, not a time series. Issues opened in the last days of the window "
  "are right-censored; section 2 handles this by eligibility, not by survival analysis.")
w("- Label events by GitHub Actions on behalf of a maintainer (for example the `waiting-response` remover) are "
  "attributed to the bot and excluded.")

(HERE / "results.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
