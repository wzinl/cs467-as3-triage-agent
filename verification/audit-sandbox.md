# Claim audit: sandbox base (2026-10-25)

This work added the sandbox base: a pinned copy of the upstream files a triage agent reads, upstream's
labels, `AGENTS.md`, and CI checks for both. Every claim it makes is listed here with what backs it.

## Checked on every push

`verification/check_claims.py` now covers `AGENTS.md`. Besides the numbers, it checks each upstream
convention `AGENTS.md` states against the imported file it comes from, that every path in backticks
exists, and that every command in its `sh` block is run by a workflow. CI also checks both checksum
manifests, re-imports the pinned commit and fails on any difference, runs the label parser tests, and
searches for Anthropic and GitHub token formats.

Each new check was shown to fail on a planted error before it was trusted:

| Planted error | Caught by |
|---|---|
| A misspelt command in `AGENTS.md` (`-s sandboxx`) | the command check |
| A misspelt path in `AGENTS.md` (`upstream-commit.text`) | the path check |
| A new number in `AGENTS.md` ("fetched 2 times") | the number check |
| A changed convention (`02_enhancement.yml` adds `bug`) | the stated-text check |
| An edit to an imported file (`docs/faq.md`) | the manifest and the fresh import |
| A new file inside an imported directory | the fresh import only |
| A GitHub token-shaped string in a tracked file | the credential search |

## Checked by hand

| Claim | Evidence |
|---|---|
| The import copies the listed upstream paths at `1e015f7` | `sandbox/import_upstream.sh` printed "imported 2449 files"; the manifest has one line per file; a second import leaves `git status` clean, here and in CI |
| Upstream defines 458 labels: 389 `service/*`, 5 `partition/*`, 64 others | `sync_labels.py --list`; the unit test counts them a second way from the `.tf` text. The 64 include 6 `size/*` labels |
| The sandbox has upstream's labels | [Labels run 1](https://github.com/wzinl/cs467-as3-triage-agent/actions/runs/40165921714) logged "458 labels wanted: 453 created, 5 updated, 10 existed before" in 10 minutes. The 5 updated are GitHub defaults upstream also defines (`bug`, `documentation`, `enhancement`, `good first issue`, `question`); the other 5 labels that already existed were left in place. `bug`, `service/xray`, `size/XXL` and `waiting-response` read back from the API with upstream's colour and description |
| A rerun changes nothing | [Labels run 2](https://github.com/wzinl/cs467-as3-triage-agent/actions/runs/40166567269) logged "458 labels wanted: 0 created, 0 updated, 463 existed before": all 458 match, plus those 5 other labels |
| Every label fits GitHub's limits | The unit test; the longest description is exactly 100 characters, the limit |
| `sync_labels.py` refuses a hashicorp repository | Run with `GITHUB_REPOSITORY=HashiCorp/terraform-provider-aws`: exit 1 before any request |
| Actions' token can only write to the repository the workflow runs in | GitHub's documented scope for `GITHUB_TOKEN`; not tested here |
| Every command in `AGENTS.md` works | All 8 ran from the repository root with exit code 0 |
| Upstream's `tcm` persona "Suggest[s] workarounds and alternatives to reported bugs" | `.agents/tcm.md` at `1e015f7`, read from the upstream clone |
| Copilot comments must open with a "not a required action" line | `.github/copilot-instructions.md` at `1e015f7`, "Review tone" section |

## Found and fixed

1. The first label test counted workflow labels as names without a slash and failed, 58 against 64. The
   parser was right: six workflow labels are `size/*`. The test now counts names outside `service/` and
   `partition/`.
2. `AGENTS.md` first said the commands need only Python 3 and coreutils. The import also needs `git` and
   `bash`; it now names `bash`, `python3`, `git` and coreutils.
3. `AGENTS.md` first said the planned agent would "ask for missing information only". The plan also has
   it point to likely duplicates and the right place for questions, so it now says that.

## Not enforced yet

- Deleting labels, issues or history: only `sync_labels.py`, which has no delete call, is covered.
  A branch rule against force-pushes to `main` needs the owner to set it; the governance tests check it.
- `CODEOWNERS` review, once the agent's configuration adds it, needs a branch rule to have any effect,
  and with one owner it cannot require a second person.
