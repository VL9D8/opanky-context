from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
from typing import Any, Callable
from urllib.parse import unquote

from jsonschema import Draft202012Validator, FormatChecker, SchemaError
import yaml

if __package__:
    from .render_context import generated_files
else:
    from render_context import generated_files


ROOT = Path(__file__).resolve().parents[1]
MAX_PUBLIC_FILE_BYTES = 1_000_000
IGNORED_PARTS = {".git", ".uv-cache", ".venv", "__pycache__"}
REQUIRED_FILES = {
    "README.md",
    "AGENTS.md",
    "CONTEXT.md",
    "llms.txt",
    "context.json",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
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
}
FRONT_MATTER = re.compile(r"\A---\n(?P<yaml>.*?)\n---\n", re.DOTALL)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\((?P<target>[^)]+)\)")
BACKSLASH = r"\\"
WINDOWS_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z]:["
    + BACKSLASH
    + r"/]|"
    + BACKSLASH
    + BACKSLASH
    + r"[^\\/\s]+[\\/][^\s]+)"
)
POSIX_LOCAL_PATH = re.compile(
    r"(?<![:A-Za-z0-9/])/"
    r"(?:bin|dev|etc|home|lib(?:64)?|mnt|opt|private|proc|root|run|sbin|srv|sys|tmp|usr|var|Users)"
    r"(?:/|$)",
    re.IGNORECASE,
)
LIKELY_SECRET = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*"
    r"[\"']?[A-Za-z0-9_./+=-]{12,}"
)
PROHIBITED_SUFFIXES = {".env", ".key", ".pem", ".p12", ".sqlite", ".db", ".zip"}


def public_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if (path.is_file() or path.is_symlink())
        and not IGNORED_PARTS.intersection(path.relative_to(root).parts)
    )


def is_within_root(path: Path, root: Path) -> bool:
    try:
        resolved_path = path.resolve()
        resolved_root = root.resolve()
    except (OSError, RuntimeError):
        return False
    return resolved_path.is_relative_to(resolved_root)


def is_safe_relative_path(root: Path, relative_path: object) -> bool:
    if not isinstance(relative_path, str) or Path(relative_path).is_absolute():
        return False
    if WINDOWS_ABSOLUTE_PATH.search(relative_path) or relative_path.startswith("\\\\"):
        return False
    return is_within_root(root / relative_path, root)


def validate_required_files(root: Path) -> list[str]:
    existing = {path.relative_to(root).as_posix() for path in public_files(root)}
    issues = [f"missing required file: {path}" for path in sorted(REQUIRED_FILES - existing)]
    for relative_path in sorted(REQUIRED_FILES & existing):
        if not is_safe_relative_path(root, relative_path):
            issues.append(f"required file escapes repository: {relative_path}")
    return issues


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def validate_schema(context: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        return [f"invalid context schema: {error.message}"]
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(context), key=lambda error: list(error.path))
    return [f"schema: {error.json_path}: {error.message}" for error in errors]


def validate_documents(root: Path, context: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    document_ids: set[str] = set()
    document_paths: set[str] = set()
    allowed_statuses = {"active", "paused", "archived"}
    documents = context.get("documents", [])
    if not isinstance(documents, list):
        return ["documents must be an array"]
    try:
        context_date = date.fromisoformat(str(context.get("last_verified_at")))
    except (TypeError, ValueError):
        context_date = None
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            issues.append(f"invalid document entry: {index}")
            continue
        document_id = document.get("document_id")
        relative_path = document.get("path")
        if document_id in document_ids:
            issues.append(f"duplicate document_id: {document_id}")
        if relative_path in document_paths:
            issues.append(f"duplicate document path: {relative_path}")
        document_ids.add(document_id)
        document_paths.add(relative_path)
        if not is_safe_relative_path(root, relative_path):
            issues.append(f"document path escapes repository: {relative_path}")
            continue
        path = root / relative_path
        if path.is_symlink():
            issues.append(f"document path is a symlink: {relative_path}")
            continue
        if not path.is_file():
            issues.append(f"document path does not exist: {relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        match = FRONT_MATTER.match(text)
        if match is None:
            issues.append(f"missing YAML front matter: {relative_path}")
            continue
        metadata = yaml.load(match.group("yaml"), Loader=yaml.BaseLoader)
        if not isinstance(metadata, dict):
            issues.append(f"invalid YAML front matter: {relative_path}")
            continue
        if metadata.get("document_id") != document_id:
            issues.append(f"document_id mismatch: {relative_path}")
        if metadata.get("owner") != "OPANKY":
            issues.append(f"invalid document owner: {relative_path}")
        if str(metadata.get("schema_version")) != str(context.get("schema_version")):
            issues.append(f"schema_version mismatch: {relative_path}")
        if metadata.get("status") not in allowed_statuses:
            issues.append(f"invalid document status: {relative_path}")
        try:
            document_date = date.fromisoformat(str(metadata.get("last_verified_at")))
        except (TypeError, ValueError):
            issues.append(f"invalid document verification date: {relative_path}")
            continue
        if context_date is not None and document_date > context_date:
            issues.append(f"document verification date is in the future: {relative_path}")
    return issues


def validate_projects(context: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    projects = context.get("projects", [])
    if not isinstance(projects, list):
        return ["projects must be an array"]
    valid_projects: list[dict[str, Any]] = []
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            issues.append(f"invalid project entry: {index}")
        else:
            valid_projects.append(project)
    project_ids = [project.get("project_id") for project in valid_projects]
    known_ids = set(project_ids)
    if len(project_ids) != len(known_ids):
        issues.append("duplicate project_id")
    try:
        context_date = date.fromisoformat(context["last_verified_at"])
    except (KeyError, TypeError, ValueError):
        return issues
    parents: dict[object, object] = {}
    for project in valid_projects:
        project_id = project.get("project_id")
        parent_id = project.get("parent_project_id")
        parents[project_id] = parent_id
        if parent_id is not None and parent_id not in known_ids:
            issues.append(f"unknown parent project for {project_id}: {parent_id}")
        if parent_id == project_id:
            issues.append(f"project cannot parent itself: {project_id}")
        try:
            verified_at = date.fromisoformat(project["last_verified_at"])
        except (KeyError, TypeError, ValueError):
            continue
        age = (context_date - verified_at).days
        if age < 0:
            issues.append(f"project verification date is in the future: {project_id}")
        if age > 90 and project.get("verification_status") != "stale":
            issues.append(f"{project_id} is older than 90 days but is not marked stale")
        if project.get("verification_status") == "verified" and not project.get("evidence_url"):
            issues.append(f"verified project lacks public evidence: {project_id}")
    for project_id in sorted(parents, key=str):
        positions: dict[object, int] = {}
        chain: list[object] = []
        current: object = project_id
        while current in parents and current not in positions:
            positions[current] = len(chain)
            chain.append(current)
            current = parents[current]
        if current in positions:
            cycle = sorted(str(item) for item in chain[positions[current] :])
            issues.append(f"project parent cycle: {' -> '.join(cycle)}")
    active_focus = context.get("active_focus", [])
    if not isinstance(active_focus, list):
        return issues + ["active_focus must be an array"]
    for project_id in active_focus:
        if project_id not in known_ids:
            issues.append(f"active_focus references unknown project: {project_id}")
            continue
        project = next(item for item in valid_projects if item.get("project_id") == project_id)
        if project.get("parent_project_id") is not None:
            issues.append(f"active_focus must contain only top-level projects: {project_id}")
    return issues


def validate_ai_references(root: Path, context: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for relative_path in ("CONTEXT.md", "llms.txt"):
        if not is_safe_relative_path(root, relative_path):
            issues.append(f"required file escapes repository: {relative_path}")
            continue
        if (root / relative_path).is_symlink():
            issues.append(f"required file is a symlink: {relative_path}")
            continue
        text = (root / relative_path).read_text(encoding="utf-8")
        for project in context.get("projects", []):
            if not isinstance(project, dict):
                continue
            token = f"`{project['project_id']}`"
            if token not in text:
                issues.append(f"{relative_path} does not reference {token}")
    return issues


def validate_generated_views(root: Path, context: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for relative_path, expected in generated_files(context).items():
        if not is_safe_relative_path(root, relative_path):
            issues.append(f"generated file escapes repository: {relative_path}")
            continue
        path = root / relative_path
        if path.is_symlink():
            issues.append(f"generated file is a symlink: {relative_path}")
            continue
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if actual != expected:
            issues.append(f"generated file is stale: {relative_path}")
    return issues


def validate_internal_links(root: Path) -> list[str]:
    issues: list[str] = []
    candidates = [path for path in public_files(root) if path.suffix == ".md"]
    candidates.append(root / "llms.txt")
    for source in candidates:
        if source.is_symlink():
            issues.append(f"prohibited public symlink: {source.relative_to(root)}")
            continue
        if not is_within_root(source, root):
            issues.append(f"public file escapes repository: {source.relative_to(root)}")
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in MARKDOWN_LINK.finditer(text):
            raw_target = match.group("target").strip().split()[0]
            target = unquote(raw_target.split("#", 1)[0])
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                continue
            destination = (root / target.lstrip("/")) if target.startswith("/") else (source.parent / target)
            if not is_within_root(destination, root):
                issues.append(f"internal link escapes repository: {source.relative_to(root)} -> {target}")
            elif not destination.exists():
                issues.append(f"broken internal link: {source.relative_to(root)} -> {target}")
    return issues


def validate_public_boundary(root: Path) -> list[str]:
    issues: list[str] = []
    for path in public_files(root):
        relative_path = path.relative_to(root).as_posix()
        if path.is_symlink():
            issues.append(f"prohibited public symlink: {relative_path}")
            continue
        if not is_within_root(path, root):
            issues.append(f"public file escapes repository: {relative_path}")
            continue
        size = path.stat().st_size
        if size > MAX_PUBLIC_FILE_BYTES:
            issues.append(f"{relative_path} exceeds {MAX_PUBLIC_FILE_BYTES} bytes")
        name_lower = path.name.lower()
        if (
            path.suffix.lower() in PROHIBITED_SUFFIXES
            or name_lower == ".env"
            or name_lower.startswith(".env.")
        ):
            issues.append(f"prohibited public file type: {relative_path}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            issues.append(f"undecodable public file: {relative_path}")
            continue
        if LIKELY_SECRET.search(text):
            issues.append(f"likely secret: {relative_path}")
        if WINDOWS_ABSOLUTE_PATH.search(text) or POSIX_LOCAL_PATH.search(text):
            issues.append(f"private local path: {relative_path}")
    return issues


def validate_repository(root: Path) -> list[str]:
    issues = validate_required_files(root)
    context_path = root / "context.json"
    schema_path = root / "schemas/context.schema.json"
    context: dict[str, Any] | None = None
    schema: dict[str, Any] | None = None
    if not context_path.is_file():
        issues.append("missing context.json")
    elif context_path.is_symlink():
        issues.append("context.json is a symlink")
    elif not is_within_root(context_path, root):
        issues.append("context.json escapes repository")
    else:
        try:
            context = load_json(context_path)
        except (json.JSONDecodeError, OSError, ValueError) as error:
            issues.append(f"cannot parse context.json: {error}")
    if not schema_path.is_file():
        issues.append("missing context schema")
    elif schema_path.is_symlink():
        issues.append("context schema is a symlink")
    elif not is_within_root(schema_path, root):
        issues.append("context schema escapes repository")
    else:
        try:
            schema = load_json(schema_path)
        except (json.JSONDecodeError, OSError, ValueError) as error:
            issues.append(f"cannot parse context schema: {error}")
    checks: list[Callable[[], list[str]]] = [
        lambda: validate_internal_links(root),
        lambda: validate_public_boundary(root),
    ]
    if context is not None and schema is not None:
        checks[0:0] = [
            lambda: validate_schema(context, schema),
            lambda: validate_documents(root, context),
            lambda: validate_projects(context),
            lambda: validate_ai_references(root, context),
            lambda: validate_generated_views(root, context),
        ]
    for check in checks:
        try:
            issues.extend(check())
        except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
            issues.append(f"validation could not complete: {error}")
    return sorted(set(issues))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the public context repository.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root.")
    arguments = parser.parse_args(argv)
    issues = validate_repository(arguments.root.resolve())
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 1
    print("Context repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
