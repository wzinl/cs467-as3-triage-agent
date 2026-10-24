# Cross-check: reporter waits, from comment author association only

Snapshot fetched 2026-10-24 03:13 UTC; 609 reporter issues of 761 opened 2026-06-01 to 2026-10-20. Regenerate with `python3 evals/metrics/crosscheck_metrics.py`.

## 1. Time until `needs-triage` is removed, by when the issue was opened (UTC)

| opened | issues | median days | 90th percentile days |
|---|---|---|---|
| any time | 584 | 0.83 | 6.2 |
| Monday to Friday noon | 495 | 0.66 | 6.4 |
| Friday noon to Sunday | 89 | 2.84 | 5.5 |

## 2. Who removes `needs-triage`

- `justinretzolk`: 449/585 (77%)
- `ewbankkit`: 64/585 (11%)
- `github-actions`: 64/585 (11%)
- `jar-b`: 8/585 (1%)

## 3. Written replies from a maintainer

- Reporter issues with at least one maintainer comment: 103/609 (17%).
- Days to the first one, where it happened: median 1.06, 75th percentile 3.7, 90th percentile 8.3.
- Triaged (`needs-triage` removed) with no maintainer comment within 7 days: 506/584.

## 4. Figures results.md also reports, recomputed with separate code

- Closed as duplicate or marked duplicate: 44/609 (7%).
- Issues that ever had a `service/*` label: 580. A person other than the author removed 114 of those labels, on 67/580 (12%) of them.

## 5. Limits

- Association depends on what the API shows the fetching account. Eight accounts commented as MEMBER or COLLABORATOR, including every person who removed `needs-triage`, but a maintainer shown as CONTRIBUTOR is missed.
- The weekend cut is in UTC; the maintainers' own time zones are not known.
- Comments beyond the first 30 per issue were not fetched (2 issues had more).
