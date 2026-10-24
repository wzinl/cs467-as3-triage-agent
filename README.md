# Issue-triage agent for the Terraform AWS Provider (CS467 AS3)

This repository configures an existing AI agent, Claude Code run by GitHub Agentic Workflows, to give new
issues on [hashicorp/terraform-provider-aws](https://github.com/hashicorp/terraform-provider-aws) a
first-pass triage. It is a sandbox: the agent is never deployed to the upstream repository.

## Why issue triage

Upstream already runs the conventional layer: `needs-triage` and regex `service/*` labels, a fixed
community note on every issue, required issue-form fields and a stale bot. What it misses needs judgement:
whether the configuration is really there, whether an older issue is the same bug in other words, whether a
released fix already covers the named resource, and whether a comment would help at all.

The need is measured in [`evals/metrics/`](evals/metrics/README.md): one maintainer removes 77% of the
`needs-triage` labels, issues opened over a weekend wait a median of 2.8 days against 0.7 on weekdays, and
only 17% of reporter issues get any written maintainer reply.

## Status

| Date | Contents |
|---|---|
| 2026-10-24 | Workflow choice and need analysis (`evals/data`, `evals/metrics`) |
