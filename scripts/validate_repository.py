#!/usr/bin/env python3
"""Check original skill contracts, routed resources, README links and inventory claims."""
from pathlib import Path
import re
import sys
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors = []
    originals = sorted((ROOT / "my-skills").glob("*/SKILL.md"))
    mirrors = sorted((ROOT / "skills").glob("*/SOURCE.md"))
    vendored = list((ROOT / "skills").rglob("SKILL.md"))
    allowed = {"name", "description", "license", "metadata", "allowed-tools"}
    for path in originals:
        text = path.read_text(encoding="utf-8-sig")
        try:
            match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
            data = yaml.safe_load(match[1]) if match else None
            if not isinstance(data, dict):
                raise ValueError("missing YAML frontmatter")
            if set(data) - allowed:
                raise ValueError(f"unsupported frontmatter: {set(data) - allowed}")
            name, description = data.get("name"), data.get("description")
            if name != path.parent.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
                raise ValueError("invalid skill name or folder mismatch")
            if not isinstance(description, str) or not 1 <= len(description) <= 1024 or "<" in description or ">" in description:
                raise ValueError("invalid description")
            if data.get("license") != "MIT":
                raise ValueError("original skill license must match declared MIT")
        except (ValueError, TypeError, yaml.YAMLError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")

    paths = [ROOT / name for name in ("README.md", "README.en.md", "README.ja.md")]
    paths += list((ROOT / "my-skills/quant-research-workflow").rglob("*.md"))
    paths += [ROOT / name for name in ("docs/validation.md", "docs/maintenance.md", "docs/historical-demos.md",
                                      "docs/quickstart.md", "docs/paper-journal.md", "reports/latest.md")]
    paths += list((ROOT / "examples/paper").rglob("*.md"))
    paths += list((ROOT / "reports/paper").rglob("*.md"))
    paths += list((ROOT / "my-skills/gold-cross-asset-research").rglob("*.md"))
    for path in paths:
        for target in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            local = unquote(target.split("#", 1)[0])
            if local and not (path.parent / local).exists():
                errors.append(f"{path.relative_to(ROOT)}: broken link {target}")

    for source in mirrors:
        if not any(p.is_file() and p.name.lower().startswith(("license", "licence", "copying")) for p in source.parent.iterdir()):
            errors.append(f"{source.parent.name}: missing mirror license file")
    route = (ROOT / "my-skills/quant-research-workflow/references/task-routing.md").read_text(encoding="utf-8")
    for row in route.splitlines():
        if row.startswith("|"):
            cells = row.split("|")
            for name in re.findall(r"\b[a-z0-9]+(?:-[a-z0-9]+)+\b", " ".join(cells[2:4])):
                if not (ROOT / "my-skills" / name / "SKILL.md").exists():
                    errors.append(f"missing route: {name}")
    expected = f"<!-- inventory: originals={len(originals)} mirrors={len(mirrors)} vendored={len(vendored)} -->"
    for path in paths[:3]:
        if expected not in path.read_text(encoding="utf-8"):
            errors.append(f"{path.name}: inventory marker must be {expected}")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"PASS: {len(originals)} original skills, {len(mirrors)} source snapshots, {len(vendored)} vendored SKILL.md files; checked frontmatter and documented local links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
