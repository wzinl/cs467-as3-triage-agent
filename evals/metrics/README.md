# Need analysis: does issue triage in terraform-provider-aws need help?

Yes, on weekends and for a written first reply. Weekday triage is quick, and one maintainer does most of it.

## What was measured, and over which period

- **Source:** hashicorp/terraform-provider-aws issues in `evals/data`, fetched once on 2026-10-24 from
  03:13 to 03:20 UTC (`fetch_meta.json`) by an earlier session. The data has the fields
  `fetch_upstream.py` requests, and that script only sends GraphQL queries, never mutations.
- **Period:** the 761 issues opened 2026-06-01 to 2026-10-20, a 20-week window. The 609 opened by
  reporters (author association NONE or CONTRIBUTOR) are the ones the planned agent would run on. Every
  other issue in the window was opened by a MEMBER or COLLABORATOR.
- **Backlog:** open issues labelled `needs-triage` on the fetch date (`backlog_needs_triage.json`).

Two scripts measure the same snapshot:

| Script | Maintainer means | Output |
|---|---|---|
| `compute_metrics.py` | a comment author with a maintainer association, or anyone who labelled, unlabelled or closed someone else's issue | `results.md` |
| `crosscheck_metrics.py`, new, written after reading the first | a comment author with association OWNER, MEMBER or COLLABORATOR, nothing else | `crosscheck.md` |

How far the cross-check confirms `results.md`:

- Duplicates and the median time until `needs-triage` is removed use the same logic in both scripts. Their
  agreement shows only that neither has a typo.
- The `service/*` removals use a looser rule in the cross-check (any person but the author removed the
  label) and still give the same count.
- The weekend split, who removes `needs-triage`, and the written-reply share come only from the
  cross-check. Nothing confirms them a second time.

Regenerate both outputs, then check every number in this file against them:

```sh
python3 evals/metrics/compute_metrics.py
python3 evals/metrics/crosscheck_metrics.py
python3 verification/check_claims.py
```

## Results

| Measure (609 reporter issues) | Result | From |
|---|---|---|
| Reporter issues per full ISO week (19 weeks) | median 30, at most 42 | `results.md` §1 |
| Days until `needs-triage` is removed, any time | median 0.83 (584 issues) | both |
| Same, opened Monday to Friday noon UTC | median 0.66 (495 issues) | `crosscheck.md` §1 |
| Same, opened Friday noon to Sunday UTC | median 2.84 (89 issues) | `crosscheck.md` §1 |
| `needs-triage` removals made by one maintainer | 449 of 585 (77%); 4 accounts in all, one a bot | `crosscheck.md` §2 |
| Reporter issues with any written maintainer comment | 103 (17%), median 1.06 days to the first | `crosscheck.md` §3 |
| Closed or marked as duplicate | 44 (7%) | both |
| `service/*` labels a person removed | 114, on 67 of 580 labelled issues (12%); 113 of them added by the regex labeler | both; adders in `crosscheck.md` §4 |
| Open `needs-triage` backlog on 2026-10-24 | 105 issues, median age 380.5 days | `results.md` §3 |

## Limits of these metrics

- One repository and one 20-week window, June to October 2026, which may not be typical of the year.
- The fetch kept the first 30 comments and 60 timeline events per issue. 2 issues had more comments,
  and none reached 60 events.
- Maintainers are found from author association and permission-gated actions. A maintainer reported with
  another association, or who only reacted, is missed, so the waits are upper bounds.
- Removing `needs-triage` records a triage decision, not its quality. A silent label is not a reply.
- 17% counts written replies only. A maintainer may answer through a linked PR, or by labels alone.
- The weekend cut is in UTC, and the maintainers' own time zones are not known.
- The newest issue was opened 3.2 days before the fetch. The "within N days" shares in `results.md`
  count only issues old enough. Deleted or transferred issues are not in the snapshot.
- The fetch cannot be replayed from the cloud session that built this repo, because it has no GitHub
  token that reads upstream issues. Anyone logged in with `gh` can rerun `fetch_upstream.py`.
