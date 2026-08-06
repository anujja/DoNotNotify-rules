# Contributing rules

Thanks for helping! This repo is moderated via pull requests; CI validates every file automatically.

## Where files go

- **Per-app list:** `rules/<packageName>/<slug>.json`
  - `<packageName>` is the app's Android package (the `id=` parameter in its Play Store URL). Every rule in the file must target that package.
  - `<slug>` is kebab-case and describes what the list does: `promos.json`, `engagement.json`, `allow-essentials.json`.
  - **Locale variants** are separate files with a language tag before `.json`: `promos.es.json`, `promos.zh-Hans.json`. Set the matching `locale` field in the envelope.
- **Curated multi-app pack:** `bundles/<slug>.json`. Bundles may mix packages but should have one clear theme.

## File format

Top-level envelope:

| Field | Required | Notes |
|---|---|---|
| `version` | yes | Always `2` (the current DoNotNotify export version) |
| `title` | yes | Short human name, shown in the catalog: `"Flipkart — promotional spam"` |
| `description` | yes | What it blocks, what it keeps. **Must mention ALLOWLIST behavior if the list uses it.** |
| `maintainer` | no | Your GitHub handle |
| `locale` | no | Language tag (`en`, `es`, `zh-Hans`) for the patterns' language |
| `rules` | yes | Non-empty array of rules |

Each rule:

| Field | Required | Notes |
|---|---|---|
| `packageName` | yes | Android package the rule targets |
| `appName` | yes | Human-readable app name |
| `ruleType` | yes | `DENYLIST` (block matches), `ALLOWLIST` (allow only matches, **block everything else**), `STACK` (group matches into one notification) |
| `titleFilter` / `textFilter` | ≥ 1 | Pattern for the notification title / text. Max 512 chars each |
| `titleMatchType` / `textMatchType` | with filter | `CONTAINS` (case-insensitive substring) or `REGEX` (Java flavor; prefix `(?i)` for case-insensitive) |
| `isEnabled` | yes | Almost always `true` |
| `name` | no | Optional label shown in the app's rule list |
| `advancedConfig` | no | Time window: `{"isTimeLimitEnabled": true, "startTimeHour": 22, "startTimeMinute": 0, "endTimeHour": 7, "endTimeMinute": 0}` |

Never include `id` or `hitCount` — CI rejects them (the app assigns fresh IDs on import).

## Rule guidelines

- **Never block transactional notifications** — OTPs, security alerts, order/delivery status, payment confirmations, messages from actual humans. Target the noise: promos, recommendations, "come back" nags, streaks, trending.
- **Prefer precise patterns.** `(?i).*(flash sale|use code).*` beats `.*sale.*` (which also kills "your item is on sale return hold"). Regexes are matched against the full title/text, so wrap keyword alternations in `.*(...).*`.
- **Regexes are Java flavor** (`java.util.regex.Pattern`) — CI compiles every one. Keep them simple; avoid nested quantifiers like `(a+)+` that can backtrack catastrophically.
- **ALLOWLIST is fail-closed**: anything not matching is blocked. Use it only when the noise is unbounded and the important notifications are predictable (e.g. gate/visitor apps), and say so in `description`.
- **Test on a device before submitting.** Import your file, trigger or wait for real notifications, and check both that the junk is blocked and that important ones still arrive.

## Before you open the PR

```bash
python3 scripts/validate.py                       # format + structure
java scripts/ValidateRegex.java build/regexes.txt # every regex compiles (Java flavor)
python3 scripts/generate_index.py                 # regenerate index.json — commit the result
```

All three must pass; CI runs exactly these. Then fill in the PR checklist.

## What reviewers look for

Correct target package, no transactional blocking, sensible patterns, honest `title`/`description`, and `index.json` regenerated. Rules that are too aggressive or too personal (e.g. blocking a specific contact's name) belong in your own fork, not the shared lists.
