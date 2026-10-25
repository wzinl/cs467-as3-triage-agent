# Claim audit: agent configuration (2026-10-25)

This work added the agent: `.github/workflows/issue-triage.md`, compiled by gh-aw v0.93.4 into
`issue-triage.lock.yml`, the `issue-triage` skill with its scripts and tests, `CONTRIBUTING.md` and
`.github/CODEOWNERS`. Every limit the docs state is listed here with what backs it.

## Checked on every push

The lock file is what runs, so `verification/check_claims.py` checks each limit a doc states against the
lock, not against the `.md` it is compiled from: labels, comment count, mentions, link domains, issue
references, job permissions, the token used for writes, the kill switch, the stop date, the rate limit,
concurrency, the checkout, threat detection, artifacts and the model. Negative checks catch a widening
the docs do not mention: any `*_CREATE_ISSUE: "true"` or `*_REPORT_AS_ISSUE: "true"`, the detection
tracking-issue step, a personal-access-token fallback, `contents: write` or `pull-requests: write`.
CI recompiles the workflow with released gh-aw v0.93.4 and fails on any difference, checks that the
runtime actions are pinned to the commit of the `v0.93.4` tag, and runs the 17 script tests.

| Planted error in the lock file | Caught by |
|---|---|
| `max_labels` 3 changed to 4 | the CONTRIBUTING.md and SKILL.md label claims |
| `GH_AW_MISSING_TOOL_CREATE_ISSUE` set to `"true"` | the CONTRIBUTING.md and workflow "never opens an issue" claims |
| Writes falling back to `secrets.GH_AW_GITHUB_TOKEN` | the AGENTS.md and CONTRIBUTING.md token claims |
| Rate limit 3 changed to 30 | the workflow's rate-limit comment |

## Checked by hand

| Claim | Evidence |
|---|---|
| Issues opened by the owner, members or collaborators are skipped | [Run 1](https://github.com/wzinl/cs467-as3-triage-agent/actions/runs/40190802523) and [run 4](https://github.com/wzinl/cs467-as3-triage-agent/actions/runs/40192006993), for issues #1 and #2 opened by the owner: conclusion `skipped` |
| The skill loads and its checks run | [Run 3](https://github.com/wzinl/cs467-as3-triage-agent/actions/runs/40191135191), agent log: the first call is `Skill {"skill": "issue-triage"}` ("Launching skill: issue-triage"); then `triage_checks.py`, an Edit of `/tmp/gh-aw/agent/plan.json`, `validate_plan.py` (`"ok": true`), one `add_labels` and one `add_comment`. 10 turns, no permission denials |
| A bot posts the comment, with the disclosure line | [Comment on #1](https://github.com/wzinl/cs467-as3-triage-agent/issues/1#issuecomment-6397381775) by `github-actions[bot]`: asks for the empty configuration, the plan output and a retry on v6.70.0, ends with the fixed line, then gh-aw's footer linking the run. `waiting-response` added |
| Threat detection screened the outputs | Run 3, detection job: `prompt_injection`, `secret_leak` and `malicious_patch` all false |
| Cost per triaged issue | Run 3: agent 25.02 AIC, Claude Code's own `total_cost_usd` 0.2502, so 1 AIC is $0.01; detection 16.62 AIC. About $0.42 an issue. Caps: 100 AIC per run for each, 2,000 AIC a day for the workflow, about 48 issues a day at this cost |
| The hardened lock still posts | [Run 5](https://github.com/wzinl/cs467-as3-triage-agent/actions/runs/40192009430), after the fixes below, on #2 (a usage question filed as a bug): same sequence, `validate_plan.py` ok with one warning that the form already set `bug`; `github-actions[bot]` [pointed it to the forum](https://github.com/wzinl/cs467-as3-triage-agent/issues/2#issuecomment-6397500823) and added `question`. Agent 25.26 AIC, 10 turns, no permission denials |
| Upstream maintainers apologised for an AI-written answer (#48821) | `evals/data/window_issues.json.gz`: on 2026-07-09 `dosubot` suggested `aws_route53_zone_tags`, which does not exist; the reporter called it a hallucination; `justinretzolk` (MEMBER) replied on the same issue "Sorry about letting that hallucination through". The substring check cannot tie the reply to the issue, so this was read by hand |
| Mentions | gh-aw's `resolve_mentions_from_payload.cjs`: with `allowed-collaborators: false` it keeps the issue author and assignees, and on a manual run the person who started it; `max: 1`. `validate_plan.py` narrows this to the author |
| The kill switch only counts this repository's issues | `check_skip_if_helpers.cjs` appends `repo:<owner>/<repo>` to the query |
| The agent never sees the expected outcomes | `corpus.json.gz` entries hold only number, url, title, body, created_at, closed_at and state_reason; `prepare_context.py` drops issues opened after the one being triaged |

## Found and fixed

1. The first dispatched run ([run 2](https://github.com/wzinl/cs467-as3-triage-agent/actions/runs/40190818213))
   failed before the agent started: `gh api` cannot write the binary corpus ("transform: short source
   buffer"). The prepare step now downloads it with `curl`, and refuses a pull-request number.
2. gh-aw's defaults let the agent open issues three ways: an incomplete-run report, a missing-tool report
   (`GH_AW_MISSING_TOOL_CREATE_ISSUE: "true"`; v0.93.4's runtime does not read it, but the lock said so),
   and an "[aw] Detection Runs" tracking issue whenever detection warned or failed. All three are off.
3. If the detector itself failed, gh-aw's default warn mode still posted the comment, which it classes
   as reviewable, and only dropped the labels. Detection now fails closed (`continue-on-error: false`).
4. Every write step used `secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN`, so adding that secret
   would have let the bot write with a personal token. Writes now use only `GITHUB_TOKEN`.
5. The safe-outputs job asked for `pull-requests: write` by default; `pull-requests: false` removes it.
   Detection had a 400 AIC default budget; it is capped at 100.
6. A development build of gh-aw compiled a lock that checked out gh-aw's `main` at run time. The lock is
   now compiled by a release build, with the runtime actions pinned to the tag's commit.
7. gh-aw's docs say `max-bot-mentions: 0` escapes every bot mention, but its schema rejects 0. It is 1.
8. `CONTRIBUTING.md` said every comment "ends with" the disclosure line; gh-aw appends its footer after
   it. It also said "post one comment" where the limit is at most one. Both reworded.
9. `AGENTS.md` said the action pin was "checked against the gh-aw release tag" before anything checked
   it; CI now does.
10. Two commit messages overstate. The one that adds the agent says mentions are limited to the author
   (gh-aw also lets through assignees and the dispatcher; see Mentions above) and that failures never
   open issues (the detection tracking issue could, see 2). The one that closes those paths says a
   missing-tool report could open an issue (the lock said so; the runtime would not have). The history
   is not rewritten for this; this ledger is the correction.

## Not enforced yet

- The 1,500-character limit, mentioning only the author, and citing only issues the duplicate search
  returned are enforced by `validate_plan.py`, which the agent runs itself. Safe outputs enforce looser
  limits: one mention among author, assignees and dispatcher, the allowed domains, this repository's
  references, and gh-aw's 65,000-character cap.
- Whether the labels and comments are right is not measured here; the evaluation measures it. One
  known effect: the agent cannot remove labels, so on #2 the form's `bug` stays next to its `question`.
- gh-aw's default tool list allows `Task` (subagents). Its cost is bounded by the AIC caps, not by turns.
- The sandbox does not run upstream's regex labeler, so `service/*` labels the agent leaves to it are
  never added here.
- "Latest release" means the newest entry in the pinned `CHANGELOG.md` (6.70.0); upstream may have
  released since.
- The kill switch relies on GitHub search, which can take a moment to index a new label. Not timed.
- `CODEOWNERS` has no effect without a branch rule, and with one owner it cannot require a second person.
