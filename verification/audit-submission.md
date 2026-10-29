# Submission check (2026-10-29)

Every check below ran on a fresh clone of `main` at `ffbc5e0`, the merge of PR #50. What the review changed is
under "Found and fixed".

## From a fresh clone

| Check | Result |
|---|---|
| Every step of `.github/workflows/checks.yml` that runs offline or against upstream: metric regeneration, claim check, `DESIGN.md` length, both manifests, a fresh upstream import, the label, skill and golden tests, the rescore, the drift check, the held-out redraw with a case rebuild and check replay from a new upstream clone, a gh-aw v0.93.4 compile, and the credential search | All pass, and none leaves a change in `git status` |
| The two steps that need GitHub's API: the action pin against gh-aw's release tag, and the kill-switch label | Passed in CI on `ffbc5e0`: [run 40844621465](https://github.com/wzinl/cs467-as3-triage-agent/actions/runs/40844621465) |
| The evaluation reproduces | `score.py` rebuilds `evals/golden/results-2026-10-28.md` from the 38 collected runs unchanged, and `select_cases.py`, `build_cases.py` and `replay_checks.py` rebuild the draw, every `input.json` and `replay.md` unchanged. The live runs are not repeated: each needs the second account, and the collected runs are what the scorer reads |
| Links | Every relative link in the authored Markdown resolves. The 56 Actions runs the docs cite all exist (the repository's run list, read 2026-10-29) |
| History | 32 commits, all authored as the owner, with no trailers; no schedule wording, no full upstream issue reference in a commit message, no credential |

## The brief, requirement by requirement

| Requirement | Where it is met |
|---|---|
| Workflow chosen, why an agent and not conventional automation | `DESIGN.md`, "Why this workflow, and why an agent"; `README.md` |
| Need measured from repository data, with the period and the metric's limits | `evals/metrics/README.md` |
| Trigger, explicit permissions, allowed tools, safe outputs with limits, timeout, network restricted | Frontmatter of `.github/workflows/issue-triage.md`, compiled into `issue-triage.lock.yml` |
| The agent cannot close or delete issues, merge pull requests or force-push | Agent job `contents: read`, `issues: read`; the only outputs are a comment, labels and no-op; tested by dev 16 |
| `AGENTS.md`: commands, structure, conventions, forbidden changes | `AGENTS.md`, one section each |
| Skill with a procedure and scripts; checks that need no judgement automated; skill use verified | `.claude/skills/issue-triage/`; `score.py` reports `skill_loaded` and both scripts for every run in `evals/golden/results-2026-10-28.md` |
| `CONTRIBUTING.md` with an AI-contribution policy | `CONTRIBUTING.md`, "AI-contribution policy" |
| Each rule where it can be enforced | `DESIGN.md`, "Where each rule lives"; `AGENTS.md`, "Forbidden changes" |
| Sandbox repository with a copy of the upstream files | This repository; `sandbox/` and the commit in `sandbox/upstream-commit.txt` |
| At least 10 real historical inputs, including cases needing no action | 33 real cases (16 held-out, 17 dev); 8 held-out cases expect no action |
| Context preserved, without later information | Each `input.json` (`upstream_commit`, `as_of`); `evals/golden/README.md`, "What each case holds" and "Limits" |
| Expected outcome recorded before running | `verification/audit-golden-set.md`: the last change under `evals/golden/cases/` predates the first case issue |
| At least one adversarial input | 5: 2 held-out, 3 dev |
| Actual output compared with the expected outcome for every case; every failure reported and explained | `evals/golden/results-2026-10-28.md`; `verification/audit-golden-set.md`, "Live run" |
| Each governance control implemented or explained, tested apart from proposed; untrusted inputs and actions | `DESIGN.md`, "Governance" and "Untrusted inputs"; `verification/audit-governance.md` |
| The five questions, the first one tested | `DESIGN.md`, "The five questions"; dev 16 through the real trigger |
| `DESIGN.md`: why this workflow, why the controls fit its risks, a rejected alternative, what is prevented, what the tests revealed, what is unresolved | One section or paragraph each |
| Bill of materials: model and whether it is pinned, instructions, tools and MCP servers, permissions, data sources, logs, evaluations, responsible humans | `DESIGN.md`, "Agent bill of materials" |
| AI-use statement at the end | `DESIGN.md`, last section |
| `DESIGN.md` at most 150 lines, normal formatting | CI step in `.github/workflows/checks.yml` |
| `evals/golden/`: inputs, expected outcomes, actual outputs, logs, how to reproduce | `cases/*/*/input.json` and `expected.json`; `actual/2026-10-28/` (outputs and tool-call traces); each result links its run log; `evals/golden/README.md`, "Running a case" |

## Found and fixed

1. `DESIGN.md` did not say why the controls fit the agent's risks, which the brief asks for. A paragraph now
   opens "Governance".
2. Its AI-use statement said Claude Code ran every test, which also covered the owner's phone steps, and named
   only two of the three pull requests the owner merged. Both corrected.
3. `CONTRIBUTING.md` said the model "is pinned in the workflow". It is named there, and has no dated version.
4. `evals/golden/README.md` said each `expected.json` "is written by hand" by "a single author". Claude Code
   wrote them, as the AI-use statement says; `verification/audit-golden-set.md` is corrected the same way.
5. `evals/metrics/README.md` still called the agent "planned".
6. `verification/audit-sandbox.md` still listed the branch rule and `CODEOWNERS` as open; both exist since
   2026-10-29.

## Not done here

- The submission tag goes on `main` once this change merges.
