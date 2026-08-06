#!/usr/bin/env python3
"""Validate every rule list against the DoNotNotify import contract.

Stdlib-only mirror of schema/rules.schema.json, plus checks a JSON Schema
cannot express: directory/package agreement, filename conventions, and
extraction of REGEX patterns for the Java-flavor compile check
(scripts/ValidateRegex.java — Python's `re` accepts/rejects different
syntax than java.util.regex, so compiling here would be misleading).

Usage: python3 scripts/validate.py
Writes build/regexes.txt (base64-encoded patterns) and exits non-zero on
any error.
"""
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MAX_FILE_BYTES = 5 * 1024 * 1024  # app-side import cap (RuleImport.MAX_IMPORT_BYTES)
MAX_FILTER_LEN = 512              # app-side cap (RuleImport.MAX_REGEX_LENGTH)
EXPORT_VERSION = 2                # app-side RULE_EXPORT_VERSION

MATCH_TYPES = {"CONTAINS", "REGEX"}
RULE_TYPES = {"DENYLIST", "ALLOWLIST", "STACK"}
ENVELOPE_KEYS = {"version", "locale", "title", "description", "maintainer", "rules"}
RULE_KEYS = {
    "appName", "packageName", "name",
    "titleFilter", "titleMatchType", "textFilter", "textMatchType",
    "ruleType", "isEnabled", "advancedConfig",
}
ADV_KEYS = {"isTimeLimitEnabled", "startTimeHour", "startTimeMinute", "endTimeHour", "endTimeMinute"}

PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")
# slug(-slug)*, optional .<language-tag>, then .json  e.g. promos.json / promos.zh-Hans.json
FILENAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*(\.[a-z]{2,3}(-[A-Za-z0-9]+)*)?\.json$")

errors = []
regexes = []  # (source-label, pattern)


def err(path, msg):
    errors.append(f"{path}: {msg}")


def check_filter(path, label, rule, filter_key, match_key):
    value = rule.get(filter_key)
    if value is None:
        return False
    if not isinstance(value, str):
        err(path, f"{label}: {filter_key} must be a string or null")
        return False
    if len(value) > MAX_FILTER_LEN:
        err(path, f"{label}: {filter_key} exceeds {MAX_FILTER_LEN} chars (app drops such rules on import)")
    if value == "":
        return False  # app treats blank as absent
    match_type = rule.get(match_key, "CONTAINS")
    if match_type not in MATCH_TYPES:
        err(path, f"{label}: {match_key} must be one of {sorted(MATCH_TYPES)}, got {match_type!r}")
    elif match_type == "REGEX":
        regexes.append((f"{path}#{label}/{filter_key}", value))
    return True


def check_rule(path, index, rule, expect_package=None):
    label = f"rules[{index}]"
    if not isinstance(rule, dict):
        err(path, f"{label}: must be an object")
        return

    unknown = set(rule) - RULE_KEYS
    if unknown & {"id", "hitCount"}:
        err(path, f"{label}: must not contain {sorted(unknown & {'id', 'hitCount'})} — the app assigns these on import")
        unknown -= {"id", "hitCount"}
    if unknown:
        err(path, f"{label}: unknown field(s) {sorted(unknown)}")

    package = rule.get("packageName")
    if not isinstance(package, str) or not PACKAGE_RE.match(package):
        err(path, f"{label}: packageName missing or not a valid Android package: {package!r}")
    elif expect_package and package != expect_package:
        err(path, f"{label}: packageName {package!r} does not match directory rules/{expect_package}/")

    if not isinstance(rule.get("appName"), str) or not rule["appName"].strip():
        err(path, f"{label}: appName is required (shown to users in the app)")

    if rule.get("ruleType") not in RULE_TYPES:
        err(path, f"{label}: ruleType must be one of {sorted(RULE_TYPES)}, got {rule.get('ruleType')!r}")

    if not isinstance(rule.get("isEnabled"), bool):
        err(path, f"{label}: isEnabled must be an explicit boolean")

    has_title = check_filter(path, label, rule, "titleFilter", "titleMatchType")
    has_text = check_filter(path, label, rule, "textFilter", "textMatchType")
    if not has_title and not has_text:
        err(path, f"{label}: needs at least one non-empty titleFilter or textFilter")

    adv = rule.get("advancedConfig")
    if adv is not None:
        if not isinstance(adv, dict):
            err(path, f"{label}: advancedConfig must be an object")
        else:
            bad = set(adv) - ADV_KEYS
            if bad:
                err(path, f"{label}: advancedConfig unknown field(s) {sorted(bad)}")
            if "isTimeLimitEnabled" in adv and not isinstance(adv["isTimeLimitEnabled"], bool):
                err(path, f"{label}: advancedConfig.isTimeLimitEnabled must be a boolean")
            for key, hi in (("startTimeHour", 23), ("startTimeMinute", 59), ("endTimeHour", 23), ("endTimeMinute", 59)):
                v = adv.get(key)
                if v is not None and not (isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= hi):
                    err(path, f"{label}: advancedConfig.{key} must be an integer in [0, {hi}]")


def check_file(fs_path, rel_path, expect_package=None):
    size = fs_path.stat().st_size
    if size > MAX_FILE_BYTES:
        err(rel_path, f"file is {size} bytes, over the app's {MAX_FILE_BYTES}-byte import cap")
        return
    try:
        data = json.loads(fs_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        err(rel_path, f"not valid UTF-8 JSON: {e}")
        return
    if not isinstance(data, dict):
        err(rel_path, "top level must be the export envelope object, not a bare array")
        return

    unknown = set(data) - ENVELOPE_KEYS
    if unknown:
        err(rel_path, f"unknown envelope field(s) {sorted(unknown)}")
    if data.get("version") != EXPORT_VERSION:
        err(rel_path, f"version must be {EXPORT_VERSION}, got {data.get('version')!r}")
    for key, lo in (("title", 3), ("description", 10)):
        v = data.get(key)
        if not isinstance(v, str) or len(v.strip()) < lo:
            err(rel_path, f"{key} is required (a string of at least {lo} chars) — it is the catalog entry")
    if "locale" in data and not isinstance(data["locale"], str):
        err(rel_path, "locale must be a string language tag")
    if "maintainer" in data and not isinstance(data["maintainer"], str):
        err(rel_path, "maintainer must be a string")

    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        err(rel_path, "rules must be a non-empty array")
        return
    has_allowlist = any(isinstance(r, dict) and r.get("ruleType") == "ALLOWLIST" for r in rules)
    if has_allowlist and "allowlist" not in str(data.get("description", "")).lower():
        err(rel_path, "list contains ALLOWLIST rules — description must mention 'allowlist' (they block all non-matching notifications)")
    for i, rule in enumerate(rules):
        check_rule(rel_path, i, rule, expect_package)


def main():
    checked = 0

    rules_dir = ROOT / "rules"
    if rules_dir.is_dir():
        for entry in sorted(rules_dir.iterdir()):
            rel = entry.relative_to(ROOT).as_posix()
            if not entry.is_dir():
                err(rel, "only per-package directories belong directly under rules/")
                continue
            if not PACKAGE_RE.match(entry.name):
                err(rel, "directory name must be a valid Android package name")
            files = sorted(entry.iterdir())
            if not files:
                err(rel, "empty package directory")
            for f in files:
                frel = f.relative_to(ROOT).as_posix()
                if not f.is_file() or not FILENAME_RE.match(f.name):
                    err(frel, "filename must be kebab-case, optionally with a locale part: <slug>[.<locale>].json")
                    continue
                check_file(f, frel, expect_package=entry.name)
                checked += 1

    bundles_dir = ROOT / "bundles"
    if bundles_dir.is_dir():
        for f in sorted(bundles_dir.iterdir()):
            frel = f.relative_to(ROOT).as_posix()
            if not f.is_file() or not FILENAME_RE.match(f.name):
                err(frel, "filename must be kebab-case, optionally with a locale part: <slug>[.<locale>].json")
                continue
            check_file(f, frel)
            checked += 1

    if checked == 0:
        errors.append("no rule files found under rules/ or bundles/")

    out = ROOT / "build" / "regexes.txt"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for source, pattern in regexes:
            encoded = base64.b64encode(pattern.encode("utf-8")).decode("ascii")
            fh.write(f"{source}\t{encoded}\n")

    print(f"{checked} file(s) checked, {len(regexes)} regex(es) extracted to {out.relative_to(ROOT)}")
    if errors:
        print(f"\n{len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
