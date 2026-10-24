# Cross-check: reporter waits, from comment author association only

Snapshot fetched 2026-10-24 03:13 UTC; 609 reporter issues of 761 opened 2026-06-01 to 2026-10-20. Regenerate with `python3 evals/metrics/crosscheck_metrics.py`.

Author association of all issues in the window: NONE 479, CONTRIBUTOR 130, MEMBER 78, COLLABORATOR 74.

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

4 accounts removed `needs-triage`, 1 of them a bot.

## 3. Written replies from a maintainer

- Reporter issues with at least one maintainer comment: 103/609 (17%).
- Days to the first one, where it happened: median 1.06, 75th percentile 3.7, 90th percentile 8.3.
- Triaged (`needs-triage` removed) with no maintainer comment within 7 days: 506/584.

## 4. Figures results.md also reports, recomputed with separate code

- Closed as duplicate or marked duplicate: 44/609 (7%).
- Issues that ever had a `service/*` label: 580. A person other than the author removed 114 of those labels, on 67/580 (12%) of them.
- Who had added the removed labels: `github-actions` 113, `justinretzolk` 1. `github-actions` is the account upstream's regex labeler (`triage.yml`) runs as.

## 5. Limits

- 8 accounts commented as OWNER, MEMBER or COLLABORATOR. 3 of the 3 people who removed `needs-triage` are among them. A maintainer the API reports with another association would be missed here.
- The weekend cut is in UTC; the maintainers' own time zones are not known.
- Only the first 30 comments per issue were fetched; 2 issues had more.
- The newest issue was opened 3.2 days before the fetch, so the last issues had little time to be triaged.
