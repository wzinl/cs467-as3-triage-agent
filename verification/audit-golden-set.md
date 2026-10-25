# Claim audit: golden set (2026-10-25)

This work added `evals/golden/`: the held-out draw (`select_cases.py`, `selection.json`), the case builder
(`build_cases.py`, `cases.md`), 38 cases with `input.json` and `expected.json`, the scorer (`score.py`) and
its tests (`test_golden.py`). No case has been run.

## Checked on every push

- `check_claims.py` checks every number in `evals/golden/README.md` and the new README row against
  `selection.json`, `cases.md` and the scripts. A planted `37/38` and `noop 7` in `cases.md`, and a pool of 30
  in the README's table, were each caught.
- CI redraws the held-out cases and rebuilds every `input.json` and `cases.md` from the issue snapshot and
  upstream's history, and fails if anything differs from what is committed.
- `build_cases.py` stops if a case's upstream commit lacks any file the agent reads. The tests check, for
  all 38 cases, that the commit is dated no later than the issue, that `as_of` is the issue's creation time,
  that the posted title and body have no mention or link left outside code, that the held-out cases are
  exactly the drawn issues and include no development case, that every expected label is in the workflow's
  allowlist, and that the scorer passes the expected outcome and fails a missing label, an extra label, a
  comment, extra mentions, a second comment and missing scripts.

## Checked by hand

| Claim | Evidence |
|---|---|
| No case has been run | The Issue triage workflow has 5 runs, all on test issues #1 and #2 (earlier smoke runs); `evals/golden/actual/` does not exist |
| Each `expected.json` follows the facts of its issue's day | Read every drawn issue, its timeline and its comments. Release facts from `CHANGELOG.md` at the case's commit: duplicate-49064 on 6.47.0, 8 minor releases behind 6.55.0; quiet-49875 on 6.58.0, 5 behind 6.63.0; not-planned-50065 on 6.64.0, 1 behind 6.65.0, whose only note for the resource changes another argument; duplicate-49404, duplicate-49263, waiting-48253 and quiet-48332 on the latest release |
| The requested resources did not exist | No `website/docs/r/` file for `aws_datazone_project_profile` at `fbbaf1768`, `aws_sesv2_email_identity_certificate` at `d987ba0fd` or `aws_ssoadmin_region` at `0031f353d` |
| The new-functionality form adds no label | `03_new_functionality.yml` at `0031f353d` has no `labels:` key; the bug, documentation and enhancement forms do |
| The duplicates' earlier issues were open and in the corpus | #47856, #48159, #47519 and #48099 are in `corpus.json.gz`, opened before their duplicates and still open when the duplicates were opened |
| Development case 20's rationale | `CHANGELOG.md` at `a2873d944` lists 6.60.0 as unreleased, with no `aws_network_acl_rule` entry |
| Development cases 06, 13 and 19 | At their commits the newest releases are 6.61.0 (August 19), 6.58.0 and 6.49.0 (June 4), as their rationales say |
| 3 of the 4 held-out duplicates were in the duplicate-search measurement | Checked against the skill's development records, which are not in this repository: #49064, #49404 and #48397 were among the 28 measured; #49263 was not. 19 of the 21 issues in the duplicate pool were, so leaving them out was not possible |
| Code spans stop mentions and links | GitHub's rendering; not tested here yet. The first posted case will show it |

## Found and fixed

1. The first draw included three development cases (#48394, #49761, #50100): the exclusion read only the
   issues the development `expected.json` files cite, and those files do not cite their own issue. The
   draw now also excludes every development case's issue. No drawn issue had been read.
2. The redirect and not-planned pools hold one issue each, so the redirect quota went from 2 to 1 and the
   waiting quota from 3 to 4, again before any drawn issue was read.
3. The exclusion then also read the generated `input.json` files, so a rebuild changed two quiet cases.
   It reads only `expected.json` now; the draw is back to the first one, and CI fails if it changes.
4. A shallow upstream fetch (`--shallow-since`) cuts main's history at any merge whose other parent is
   older than the cut, so it reached back only to 2026-07-06. The builder now uses main's whole history
   without trees (62 MB, about 4 s here); both histories gave the same commit for all 38 cases.
5. The `owner/repo#N` pattern matched inside other sites' URLs (`registry.terraform.io/x#1`), and URLs
   took trailing commas along. Both fixed, with a test.
6. Development cases: run-history wording removed; case 10 named a setting this workflow does not use; case
   20 said its release was missing from the changelog, when it is listed as unreleased without the fix;
   case 03 said the search "does not return" its duplicate, which nothing here measures.
7. Held-out maintainer histories were corrected before the commit: "no comment" where other people had
   commented, a release attributed to a docs fix without evidence, and the timing of two maintainer actions.

## Not enforced yet

- Nothing stops an `expected.json` from changing after its case is run; the git history shows it.
- A single author wrote every `expected.json`; nobody else has reviewed them.
- The live run that imports each case's upstream files and posts its neutral text is not built.
- Development case 10 tests the skip of maintainers' issues, so it must be opened by the owner.
