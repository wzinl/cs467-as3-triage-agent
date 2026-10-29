#!/usr/bin/env python3
"""Create or update this repository's labels from upstream's label definitions in infrastructure/repository,
plus the agent's kill-switch label.

Upstream applies those .tf files with Terraform's GitHub provider. This does the same with the REST API:
it reads every `github_issue_label` resource, creates labels that are missing and fixes the colour or
description of ones that differ. It never deletes a label.

Usage:
  python3 sandbox/sync_labels.py --list                 print the labels, touch nothing
  GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python3 sandbox/sync_labels.py
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TF = Path(__file__).resolve().parent.parent / "infrastructure" / "repository"


def parse_labels(text):
    """{name: (color, description)} for every github_issue_label resource in the .tf text."""
    variables = {}
    for name, body in re.findall(r'variable "(\w+)" \{\s*default = (.*?)\n  (?:description|type)', text, re.S):
        entries = re.findall(r'"([^"]+)" = \{\s*color\s*=\s*"(\w+)",?[^\n]*\n\s*description\s*=\s*"((?:[^"\\]|\\.)*)"', body)
        variables[name] = ({k: (c, d) for k, c, d in entries} if entries
                           else {v: None for v in re.findall(r'^\s*"([^"]+)",', body, re.M)})
    labels = {}
    for body in re.findall(r'resource "github_issue_label" "\w+" \{(.*?)\n\}', text, re.S):
        get = lambda key: re.search(rf'^\s*{key}\s*=\s*(.+?)\s*(?:#.*)?$', body, re.M).group(1)
        for key, value in variables[get("for_each").removeprefix("var.")].items():
            def fill(expr):
                if expr == "each.key":
                    return key
                if expr == "each.value.color":
                    return value[0]
                if expr == "each.value.description":
                    return value[1]
                return json.loads(expr).replace("${each.value}", key)
            labels[fill(get("name"))] = (fill(get("color")), fill(get("description")))
    return labels


def api(method, path, body=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}{path}", method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def main():
    wanted = parse_labels("\n".join(p.read_text() for p in sorted(TF.glob("labels-*.tf"))))
    if "--list" in sys.argv:
        for name, (color, desc) in sorted(wanted.items()):
            print(f"{name}\t{color}\t{desc}")
        print(f"{len(wanted)} labels", file=sys.stderr)
        return
    if os.environ["GITHUB_REPOSITORY"].lower().startswith("hashicorp/"):
        sys.exit("refusing to change labels on a hashicorp repository; this script is for the sandbox only")
    # The sandbox's own kill switch (CONTRIBUTING.md) must exist before anyone needs it.
    wanted["triage-agent-paused"] = ("B60205", "Kill switch: while any issue has this label, the triage agent does not run")
    have, page = {}, 1
    while batch := api("GET", f"/labels?per_page=100&page={page}"):
        have.update({l["name"]: (l["color"], l["description"] or "") for l in batch})
        page += 1
    created = updated = 0
    for name, (color, desc) in sorted(wanted.items()):
        if name not in have:
            api("POST", "/labels", {"name": name, "color": color, "description": desc})
            created += 1
        elif have[name] != (color, desc):
            api("PATCH", f"/labels/{urllib.parse.quote(name, safe='')}", {"color": color, "description": desc})
            updated += 1
        else:
            continue
        # GitHub's secondary rate limit allows about 80 writes a minute and 500 an hour.
        # ponytail: no retry; a rate-limit error stops the run, and a rerun skips labels that already match.
        time.sleep(1)
    print(f"{len(wanted)} labels wanted: {created} created, {updated} updated, {len(have)} existed before")


if __name__ == "__main__":
    main()
