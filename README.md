# DB Governance CLI (`dbg`) & Skill

[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`db-governance` is a standalone, read-only-first CLI tool and agent skill that discovers database documentation contracts, detects unsynchronized semantic schema changes, executes explicitly approved project validators, and reports documentation state completely separately from live database state.

> [!IMPORTANT]
> **v0.1 Safety Boundary & Zero Live DB Guarantee**
> - `dbg` core **never** connects to a database, executes SQL, applies migrations, or infers live deployment status.
> - Reports always declare `live_database_state: "not_checked"`.
> - External project validators (`--run-project-validators`) run as separate processes declared in the profile via `shell=False`. Their side effects are outside `dbg`'s core scope.

---

## Installation

Install using `uv`:
```bash
# From local repository
uv tool install .

# Or run directly via uv without installing:
uv run dbg --help
```

---

## Public CLI Commands

### 1. `dbg doctor`
Inspects system environment, Python version, Git availability, project directory, and profile loading.
```bash
dbg doctor --project /path/to/project
```

### 2. `dbg init`
Previews candidate `.db-governance.toml` profile without making filesystem changes.
```bash
# Dry-run preview
dbg init --project /path/to/project

# Write profile file to disk (exits 2 if file exists)
dbg init --project /path/to/project --write
```

### 3. `dbg inspect`
Inventories matched database source, derived, migration, and history artifacts across configured groups.
```bash
dbg inspect --project /path/to/project --format json
```

### 4. `dbg check`
Evaluates profile synchronization rules against changed files or Git base reference.
```bash
# Check explicit changed files
dbg check --project /path/to/project \
  --changed-file database/tables/USERS.md \
  --changed-file database/migrations/V1__users.sql \
  --change-type semantic

# Check Git diff relative to base ref and run project validators
dbg check --project /path/to/project \
  --base HEAD \
  --change-type semantic \
  --run-project-validators
```

### 5. `dbg evidence`
Evaluates rules and atomically generates `report.json` and `report.md` into `--output`.
```bash
dbg evidence --project /path/to/project \
  --base HEAD \
  --output .evidence/bundle \
  --overwrite
```

### 6. `dbg render`
Renders Mermaid ERD or DBML diagram code from discovered table specifications.
```bash
# Output Mermaid erDiagram to stdout
dbg render --project /path/to/project --format mermaid

# Output DBML code to file
dbg render --project /path/to/project --format dbml --output schema.dbml
```

### 7. `dbg dictionary`
Validates discovered table specifications against data dictionary term recommendations and domain data type standards.
```bash
dbg dictionary --project /path/to/project --dictionary .db-dictionary.toml
```

### 8. `dbg impact`
Analyzes downstream file dependencies and impact when a table or column changes.
```bash
dbg impact --project /path/to/project --table USERS --column status
```

### 9. `dbg generate-spec`
Generates table markdown specification and DDL migration template scaffolding.
```bash
# Preview scaffolding
dbg generate-spec --table PAYMENTS --columns "id:BIGINT,amount:DECIMAL(18_2)"

# Write scaffold files to disk
dbg generate-spec --table PAYMENTS --columns "id:BIGINT,amount:DECIMAL(18_2)" --write
```

### 10. `dbg install-skill`
Installs or symlinks the `database-governance` skill into Antigravity's skills directory (`~/.gemini/config/skills/database-governance`).
```bash
# Copy skill to default ~/.gemini/config/skills/database-governance
dbg install-skill --overwrite

# Symlink for development
dbg install-skill --symlink --overwrite
```

---

## Exit Code Contract

| Exit Code | Meaning | Examples |
| --- | --- | --- |
| `0` | Clean audit pass | No error findings detected (`documentation_state: "clean"`) |
| `1` | Governance finding detected | Missing companion change (`DBG201`), missing required group (`DBG101`), validator failure (`DBG301`) |
| `2` | Execution / Usage / Config Error | Missing profile (`DBG001`), invalid TOML (`DBG002`), path escaping (`DBG003`), validator timeout/exec error (`DBG302`), evidence existing destination (`DBG401`) |

---

## EVBP Reference Profile Usage

To run `dbg` against the EVBP checkout without modifying it:

```bash
dbg check \
  --project /path/to/evbp-etl \
  --profile examples/evbp-etl.toml \
  --base HEAD \
  --change-type semantic \
  --run-project-validators
```

---

## Finding Codes Table

| Code | Severity | Description | Exit Code |
| --- | --- | --- | --- |
| `DBG001` | ERROR | Profile file not found | 2 |
| `DBG002` | ERROR | Profile invalid or unsupported version | 2 |
| `DBG003` | ERROR | Project root invalid or path escapes root | 2 |
| `DBG101` | ERROR | Required artifact group has zero matches | 1 |
| `DBG201` | ERROR | Synchronization rule requirement missing | 1 |
| `DBG202` | WARNING | Change type unknown; conservative rules applied | 0 |
| `DBG301` | ERROR | Project validator returned non-zero exit code | 1 |
| `DBG302` | ERROR | Project validator could not start or timed out | 2 |
| `DBG401` | ERROR | Evidence output destination already exists | 2 |
