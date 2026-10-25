#!/usr/bin/env python3
"""Check the agent's triage plan against the repository's rules before anything is posted.

Reads $TRIAGE_DIR/plan.json (written by the agent), checks.json (from triage_checks.py) and
issue.json, plus the label taxonomy in infrastructure/repository/labels-*.tf and the label
allowlist and allowed domains in .github/workflows/issue-triage.md.

Prints {"ok": bool, "errors": [...], "warnings": [...]}; exits 1 when there are errors.
The safe-outputs limits in the workflow enforce the hard caps again after the agent finishes;
this script exists so the agent can fix a bad plan instead of having it rejected.
"""
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

TRIAGE_DIR = os.environ.get("TRIAGE_DIR", "/tmp/gh-aw/agent")
REPO = os.environ.get("TRIAGE_REPO_ROOT", ".")
WORKFLOW = os.path.join(REPO, ".github/workflows/issue-triage.md")

FOOTER = "_Automated first-pass triage. A maintainer will review this issue and make every decision on it._"
TYPE_LABELS = {"bug", "enhancement", "documentation", "question"}
NEW_KIND = {"new-resource": "resource_exists", "new-data-source": "data_source_exists"}
NEEDS_COMMENT = {"waiting-response", "question", "upstream-terraform"}
ISSUE_URL = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/(?:issues|pull)/\d+")
REF = re.compile(r"(?<![\w/])((?:[\w.-]+/[\w.-]+)?#\d+)")
MAX_LABELS, MAX_COMMENT = 3, 1500
# First-person claims of actions the agent cannot take, or appeals to authority it does not have.
FORBIDDEN = re.compile(r"(?i)\b(I|we)(\s+have|'ve|\s+will|'ll)?\s+(closed|close|closing|locked|lock|removed|remove|"
                       r"assigned|assign|merged|merge|deleted|delete|prioriti[sz]ed?)\b|maintainer[s]? (has|have) approved")


def load(name):
    with open(os.path.join(TRIAGE_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def frontmatter_list(key, after=None):
    """Return the inline YAML list for `key:` in the workflow frontmatter (optionally after a section)."""
    text = Path(WORKFLOW).read_text(encoding="utf-8").split("\n---", 1)[0]
    if after:
        text = text.split(after, 1)[1]
    m = re.search(rf"^\s*{re.escape(key)}:\s*\[(.*?)\]", text, re.M)
    return [x.strip().strip("\"'") for x in m.group(1).split(",")] if m else []


def taxonomy():
    names = set()
    path = os.path.join(REPO, "infrastructure/repository/labels-workflow.tf")
    names.update(re.findall(r'^\s*"([^"]+)"\s*=\s*\{', Path(path).read_text(encoding="utf-8"), re.M))
    path = os.path.join(REPO, "infrastructure/repository/labels-service.tf")
    names.update("service/" + s for s in re.findall(r'^\s*"([a-z0-9]+)",?\s*$', Path(path).read_text(encoding="utf-8"), re.M))
    return names


def validate(plan, checks, issue):
    errors, warnings = [], []
    decision = plan.get("decision")
    labels = plan.get("labels") or []
    comment = plan.get("comment")
    dups = plan.get("duplicate_of") or []

    if decision not in ("comment", "labels", "noop"):
        errors.append("decision must be one of comment, labels, noop")
    if not plan.get("reason"):
        errors.append("reason is required (one line, kept in the run log)")
    if decision == "noop" and (labels or comment):
        errors.append("a noop plan must have no labels and no comment")
    if decision == "labels" and (comment or not labels):
        errors.append("a labels plan needs at least one label and no comment")
    if decision == "comment" and not comment:
        errors.append("a comment plan needs a comment")

    # labels
    allowed = frontmatter_list("allowed", after="add-labels:")
    blocked = frontmatter_list("blocked", after="add-labels:")
    known = taxonomy()
    services = checks.get("services", {})
    service_ok = {services.get("primary_service_label")} | {r.get("service_label") for r in services.get("resources_mentioned", [])}
    already = set(issue.get("labels", []))
    if len(labels) > MAX_LABELS:
        errors.append(f"at most {MAX_LABELS} labels")
    if len(labels) != len(set(labels)):
        errors.append("duplicate labels in plan")
    for lab in labels:
        if any(fnmatch.fnmatch(lab, b) for b in blocked) or not any(fnmatch.fnmatch(lab, a) for a in allowed):
            errors.append(f"label {lab!r} is not on the workflow allowlist")
        elif lab not in known:
            errors.append(f"label {lab!r} does not exist in infrastructure/repository/labels-*.tf")
        if lab in already:
            errors.append(f"label {lab!r} is already on the issue")
        if lab in services.get("regex_labeler_would_apply", []):
            errors.append(f"{lab!r} is redundant: the regex labeler already applies it")
        if lab.startswith("service/") and lab not in service_ok:
            errors.append(f"{lab!r} does not match any resource named in the issue (see checks.services)")
    if len([l for l in labels if l in TYPE_LABELS]) > 1:
        errors.append("at most one type label (bug, enhancement, documentation, question)")
    for lab, field in NEW_KIND.items():
        named = services.get("resources_mentioned", [])
        if lab in labels and named and all(r.get(field) for r in named):
            errors.append(f"{lab!r}, but every aws_ name in the issue already exists (see checks.services.resources_mentioned)")
    if already & TYPE_LABELS and set(labels) & TYPE_LABELS:
        warnings.append("the issue form already set a type label; add another only if the form label is clearly wrong")
    for lab in NEEDS_COMMENT & set(labels):
        if not comment:
            errors.append(f"{lab!r} needs a comment that explains it to the reporter")
    if "waiting-response" in labels and comment and "?" not in comment:
        errors.append("waiting-response needs a comment that asks the reporter a question")

    # comment
    if comment:
        if len(comment) > MAX_COMMENT:
            errors.append(f"comment is {len(comment)} characters; the limit is {MAX_COMMENT}")
        if FOOTER not in comment:
            errors.append("comment must end with the disclosure footer from references/comment-format.md")
        mentions = set(re.findall(r"(?<![\w`])@([A-Za-z0-9-]+)", comment))
        if mentions - {issue.get("author")}:
            errors.append(f"only the issue author may be mentioned, found {sorted(mentions)}")
        domains = set(frontmatter_list("allowed-domains")) | {"github.com"}
        for url in re.findall(r"https?://[^\s)>\]]+", comment):
            host = re.sub(r"^https?://([^/]+).*", r"\1", url).lower()
            if url.startswith("http://") or not any(host == d or host.endswith("." + d) for d in domains):
                errors.append(f"link {url} is not on an allowed https domain")
        for url in ISSUE_URL.findall(comment):
            errors.append(f"refer to {url} by the `ref` the duplicate search printed, not by its URL")
        candidates = {c.get("ref") for c in checks.get("similar_issues", [])}
        for r in set(REF.findall(comment)) - candidates - {f"#{issue.get('number')}"}:
            errors.append(f"{r} is referenced but was not returned by the duplicate search")
        if FORBIDDEN.search(comment):
            errors.append("comment claims an action the agent cannot take or an approval it cannot verify")

    # duplicates
    for n in dups:
        c = {c["number"]: c for c in checks.get("similar_issues", [])}.get(n)
        if not c:
            errors.append(f"duplicate_of #{n} is not a duplicate-search candidate")
        elif c["band"] == "weak":
            warnings.append(f"#{n} scored {c['score']} (weak); cite it only if the titles and bodies clearly match")
        if c and comment and not re.search(re.escape(c["ref"]) + r"(?!\d)", comment):
            errors.append(f"duplicate_of {n} must be referenced in the comment as {c['ref']}")
    if dups and not comment:
        errors.append("a suspected duplicate must be explained in a comment")
    return errors, warnings


def main():
    try:
        plan, checks, issue = load("plan.json"), load("checks.json"), load("issue.json")
    except FileNotFoundError as e:
        print(json.dumps({"ok": False, "errors": [f"missing {e.filename}; run triage_checks.py first"], "warnings": []}))
        return 1
    except json.JSONDecodeError as e:
        print(json.dumps({"ok": False, "errors": [f"plan.json is not valid JSON: {e}"], "warnings": []}))
        return 1
    errors, warnings = validate(plan, checks, issue)
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
