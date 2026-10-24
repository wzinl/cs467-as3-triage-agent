# Claim audit: need analysis (2026-10-24)

Rule: before work is handed over, each claim made in it (repo files, the plan doc, replies)
is traced to the command output or file that backs it. A claim with nothing behind it is fixed or removed.
`check_claims.py` checks the numbers in `README.md` and `evals/metrics/README.md` on every push; this file
records the claims a substring cannot check, and what the audit changed.

## Found and fixed

| # | Where | First written as | What the evidence shows | Now |
|---|---|---|---|---|
| 1 | `evals/metrics/README.md` | Both scripts agree on duplicates and `service/*` removals | `crosscheck_metrics.py` computed neither | Both computed; same 44 and 114 |
| 2 | `evals/metrics/README.md`, plan doc | The cross-check is independent and "rules out a coding slip" | It was written after reading the first script, with the same logic for duplicates and `needs-triage` removal | Says how far each figure is confirmed, and the commit message no longer calls it independent |
| 3 | `README.md` | "This repository configures an existing AI agent" | No agent configuration exists yet | Future tense |
| 4 | Both READMEs, plan doc | 114 wrong labels from the regex labeler | 113 of the 114 removed labels were added by `github-actions`, 1 by a maintainer | 113 of 114, computed in `crosscheck.md` §4 |
| 5 | `evals/metrics/README.md`, plan doc | Weekly range 18 to 42 | 18 came from a one-off command, in no committed output | "at most 42", from `results.md` |
| 6 | `evals/metrics/README.md`, plan doc | Backlog median age 380 days | `results.md`: 380.5 | 380.5 |
| 7 | `evals/metrics/README.md`, plan doc | The newest issues had at least 4 days | The newest issue was opened 3.2 days before the fetch | 3.2, computed |
| 8 | `crosscheck_metrics.py`, plan doc | Maintainers are US-based, mostly in US time zones | Nothing in the data shows time zones | Removed |
| 9 | `crosscheck.md` | "2 issues had more" comments, typed into the script | Correct, but not computed | Computed |
| 10 | Plan doc | Weekday triage is quick "because" one maintainer does most of it | A correlation, not a cause | "and" |
| 11 | Plan doc | "PR code runs under `pull_request_target`" | That trigger runs base-branch code with a write token; the risk is an agent reading untrusted PR code with it | Reworded |
| 12 | Plan doc | The agent "looks at" new issues and "skips maintainers" | Not built yet | Planned, future tense |
| 13 | Plan doc | "Only 7% of issues are duplicates" | 7% of reporter issues | Fixed |
| 14 | Reply, 06:01 UTC | "Pushes already go through your connected GitHub account" | Unchecked when sent. Later, `get_me` returned `wzinl`, and every CI run names `wzinl` as the actor of its push | Left as sent, now backed |

## Checked and held

| Claim | Evidence |
|---|---|
| Upstream runs `triage.yml` (`needs-triage` + `github/issue-labeler` regex labels), `community_note.yml`, `stale.yml` (720 days), `generate_changelog.yml` (`go-changelog`) | Read at upstream `1e015f7` (2026-10-23), sparse clone of `.github` |
| The bug form's configuration field is `required: true`, but its pre-filled value is an empty `hcl` block, so an empty block passes | `.github/ISSUE_TEMPLATE/00_bug_report.yml` at `1e015f7` |
| #48253 was filed with that empty block | Its body in `evals/data/window_issues.json.gz` |
| Upstream builds the changelog from `.changelog/` entries | `.changelog/` has 274 files at `1e015f7`; `generate_changelog.yml` runs `changelog-build` |
| Acceptance tests need AWS credentials and cost money | `docs/running-and-writing-acceptance-tests.md` at `1e015f7` |
| Upstream PR workflows use `pull_request_target` | `closed_items.yml`, `community_note.yml`, `maintainer_helpers.yml`, `triage.yml` |
| This session cannot read upstream issues through the API | `gh auth status`: the token in `GH_TOKEN` is invalid |
| `results.md` regenerates byte for byte | CI regenerates it on every push and fails on any difference |
| All commits are authored and committed as `wzinl` | `git log`; GitHub `list_commits` |
| `results.md` and `crosscheck.md` regenerate unchanged and every README number is backed | CI passes on every push: https://github.com/wzinl/cs467-as3-triage-agent/actions/workflows/checks.yml |
| `pack.py` drops labels from the corpus | Corpus keys: number, url, title, body, created_at, closed_at, state_reason |
| Data counts: 761 issues, 105 backlog of 2,667 open, 11,875 corpus issues, 2,698 resource docs, 16 fields per issue | Commands run on `evals/data` in this session |

## Not checkable, so labelled as judgement or estimate

- A re-fetch today would add almost nothing (the window ends 2026-10-20).
- Public repositories get free Actions minutes (GitHub's published policy, not checked here).
