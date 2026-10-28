"""Unit tests for the issue-triage scripts. Run from the repo root: python3 -m unittest discover -s .claude/skills/issue-triage/tests"""
import fnmatch
import gzip
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / ".claude/skills/issue-triage/scripts"
sys.path.insert(0, str(SCRIPTS))
import triage_checks as tc  # noqa: E402
import validate_plan as vp  # noqa: E402
sys.path.insert(0, str(ROOT / "sandbox"))
import sync_labels  # noqa: E402

tc.REPO = vp.REPO = str(ROOT)
vp.WORKFLOW = str(ROOT / ".github/workflows/issue-triage.md")
FOOTER = vp.FOOTER

BUG = """### Terraform and AWS Provider Version

```console
Terraform v1.15.5
+ provider registry.terraform.io/hashicorp/aws v{ver}
```

### Affected Resource(s) or Data Source(s)

* `aws_s3_bucket`

### Expected Behavior

no drift

### Actual Behavior

drift

### Sample Terraform Configuration

<details open>
<summary>Click to expand configuration</summary>

```hcl

```
</details>

### Steps to Reproduce

apply twice
"""
AS_OF = datetime(2026, 9, 20, tzinfo=timezone.utc)


class Checks(unittest.TestCase):
    def test_release_dated_same_day_is_not_yet_known(self):
        # 6.60.0 is dated 2026-08-13; an issue opened at 02:42 that day must not see it.
        latest = tc.releases(datetime(2026, 8, 13, 2, 42, tzinfo=timezone.utc))[0][0]
        self.assertEqual(latest, "6.59.0")
        self.assertEqual(tc.releases(datetime(2026, 8, 14, tzinfo=timezone.utc))[0][0], "6.60.0")

    def test_reporter_on_same_day_release_counts_as_current(self):
        opened = datetime(2026, 8, 13, 2, 42, tzinfo=timezone.utc)
        v = tc.version_check(BUG.format(ver="6.60.0"), opened)
        self.assertEqual((v["latest_release"], v["provider_status"]), ("6.60.0", "current"))
        self.assertEqual(tc.version_check(BUG.format(ver="6.59.0"), opened)["latest_release"], "6.59.0")

    def test_newer_fix_for_named_resource_is_reported(self):
        body = BUG.format(ver="6.59.0").replace("aws_s3_bucket", "aws_network_acl_rule")
        v = tc.version_check(body, datetime(2026, 8, 14, tzinfo=timezone.utc), ["aws_network_acl_rule"])
        self.assertEqual(v["provider_status"], "current")
        self.assertEqual(v["newer_fixes"], ["6.60.0"])

    def test_empty_configuration_is_missing(self):
        f = tc.form_check(BUG.format(ver="6.60.0"))
        self.assertEqual(f["template"], "Report a Bug")
        self.assertIn("Sample Terraform Configuration", f["missing_required"])

    def test_versions(self):
        self.assertEqual(tc.version_check(BUG.format(ver="5.100.0"), AS_OF)["provider_status"], "older_major")
        self.assertEqual(tc.version_check(BUG.format(ver="6.40.0"), AS_OF)["provider_status"], "outdated")
        v = tc.version_check(BUG.format(ver="6.64.0"), AS_OF)
        self.assertEqual((v["provider_status"], v["latest_release"]), ("current", "6.65.0"))
        self.assertEqual(tc.version_check("no version here", AS_OF)["provider_status"], "not_reported")

    def test_release_notes_after_reported_version(self):
        v = tc.version_check(BUG.format(ver="6.60.0"), datetime(2026, 8, 20, tzinfo=timezone.utc), ["aws_bedrockagentcore_harness"])
        self.assertTrue(any(n["version"] == "6.61.0" and "Fix" in n["note"] for n in v["newer_release_notes"]))
        self.assertTrue(all(n["version"] != "6.62.0" for n in v["newer_release_notes"]))   # released after as_of

    def test_services(self):
        s = tc.service_check("aws_s3_bucket drift", BUG.format(ver="6.60.0"))
        self.assertIn("service/s3", s["regex_labeler_would_apply"])
        self.assertEqual(s["primary_service_label"], "service/s3")
        s = tc.service_check("Affected: aws_opensearch_domain.x", "aws_opensearch_domain.aiml_options")
        self.assertEqual((s["regex_labeler_would_apply"], s["primary_service_label"]), ([], "service/opensearch"))

    def test_resource_kinds(self):
        with mock.patch.object(tc, "known_resources", lambda: {"aws_s3_bucket", "data.aws_s3_bucket", "aws_iam_role"}):
            s = tc.service_check("New data source: aws_iam_role", "")
        self.assertEqual(s["resources_mentioned"][0],
                         {"name": "aws_iam_role", "resource_exists": True, "data_source_exists": False, "service_label": "service/iam"})

    def test_duplicate_search_ranks_the_same_issue_first(self):
        up = "https://github.com/hashicorp/terraform-provider-aws/issues/"
        corpus = [{"number": 1, "url": up + "1", "title": "aws_s3_bucket lifecycle rule drift", "body": "lifecycle rule drift after apply"},
                  {"number": 2, "url": up + "2", "title": "aws_iam_role trust policy error", "body": "trust policy"},
                  {"number": 3, "url": up + "3", "title": "aws_lambda_function timeout", "body": "timeout"}]
        issue = {"number": 1, "url": "https://github.com/wzinl/sandbox/issues/1", "repo": "wzinl/sandbox",
                 "title": "aws_s3_bucket: lifecycle rule drift", "body": "drift after apply"}
        hits = tc.similar_issues(issue, corpus)
        self.assertEqual((hits[0]["number"], hits[0]["ref"]), (1, "hashicorp/terraform-provider-aws#1"))
        self.assertNotIn(1, [h["number"] for h in tc.similar_issues({**issue, "url": up + "1"}, corpus)])   # never itself
        self.assertEqual(tc.ref(up + "2", "hashicorp/terraform-provider-aws"), "#2")


class Plan(unittest.TestCase):
    checks = {"services": {"primary_service_label": "service/opensearch", "regex_labeler_would_apply": ["service/iam", "bug"],
                           "resources_mentioned": [{"name": "aws_opensearch_domain", "service_label": "service/opensearch",
                                                    "resource_exists": True, "data_source_exists": False}]},
              "similar_issues": [{"number": 77, "ref": "hashicorp/terraform-provider-aws#77", "score": 0.5, "band": "likely"}]}
    issue = {"number": 9, "author": "reporter", "labels": ["bug"]}

    def errors(self, **plan):
        base = {"decision": "labels", "labels": [], "comment": None, "duplicate_of": [], "reason": "r"}
        return vp.validate({**base, **plan}, self.checks, self.issue)[0]

    def test_valid_plans(self):
        self.assertEqual(self.errors(labels=["service/opensearch"]), [])
        self.assertEqual(self.errors(decision="noop"), [])
        ok = f"Thanks, @reporter. Could you add the configuration?\n\n{FOOTER}"
        self.assertEqual(self.errors(decision="comment", labels=["waiting-response"], comment=ok), [])
        dup = f"Thanks, @reporter. This may be the same as hashicorp/terraform-provider-aws#77.\n\n{FOOTER}"
        self.assertEqual(self.errors(decision="comment", comment=dup, duplicate_of=[77]), [])
        self.assertEqual(self.errors(labels=["new-data-source"]), [])                 # only the resource exists

    def test_rejected_labels(self):
        self.assertTrue(self.errors(labels=["needs-triage"]))          # blocked
        self.assertTrue(self.errors(labels=["prioritized"]))           # blocked
        self.assertTrue(self.errors(labels=["tests"]))                 # exists, not allowlisted
        self.assertTrue(self.errors(labels=["bug"]))                   # already on the issue
        self.assertTrue(self.errors(labels=["service/iam"]))           # regex labeler adds it
        self.assertTrue(self.errors(labels=["service/s3"]))            # not about this issue
        self.assertTrue(self.errors(labels=["enhancement", "documentation"]))   # two type labels
        self.assertTrue(self.errors(labels=["a", "b", "c", "d"]))
        self.assertTrue(self.errors(labels=["waiting-response"]))      # needs a question
        self.assertTrue(self.errors(labels=["new-resource"]))          # aws_opensearch_domain exists

    def test_rejected_comments(self):
        def c(text):
            return self.errors(decision="comment", comment=text)
        self.assertTrue(c("Thanks @reporter."))                                         # no footer
        self.assertTrue(c(f"cc @ewbankkit\n\n{FOOTER}"))                                # mentions a maintainer
        self.assertTrue(c(f"I have closed the stale issues.\n\n{FOOTER}"))              # claims an action
        self.assertTrue(c(f"A maintainer has approved this.\n\n{FOOTER}"))
        self.assertTrue(c(f"Same as #12345.\n\n{FOOTER}"))                              # not a search result
        self.assertTrue(c(f"Same as #77.\n\n{FOOTER}"))                                 # #77 here is this repository's
        self.assertTrue(c(f"See https://github.com/hashicorp/terraform-provider-aws/issues/77\n\n{FOOTER}"))   # URL, not ref
        self.assertTrue(self.errors(decision="comment", comment=f"Thanks @reporter.\n\n{FOOTER}", duplicate_of=[77]))
        self.assertTrue(c(f"See https://example.invalid/x\n\n{FOOTER}"))                # domain not allowed
        self.assertTrue(c("x" * 1600 + FOOTER))
        self.assertTrue(self.errors(decision="noop", labels=["bug"]))

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            for name, obj in (("plan.json", {"decision": "noop", "labels": [], "comment": None, "reason": "x"}),
                              ("checks.json", self.checks), ("issue.json", self.issue)):
                Path(d, name).write_text(json.dumps(obj))
            env = {**os.environ, "TRIAGE_DIR": d}
            ok = subprocess.run([sys.executable, str(SCRIPTS / "validate_plan.py")], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stdout)
            Path(d, "plan.json").write_text("{not json")
            bad = subprocess.run([sys.executable, str(SCRIPTS / "validate_plan.py")], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1)


class Prepare(unittest.TestCase):
    def test_inputs_are_cut_at_the_issue_date(self):
        up = "https://github.com/hashicorp/terraform-provider-aws/issues/"
        corpus = [{"number": 1, "url": up + "1", "title": "a", "body": "b", "created_at": "2026-09-01T00:00:00Z",
                   "closed_at": "2026-10-02T00:00:00Z", "state_reason": "COMPLETED"},
                  {"number": 2, "url": up + "2", "title": "c", "body": None, "created_at": "2026-09-02T00:00:00Z",
                   "closed_at": "2026-09-03T00:00:00Z", "state_reason": "DUPLICATE"},
                  {"number": 3, "url": up + "3", "title": "later", "body": "", "created_at": "2026-10-02T00:00:00Z",
                   "closed_at": None, "state_reason": None}]
        raw = {"number": 5, "html_url": "https://github.com/o/r/issues/5", "repository_url": "https://api.github.com/repos/o/r",
               "title": "T", "body": "B\x00", "user": {"login": "u"}, "author_association": "NONE",
               "labels": [{"name": "bug"}], "created_at": "2026-10-01T00:00:00Z"}
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            with gzip.open(d / "corpus.json.gz", "wt") as f:
                json.dump(corpus, f)
            (d / "issue.json").write_text(json.dumps(raw))
            subprocess.run([sys.executable, str(SCRIPTS / "prepare_context.py"), "--issue", str(d / "issue.json"),
                            "--corpus", str(d / "corpus.json.gz"), "--out", str(d / "out")], cwd=ROOT, check=True, capture_output=True)
            issue = json.loads((d / "out/issue.json").read_text())
            got = json.loads((d / "out/corpus.json").read_text())["issues"]
            names = (d / "out/resources.txt").read_text().split()
            plan = json.loads((d / "out/plan.json").read_text())
        self.assertEqual((issue["repo"], issue["as_of"], issue["body"], issue["labels"]), ("o/r", "2026-10-01T00:00:00Z", "B", ["bug"]))
        self.assertEqual([(c["number"], c["state"], c["state_reason"]) for c in got], [(1, "open", None), (2, "closed", "duplicate")])
        self.assertIn("aws_s3_bucket", names)
        self.assertIn("data.aws_s3_bucket", names)
        self.assertIsNone(plan["decision"])

    def test_a_pull_request_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "issue.json").write_text(json.dumps({"number": 7, "pull_request": {}}))
            r = subprocess.run([sys.executable, str(SCRIPTS / "prepare_context.py"), "--issue", str(Path(d) / "issue.json"),
                                "--corpus", "unused", "--out", str(Path(d) / "out")], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("pull request", r.stderr)

    def test_as_of_replaces_the_creation_date_and_must_have_an_offset(self):
        up = "https://github.com/hashicorp/terraform-provider-aws/issues/"
        corpus = [{"number": n, "url": up + str(n), "title": "t", "body": "", "created_at": f"2026-09-0{n}T00:00:00Z",
                   "closed_at": None, "state_reason": None} for n in (1, 2)]
        raw = {"number": 5, "html_url": "https://github.com/o/r/issues/5", "repository_url": "https://api.github.com/repos/o/r",
               "title": "T", "body": "B", "user": {"login": "u"}, "author_association": "NONE", "labels": [],
               "created_at": "2026-10-29T00:00:00Z"}
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            with gzip.open(d / "corpus.json.gz", "wt") as f:
                json.dump(corpus, f)
            (d / "issue.json").write_text(json.dumps(raw))

            def prepare(as_of):
                return subprocess.run([sys.executable, str(SCRIPTS / "prepare_context.py"), "--issue", str(d / "issue.json"),
                                       "--corpus", str(d / "corpus.json.gz"), "--out", str(d / "out"), "--as-of", as_of],
                                      cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(prepare("2026-09-01T12:00:00Z").returncode, 0)
            issue = json.loads((d / "out/issue.json").read_text())
            got = json.loads((d / "out/corpus.json").read_text())["issues"]
            self.assertEqual((issue["created_at"], issue["as_of"], [c["number"] for c in got]),
                             ("2026-10-29T00:00:00Z", "2026-09-01T12:00:00Z", [1]))
            for bad in ("2026-09-01T12:00:00", "yesterday"):
                r = prepare(bad)
                self.assertNotEqual(r.returncode, 0, bad)
                self.assertIn("is not an ISO 8601 time", r.stderr)


class Config(unittest.TestCase):
    def test_taxonomy_matches_the_label_sync(self):
        text = "\n".join(p.read_text() for p in sorted((ROOT / "infrastructure/repository").glob("labels-*.tf")))
        synced = {name for name in sync_labels.parse_labels(text) if not name.startswith("partition/")}
        self.assertEqual(vp.taxonomy(), synced)

    def test_every_allowed_label_exists(self):
        allowed = vp.frontmatter_list("allowed", after="add-labels:")
        self.assertIn("service/*", allowed)
        for lab in allowed:
            self.assertTrue(any(fnmatch.fnmatch(t, lab) for t in vp.taxonomy()), lab)


if __name__ == "__main__":
    unittest.main()
