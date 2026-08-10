import json
from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
FRONT_MATTER = re.compile(r"\A---\n(?P<yaml>.*?)\n---\n", re.DOTALL)
REQUIRED_HEADINGS = {
    "README.md": ("# OPANKY Context", "## Start here", "## Public boundary"),
    "CONTEXT.md": ("# Current Context", "## Active focus", "## Immediate milestones"),
    "docs/VISION.md": ("# Vision", "## Product idea", "## Decision principles"),
    "docs/CURRENT_STATE.md": ("# Current State", "## Verified now", "## Unknown or partial"),
    "docs/ARCHITECTURE.md": ("# Architecture", "## Source ownership", "## Boundaries"),
    "docs/PROCESSES.md": ("# Processes", "## Capture and curation", "## Engineering changes"),
    "docs/DECISIONS.md": ("# Decisions", "## D-001", "## D-006"),
    "docs/ROADMAP.md": ("# Roadmap", "## Milestone 1", "## Milestone 3"),
    "docs/RESEARCH.md": ("# Research", "## Admission rule"),
    "docs/BUILD_LOG.md": ("# Build Log", "## 2026-08-10"),
}


class NarrativeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = json.loads((ROOT / "context.json").read_text(encoding="utf-8"))

    def test_canonical_markdown_front_matter_matches_registry(self) -> None:
        for document in self.context["documents"]:
            path = ROOT / document["path"]
            text = path.read_text(encoding="utf-8")
            match = FRONT_MATTER.match(text)
            self.assertIsNotNone(match, document["path"])
            metadata = yaml.safe_load(match.group("yaml"))
            self.assertEqual(document["document_id"], metadata["document_id"])
            self.assertEqual(1, metadata["schema_version"])
            self.assertIn(metadata["status"], {"active", "paused", "archived"})

    def test_narrative_documents_have_required_sections(self) -> None:
        for relative_path, headings in REQUIRED_HEADINGS.items():
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            for heading in headings:
                self.assertIn(heading, text, relative_path)

    def test_ai_entry_points_name_every_project_id(self) -> None:
        entry_text = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in ("CONTEXT.md", "llms.txt")
        )
        for project in self.context["projects"]:
            self.assertIn(f"`{project['project_id']}`", entry_text)

    def test_canonical_content_is_english_only(self) -> None:
        canonical = [item["path"] for item in self.context["documents"]]
        canonical.extend(("llms.txt", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md"))
        for relative_path in canonical:
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"[\u0400-\u04FF]", text), relative_path)


if __name__ == "__main__":
    unittest.main()
