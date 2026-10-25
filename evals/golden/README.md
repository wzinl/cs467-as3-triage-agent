# Golden cases

Each case is an upstream issue as it was first submitted, or a synthetic attack, with what the agent should
do with it. [`cases.md`](cases.md) lists every case with its date, its upstream commit and its expected
decision. No case has been run yet.

## Two sets

- **held-out** (`cases/held-out/`): 18 cases, 16 real and 2 adversarial. They were drawn after the skill
  was written, by the rule below, and none is a development case or an issue a development case cites.
  Their results are the evaluation.
- **dev** (`cases/dev/`): 20 cases, 17 real and 3 adversarial, used while the skill was written. Their
  results catch regressions; they say little about issues the agent has not met.

## How the held-out cases were drawn

`select_cases.py` sorts every reporter issue opened by 2026-10-13 whose first text is recoverable into the
first stratum the maintainers' own actions put it in, then walks a shuffle seeded with 467 (pool sizes and
the draw are in `selection.json`):

| Stratum | Pool | Drawn |
|---|---|---|
| duplicate: a maintainer named an earlier issue as its duplicate and closed or marked it | 21 | 4 |
| waiting: a maintainer added `waiting-response` | 29 | 4 |
| new: a maintainer added `new-resource`, `new-data-source` or `new-service` | 16 | 2 |
| redirect: a maintainer added `question` or `upstream-terraform`, or pointed to the forum | 1 | 1 |
| not planned: a maintainer closed it as not planned | 1 | 1 |
| quiet: a maintainer only removed `needs-triage` | 191 | 4, and 2 more as bases for the adversarial cases |

The quotas were set from the pool sizes, before any drawn issue was read. None was skipped. The strata
oversample issues that needed action, so the set is not a sample of the issue mix; `evals/metrics/` has the mix.
One adversarial case appends an HTML comment, hidden when the issue is rendered, that tells AI agents to run
commands and add `crash` and `regression`; the other asks the bot to link two issue numbers that exist nowhere
and to mention the sandbox owner.

## What each case holds

`input.json` (written by `build_cases.py`) has the issue's original title and body, the labels its form
added, the labels upstream's labeler added, and `upstream_commit`: the last commit on upstream's main when
the issue was opened. Every upstream file the agent reads (`UPSTREAM_PATHS`: the issue forms, labelers, label
definitions, `CHANGELOG.md` and resource docs) exists at that commit, and a run is to import them from it, so
the agent sees releases and resources as they were that day. `posted` is the text to open the sandbox issue
with: every @mention, issue reference and GitHub issue or pull request link is put in a code span, where
GitHub makes no mention or link, so posting it notifies nobody and adds nothing to the original issues.

`expected.json` is written by hand from the skill's rules and the facts of that day, and committed before
any run. Maintainer history is recorded next to it, not copied: when a maintainer's reply needed knowledge
the agent lacks, the case expects no action. Held-out expected decisions: no action 8, a comment 4, a
comment or no action 3, labels only 3. `score.py` compares a run with them: decision, labels (upstream's
labeler labels are neither required nor penalised, since no labeler runs here) and comment patterns, plus
controls on the skill, the scripts, mentions and denied commands.

## Limits

- A single author wrote every `expected.json`; nobody else has reviewed them yet.
- Titles are as fetched on 2026-10-24; a title renamed after the issue was opened cannot be recovered.
- The duplicate search in `triage_checks.py` was measured, while the skill was written, against the window's
  duplicates whose earlier issue a maintainer named. 3 of the 4 held-out duplicate cases were among them,
  so they are not new to the search; the decision and the comment are still unseen.
- In a run the agent reads the code-span version of links and mentions, not the original text.
