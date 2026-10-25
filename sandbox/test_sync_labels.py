"""Check sync_labels.parse_labels against the imported .tf files. Run: python3 -m unittest discover sandbox"""
import re
import unittest

from sync_labels import TF, parse_labels

TEXT = {p.name: p.read_text() for p in TF.glob("labels-*.tf")}


class ParseLabels(unittest.TestCase):
    labels = parse_labels("\n".join(TEXT.values()))

    def test_counts_match_the_entries_in_each_file(self):
        # Counted a second way: map entries in workflow_labels, list items in the two sets.
        workflow = len(re.findall(r'^\s*"[^"]+" = \{', TEXT["labels-workflow.tf"], re.M))
        service = len(re.findall(r'^\s*"[^"]+",$', TEXT["labels-service.tf"], re.M))
        partition = len(re.findall(r'^\s*"[^"]+",$', TEXT["labels-partition.tf"], re.M))
        names = list(self.labels)
        self.assertEqual(sum(n.startswith("service/") for n in names), service)
        self.assertEqual(sum(n.startswith("partition/") for n in names), partition)
        self.assertEqual(sum(not n.startswith(("service/", "partition/")) for n in names), workflow)
        self.assertEqual(len(names), workflow + service + partition)

    def test_spot_checks(self):
        self.assertEqual(self.labels["bug"], ("e05959", "Addresses a defect in current functionality."))
        self.assertEqual(self.labels["service/s3"], ("7b42bc", "Issues and PRs that pertain to the s3 service."))
        self.assertEqual(self.labels["partition/aws-cn"], ("844fba", "Pertains to the aws-cn partition."))
        self.assertIn("needs-triage", self.labels)

    def test_fits_github_limits(self):
        # GitHub rejects names over 50 characters, descriptions over 100 and colours that are not 6 hex digits.
        for name, (color, desc) in self.labels.items():
            self.assertLessEqual(len(name), 50, name)
            self.assertLessEqual(len(desc), 100, name)
            self.assertRegex(color, r"^[0-9a-f]{6}$", name)


if __name__ == "__main__":
    unittest.main()
