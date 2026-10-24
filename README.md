# Issue-triage agent for the Terraform AWS Provider (CS467 AS3)

This repository will configure an existing AI agent, Claude Code run by GitHub Agentic Workflows, to give
new issues on [hashicorp/terraform-provider-aws](https://github.com/hashicorp/terraform-provider-aws) a
first-pass triage. It is a sandbox: the agent is never deployed to the upstream repository. So far it holds
the need analysis; the agent's configuration comes later.

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

Every number in this file and in `evals/metrics/README.md` is checked against the generated outputs by
`python3 verification/check_claims.py`, which CI runs on every push.
