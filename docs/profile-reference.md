# Profile TOML Specification Reference

## TOML Profile Structure

```toml
version = 1
name = "project-name"

[[artifact_groups]]
name = "table-docs"
role = "source"       # source | derived | migration | history | reference
patterns = ["database/tables/**/*.md"]
required = true

[[rules]]
id = "DBDOC-001"
description = "Rule description"
when_changed_any = ["database/tables/**/*.md"]
applies_to = ["semantic", "unknown"]
severity = "error"   # error | warning | info

[[rules.require_changed]]
label = "migration"
match_any = ["database/migrations/*.sql"]

[[validators]]
name = "verify-script"
argv = ["python", "scripts/verify.py"]
cwd = "."
timeout_seconds = 120
max_output_bytes = 1048576
```

## Model Constraints
- `version`: Must be `1`.
- `artifact_groups.patterns`: Must have at least 1 pattern, cannot escape project root.
- `rules.require_changed.match_any`: Must have at least 1 pattern per requirement.
- `validators.argv`: List of string tokens executed without a shell (`shell=False`).
- `validators.timeout_seconds`: Integer between 1 and 1800 (default 120).
