# AGENTS.md

This repository is a sandbox for a first-pass issue-triage agent for
[hashicorp/terraform-provider-aws](https://github.com/hashicorp/terraform-provider-aws). It holds a pinned
copy of the upstream files a triage agent reads, the need analysis, the agent (a GitHub Agentic Workflows
workflow that runs Claude Code with a skill), the golden cases it is evaluated on, and the checks behind every
claim. No golden case has been run yet. Nothing here acts on the upstream repository.

## Commands

Run from the repository root. They need `bash`, `python3`, `git` and coreutils only; nothing to install.
CI (`.github/workflows/checks.yml`) runs each of them on every push, so a change is done when they all pass.

```sh
python3 evals/metrics/compute_metrics.py > /dev/null     # regenerate evals/metrics/results.md
python3 evals/metrics/crosscheck_metrics.py > /dev/null  # regenerate evals/metrics/crosscheck.md
python3 verification/check_claims.py                      # every number in the docs is backed
sha256sum -c evals/data/snapshot.sha256 --quiet           # the issue snapshot is unchanged
sha256sum -c sandbox/upstream.sha256 --quiet              # the upstream copy is unchanged
python3 -m unittest discover -s sandbox                   # label parser tests
python3 -m unittest discover -s .claude/skills/issue-triage/tests   # triage script tests
python3 -m unittest discover -s evals/golden              # golden-case and scorer tests
python3 evals/golden/select_cases.py > /dev/null          # redraw the held-out cases; must change nothing
git init -q ../upstream && git -C ../upstream fetch -q --filter=tree:0 https://github.com/hashicorp/terraform-provider-aws main
python3 evals/golden/build_cases.py ../upstream > /dev/null   # rebuild every case input; must change nothing
python3 sandbox/sync_labels.py --list                     # print upstream's labels, change nothing
sandbox/import_upstream.sh                                # re-import the pinned commit (needs network)
```

After a re-import, `git status` must be clean unless the pinned commit changed. To create or update the
repository's labels, run the Labels workflow (`.github/workflows/labels.yml`) from the Actions tab.

The agent's limits live in the frontmatter of `.github/workflows/issue-triage.md`. After editing it, run
`gh aw compile issue-triage` with gh-aw v0.93.4 and commit the regenerated `.github/workflows/issue-triage.lock.yml`
with it; CI recompiles and fails on any difference. To triage an issue by hand, run the Issue triage workflow
from the Actions tab with its number.

## Structure

| Path | What it is | Changed only by |
|---|---|---|
| `.github/ISSUE_TEMPLATE/`, `.github/labeler-issue-triage.yml`, `.github/labeler-issue-trigger.yml`, `.github/SUPPORT.md`, `CHANGELOG.md`, `LICENSE`, `docs/`, `infrastructure/repository/`, `names/`, `website/docs/` | Upstream files at the commit in `sandbox/upstream-commit.txt` | `sandbox/import_upstream.sh` |
| `sandbox/` | Import script, its checksum manifest, label sync and its tests | hand |
| `evals/data/` | Read-only snapshot of upstream issues, fetched once | `evals/data/fetch_upstream.py`, then `evals/data/pack.py` |
| `evals/metrics/` | Need analysis: two scripts and the outputs they write | outputs: running the scripts |
| `evals/golden/` | Golden cases (`cases/held-out/`, `cases/dev/`), the held-out draw, the case builder, the scorer and their tests | `selection.json`, `cases.md` and every `input.json`: the two scripts; `expected.json`: hand, before the case's first run |
| `verification/` | `check_claims.py` and the claim audits (`verification/audit-*.md`) | hand |
| `.github/workflows/` | `checks.yml` (CI), `labels.yml`, and the agent: `issue-triage.md` and its compiled `issue-triage.lock.yml` | hand; the lock file only by `gh aw compile` |
| `.github/aw/actions-lock.json` | The commit that gh-aw's runtime actions are pinned to | hand; CI checks it against the gh-aw release tag |
| `.claude/skills/issue-triage/` | The agent's skill: procedure, comment format, the scripts it runs and their tests | hand |
| `CONTRIBUTING.md`, `.github/CODEOWNERS` | How to change the agent, the AI-contribution policy, review owners | hand |

## Upstream conventions a triage agent follows

Each is taken from the imported files, which are the reference when this list and they differ.

- **Two labels per issue**: a type (`bug`, `enhancement`, `documentation` or `question`) and a section,
  usually the AWS service (`docs/issue-reporting-and-lifecycle.md`).
- **Issue forms add the type label**: `.github/ISSUE_TEMPLATE/00_bug_report.yml` adds `bug`,
  `01_documentation.yml` adds `documentation` and `02_enhancement.yml` adds `enhancement`. Blank issues are
  off, and questions belong on discuss.hashicorp.com (`.github/ISSUE_TEMPLATE/config.yml`).
- **Service labels** are `service/<package>`, where the package is the `provider_package_correct` (or the
  block name) of a `service` block in `names/data/names_data.hcl`. The regex labeler
  (`.github/labeler-issue-triage.yml`) maps resource names to them, for example `aws_s3_bucket` to
  `service/s3`. A label exists only if `infrastructure/repository/labels-*.tf` defines it; never invent one.
- **Resource docs**: `aws_<name>` is documented in `website/docs/r/<name>.html.markdown`, and the data
  source of the same name in `website/docs/d/`.
- **Releases** are in `CHANGELOG.md` as `## X.Y.Z (Month DD, YYYY)` with sections such as `BUG FIXES:`, and
  entries like `* resource/aws_<name>: ... ([#N](...))`. The copy starts at 6.0.0, so older fixes are not in it.
- **AI use is disclosed**: `docs/ai-usage.md` asks for transparency, and upstream's
  [Copilot instructions](https://github.com/hashicorp/terraform-provider-aws/blob/1e015f77bf1464d7ca816f19a506ee55d3f92a7f/.github/copilot-instructions.md)
  make AI review comments open with a note that they are not a required action.
- **Upstream's own agent guidance** is its
  [AGENTS.md](https://github.com/hashicorp/terraform-provider-aws/blob/1e015f77bf1464d7ca816f19a506ee55d3f92a7f/AGENTS.md)
  and the personas in [`.agents/`](https://github.com/hashicorp/terraform-provider-aws/tree/1e015f77bf1464d7ca816f19a506ee55d3f92a7f/.agents).
  Its [`tcm` persona](https://github.com/hashicorp/terraform-provider-aws/blob/1e015f77bf1464d7ca816f19a506ee55d3f92a7f/.agents/tcm.md)
  triages issues and also suggests workarounds. The agent built here adds labels and posts at most one
  comment, which asks for missing information or points to a likely duplicate or the right place, with no
  workarounds or other technical advice. So it does not adopt that persona.

## Forbidden changes

| Rule | Where it is enforced |
|---|---|
| Do not edit the upstream copy by hand; change the commit in `sandbox/import_upstream.sh` and re-run it | CI: the manifest check, and a fresh import must leave `git status` clean |
| Do not edit the issue snapshot; a re-fetch replaces it whole and rewrites `evals/data/snapshot.sha256` | CI: the snapshot manifest, and the regenerated metric outputs must match the committed ones |
| Do not edit `.github/workflows/issue-triage.lock.yml` by hand; edit the `.md` and recompile | CI: recompiles with gh-aw v0.93.4 and fails on any difference |
| The agent's comments mention only the issue author, link only allow-listed domains, and never reference an issue in another repository (which would show up in that issue's timeline) | `validate_plan.py`, then the workflow's safe outputs (`mentions`, `allowed-github-references`, `allowed-domains`) |
| Do not add a number to a checked doc without registering what backs it | CI: `verification/check_claims.py` |
| Do not change a case's `expected.json` after the case has been run; add a new case instead | Not enforced yet; the git history shows it |
| Do not run anything that writes to a hashicorp repository | `sandbox/sync_labels.py` refuses one; Actions' token can only write to this repository |
| Do not commit credentials; the API key lives in the repository's Actions secrets | CI: a search for Anthropic and GitHub token formats |
| Do not delete labels, issues or history | `sandbox/sync_labels.py` has no delete call; not otherwise enforced yet |
