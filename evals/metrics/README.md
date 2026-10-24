# Need analysis: does issue triage in terraform-provider-aws need help?

Yes, on weekends and for a written first reply. Weekday triage is quick, but one maintainer does most of it.

## What was measured, and over which period

- **Source:** hashicorp/terraform-provider-aws issues, fetched read-only through the GitHub GraphQL API by
  `evals/data/fetch_upstream.py` on 2026-10-24 03:13 UTC (`evals/data/fetch_meta.json`).
- **Period:** the 761 issues opened 2026-06-01 to 2026-10-20 (20 weeks). The 609 opened by reporters
  (author association NONE or CONTRIBUTOR) are the ones the agent would run on.
- **Backlog:** open issues labelled `needs-triage` on the fetch date (`backlog_needs_triage.json`).

Two scripts measure the same snapshot with different definitions of "maintainer":

| Script | Maintainer means | Output |
|---|---|---|
| `compute_metrics.py` | a comment author with a maintainer association, or anyone who labelled, unlabelled or closed someone else's issue | `results.md` |
| `crosscheck_metrics.py` | a comment author with association OWNER, MEMBER or COLLABORATOR, nothing else | `crosscheck.md` |

Where both report the same figure (a median of 0.83 days until `needs-triage` is removed, 44 duplicates,
114 wrong `service/*` labels removed), the separately written code gives the same answer, which rules out a
coding slip in either. The weekend split, who removes `needs-triage` and the written-reply share come only
from the cross-check. Regenerate both with:

```sh
python3 evals/metrics/compute_metrics.py
python3 evals/metrics/crosscheck_metrics.py
```

## Results

| Measure (609 reporter issues) | Result |
|---|---|
| Reporter issues per full ISO week (19 weeks) | median 30, range 18 to 42 |
| Days until `needs-triage` is removed, opened Monday to Friday noon UTC | median 0.66 (495 issues) |
| Same, opened Friday noon to Sunday UTC | median 2.84 (89 issues) |
| `needs-triage` removals made by one maintainer | 449 of 585 (77%); 4 accounts in all, one a bot |
| Reporter issues with any written maintainer comment | 103 (17%), median 1.06 days to the first |
| Closed or marked as duplicate | 44 (7%) |
| Wrong regex `service/*` labels removed by maintainers | 114, on 67 of 580 labelled issues (12%) |
| Open `needs-triage` backlog on 2026-10-24 | 105 issues, median age 380 days |

## Limits of these metrics

- One repository and one 20-week summer window, during the provider's v6 release cadence.
- The fetch kept the first 30 comments and 60 timeline events per issue. Two issues had more comments.
- Maintainers are found from author association and permission-gated actions. A maintainer the API shows
  as CONTRIBUTOR, or who only reacted, is missed, so the waits are upper bounds.
- Removing `needs-triage` records a triage decision, not its quality. A silent label is not a reply.
- 17% counts written replies only. A maintainer may answer through a linked PR, or by labels alone.
- The weekend cut is in UTC, and the maintainers' own time zones are not known.
- Issues opened near the window's end had at least 4 days to be triaged; the "within N days" shares in
  `results.md` count only issues old enough. Deleted or transferred issues are not in the snapshot.
