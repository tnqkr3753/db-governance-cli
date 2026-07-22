# CLI & Skill Workflow Guide

## Command Reference

### `dbg doctor`
Checks Python 3.12+ runtime environment, Git installation, project directory validity, and profile presence.
```bash
dbg doctor [--project PATH] [--format text|json]
```

### `dbg init`
Previews or writes repository-local `.db-governance.toml`.
- Without `--write`: Prints candidate profile to stdout (dry run).
- With `--write`: Creates `.db-governance.toml` (fails if file already exists).
```bash
dbg init [--project PATH] [--template PATH] [--write]
```

### `dbg inspect`
Discovers matching database artifacts across configured artifact groups. Never runs change rules or validators.
```bash
dbg inspect [--project PATH] [--profile PATH] [--format text|json]
```

### `dbg check`
Evaluates profile synchronization rules against changed files or Git base reference.
```bash
dbg check [--project PATH] [--profile PATH] [--base REF | --changed-file PATH ...] [--change-type semantic|formatting|unknown] [--run-project-validators] [--format text|json]
```

### `dbg evidence`
Evaluates rules and writes `report.json` and `report.md` atomically into `--output`.
```bash
dbg evidence --project PATH --output PATH [--overwrite]
```

## Exit Code Contract
- `0`: No error findings exist (pass).
- `1`: Governance findings exist (unsynchronized changes `DBG201`, missing required group `DBG101`, or validator failure `DBG301`).
- `2`: Usage, configuration, path escaping, or process execution failure (`DBG001`, `DBG002`, `DBG003`, `DBG302`, `DBG401`).
