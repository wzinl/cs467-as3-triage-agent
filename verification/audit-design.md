# Claim audit: DESIGN.md (2026-10-29)

`DESIGN.md` summarises the work for the brief. Every number in it is registered in
`verification/check_claims.py` with the output, data, lock file or ledger row that backs it, and CI checks
that it stays at 150 lines or fewer with prose lines of at most 120 characters. This ledger holds the claims a
substring cannot check.

## Checked by hand

| Claim | Evidence |
|---|---|
| The agent's comments are posted by `github-actions[bot]` | The comments on sandbox issues #5 to #42, read on 2026-10-29: 16, all by `github-actions[bot]` (type `Bot`) |
| A first response comes within minutes | Live-run examples from start to last update: 5 minutes ([run 40733678322](https://github.com/wzinl/cs467-as3-triage-agent/actions/runs/40733678322)), 7 minutes ([run 40736057205](https://github.com/wzinl/cs467-as3-triage-agent/actions/runs/40736057205)), 5 minutes for dev 16 through the real trigger ([run 40733519963](https://github.com/wzinl/cs467-as3-triage-agent/actions/runs/40733519963)) |
| `claude-sonnet-5-5` has no dated snapshot | The Claude API's model list gives `claude-sonnet-5-5` as the only ID for Claude Sonnet 5.5, with no dated full ID (read 2026-10-29); older models such as Claude Haiku 4.5 have one |
| The API key stays in gh-aw's proxy | The lock starts the agent's container with `--exclude-env ANTHROPIC_API_KEY`; the key is passed to the API proxy |
| Tools | The lock's `--allowed-tools` list: read-only shell tools (`cat`, `grep`, `head`, `ls` and the like), the skill's two scripts, `Edit(//tmp/**)`, Read, Glob, Grep, Skill, Task, TodoWrite and the safe-outputs tools; `--disallowed-tools` names WebFetch, WebSearch, Write, MultiEdit and NotebookEdit |
| Upstream runs PR workflows under `pull_request_target` | `verification/audit-need-analysis.md` |
| 300 issues: about 43 a day, about 130 runs a day under the cap, about $45 | Arithmetic: 300 / 7 = 42.9; 2,000 credits / 15.2 credits a case ($5.64 / 37 runs) = 131; 300 × $0.15 = $45 |
| PRs #43 and #49 were merged by `wzinl` | GitHub's pull request records, read 2026-10-29: `merged_by` is `wzinl` for both |
| Claude Code opened the test issues from the owner's accounts | Every reply in `evals/golden/results-2026-10-28.md` thanks `@zzzinn`, the second account; PR #43's AI disclosure says Claude Code opened the case issues on the owner's machine |
| What the owner decided and did | The owner's own account, given on 2026-10-29 for the AI-use statement |

## Found and fixed while writing it

1. The first draft listed "mentioning anyone but the author" and "linking issues in other repositories" as
   prevented by safe outputs. Safe outputs allow one mention of the author, an assignee or the person who
   started the run, and pass full github.com links; only `validate_plan.py`, which the agent runs itself,
   holds the narrower rules. Moved to the rules that rest on the skill.
2. It said the agent "must" pass its plan through `validate_plan.py`; that is an instruction, not a gate.
   Now it says the skill has the agent do so and every live run did.
3. It marked least privilege "tested" by the stale-close attack, which shows the agent did not close
   anything, not that it could not. Now "CI-checked", since CI checks the permissions in the lock.
4. It named five misses; there are six.
5. Question 2 said CI catches "every change on our side". The drift check covers the lock, the skill and
   `AGENTS.md`; the issue snapshot and upstream copy have their own manifests, which do not ask for a rerun.
6. The open list said one person wrote every expected outcome. Claude Code wrote them, as the AI-use
   statement says, so it now names Claude Code.

## Not enforced yet

- Table rows are exempt from the 120-character check, since a Markdown table row cannot wrap.
