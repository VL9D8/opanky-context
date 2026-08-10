from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = {
    "README.md",
    "AGENTS.md",
    "CONTEXT.md",
    "llms.txt",
    "context.json",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    ".gitignore",
    ".lychee.toml",
    ".python-version",
    "pyproject.toml",
    "uv.lock",
    "docs/VISION.md",
    "docs/CURRENT_STATE.md",
    "docs/ARCHITECTURE.md",
    "docs/PROJECTS.md",
    "docs/PORTFOLIO.md",
    "docs/PROCESSES.md",
    "docs/DECISIONS.md",
    "docs/ROADMAP.md",
    "docs/RESEARCH.md",
    "docs/BUILD_LOG.md",
    "schemas/context.schema.json",
    "scripts/render_context.py",
    "scripts/validate_context.py",
    ".github/workflows/validate.yml",
    ".github/ISSUE_TEMPLATE/research-note.yml",
    ".github/ISSUE_TEMPLATE/context-correction.yml",
    ".github/pull_request_template.md",
}


class RepositoryStructureTests(unittest.TestCase):
    def test_required_files_exist_with_exact_case(self) -> None:
        existing = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.parts
        }
        self.assertEqual(set(), REQUIRED_FILES - existing)

    def test_v1_has_no_license_file(self) -> None:
        self.assertFalse(any(ROOT.glob("LICENSE*")))


if __name__ == "__main__":
    unittest.main()
