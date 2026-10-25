"""Tests for the golden cases, their builder and the scorer. Run from the repo root: python3 -m unittest discover -s evals/golden"""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_cases import DEV, neutralize  # noqa: E402
from score import score  # noqa: E402

ROOT = HERE.parents[1]
CASES = sorted(p for p in (HERE / "cases").glob("*/*") if p.is_dir())
ALLOWED = re.search(r"allowed: \[(.*)\]", (ROOT / ".github/workflows/issue-triage.md").read_text()).group(1)
ALLOWED = [a.strip().strip('"') for a in ALLOWED.split(",")]


class Neutralize(unittest.TestCase):
    def test_links_and_mentions_go_into_code_spans(self):
        text, spans = neutralize("cc @someone and @org/team, see #12, GH-3, other/repo#4 and "
                                 "https://github.com/o/r/issues/5, [here](https://github.com/o/r/pull/6).")
        self.assertEqual(spans, ["@someone", "@org/team", "#12", "GH-3", "other/repo#4",
                                 "https://github.com/o/r/issues/5", "[here](https://github.com/o/r/pull/6)"])
        self.assertEqual(text, "cc `@someone` and `@org/team`, see `#12`, `GH-3`, `other/repo#4` and "
                               "`https://github.com/o/r/issues/5`, `[here](https://github.com/o/r/pull/6)`.")

    def test_code_emails_and_other_links_are_left_alone(self):
        text = "mail a@b.com\n```\n@x #1\n```\nrun `@y #2`; docs https://registry.terraform.io/x#1; ### Heading"
        self.assertEqual(neutralize(text), (text, []))

    def test_a_link_whose_text_is_code_still_gets_its_url_in_a_code_span(self):
        self.assertEqual(neutralize("[`x`](https://github.com/o/r/issues/1)")[0], "[`x`](`https://github.com/o/r/issues/1`)")

    def test_it_is_idempotent(self):
        once = neutralize("@a #1 https://github.com/o/r/issues/2 [`x`](https://github.com/o/r/pull/3)")[0]
        self.assertEqual(neutralize(once), (once, []))


class Cases(unittest.TestCase):
    def test_every_case_has_both_files_and_matching_ids(self):
        for d in CASES:
            for name in ("input.json", "expected.json"):
                self.assertEqual(json.loads((d / name).read_text())["id"], d.name, f"{d}/{name}")

    def test_the_sets(self):
        held = [d for d in CASES if d.parent.name == "held-out"]
        self.assertEqual(len([d for d in CASES if d.parent.name == "dev"]), 20)
        self.assertEqual(len(held), 18)
        self.assertEqual(sum(d.name.startswith("adversarial-") for d in held), 2)
        drawn = json.loads((HERE / "selection.json").read_text())["drawn"]
        self.assertEqual(sorted(int(d.name.rsplit("-", 1)[1]) for d in held), sorted(n for ns in drawn.values() for n in ns))
        self.assertFalse({int(d.name.rsplit("-", 1)[1]) for d in held} & set(DEV.values()))

    def test_expected_files_use_known_decisions_and_allowed_labels(self):
        for d in CASES:
            exp = json.loads((d / "expected.json").read_text())
            self.assertTrue(exp["decision"] and set(exp["decision"]) <= {"comment", "labels", "noop", "skipped"}, d.name)
            labels = exp["labels"].get("required", []) + exp["labels"].get("optional", []) + sum(exp["labels"].get("any_of", []), [])
            for label in labels:
                self.assertTrue(label in ALLOWED or label.startswith("service/") and "service/*" in ALLOWED, f"{d.name}: {label}")
            for p in exp["comment"].get("must_include_any", []) + exp["comment"]["must_not_include"] + exp.get("must_not_run", []):
                re.compile(p)

    def test_context_predates_the_issue_and_posted_text_is_neutral(self):
        for d in CASES:
            case = json.loads((d / "input.json").read_text())
            self.assertLessEqual(case["upstream_commit_date"], case["as_of"], d.name)
            self.assertEqual(case["as_of"], case["issue"]["created_at"], d.name)
            for key in ("title", "body"):
                self.assertEqual(neutralize(case["posted"][key])[1], [], f"{d.name} {key}")


class Score(unittest.TestCase):
    CASE = HERE / "cases/held-out/new-50107"   # requires new-resource; upstream's labeler added service/datazone and service/sts

    def run_case(self, labels=(), comment=None, raw=(), commands=("python3 triage_checks.py", "python3 validate_plan.py")):
        return score(self.CASE, {"author": "reporter", "applied": {"labels": list(labels), "comment": comment, "rejected": []},
                                 "raw_outputs": list(raw), "trace": {"skill_loaded": True, "bash_commands": list(commands)}})

    def test_the_expected_outcome_passes(self):
        r = self.run_case(["new-resource"])
        self.assertTrue(r["ok"], r["problems"])
        self.assertTrue(all(r["controls"].values()), r["controls"])

    def test_labels_the_labeler_added_are_neither_required_nor_penalised(self):
        self.assertTrue(self.run_case(["new-resource", "service/datazone"])["ok"])

    def test_a_missing_or_unexpected_label_or_a_comment_fails(self):
        self.assertEqual(self.run_case([])["problems"], ["decision noop, expected labels", "missing labels ['new-resource']"])
        self.assertEqual(self.run_case(["new-resource", "bug"])["problems"], ["unexpected labels ['bug']"])
        self.assertIn("decision comment, expected labels", self.run_case(["new-resource"], "We closed this.")["problems"])

    def test_controls_catch_extra_mentions_comments_and_missing_scripts(self):
        raw = [{"type": "add_comment", "body": "@reporter thanks, cc @someone"}, {"type": "add_comment", "body": "again"}]
        c = self.run_case(["new-resource"], raw=raw, commands=())["controls"]
        self.assertFalse(c["mentions only the author"] or c["at most one comment"] or c["triage_checks.py ran"])


if __name__ == "__main__":
    unittest.main()
