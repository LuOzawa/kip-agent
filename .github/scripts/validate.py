#!/usr/bin/env python3
"""Structure checks for the kip-agent team repo.

Rules enforced (see data/README.md, skills/README.md, packages/README.md):
  data/<name>/      needs card.md, schema.json (fields[].name + .type), and a v<N>/ folder
  skills/<name>/    needs skill.json (name, semver version, description, entry) + SKILL.md
  packages/<name>/  needs README.md and one manifest (package.json / pyproject.toml / go.mod)

Also fails on JSON that does not parse, and on obvious credential patterns.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}

SECRET_PATTERNS = {
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key block": re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|PGP) PRIVATE KEY-----"),
}
TEXT_SUFFIXES = {".md", ".json", ".yml", ".yaml", ".py", ".ts", ".js", ".cjs", ".mjs", ".toml", ".sh", ".txt", ".csv", ".conf"}

errors: list[str] = []
notes: list[str] = []


def walk_dirs(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted(p for p in path.iterdir() if p.is_dir() and not p.name.startswith("."))


def check_data() -> int:
    count = 0
    for d in walk_dirs(ROOT / "data"):
        count += 1
        name = d.name
        for required in ("card.md", "schema.json"):
            if not (d / required).is_file():
                errors.append(f"data/{name}: missing {required}")
        versions = [p for p in d.iterdir() if re.fullmatch(r"v\d+", p.name) and p.is_dir()]
        if not versions:
            errors.append(f"data/{name}: no version folder (expected v1/, v2/, ...)")
        schema_file = d / "schema.json"
        if schema_file.is_file():
            try:
                schema = json.loads(schema_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"data/{name}/schema.json: invalid JSON ({exc})")
                continue
            fields = schema.get("fields")
            if not isinstance(fields, list) or not fields:
                errors.append(f"data/{name}/schema.json: 'fields' must be a non-empty list")
            else:
                for i, field in enumerate(fields):
                    if not isinstance(field, dict):
                        errors.append(f"data/{name}/schema.json: fields[{i}] is not an object")
                        continue
                    for key in ("name", "type"):
                        if not field.get(key):
                            errors.append(f"data/{name}/schema.json: fields[{i}] missing '{key}'")
    return count


def check_skills() -> int:
    count = 0
    for d in walk_dirs(ROOT / "skills"):
        count += 1
        name = d.name
        manifest_file = d / "skill.json"
        if not manifest_file.is_file():
            errors.append(f"skills/{name}: missing skill.json")
            continue
        if not (d / "SKILL.md").is_file():
            errors.append(f"skills/{name}: missing SKILL.md")
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"skills/{name}/skill.json: invalid JSON ({exc})")
            continue
        for key in ("name", "version", "description", "entry"):
            if not manifest.get(key):
                errors.append(f"skills/{name}/skill.json: missing '{key}'")
        if manifest.get("name") and manifest["name"] != name:
            errors.append(f"skills/{name}: skill.json name '{manifest['name']}' != folder '{name}'")
        version = manifest.get("version")
        if version and not SEMVER.match(str(version)):
            errors.append(f"skills/{name}/skill.json: version '{version}' is not semver")
        entry = manifest.get("entry")
        if entry and not (d / str(entry)).exists():
            errors.append(f"skills/{name}: entry '{entry}' does not exist")
    return count


def check_packages() -> int:
    count = 0
    manifests = ("package.json", "pyproject.toml", "go.mod", "Cargo.toml")
    for d in walk_dirs(ROOT / "packages"):
        count += 1
        name = d.name
        if not (d / "README.md").is_file():
            errors.append(f"packages/{name}: missing README.md")
        if not any((d / m).is_file() for m in manifests):
            errors.append(f"packages/{name}: no manifest ({', '.join(manifests)})")
    return count


def check_json_and_secrets() -> None:
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{rel}: invalid JSON ({exc})")
        if path.suffix in TEXT_SUFFIXES and path.stat().st_size < 1_000_000:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(text):
                    errors.append(f"{rel}: looks like a committed {label}")


def main() -> int:
    n_data = check_data()
    n_skills = check_skills()
    n_packages = check_packages()
    check_json_and_secrets()

    notes.append(f"data: {n_data} dataset(s), skills: {n_skills}, packages: {n_packages}")
    for note in notes:
        print(f"· {note}")

    if errors:
        print(f"\n{len(errors)} problem(s):")
        for err in errors:
            print(f"  ✗ {err}")
        return 1

    print("\n✓ all structure checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
