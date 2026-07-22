# Project Profile TOML Specification

The `.db-governance.toml` profile defines artifact groups, synchronization rules, and project validators.

## Schema Specification

```toml
version = 1
name = "project-name"

[[artifact_groups]]
name = "table-docs"
role = "source" # source | derived | migration | history | reference
patterns = ["database/tables/**/*.md"]
required = true

[[rules]]
id = "DBDOC-001"
description = "Sync rule description"
when_changed_any = ["database/tables/**/*.md"]
applies_to = ["semantic", "unknown"] # semantic | formatting | unknown
severity = "error" # error | warning | info

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

## Security & Path Boundaries
- Patterns starting with `..` or escaping project root are strictly prohibited (`DBG003`).
- Validators run with `shell=False` without shell variable interpolation.
- Secrets ending in `_PASSWORD`, `_SECRET`, `_TOKEN`, or `_KEY` in environment variables are automatically masked (`***REDACTED***`).
