#!/usr/bin/env python3
"""Generate index.json — the machine-readable catalog of every rule list.

Deterministic (sorted, no timestamps) so it diffs cleanly and CI can verify
it is up to date. Run after adding or editing rule files and commit the
result.

Usage:
    python3 scripts/generate_index.py           # rewrite index.json
    python3 scripts/generate_index.py --check   # exit 1 if index.json is stale
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.json"


def collect():
    files = []
    for base in ("rules", "bundles"):
        d = ROOT / base
        if d.is_dir():
            files.extend(p for p in d.rglob("*.json") if p.is_file())

    entries = []
    for path in sorted(files, key=lambda p: p.relative_to(ROOT).as_posix()):
        data = json.loads(path.read_text(encoding="utf-8"))
        rules = data.get("rules", [])
        entry = {
            "path": path.relative_to(ROOT).as_posix(),
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "packages": sorted({r.get("packageName", "") for r in rules if isinstance(r, dict)}),
            "ruleCount": len(rules),
            "ruleTypes": sorted({r.get("ruleType", "DENYLIST") for r in rules if isinstance(r, dict)}),
        }
        if "locale" in data:
            entry["locale"] = data["locale"]
        if "maintainer" in data:
            entry["maintainer"] = data["maintainer"]
        entries.append(entry)

    return {"indexVersion": 1, "files": entries}


def main():
    rendered = json.dumps(collect(), indent=2, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        current = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
        if current != rendered:
            print("index.json is out of date — run: python3 scripts/generate_index.py", file=sys.stderr)
            sys.exit(1)
        print("index.json is up to date")
    else:
        INDEX.write_text(rendered, encoding="utf-8")
        print(f"wrote {INDEX.relative_to(ROOT)} ({len(json.loads(rendered)['files'])} entries)")


if __name__ == "__main__":
    main()
