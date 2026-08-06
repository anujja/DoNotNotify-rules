#!/usr/bin/env python3
"""Generate index.json and the README contributors section.

Deterministic (sorted, no timestamps) so it diffs cleanly and CI can verify
both are up to date. Run after adding or editing rule files and commit the
result.

Usage:
    python3 scripts/generate_index.py           # rewrite index.json + README section
    python3 scripts/generate_index.py --check   # exit 1 if either is stale
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.json"
README = ROOT / "README.md"
MARK_START = "<!-- contributors:start -->"
MARK_END = "<!-- contributors:end -->"


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


def contributors_block(entries):
    stats = {}
    for entry in entries:
        handle = entry.get("maintainer")
        if not handle:
            continue
        s = stats.setdefault(handle, {"lists": 0, "rules": 0})
        s["lists"] += 1
        s["rules"] += entry["ruleCount"]
    lines = [
        MARK_START,
        "| Contributor | Lists | Rules |",
        "|---|---:|---:|",
    ]
    for handle, s in sorted(stats.items(), key=lambda kv: (-kv[1]["lists"], kv[0].lower())):
        lines.append(f"| [@{handle}](https://github.com/{handle}) | {s['lists']} | {s['rules']} |")
    lines.append(MARK_END)
    return "\n".join(lines)


def updated_readme(entries):
    current = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(MARK_START) + r".*?" + re.escape(MARK_END), re.DOTALL)
    if not pattern.search(current):
        print(f"README.md is missing the {MARK_START} … {MARK_END} markers", file=sys.stderr)
        sys.exit(1)
    return pattern.sub(lambda _: contributors_block(entries), current, count=1)


def main():
    index = collect()
    rendered = json.dumps(index, indent=2, ensure_ascii=False) + "\n"
    readme = updated_readme(index["files"])
    if "--check" in sys.argv:
        stale = []
        if (INDEX.read_text(encoding="utf-8") if INDEX.exists() else "") != rendered:
            stale.append("index.json")
        if README.read_text(encoding="utf-8") != readme:
            stale.append("README.md contributors section")
        if stale:
            print(f"stale: {', '.join(stale)} — run: python3 scripts/generate_index.py", file=sys.stderr)
            sys.exit(1)
        print("index.json and README contributors are up to date")
    else:
        INDEX.write_text(rendered, encoding="utf-8")
        README.write_text(readme, encoding="utf-8")
        print(f"wrote {INDEX.relative_to(ROOT)} ({len(index['files'])} entries) and README contributors")


if __name__ == "__main__":
    main()
