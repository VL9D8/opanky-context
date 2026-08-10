from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/validate.yml"
EXPECTED_ACTIONS = {
    "actions/checkout": "de0fac2e4500dabe0009e67214ff5f5447ce83dd",
    "astral-sh/setup-uv": "c771a70e6277c0a99b617c7a806ffedaca235ff9",
    "lycheeverse/lychee-action": "e7477775783ea5526144ba13e8db5eec57747ce8",
    "gitleaks/gitleaks-action": "ff98106e4c7b2bc287b24eaf42907196329070c7",
}


class CIConfigurationTests(unittest.TestCase):
    def test_workflow_is_valid_yaml_with_stable_job_names(self) -> None:
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.assertEqual({"context", "links", "secrets"}, set(workflow["jobs"]))
        for job_id, job in workflow["jobs"].items():
            self.assertEqual(job_id, job["name"])

    def test_every_action_uses_the_approved_immutable_sha(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        references = re.findall(r"uses:\s+([^@\s]+)@([0-9a-f]{40})", text)
        self.assertEqual(text.count("uses:"), len(references))
        self.assertEqual(set(EXPECTED_ACTIONS), {name for name, _ in references})
        for name, reference in references:
            self.assertEqual(EXPECTED_ACTIONS[name], reference)

    def test_issue_forms_are_valid_yaml(self) -> None:
        for path in sorted((ROOT / ".github/ISSUE_TEMPLATE").glob("*.yml")):
            form = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertIn("name", form, path.name)
            self.assertIn("description", form, path.name)
            self.assertIsInstance(form.get("body"), list, path.name)


if __name__ == "__main__":
    unittest.main()
