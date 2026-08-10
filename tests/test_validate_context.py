import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from scripts.validate_context import validate_repository


ROOT = Path(__file__).resolve().parents[1]


class ValidateContextTests(unittest.TestCase):
    def copy_repository(self, destination: Path) -> Path:
        copied = destination / "repository"
        shutil.copytree(
            ROOT,
            copied,
            ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"),
        )
        return copied

    def assert_issue_contains(self, root: Path, expected: str) -> None:
        issues = validate_repository(root)
        self.assertTrue(any(expected in issue for issue in issues), issues)

    def test_current_repository_is_valid(self) -> None:
        self.assertEqual([], validate_repository(ROOT))

    def test_malformed_json_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            (root / "context.json").write_text("{invalid\n", encoding="utf-8")
            self.assert_issue_contains(root, "cannot parse context.json")

    def test_schema_error_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            context_path = root / "context.json"
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["active_focus"] = []
            context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
            self.assert_issue_contains(root, "schema:")

    def test_broken_internal_link_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            readme = root / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8") + "\n[Missing](docs/MISSING.md)\n",
                encoding="utf-8",
            )
            self.assert_issue_contains(root, "broken internal link")

    def test_stale_unmarked_project_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            context_path = root / "context.json"
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["projects"][0]["last_verified_at"] = "2025-01-01"
            context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
            self.assert_issue_contains(root, "older than 90 days but is not marked stale")

    def test_invalid_date_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            context_path = root / "context.json"
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["last_verified_at"] = "2026-99-99"
            context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
            self.assert_issue_contains(root, "schema:")

    def test_likely_secret_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            fake_secret = "api_" + "key=" + ("A" * 24)
            (root / "accidental.txt").write_text(fake_secret, encoding="utf-8")
            self.assert_issue_contains(root, "likely secret")

    def test_private_local_path_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            private_path = "C:" + "\\Users\\Example\\private.txt"
            (root / "accidental.txt").write_text(private_path, encoding="utf-8")
            self.assert_issue_contains(root, "private local path")

    def test_oversized_file_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            (root / "oversized.bin").write_bytes(b"0" * 1_000_001)
            self.assert_issue_contains(root, "exceeds 1000000 bytes")

    def test_generated_drift_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            (root / "docs/PROJECTS.md").write_text("drift\n", encoding="utf-8")
            self.assert_issue_contains(root, "generated file is stale")


if __name__ == "__main__":
    unittest.main()
