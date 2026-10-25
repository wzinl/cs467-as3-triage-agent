# Issue-triage agent for the Terraform AWS Provider (CS467 AS3)

This repository will configure an existing AI agent, Claude Code run by GitHub Agentic Workflows, to give
new issues on [hashicorp/terraform-provider-aws](https://github.com/hashicorp/terraform-provider-aws) a
first-pass triage. It is a sandbox: the agent is never deployed to the upstream repository. So far it holds
the need analysis and the sandbox base; the agent's configuration comes later. Start with
[`AGENTS.md`](AGENTS.md) for the layout, the commands and the rules.

## Why issue triage

Upstream already runs the conventional layer (checked at upstream commit `1e015f7`, 2026-10-23):
`triage.yml` adds `needs-triage` and regex `service/*` labels, `community_note.yml` posts a fixed note on
every new issue, the issue forms mark fields as required, and `stale.yml` marks long-idle issues. What it
misses needs judgement: whether the configuration is really there, whether an older issue is the same bug
in other words, whether a released fix already covers the named resource, and whether a comment would help.

The need is measured in [`evals/metrics/`](evals/metrics/README.md). Over 609 reporter issues, one
maintainer made 77% of the `needs-triage` removals. Issues opened from Friday noon to Sunday (UTC) waited a
median of 2.84 days for that removal, against 0.66 days otherwise. Only 17% got any written maintainer comment.

## Status

| Date | Contents |
|---|---|
| 2026-10-24 | Workflow choice, need analysis (`evals/data`, `evals/metrics`), claim checks (`verification`) |
| 2026-10-25 | Pinned copy of the upstream files a triage agent reads (`sandbox/`), upstream's labels, `AGENTS.md` |

Every number in this file, `AGENTS.md` and `evals/metrics/README.md` is checked against the generated outputs by
`python3 verification/check_claims.py`, which CI runs on every push.
