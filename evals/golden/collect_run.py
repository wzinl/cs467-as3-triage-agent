#!/usr/bin/env python3
"""Turn one live run of a golden case into actual/<run>/<case>.json, the file score.py reads.

Inputs, saved from the GitHub API after the run finished:
  AGENT_LOG      the log of the run's agent job (plain text, or the JSON get_job_logs returns, with logs_content)
  DETECTION_LOG  the log of its detection job, or - when detection did not run
  ISSUE          {"author": login of who opened the issue, "labels": [names on the issue after the run],
                  "comments": [{"author": login, "body": str}]}
The agent's trace comes from the Claude Code stream-json lines in the agent log: the skill, the commands, the
denials, the safe-output calls as made, and plan.json as it stood at the last validate_plan.py run that passed
(rebuilt from the agent's edits, starting from the empty plan prepare_context.py writes). What was applied is
read from the issue: the labels added beyond the case's form labels, and the comment github-actions[bot] posted.
Usage: python3 evals/golden/collect_run.py RUN CASE_ID AGENT_LOG DETECTION_LOG ISSUE
       python3 evals/golden/collect_run.py RUN CASE_ID --skipped    (the workflow skipped the issue, as it should for dev 10)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1] / ".claude/skills/issue-triage/scripts"))
from prepare_context import EMPTY_PLAN  # noqa: E402

BOT = "github-actions[bot]"
ALLOWED = re.search(r"allowed: \[(.*)\]", (HERE.parents[1] / ".github/workflows/issue-triage.md").read_text()).group(1)
ALLOWED = [a.strip().strip('"') for a in ALLOWED.split(",")]


def log_text(path):
    text = Path(path).read_text()
    return json.loads(text)["logs_content"] if text.lstrip().startswith("{") else text


def stream(log):
    """The JSON objects Claude Code printed, in order (each log line is a timestamp, then the object)."""
    for line in log.split("\n"):
        start = line.find("{")
        if start > 0 and line[:start].strip().endswith("Z"):
            try:
                yield json.loads(line[start:])
            except ValueError:
                pass


def result_text(r):
    c = r.get("content")
    return c if isinstance(c, str) else "".join(x.get("text", "") for x in c or [] if isinstance(x, dict))


def trace_of(log):
    uses, results, final = [], {}, {}
    for o in stream(log):
        content = (o.get("message") or {}).get("content") or []
        if o.get("type") == "assistant":
            uses += [c for c in content if c.get("type") == "tool_use"]
        elif o.get("type") == "user":
            results.update({c["tool_use_id"]: c for c in content if isinstance(c, dict) and c.get("type") == "tool_result"})
        elif "total_cost_usd" in o:
            final = o
    plan, validated, raw, commands = json.dumps(EMPTY_PLAN, indent=2), None, [], []
    for u in uses:
        r = results.get(u["id"], {})
        ok, inp, name = not r.get("is_error"), u["input"], u["name"]
        if name == "Bash":
            commands.append(inp.get("command", ""))
            if "validate_plan.py" in inp.get("command", "") and re.search(r'"ok":\s*true', result_text(r)):
                validated = json.loads(plan)
        elif name in ("Edit", "Write") and ok and inp.get("file_path", "").endswith("/plan.json"):
            plan = inp["content"] if name == "Write" else plan.replace(inp["old_string"], inp["new_string"], -1 if inp.get("replace_all") else 1)
        elif name.startswith("mcp__safeoutputs__"):
            kind = name.removeprefix("mcp__safeoutputs__")
            out = {"type": kind}
            if kind == "add_labels":
                out["labels"] = [x["name"] if isinstance(x, dict) else x for x in inp.get("labels", [])]
            elif kind == "add_comment":
                out["body"] = inp.get("body", "")
            else:
                out["message"] = inp.get("message") or inp.get("reason") or ""
            raw.append(out)
    return raw, {"skill_loaded": any(u["name"] == "Skill" and u["input"].get("skill") == "issue-triage"
                                     and "Launching skill" in result_text(results.get(u["id"], {})) for u in uses),
                 "bash_commands": commands, "tool_calls": [u["name"] for u in uses],
                 "permission_denials": final.get("permission_denials") or [], "validated_plan": validated,
                 "result": {"total_cost_usd": final.get("total_cost_usd"), "num_turns": final.get("num_turns")}}


def detection_cost(log):
    # the detection run prints no result object; gh-aw's token-usage step prints its total (1 AI credit = USD 0.01)
    credits = re.findall(r"AI Credits: ([\d.]+)", log)
    return float(credits[-1]) / 100 if credits else 0


def collect(case_dir, agent_log, detection_log, issue):
    form = set(json.loads((case_dir / "input.json").read_text())["issue"]["form_labels"])
    raw, trace = trace_of(agent_log)
    comments = [c["body"] for c in issue["comments"] if c["author"] == BOT]
    emitted = [lab for o in raw if o["type"] == "add_labels" for lab in o["labels"]]
    bad = [lab for lab in emitted if lab not in ALLOWED and not (lab.startswith("service/") and "service/*" in ALLOWED)]
    return {"skipped": False, "author": issue["author"],
            "applied": {"labels": sorted(set(issue["labels"]) - form), "comment": comments[-1] if comments else None,
                        "rejected": [{"type": "add_labels", "labels": bad}] if bad else []},
            "raw_outputs": raw, "detection_cost_usd": detection_cost(detection_log) if detection_log else 0, "trace": trace}


def main():
    if len(sys.argv) == 4 and sys.argv[3] == "--skipped":
        actual = {"skipped": True}
    elif len(sys.argv) == 6:
        detection = None if sys.argv[4] == "-" else log_text(sys.argv[4])
        actual = collect(next((HERE / "cases").glob(f"*/{sys.argv[2]}")), log_text(sys.argv[3]), detection,
                         json.loads(Path(sys.argv[5]).read_text()))
    else:
        sys.exit(__doc__)
    out = HERE / "actual" / sys.argv[1] / f"{sys.argv[2]}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(actual, indent=2, ensure_ascii=False) + "\n")
    print(out)


if __name__ == "__main__":
    main()
