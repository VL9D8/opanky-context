from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GENERATED_MARKER = (
    "<!-- Generated from context.json by scripts/render_context.py; "
    "do not edit directly. -->"
)
PORTFOLIO_STATES = ("active", "next", "incubating", "paused", "archived")


def load_context(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def front_matter(document_id: str, verified_at: str) -> str:
    return "\n".join(
        (
            "---",
            "schema_version: 1",
            f"document_id: {document_id}",
            "owner: OPANKY",
            "status: active",
            f"last_verified_at: {verified_at}",
            "---",
        )
    )


def public_value(value: Any) -> str:
    if value is None:
        return "Not published"
    return str(value)


def render_projects(context: dict[str, Any]) -> str:
    lines = [
        front_matter("projects", context["last_verified_at"]),
        "",
        GENERATED_MARKER,
        "",
        "# Projects",
        "",
        "This is the public-safe registry. Unknown or private source locations are not guessed.",
    ]
    for project in sorted(context["projects"], key=lambda item: item["project_id"]):
        lines.extend(
            (
                "",
                f"## {project['display_name']}",
                "",
                f"- `project_id`: `{project['project_id']}`",
                f"- Type: {project['project_type']}",
                f"- Purpose: {project['purpose']}",
                f"- Owner: {project['owner']}",
                f"- Parent project: {public_value(project['parent_project_id'])}",
                f"- Portfolio state: {project['portfolio_state']}",
                f"- Revenue horizon: {project['revenue_horizon']}",
                f"- Verification status: {project['verification_status']}",
                f"- Source: {public_value(project['source_url'])}",
                f"- Evidence: {public_value(project['evidence_url'])}",
                f"- Nearest action: {project['nearest_action']}",
                f"- Last verified: {project['last_verified_at']}",
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def render_portfolio(context: dict[str, Any]) -> str:
    projects = {item["project_id"]: item for item in context["projects"]}
    lines = [
        front_matter("portfolio", context["last_verified_at"]),
        "",
        GENERATED_MARKER,
        "",
        "# Portfolio",
        "",
        "This view allocates attention; it is not a second task database.",
        "",
        "## Active focus",
        "",
    ]
    lines.extend(
        f"- `{project_id}` — {projects[project_id]['nearest_action']}"
        for project_id in context["active_focus"]
    )
    for state in PORTFOLIO_STATES:
        lines.extend(("", f"## {state.title()}", ""))
        matching = sorted(
            (item for item in context["projects"] if item["portfolio_state"] == state),
            key=lambda item: item["project_id"],
        )
        if not matching:
            lines.append("_None registered._")
            continue
        for project in matching:
            lines.append(
                f"- `{project['project_id']}` — owner: {project['owner']}; "
                f"revenue: {project['revenue_horizon']}; "
                f"verification: {project['verification_status']}; "
                f"next: {project['nearest_action']}"
            )
    return "\n".join(lines).rstrip() + "\n"


def generated_files(context: dict[str, Any]) -> dict[str, str]:
    return {
        "docs/PROJECTS.md": render_projects(context),
        "docs/PORTFOLIO.md": render_portfolio(context),
    }


def write_generated(
    context: dict[str, Any], root: Path, *, check: bool
) -> tuple[str, ...]:
    drifted: list[str] = []
    for relative_path, expected in generated_files(context).items():
        destination = root / relative_path
        actual = destination.read_text(encoding="utf-8") if destination.exists() else None
        if actual == expected:
            continue
        if check:
            drifted.append(relative_path)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(expected, encoding="utf-8", newline="\n")
    return tuple(sorted(drifted))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render context.json Markdown views.")
    parser.add_argument("--check", action="store_true", help="Fail if output is stale.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root.")
    arguments = parser.parse_args(argv)
    context = load_context(arguments.root / "context.json")
    drifted = write_generated(context, arguments.root, check=arguments.check)
    if drifted:
        print("Generated files are stale: " + ", ".join(drifted))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
