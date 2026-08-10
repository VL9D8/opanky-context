import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]


class ContextContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = json.loads((ROOT / "context.json").read_text(encoding="utf-8"))
        cls.schema = json.loads(
            (ROOT / "schemas/context.schema.json").read_text(encoding="utf-8")
        )

    def test_context_matches_schema(self) -> None:
        validator = Draft202012Validator(self.schema, format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(self.context), key=lambda error: list(error.path))
        self.assertEqual([], [error.message for error in errors])

    def test_initial_registry_contains_safe_verified_scope(self) -> None:
        projects = {item["project_id"]: item for item in self.context["projects"]}
        self.assertEqual(
            {"ashie-studio", "opanky-outreach", "opanky-operator"},
            set(projects),
        )
        self.assertEqual("ashie-studio", projects["opanky-outreach"]["parent_project_id"])
        self.assertIsNone(projects["opanky-outreach"]["source_url"])
        self.assertIsNone(projects["opanky-operator"]["source_url"])
        self.assertNotIn("cliffora", projects)

    def test_active_focus_contains_only_top_level_projects(self) -> None:
        projects = {item["project_id"]: item for item in self.context["projects"]}
        for project_id in self.context["active_focus"]:
            self.assertIsNone(projects[project_id]["parent_project_id"])


if __name__ == "__main__":
    unittest.main()
