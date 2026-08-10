from collections import Counter
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/validate.yml"
PR_TEMPLATE = ROOT / ".github/pull_request_template.md"
EXPECTED_ACTIONS = Counter(
    {
        "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd": 3,
        "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9": 1,
        "lycheeverse/lychee-action@e7477775783ea5526144ba13e8db5eec57747ce8": 1,
        "gitleaks/gitleaks-action@ff98106e4c7b2bc287b24eaf42907196329070c7": 1,
    }
)
EXPECTED_FORM_IDS = {
    "context-correction.yml": {
        "document",
        "current_claim",
        "correction",
        "evidence",
        "verified_at",
        "safety",
    },
    "research-note.yml": {
        "question",
        "finding",
        "sources",
        "confidence",
        "projects",
        "destination",
        "safety",
    },
}
REQUIRED_FORM_IDS = {
    "context-correction.yml": {"document", "current_claim", "correction", "verified_at"},
    "research-note.yml": {
        "question",
        "finding",
        "sources",
        "confidence",
        "projects",
        "destination",
    },
}
ALLOWED_FORM_TYPES = {"input", "textarea", "dropdown", "checkboxes"}


class CIConfigurationTests(unittest.TestCase):
    def test_workflow_is_valid_yaml_with_stable_job_names(self) -> None:
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.assertEqual({"context", "links", "secrets"}, set(workflow["jobs"]))
        for job_id, job in workflow["jobs"].items():
            self.assertEqual(job_id, job["name"])

    def test_every_action_uses_the_approved_immutable_sha(self) -> None:
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        references = []
        for job in workflow["jobs"].values():
            for step in job["steps"]:
                if "uses" in step:
                    self.assertIsInstance(step["uses"], str)
                    references.append(step["uses"])
        self.assertEqual(EXPECTED_ACTIONS, Counter(references))

    def test_issue_forms_have_safe_complete_contracts(self) -> None:
        for path in sorted((ROOT / ".github/ISSUE_TEMPLATE").glob("*.yml")):
            form = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertIn("name", form, path.name)
            self.assertIn("description", form, path.name)
            self.assertIsInstance(form.get("body"), list, path.name)
            self.assertEqual(EXPECTED_FORM_IDS[path.name], {item["id"] for item in form["body"]})

            ids = [item["id"] for item in form["body"]]
            self.assertEqual(len(ids), len(set(ids)), path.name)
            items_by_id = {item["id"]: item for item in form["body"]}
            for item in form["body"]:
                self.assertIn(item["type"], ALLOWED_FORM_TYPES, path.name)
            for item_id in REQUIRED_FORM_IDS[path.name]:
                self.assertTrue(items_by_id[item_id].get("validations", {}).get("required"), item_id)

            safety = items_by_id["safety"]
            self.assertEqual("checkboxes", safety["type"])
            options = safety.get("attributes", {}).get("options")
            self.assertIsInstance(options, list)
            self.assertTrue(options)
            self.assertTrue(all(option.get("required") is True for option in options))

    def test_pull_request_template_has_public_context_contract(self) -> None:
        template = PR_TEMPLATE.read_text(encoding="utf-8")
        for required_text in (
            "Affected project/document IDs:",
            "Source or owner confirmation:",
            "`last_verified_at`:",
            "No secrets, private contacts, raw chats, local paths, confidential briefs, or unpublished assets are included.",
            "Generated views were produced from `context.json`, not edited manually.",
            "Unknown or partial claims remain explicitly labeled.",
            '`uv run python -m unittest discover -s tests -p "test_*.py" -v`',
            "`uv run python scripts/render_context.py --check`",
            "`uv run python scripts/validate_context.py`",
        ):
            self.assertIn(required_text, template)


if __name__ == "__main__":
    unittest.main()
