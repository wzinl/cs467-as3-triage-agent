#!/usr/bin/env python3
"""Fail when a claim in the docs is not backed by a generated output, a data file or the code.

Each claim is (doc, text the doc states, [(file, text it must contain), ...]). A file written "!path" must
NOT contain the text. Every number in a checked doc (outside code blocks; dates, times, versions and paths
are skipped) must also sit inside some claim's stated text, so a number cannot be added to a doc without
saying what backs it. Claims a substring cannot check (logic, upstream facts) go in verification/audit-*.md.

For AGENTS.md it also checks that every path in backticks exists and that every command in its `sh` block
is run by a workflow in .github/workflows, so the commands it lists are the ones CI runs.

Run the metric scripts first, as CI does (.github/workflows/checks.yml).
Usage: python3 verification/check_claims.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R, X, META = "evals/metrics/results.md", "evals/metrics/crosscheck.md", "evals/data/fetch_meta.json"
A, FORMS = "AGENTS.md", ".github/ISSUE_TEMPLATE/"

CLAIMS = [
    # README.md
    ("README.md", "Over 609 reporter issues, one maintainer made 77% of the `needs-triage` removals",
     [(X, "609 reporter issues of 761"), (X, "`justinretzolk`: 449/585 (77%)")]),
    ("README.md", "waited a median of 2.84 days for that removal, against 0.66 days otherwise",
     [(X, "| Friday noon to Sunday | 89 | 2.84 |"), (X, "| Monday to Friday noon | 495 | 0.66 |")]),
    ("README.md", "Only 17% got any written maintainer comment", [(X, "103/609 (17%)")]),
    # evals/metrics/README.md
    ("evals/metrics/README.md", "fetched once on 2026-10-24 from 03:13 to 03:20 UTC",
     [(META, '"started_at": "2026-10-24T03:13'), (META, '"finished_at": "2026-10-24T03:20')]),
    ("evals/metrics/README.md", "that script only sends GraphQL queries, never mutations",
     [("evals/data/fetch_upstream.py", '["gh", "api", "graphql"'), ("!evals/data/fetch_upstream.py", "mutation")]),
    ("evals/metrics/README.md", "the 761 issues opened 2026-06-01 to 2026-10-20, a 20-week window",
     [(X, "609 reporter issues of 761 opened 2026-06-01 to 2026-10-20"), (R, "one 20-week window")]),
    ("evals/metrics/README.md", "The 609 opened by reporters (author association NONE or CONTRIBUTOR)",
     [(X, "NONE 479, CONTRIBUTOR 130")]),
    ("evals/metrics/README.md", "Every other issue in the window was opened by a MEMBER or COLLABORATOR",
     [(X, "NONE 479, CONTRIBUTOR 130, MEMBER 78, COLLABORATOR 74.")]),
    ("evals/metrics/README.md", "| Reporter issues per full ISO week (19 weeks) | median 30, at most 42 |",
     [(R, "Full ISO weeks: 19."), (R, "Reporter issues per week: median 30, max 42.")]),
    ("evals/metrics/README.md", "| median 0.83 (584 issues) | both |",
     [(X, "| any time | 584 | 0.83 |"), (R, "| `needs-triage` removed | 0.8 | 584/609")]),
    ("evals/metrics/README.md", "| median 0.66 (495 issues) |", [(X, "| Monday to Friday noon | 495 | 0.66 |")]),
    ("evals/metrics/README.md", "| median 2.84 (89 issues) |", [(X, "| Friday noon to Sunday | 89 | 2.84 |")]),
    ("evals/metrics/README.md", "| 449 of 585 (77%); 4 accounts in all, one a bot |",
     [(X, "`justinretzolk`: 449/585 (77%)"), (X, "4 accounts removed `needs-triage`, 1 of them a bot.")]),
    ("evals/metrics/README.md", "| 103 (17%), median 1.06 days to the first |",
     [(X, "103/609 (17%)"), (X, "median 1.06,")]),
    ("evals/metrics/README.md", "| 44 (7%) | both |",
     [(R, "Closed as duplicate or marked duplicate: 44/609 (7%)."),
      (X, "Closed as duplicate or marked duplicate: 44/609 (7%).")]),
    ("evals/metrics/README.md", "| 114, on 67 of 580 labelled issues (12%); 113 of them added by the regex labeler |",
     [(R, "Maintainers removed 114 `service/*` labels, on 67/580 (12%)"),
      (X, "removed 114 of those labels, on 67/580 (12%)"), (X, "`github-actions` 113,"),
      (X, "`github-actions` is the account upstream's regex labeler")]),
    ("evals/metrics/README.md", "| 105 issues, median age 380.5 days |",
     [(R, "Open with `needs-triage`: 105"), (R, "Age of those 105: median 380.5 days")]),
    ("evals/metrics/README.md", "One repository and one 20-week window, June to October 2026",
     [(R, "One repository, one 20-week window.")]),
    ("evals/metrics/README.md", "The fetch kept the first 30 comments and 60 timeline events per issue. 2 issues had more "
     "comments, and none reached 60 events.",
     [(R, "the first 30 comments (2 issues had more) and the first 60 timeline events (none reached it)"),
      (X, "Only the first 30 comments per issue were fetched; 2 issues had more.")]),
    ("evals/metrics/README.md", "17% counts written replies only", [(X, "103/609 (17%)")]),
    ("evals/metrics/README.md", "The newest issue was opened 3.2 days before the fetch",
     [(X, "The newest issue was opened 3.2 days before the fetch")]),
    # AGENTS.md: the upstream conventions, checked against the imported files
    (A, "a type (`bug`, `enhancement`, `documentation` or `question`) and a section, usually the AWS service",
     [("docs/issue-reporting-and-lifecycle.md", 'Type is one of "bug", "enhancement", "documentation", or "question", '
       "and section is usually the AWS service name.")]),
    (A, "`.github/ISSUE_TEMPLATE/00_bug_report.yml` adds `bug`", [(FORMS + "00_bug_report.yml", "labels: - bug")]),
    (A, "`01_documentation.yml` adds `documentation`", [(FORMS + "01_documentation.yml", "labels: - documentation")]),
    (A, "`02_enhancement.yml` adds `enhancement`", [(FORMS + "02_enhancement.yml", "labels: - enhancement")]),
    (A, "Blank issues are off, and questions belong on discuss.hashicorp.com",
     [(FORMS + "config.yml", "blank_issues_enabled: false"),
      (FORMS + "config.yml", "url: https://discuss.hashicorp.com/c/terraform-providers/tf-aws")]),
    (A, "the package is the `provider_package_correct` (or the block name) of a `service` block",
     [("names/data/names_data.hcl", 'service "s3" {'), ("names/data/names_data.hcl", 'provider_package_correct = "s3"'),
      ("infrastructure/repository/labels-service.tf", 'name = "service/${each.value}"')]),
    (A, "for example `aws_s3_bucket` to `service/s3`",
     [(".github/labeler-issue-triage.yml", "service/s3: - '((\\*|-)\\s*`?|(data|resource)\\s+\"?)aws_(canonical_user_id|s3_bucket")]),
    (A, "`aws_<name>` is documented in `website/docs/r/<name>.html.markdown`, and the data source of the same name in",
     [("website/docs/r/s3_bucket.html.markdown", "# Resource: aws_s3_bucket"),
      ("website/docs/d/s3_bucket.html.markdown", "# Data Source: aws_s3_bucket")]),
    (A, "as `## X.Y.Z (Month DD, YYYY)` with sections such as `BUG FIXES:`",
     [("CHANGELOG.md", "## 6.70.0 (October 21, 2026)"), ("CHANGELOG.md", "BUG FIXES:")]),
    (A, "The copy starts at 6.0.0, so older fixes are not in it",
     [("CHANGELOG.md", "## 6.0.0 (June 18, 2025)"), ("!CHANGELOG.md", "## 5.")]),
    (A, "`docs/ai-usage.md` asks for transparency", [("docs/ai-usage.md", "transparency, accountability and quality")]),
    (A, "`sandbox/sync_labels.py` refuses one",
     [("sandbox/sync_labels.py", '.lower().startswith("hashicorp/"): sys.exit(')]),
    (A, "`sandbox/sync_labels.py` has no delete call", [("!sandbox/sync_labels.py", '"DELETE"')]),
    (A, "CI: a search for Anthropic and GitHub token formats",
     [(".github/workflows/checks.yml", "! git grep -nIE 'sk-ant-")]),
]

NUM = re.compile(r"(?<![\w./:§-])\d[\d,.]*(?![\w/:-])")


def norm(s):
    return re.sub(r"\s+", " ", s)


def read(path):
    return norm((ROOT / path).read_text())


def numbers(text):
    return {m.group().rstrip(".,") for m in NUM.finditer(text)}


problems = []
for doc, stated, backing in CLAIMS:
    if norm(stated) not in read(doc):
        problems.append(f"{doc}: no longer says {stated!r}; update or remove the claim")
    for path, text in backing:
        present = norm(text) in read(path.lstrip("!"))
        if present == path.startswith("!"):
            problems.append(f"{doc}: {stated!r} needs {path.lstrip('!')} {'not ' * path.startswith('!')}to contain {text!r}")
workflows = norm(" ".join(p.read_text() for p in sorted((ROOT / ".github/workflows").glob("*.yml"))))
agents = (ROOT / A).read_text()
for block in re.findall(r"```sh\n(.*?)```", agents, re.S):
    for line in block.splitlines():
        command = norm(line.split("  #")[0]).strip()
        if command and command not in workflows:
            problems.append(f"{A}: the command {command!r} is not run by any workflow in .github/workflows")
for path in re.findall(r"`([^`\s<]+)`", agents):
    if (ROOT / path.split("/")[0]).exists() and not list(ROOT.glob(path.rstrip("/"))):
        problems.append(f"{A}: the path {path} does not exist")
for doc in sorted({c[0] for c in CLAIMS}):
    prose = re.sub(r"```.*?```", "", read(doc))
    covered = set().union(*(numbers(norm(s)) for d, s, _ in CLAIMS if d == doc))
    for n in sorted(numbers(prose) - covered):
        problems.append(f"{doc}: the number {n} is not inside any claim in CLAIMS")

print("\n".join(problems) or f"all {len(CLAIMS)} claims backed")
sys.exit(bool(problems))
