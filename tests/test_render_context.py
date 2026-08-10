import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.render_context import (
    generated_files,
    render_portfolio,
    render_projects,
    write_generated,
)


ROOT = Path(__file__).resolve().parents[1]


class RenderContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = json.loads((ROOT / "context.json").read_text(encoding="utf-8"))

    def test_projects_view_contains_every_registry_field(self) -> None:
        rendered = render_projects(self.context)
        for project in self.context["projects"]:
            for value in (
                project["project_id"],
                project["display_name"],
                project["owner"],
                project["portfolio_state"],
                project["revenue_horizon"],
                project["verification_status"],
                project["last_verified_at"],
            ):
                self.assertIn(str(value), rendered)

    def test_portfolio_view_contains_all_states_and_active_focus(self) -> None:
        rendered = render_portfolio(self.context)
        for heading in ("Active", "Next", "Incubating", "Paused", "Archived"):
            self.assertIn(f"## {heading}", rendered)
        for project_id in self.context["active_focus"]:
            self.assertIn(f"`{project_id}`", rendered)

    def test_generated_files_have_stable_paths_and_trailing_newlines(self) -> None:
        outputs = generated_files(self.context)
        self.assertEqual({"docs/PROJECTS.md", "docs/PORTFOLIO.md"}, set(outputs))
        self.assertTrue(all(value.endswith("\n") for value in outputs.values()))

    def test_check_mode_reports_only_drifted_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual((), write_generated(self.context, root, check=False))
            self.assertEqual((), write_generated(self.context, root, check=True))
            (root / "docs/PROJECTS.md").write_text("drift\n", encoding="utf-8")
            self.assertEqual(
                ("docs/PROJECTS.md",),
                write_generated(self.context, root, check=True),
            )


if __name__ == "__main__":
    unittest.main()
