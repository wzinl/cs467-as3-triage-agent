#!/usr/bin/env python3
"""Deterministic first-pass checks for a newly opened issue.

Reads   $TRIAGE_DIR/issue.json, corpus.json and resources.txt (default /tmp/gh-aw/agent;
        prepare_context.py writes them),
        plus .github/ISSUE_TEMPLATE/*.yml, .github/labeler-issue-triage.yml and
        CHANGELOG.md from the repository checkout (the current directory).
Writes  $TRIAGE_DIR/checks.json and prints the same JSON to stdout.

No judgement happens here: the script reports facts (missing form fields,
versions, mentioned resources, regex service matches, similar earlier issues)
and the agent decides what to do with them. Standard library only.
"""
import glob
import json
import math
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

TRIAGE_DIR = os.environ.get("TRIAGE_DIR", "/tmp/gh-aw/agent")
REPO = os.environ.get("TRIAGE_REPO_ROOT", ".")

# Similarity bands for the duplicate search. Starting values, not yet calibrated against labelled duplicates.
DUP_LIKELY = 0.40
DUP_POSSIBLE = 0.28
TOP_K = 5

STOP = set("""the and for with that this from are was were has have had not but can could would should
will when then than into onto there their they them its it's also any all one two use used using
what which who how why where does did doing done get got set make made like just only some more most
very much many such each other same issue issues bug error errors terraform provider aws resource
resources data source sources resolve resolved please thanks thank expected actual behavior behaviour
version versions response steps reproduce output config configuration sample relevant panic debug
logging important facts references would you implement fix enhancement description affected none
true false null new add support supported""".split())


def load_json(name, default=None):
    path = os.path.join(TRIAGE_DIR, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_date(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


# ---------- issue forms ----------

def template_required_fields():
    """{template name: {field label: required}} parsed from .github/ISSUE_TEMPLATE/*.yml."""
    out = {}
    for path in sorted(glob.glob(os.path.join(REPO, ".github/ISSUE_TEMPLATE/*.yml"))):
        if path.endswith("config.yml"):
            continue
        name, fields, label = None, {}, None
        for line in open(path, encoding="utf-8"):
            m = re.match(r"^name:\s*(.+)$", line)
            if m:
                name = m.group(1).strip().strip("\"'")
            m = re.match(r"^\s+label:\s*(.+)$", line)
            if m:
                label = m.group(1).strip().strip("\"'")
                fields[label] = False
            if label and re.match(r"^\s+required:\s*true", line):
                fields[label] = True
        if name:
            out[name] = fields
    return out


def split_sections(body):
    sections, current = {}, None
    for line in (body or "").splitlines():
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            current = m.group(1)
            sections[current] = []
        elif current:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def is_empty(text):
    t = re.sub(r"<[^>]+>", "", text or "")            # <details>, <summary> wrappers
    t = re.sub(r"Click to expand[^\n]*", "", t)
    t = re.sub(r"```[a-z]*", "", t)                     # empty code fences
    t = t.replace("_No response_", "")
    return not re.search(r"\w", t)


def form_check(body):
    sections = split_sections(body)
    templates = template_required_fields()
    best, best_score, best_overlap = None, 0, 0
    for name, fields in templates.items():
        overlap = len(set(fields) & set(sections))
        missing = sum(1 for f, req in fields.items() if req and f not in sections)
        if overlap - missing > best_score:   # the closest form: most shared headings, fewest absent required ones
            best, best_score, best_overlap = name, overlap - missing, overlap
    if not best or best_overlap < 2:
        return {"template": None, "missing_required": [], "empty_optional": [], "used_form": False}
    fields = templates[best]
    missing = [f for f, req in fields.items() if req and (f not in sections or is_empty(sections[f]))]
    empty_opt = [f for f, req in fields.items() if not req and f in sections and is_empty(sections[f])]
    return {"template": best, "missing_required": missing, "empty_optional": empty_opt, "used_form": True}


# ---------- versions ----------

def releases(as_of, same_day=False):
    """[(version, date, [changelog bullet lines])] for releases dated before as_of's day, newest first."""
    out, current = [], None
    path = os.path.join(REPO, "CHANGELOG.md")
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        if line.startswith("## "):
            current = None
            m = re.match(r"^## (\d+\.\d+\.\d+) \(([A-Z][a-z]+ \d{1,2}, \d{4})\)", line)
            if m:
                d = datetime.strptime(m.group(2), "%B %d, %Y").replace(tzinfo=timezone.utc)
                # CHANGELOG dates have no time of day, so a release dated the day the issue was opened
                # may have come out after it. Count only releases from earlier days.
                if d.date() < as_of.date() or same_day and d.date() == as_of.date():
                    current = (m.group(1), d.date().isoformat(), [])
                    out.append(current)
        elif current and line.startswith("* "):
            current[2].append(line[2:].strip())
    return out


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


def version_check(body, as_of, resources=()):
    text = body or ""
    tf = re.search(r"Terraform v?(\d+\.\d+\.\d+)", text)
    prov = (re.search(r"hashicorp/aws v?(\d+\.\d+\.\d+)", text)
            or re.search(r"(?i)aws provider[^\n0-9]{0,30}v?(\d+\.\d+\.\d+)", text)
            or re.search(r"(?i)provider[^\n0-9]{0,20}version[^\n0-9]{0,10}v?(\d+\.\d+\.\d+)", text))
    rel = releases(as_of)
    if prov:   # a reporter on a release dated that same day shows it was already out
        rel = [r for r in releases(as_of, same_day=True) if r[0] == prov.group(1) and r not in rel] + rel
    latest = rel[0][0] if rel else None
    notes = []
    out = {"terraform": tf.group(1) if tf else None,
           "provider": prov.group(1) if prov else None,
           "latest_release": latest,
           "latest_release_date": rel[0][1] if rel else None,
           "provider_status": "unknown"}
    if out["provider"] and latest:
        p, l = vtuple(out["provider"]), vtuple(latest)
        if p > l:
            out["provider_status"] = "newer_than_latest_release"
        elif p[0] < l[0]:
            out["provider_status"] = "older_major"
        else:
            behind = len({vtuple(v)[:2] for v, _, _ in rel if vtuple(v)[:2] > p[:2]})
            out["minor_releases_behind"] = behind
            out["provider_status"] = "current" if behind <= 3 else "outdated"
        # Release notes, newer than the reported version, that mention a resource named in the issue.
        pattern = re.compile(r"\b(?:%s)\b" % "|".join(map(re.escape, resources))) if resources else None
        for v, d, lines in rel:
            if pattern and vtuple(v) > p:
                notes += [{"version": v, "date": d, "note": l[:220]} for l in lines if pattern.search(l)]
    elif not out["provider"]:
        out["provider_status"] = "not_reported"
    notes.sort(key=lambda n: ("fix" not in n["note"].lower(), vtuple(n["version"])))   # fixes first, oldest first
    out["newer_release_notes"] = notes[:8]
    out["newer_fixes"] = sorted({n["version"] for n in notes if "fix" in n["note"].lower()}, key=vtuple)
    return out


# ---------- resources and service labels ----------

RES_RE = re.compile(r"\baws_[a-z0-9]+(?:_[a-z0-9]+)+\b")


def known_resources():
    """Names in resources.txt: `aws_x` for a resource, `data.aws_x` for a data source."""
    names = set()
    path = os.path.join(TRIAGE_DIR, "resources.txt")
    if os.path.exists(path):
        names.update(l.strip() for l in open(path, encoding="utf-8") if l.strip())
    return names


def labeler_rules():
    """[(label, compiled regex, compiled resource-name regex)] from the upstream regex labeler configs."""
    rules, label = [], None
    lines = []
    for name in ("labeler-issue-triage.yml", "labeler-issue-trigger.yml"):
        path = os.path.join(REPO, ".github", name)
        if os.path.exists(path):
            lines += open(path, encoding="utf-8").read().splitlines()
    for line in lines:
        m = re.match(r"^([A-Za-z0-9_/.-]+):\s*$", line)
        if m:
            label = m.group(1)
            continue
        m = re.match(r"^\s+-\s+(['\"])(.*)\1\s*$", line)
        if m and label:
            raw = m.group(2).replace("''", "'") if m.group(1) == "'" else json.loads('"' + m.group(2) + '"')
            tail = raw.split('"?)', 1)[1] if '"?)' in raw else None
            try:
                rules.append((label, re.compile(raw), re.compile(tail) if tail else None))
            except re.error:
                pass
    return rules


def service_check(title, body):
    text = (title or "") + "\n" + (body or "")
    rules = labeler_rules()
    regex_labels = sorted({lab for lab, rx, _ in rules if rx.search(text)})
    mentioned = list(dict.fromkeys(RES_RE.findall(text)))
    known = known_resources()

    def service_of(name):
        for lab, _, tail in rules:
            if lab.startswith("service/") and tail and tail.match(name):
                return lab
        return None

    sections = split_sections(body)
    affected = RES_RE.findall(sections.get("Affected Resource(s) or Data Source(s)", ""))
    title_res = RES_RE.findall(title or "")
    primary_from = title_res or affected or mentioned
    primary = next((s for s in map(service_of, primary_from) if s), None)
    return {
        "resources_mentioned": [
            {"name": n, "resource_exists": (n in known) if known else None,
             "data_source_exists": ("data." + n in known) if known else None, "service_label": service_of(n)}
            for n in mentioned[:15]
        ],
        "regex_labeler_would_apply": regex_labels,
        "primary_service_label": primary,
    }


# ---------- duplicate search ----------

def clean_body(body):
    # Drop the version block: provider and platform lines are the same in every report and drown the signal.
    b = re.sub(r"(?ms)^### Terraform and AWS Provider Version.*?(?=^### |\Z)", "\n", body or "")
    b = re.sub(r"(?m)^\s*(\+ provider |Terraform v\d|on [a-z]+_[a-z0-9]+\s*$).*$", " ", b)
    b = re.sub(r"(?m)^###\s+.*$", " ", b)
    b = b.replace("_No response_", " ")
    b = re.sub(r"<[^>]+>", " ", b)
    b = re.sub(r"https?://\S+", " ", b)
    return b[:1000]


def tokens(title, body):
    def tok(s):
        return [t for t in re.findall(r"[a-z0-9_]+", s.lower())
                if len(t) > 2 and t not in STOP and not t.isdigit()]
    return tok(title or "") * 2 + tok(clean_body(body))


def ref(url, repo):
    """How the comment refers to an issue: #N in the same repository, owner/repo#N in another one.
    Cross-repository references are escaped by the workflow's safe outputs, so they never notify the other repository."""
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/issues/(\d+)$", url or "")
    if not m:
        return None
    return "#" + m.group(2) if m.group(1).lower() == (repo or "").lower() else f"{m.group(1)}#{m.group(2)}"


def similar_issues(issue, corpus):
    docs = [(c, Counter(tokens(c.get("title"), c.get("body")))) for c in corpus
            if c.get("url") is None or c.get("url") != issue.get("url")]
    if not docs:
        return []
    df = Counter()
    for _, tf in docs:
        df.update(tf.keys())
    n = len(docs)

    def vec(tf):
        v = {t: (1 + math.log(c)) * (1 + math.log((n + 1) / (df.get(t, 0) + 1))) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    q = vec(Counter(tokens(issue.get("title"), issue.get("body"))))
    scored = []
    for c, tf in docs:
        d = vec(tf)
        s = sum(w * d.get(t, 0.0) for t, w in q.items())
        if s > 0:
            scored.append((s, c))
    scored.sort(key=lambda x: -x[0])
    out = []
    for s, c in scored[:TOP_K]:
        excerpt = re.sub(r"\s+", " ", clean_body(c.get("body")).replace("`", "")).strip()[:400]
        out.append({"number": c["number"], "ref": ref(c.get("url"), issue.get("repo")),
                    "title": c.get("title"), "body_excerpt": excerpt,
                    "state": c.get("state"), "state_reason": c.get("state_reason"),
                    "created_at": c.get("created_at"), "score": round(s, 3),
                    "band": "likely" if s >= DUP_LIKELY else "possible" if s >= DUP_POSSIBLE else "weak"})
    return out


def main():
    issue = load_json("issue.json")
    if issue is None:
        print(json.dumps({"error": "issue.json not found in " + TRIAGE_DIR}))
        return 1
    corpus = (load_json("corpus.json", {}) or {}).get("issues", [])
    as_of = parse_date(issue.get("as_of") or issue.get("created_at")) or datetime.now(timezone.utc)
    form = form_check(issue.get("body"))
    services = service_check(issue.get("title"), issue.get("body"))
    report = {
        "issue": {"number": issue.get("number"), "title": issue.get("title"),
                  "author_association": issue.get("author_association"),
                  "labels_at_open": issue.get("labels", [])},
        "as_of": as_of.isoformat(),
        "form": form,
        "services": services,
        "versions": version_check(issue.get("body"), as_of, [r["name"] for r in services["resources_mentioned"]]),
        "similar_issues": similar_issues(issue, corpus),
        "corpus_size": len(corpus),
        "thresholds": {"likely": DUP_LIKELY, "possible": DUP_POSSIBLE},
    }
    with open(os.path.join(TRIAGE_DIR, "checks.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    return 0


def egress_probe():
    # Network test only (test branch): report whether this sandbox can reach anything outside it.
    import socket
    import urllib.request
    for url in ["https://example.com", "https://api.github.com/zen", "https://registry.terraform.io",
                "https://api.anthropic.com"]:
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                print(f"EGRESS_PROBE {url} -> REACHED (HTTP {r.status})", file=sys.stderr)
        except Exception as e:
            print(f"EGRESS_PROBE {url} -> BLOCKED ({type(e).__name__}: {e})", file=sys.stderr)
    for host, port in [("1.1.1.1", 443), ("8.8.8.8", 53)]:
        try:
            socket.create_connection((host, port), timeout=8).close()
            print(f"EGRESS_PROBE tcp {host}:{port} -> REACHED", file=sys.stderr)
        except Exception as e:
            print(f"EGRESS_PROBE tcp {host}:{port} -> BLOCKED ({type(e).__name__}: {e})", file=sys.stderr)
    print("EGRESS_PROBE proxy env: " + ", ".join(f"{k}={os.environ.get(k)}" for k in
          ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "NO_PROXY")), file=sys.stderr)


if __name__ == "__main__":
    egress_probe()
    sys.exit(main())
