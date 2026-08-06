## What this adds/changes

<!-- One or two sentences: which app(s), what gets blocked, what stays. -->

## Checklist

- [ ] `python3 scripts/validate.py` passes
- [ ] `java scripts/ValidateRegex.java build/regexes.txt` passes
- [ ] `index.json` regenerated (`python3 scripts/generate_index.py`) and committed
- [ ] Tested on a real device: junk is blocked, important notifications still arrive
- [ ] No transactional notifications affected (OTPs, security alerts, order status, human messages)
- [ ] If any rule is `ALLOWLIST`, the file's `description` says so
