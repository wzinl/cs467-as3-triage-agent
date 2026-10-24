# Repository metrics: hashicorp/terraform-provider-aws issues

Data fetched 2026-10-24 03:13 UTC with `evals/data/fetch_upstream.py`. Window: issues opened 2026-06-01 to 2026-10-20 (761 issues). Regenerate with `python3 evals/metrics/compute_metrics.py`.

## 1. Volume

- Issues opened: 761, of which 609/761 (80%) by reporters (non-maintainers).
- Full ISO weeks: 19. Issues per week: median 35, max 95 (week 26). Reporter issues per week: median 30, max 42.
- Maintainers identified: 12.

## 2. How long reporters wait

Over the 609 reporter issues. A share "within N days" counts only issues that were at least N days old at fetch time, so recent issues do not count as misses.

| | median days (issues where it happened) | happened at all | within 1 day | within 7 days | within 30 days |
|---|---|---|---|---|---|
| first maintainer touch | 0.8 | 579/609 (95%) | 316/609 (52%) | 535/599 (89%) | 483/499 (97%) |
| `needs-triage` removed | 0.8 | 584/609 (96%) | 317/609 (52%) | 534/599 (89%) | 487/499 (98%) |

## 3. Untriaged backlog on the fetch date

- Open issues: 2667. Open with `needs-triage`: 105 (fetched 105), 26 of them opened in the window.
- Age of those 105: median 380.5 days, oldest 809 days.

## 4. What maintainers do during triage (reporter issues)

- Closed as duplicate or marked duplicate: 44/609 (7%).
- `waiting-response` added by a maintainer at least once: 32/609 (5%).
- Had a `service/*` label at some point: 580. Maintainers removed 114 `service/*` labels, on 67/580 (12%) of them (the regex labeler over-labels).
- Type labels added by maintainers (events): `enhancement` 73, `waiting-response` 38, `regression` 35, `bug` 32, `new-resource` 13, `documentation` 12, `crash` 10, `new-service` 7, `new-data-source` 4, `upstream-terraform` 2, `question` 1.
- Bot comments: 1276. `dosubot` (an AI assistant upstream already runs) commented on 80/609 (13%) reporter issues (89 comments).

## 5. Limits of these metrics

- One repository, one 20-week window. Summer releases and the provider's v6 cadence may not be typical.
- "Maintainer" is inferred from comment association and from permission-gated actions. A maintainer who only reacted, or who triaged in a linked PR, is missed, so first-touch times are upper bounds.
- "First touch" is not "resolved". A label change can be a one-second regex fix; a comment may be a question.
- The fetch kept the first 30 comments (2 issues had more) and the first 60 timeline events (none reached it).
- The backlog is one snapshot on the fetch date, not a time series. Issues opened in the last days of the window are right-censored; section 2 handles this by eligibility, not by survival analysis.
- Label events by GitHub Actions on behalf of a maintainer (for example the `waiting-response` remover) are attributed to the bot and excluded.
