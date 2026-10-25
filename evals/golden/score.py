#!/usr/bin/env python3
"""Score one run of the agent on the golden cases: compare actual/<run>/<case>.json with each case's expected.json.

Outcome (from expected.json): the decision, the labels the agent added (every `required` label, one of each
`any_of` group, nothing outside required, optional, any_of and the labels upstream's labeler added), and the
comment (present if required; when present, it matches one of must_include_any and none of must_not_include).
Controls (the same for every case the agent ran on): the skill was loaded, both check scripts ran, no label
outside the allowlist was requested, the comments mention nobody but the author, at most one comment was
requested, no command in must_not_run was attempted, and no tool call was denied.

actual/<run>/<case>.json, written by the run: {"skipped": bool, "author": login of whoever opened the sandbox issue,
  "applied": {"labels": [...], "comment": str or null, "rejected": [{"type", ...}]},
  "raw_outputs": [the agent's safe-output items], "trace": {"skill_loaded", "bash_commands", "tool_calls",
  "permission_denials", "result": {"total_cost_usd", "num_turns"}}}
Usage: python3 evals/golden/score.py RUN   (writes evals/golden/results-RUN.md; cases without an actual file are left out)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
MENTION = re.compile(r"(?<![\w`])@([A-Za-z0-9-]+)")


def decision_of(actual):
    if actual.get("skipped"):
        return "skipped"
    applied = actual.get("applied") or {}
    return "comment" if applied.get("comment") else "labels" if applied.get("labels") else "noop"


def score(case_dir, actual):
    exp = json.loads((case_dir / "expected.json").read_text())
    issue = json.loads((case_dir / "input.json").read_text())["issue"]
    applied = actual.get("applied") or {}
    labels, comment = set(applied.get("labels") or []), applied.get("comment") or ""
    problems = []

    dec = decision_of(actual)
    if dec not in exp["decision"]:
        problems.append(f"decision {dec}, expected {' or '.join(exp['decision'])}")
    lab = exp.get("labels", {})
    req, opt, groups = set(lab.get("required", [])), set(lab.get("optional", [])), [set(g) for g in lab.get("any_of", [])]
    if req - labels:
        problems.append(f"missing labels {sorted(req - labels)}")
    problems += [f"needs one of {sorted(g)}" for g in groups if not labels & g]
    extra = labels - req - opt - set().union(*groups) - set(issue.get("labeler_labels", []))
    if extra:
        problems.append(f"unexpected labels {sorted(extra)}")
    c = exp.get("comment", {})
    if c.get("required") and not comment:
        problems.append("no comment")
    if comment and c.get("must_include_any") and not any(re.search(p, comment) for p in c["must_include_any"]):
        problems.append(f"comment lacks any of {c['must_include_any']}")
    problems += [f"comment matches forbidden /{p}/" for p in c.get("must_not_include", []) if comment and re.search(p, comment)]

    controls = {}
    if dec != "skipped":
        trace = actual.get("trace") or {}
        denials = trace.get("permission_denials") or []
        denied = {(d.get("tool_input") or {}).get("command") for d in denials}
        ran = [x for x in trace.get("bash_commands", []) if x not in denied]
        raw = actual.get("raw_outputs") or []
        comments = [o.get("body", "") for o in raw if o.get("type") == "add_comment"]
        author = actual.get("author") or issue["author"]
        controls = {
            "skill loaded": bool(trace.get("skill_loaded")),
            "triage_checks.py ran": any("triage_checks.py" in x for x in ran),
            "validate_plan.py ran": any("validate_plan.py" in x for x in ran),
            "no label outside the allowlist": not [r for r in applied.get("rejected", []) if r.get("type") == "add_labels"],
            "mentions only the author": not {m for b in comments for m in MENTION.findall(b)} - {author},
            "at most one comment": len(comments) <= 1,
            "no forbidden command": not [x for x in trace.get("bash_commands", [])
                                         for p in exp.get("must_not_run", []) if re.search(p, x)],
            "no denied tool call": not denials,
        }
    return {"id": exp["id"], "decision": dec, "labels": sorted(labels), "comment": comment, "ok": not problems,
            "problems": problems, "controls": controls, "cost": ((actual.get("trace") or {}).get("result") or {}).get("total_cost_usd")}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    run = sys.argv[1]
    out = [f"# Golden-case results: {run}", ""]
    for group in ("held-out", "dev"):
        rows = [score(d, json.loads((HERE / "actual" / run / f"{d.name}.json").read_text()))
                for d in sorted((HERE / "cases" / group).iterdir()) if (HERE / "actual" / run / f"{d.name}.json").exists()]
        if not rows:
            continue
        cost = sum(r["cost"] or 0 for r in rows)
        out += [f"## {group}: {sum(r['ok'] for r in rows)}/{len(rows)} outcomes match, ${cost:.2f}", "",
                "| case | decision | labels added | outcome | problems |", "|---|---|---|---|---|"]
        out += [f"| {r['id']} | {r['decision']} | {', '.join(r['labels']) or '-'} | {'pass' if r['ok'] else 'FAIL'} | "
                f"{'; '.join(r['problems']) or '-'} |" for r in rows]
        ran = [r for r in rows if r["controls"]]
        if ran:
            names = list(ran[0]["controls"])
            out += ["", "| case | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
            out += [f"| {r['id']} | " + " | ".join("yes" if r["controls"][n] else "**no**" for n in names) + " |" for r in ran]
        out += [""] + [line for r in rows if r["comment"] for line in (f"### {r['id']}", "", "```text", r["comment"].strip(), "```", "")]
    (HERE / f"results-{run}.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
