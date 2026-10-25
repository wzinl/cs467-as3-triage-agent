#!/usr/bin/env python3
"""Draw the held-out golden cases from the frozen upstream issues, by a rule fixed before any of them was read.

Pool: issues in evals/data/window_issues.json.gz opened by a reporter (author association NONE or CONTRIBUTOR)
by 2026-10-13, so maintainers had at least 11 days before the fetch, whose first-submitted text is
recoverable, and that no development case uses (as its issue or as an issue its expected.json cites).

Each issue goes to the first stratum, in this order, that the maintainers' own actions put it in:
  duplicate     closed or marked as a duplicate of an earlier issue that is in evals/data/corpus.json.gz
  waiting       a maintainer added waiting-response
  new           a maintainer added new-resource, new-data-source or new-service
  redirect      a maintainer added question or upstream-terraform, or pointed to discuss.hashicorp.com
  not-planned   a maintainer closed it as not planned
  quiet         a maintainer removed needs-triage and did nothing else: no comment, no other label
Issues with no maintainer action yet have no outcome to compare with and are left out.

From each stratum a seeded shuffle (random.Random(467)) is walked in order and the first QUOTA issues are
taken; the next two quiet issues become the bases of the two adversarial cases. The quotas were set from the
pool sizes alone, before any drawn issue was read: only one issue each is in the redirect and not-planned pools.
A drawn issue is skipped only for a reason listed in SKIPPED, written down when the case was read, and the
next one in the shuffle replaces it. Writes evals/golden/selection.json.
Usage: python3 evals/golden/select_cases.py
"""
import gzip
import json
import random
import re
from pathlib import Path

from build_cases import DEV

HERE = Path(__file__).parent
DATA = HERE.parent / "data"
SEED = 467
LAST_OPENED = "2026-10-13T23:59:59Z"
QUOTA = {"duplicate": 4, "waiting": 4, "new": 2, "redirect": 1, "not-planned": 1, "quiet": 4}
ADVERSARIAL_BASES = 2
MAINT = {"OWNER", "MEMBER", "COLLABORATOR"}
# Drawn issues left out after reading them, with the reason. Each skip moves to the next issue in the shuffle.
SKIPPED = {}
DUP_REF = re.compile(r"[Dd]uplicate of (?:#|https://github\.com/hashicorp/terraform-provider-aws/issues/)(\d+)")


def login(node, key):
    return (node.get(key) or {}).get("login") or ""


def is_bot(name):
    return not name or name.endswith("bot") or name.endswith("[bot]") or name == "github-actions"


def first_body_known(i):
    return not i.get("lastEditedAt") or any(e["editedAt"] == i["createdAt"] and e.get("diff") is not None
                                            for e in i["userContentEdits"]["nodes"])


def dev_numbers():
    """Every development case's issue, and every upstream issue number its expected.json mentions."""
    nums = set(DEV.values())
    for f in (HERE / "cases" / "dev").glob("*/expected.json"):
        nums |= {int(n) for n in re.findall(r"(?:#|issues/|\"number\": )(\d{5})\b", f.read_text())}
    return nums


def stratum(i, corpus_dates):
    author, events = login(i, "author"), i["timelineItems"]["nodes"]
    by_maint = [e for e in events if login(e, "actor") not in ("", author) and not is_bot(login(e, "actor"))]
    added = {e["label"]["name"] for e in by_maint if e["__typename"] == "LabeledEvent"}
    comments = [c for c in i["comments"]["nodes"] if c["authorAssociation"] in MAINT and not is_bot(login(c, "author"))]
    canon = [e["canonical"]["number"] for e in events if e["__typename"] == "MarkedAsDuplicateEvent" and e.get("canonical")]
    canon += [int(n) for c in comments for n in DUP_REF.findall(c["body"])]
    canon = [n for n in canon if n in corpus_dates and corpus_dates[n] < i["createdAt"]]
    if canon and any(e["__typename"] in ("MarkedAsDuplicateEvent", "ClosedEvent") for e in by_maint):
        return "duplicate", canon[0]
    if "waiting-response" in added:
        return "waiting", None
    if added & {"new-resource", "new-data-source", "new-service"}:
        return "new", None
    if added & {"question", "upstream-terraform"} or any("discuss.hashicorp.com" in c["body"] for c in comments):
        return "redirect", None
    if any(e["__typename"] == "ClosedEvent" and e.get("stateReason") == "NOT_PLANNED" for e in by_maint):
        return "not-planned", None
    removed = [e for e in by_maint if e["__typename"] == "UnlabeledEvent" and e["label"]["name"] == "needs-triage"]
    if removed and not comments and not added and not any(e["__typename"] == "ClosedEvent" for e in by_maint):
        return "quiet", None
    return None, None


def main():
    window = json.load(gzip.open(DATA / "window_issues.json.gz"))
    corpus_dates = {c["number"]: c["created_at"] for c in json.load(gzip.open(DATA / "corpus.json.gz"))}
    dev = dev_numbers()
    strata = {k: [] for k in QUOTA}
    canonical = {}
    for i in sorted(window, key=lambda i: i["number"]):
        if (i["authorAssociation"] not in ("NONE", "CONTRIBUTOR") or i["createdAt"] > LAST_OPENED
                or not first_body_known(i) or i["number"] in dev):
            continue
        s, canon = stratum(i, corpus_dates)
        if s:
            strata[s].append(i["number"])
            if canon:
                canonical[i["number"]] = canon
    rng = random.Random(SEED)
    drawn = {}
    for s, quota in QUOTA.items():
        order = rng.sample(strata[s], len(strata[s]))
        order = [n for n in order if n not in SKIPPED]
        drawn[s] = order[:quota]
        if s == "quiet":
            drawn["adversarial-base"] = order[quota:quota + ADVERSARIAL_BASES]
    out = {"seed": SEED, "last_opened": LAST_OPENED, "quota": QUOTA,
           "pool": {s: len(v) for s, v in strata.items()}, "skipped": {str(k): v for k, v in SKIPPED.items()},
           "drawn": drawn, "canonical": {str(n): canonical[n] for ns in drawn.values() for n in ns if n in canonical}}
    (HERE / "selection.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["pool"]), json.dumps(drawn))


if __name__ == "__main__":
    main()
