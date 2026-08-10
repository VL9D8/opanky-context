import json
import os
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
            ignore=shutil.ignore_patterns(".git", ".uv-cache", ".venv", "__pycache__"),
        )
        return copied

    def assert_issue_contains(self, root: Path, expected: str) -> None:
        issues = validate_repository(root)
        self.assertTrue(any(expected in issue for issue in issues), issues)

    def assert_public_content_issue(self, content: str, expected: str) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            (root / "accidental.txt").write_text(content, encoding="utf-8")
            self.assert_issue_contains(root, expected)

    def assert_public_content_is_allowed(self, content: str) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            (root / "accidental.txt").write_text(content, encoding="utf-8")
            self.assertEqual([], validate_repository(root))

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

    def test_root_relative_repository_link_is_allowed(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            readme = root / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8") + "\n[Docs](/docs/PROJECTS.md)\n",
                encoding="utf-8",
            )
            self.assertEqual([], validate_repository(root))

    def test_route_text_is_allowed(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            readme = root / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8") + "\nRoute: GET /api/items\n",
                encoding="utf-8",
            )
            self.assertEqual([], validate_repository(root))

    def test_dot_relative_path_is_allowed(self) -> None:
        self.assert_public_content_is_allowed("." + "/" + "docs/file.md")

    def test_parent_relative_path_is_allowed(self) -> None:
        self.assert_public_content_is_allowed(".." + "/" + "docs/file.md")

    def test_https_query_with_relative_path_is_allowed(self) -> None:
        url = "https:" + "//" + "example.test/callback?next=/" + "docs"
        self.assert_public_content_is_allowed(url)

    def test_posix_etc_path_is_rejected(self) -> None:
        self.assert_public_content_issue("/" + "etc/passwd", "private local path")

    def test_posix_applications_path_is_rejected(self) -> None:
        self.assert_public_content_issue("/" + "Applications/App", "private local path")

    def test_posix_library_path_is_rejected(self) -> None:
        self.assert_public_content_issue("/" + "Library/Preferences", "private local path")

    def test_posix_system_path_is_rejected(self) -> None:
        self.assert_public_content_issue("/" + "System/Library", "private local path")

    def test_posix_volumes_path_is_rejected(self) -> None:
        self.assert_public_content_issue("/" + "Volumes/Drive", "private local path")

    def test_arbitrary_posix_path_is_rejected(self) -> None:
        self.assert_public_content_issue("/" + "custom/private", "private local path")

    def test_wsl_path_is_rejected(self) -> None:
        self.assert_public_content_issue("/" + "mnt/c/private.txt", "private local path")

    def test_posix_file_uri_is_rejected(self) -> None:
        file_uri = "FiLe:" + "///" + "etc/passwd"
        self.assert_public_content_issue(file_uri, "file URI")

    def test_windows_file_uri_is_rejected(self) -> None:
        file_uri = "FILE:" + "///" + "C:" + "/" + "private.txt"
        self.assert_public_content_issue(file_uri, "file URI")

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
            slash = chr(92)
            private_path = "C:" + slash + "Users" + slash + "Example" + slash + "private.txt"
            (root / "accidental.txt").write_text(private_path, encoding="utf-8")
            self.assert_issue_contains(root, "private local path")

    def test_generic_windows_drive_path_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            slash = chr(92)
            drive_path = "D:" + slash + "clients" + slash + "brief.txt"
            (root / "accidental.txt").write_text(drive_path, encoding="utf-8")
            self.assert_issue_contains(root, "private local path")

    def test_unc_path_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            slash = chr(92)
            unc_path = slash + slash + "server" + slash + "share" + slash + "brief.txt"
            (root / "accidental.txt").write_text(unc_path, encoding="utf-8")
            self.assert_issue_contains(root, "private local path")

    def test_posix_and_wsl_paths_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            posix_path = "/" + "tmp/private.txt"
            wsl_path = "/" + "mnt/c/private.txt"
            (root / "accidental.txt").write_text(
                posix_path + "\n" + wsl_path,
                encoding="utf-8",
            )
            self.assert_issue_contains(root, "private local path")

    def test_invalid_utf8_public_file_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            (root / "accidental.bin").write_bytes(b"\xff\xfe")
            self.assert_issue_contains(root, "undecodable public file")

    def test_non_object_document_entry_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            context_path = root / "context.json"
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["documents"] = ["bad"]
            context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
            self.assert_issue_contains(root, "invalid document entry: 0")

    def test_non_object_project_entry_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            context_path = root / "context.json"
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["projects"] = ["bad"]
            context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
            self.assert_issue_contains(root, "invalid project entry: 0")

    def test_invalid_schema_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            schema_path = root / "schemas/context.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["type"] = 17
            schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
            self.assert_issue_contains(root, "invalid context schema")

    def test_escaping_document_path_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            context_path = root / "context.json"
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["documents"][0]["path"] = ".." + "/" + "outside.md"
            context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
            self.assert_issue_contains(root, "document path escapes repository")

    def test_live_file_symlink_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            root = self.copy_repository(temporary_root)
            target = root / "target.txt"
            target.write_text("target", encoding="utf-8")
            link = root / "linked.txt"
            try:
                os.symlink(target, link)
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")
            self.assert_issue_contains(root, "prohibited public symlink")

    def test_broken_symlink_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            root = self.copy_repository(temporary_root)
            link = root / "broken.txt"
            try:
                os.symlink(temporary_root / "missing.txt", link)
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")
            self.assert_issue_contains(root, "prohibited public symlink")

    def test_directory_symlink_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            root = self.copy_repository(temporary_root)
            target = root / "target-directory"
            target.mkdir()
            link = root / "linked-directory"
            try:
                os.symlink(target, link, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")
            self.assert_issue_contains(root, "prohibited public symlink")

    def test_invalid_front_matter_date_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            readme = root / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace(
                    "last_verified_at: 2026-08-10",
                    "last_verified_at: 2026-99-99",
                    1,
                ),
                encoding="utf-8",
            )
            self.assert_issue_contains(root, "invalid document verification date")

    def test_missing_front_matter_owner_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            readme = root / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace("owner: OPANKY\n", "", 1),
                encoding="utf-8",
            )
            self.assert_issue_contains(root, "invalid document owner")

    def test_wrong_front_matter_owner_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            readme = root / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace(
                    "owner: OPANKY",
                    "owner: OTHER",
                    1,
                ),
                encoding="utf-8",
            )
            self.assert_issue_contains(root, "invalid document owner")

    def test_uppercase_env_file_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            (root / ".ENV").write_text("placeholder", encoding="utf-8")
            self.assertIn("prohibited public file type: .ENV", validate_repository(root))

    def test_env_local_file_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            (root / ".env.local").write_text("placeholder", encoding="utf-8")
            self.assertIn("prohibited public file type: .env.local", validate_repository(root))

    def test_two_node_parent_cycle_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            context_path = root / "context.json"
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["projects"][0]["parent_project_id"] = "opanky-operator"
            context["projects"][2]["parent_project_id"] = "ashie-studio"
            context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
            self.assert_issue_contains(root, "project parent cycle")

    def test_public_boundary_runs_when_context_is_missing(self) -> None:
        with TemporaryDirectory() as directory:
            root = self.copy_repository(Path(directory))
            (root / "context.json").unlink()
            fake_secret = "api_" + "key=" + ("A" * 24)
            (root / "accidental.txt").write_text(fake_secret, encoding="utf-8")
            issues = validate_repository(root)
            self.assertTrue(any("missing context.json" in issue for issue in issues), issues)
            self.assertTrue(any("likely secret" in issue for issue in issues), issues)

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
