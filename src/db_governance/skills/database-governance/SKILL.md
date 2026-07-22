---
name: database-governance
description: Inspect and maintain database documentation governance across repositories. Use this skill whenever a user asks to document or review schema changes, synchronize migrations with table docs, DBML or ERD artifacts, update database change history, audit whether database documentation is complete, or distinguish documented schema state from live database state. Do not use it merely to write an application query or tune SQL performance.
---

# Database Governance Skill

This skill provides workflow guidance and deterministic auditing for database documentation synchronization, contract governance, and validator execution.

> [!IMPORTANT]
> **Safety Boundary & DB State Rule**
> - The `dbg` CLI and database governance skill audit documentation and contract alignment only.
> - `dbg` NEVER connects to a database, executes SQL, applies migrations, or infers live deployment status.
> - Reports always declare `live_database_state: "not_checked"`.

## Standard Audit & Governance Workflow

Follow this procedure when assisting with database documentation and contract governance:

### 1. Installation & Environment Inspection
Verify the CLI is installed or run it via `uv`:
```bash
dbg doctor --project .
# or fallback:
uv run dbg doctor --project .
```

### 2. Profile Discovery & Inspection
Run `dbg inspect` to inventory database artifacts (table docs, migrations, changelog, DBML):
```bash
dbg inspect --project . --format text
```
If `.db-governance.toml` is missing:
1. Preview candidate profile: `dbg init --project .`
2. Write profile with user confirmation: `dbg init --project . --write`
3. Refer to [project-profile.md](file:///Users/yuntaepark/Work/database-manager/db-governance/skills/database-governance/references/project-profile.md) for custom TOML rules.

### 3. Change Set Classification
Classify changed artifacts into one of three categories (see [change-classification.md](file:///Users/yuntaepark/Work/database-manager/db-governance/skills/database-governance/references/change-classification.md)):
- `semantic`: Schema structure, column additions/deletions, type/nullability modifications.
- `formatting`: Typos, markdown formatting, whitespace, comments (bypasses migration requirements).
- `unknown`: Unsure or unclassified (evaluates semantic rules conservatively with `DBG202` warning).

### 4. Synchronization Check
Run `dbg check` with explicit changed files or Git base reference:
```bash
dbg check --project . --changed-file database/tables/USERS.md --change-type semantic
```
For trusted repositories with configured project validators:
```bash
dbg check --project . --base HEAD --change-type semantic --run-project-validators
```

### 5. Remediation & Companion Updates
If `dbg check` reports missing companion changes (`DBG201`):
1. Update the required companion artifacts (e.g. migration SQL, change history, DBML).
2. Re-run `dbg check` until documentation state is `clean` (verdict: PASS).

### 6. Evidence Generation
When evidence artifacts are requested:
```bash
dbg evidence --project . --output .evidence/bundle --overwrite
```
This produces `report.json` and `report.md` atomically.

## Detailed References
- [workflow.md](file:///Users/yuntaepark/Work/database-manager/db-governance/skills/database-governance/references/workflow.md): Complete CLI command selection and fallback workflows.
- [change-classification.md](file:///Users/yuntaepark/Work/database-manager/db-governance/skills/database-governance/references/change-classification.md): Rules and examples for semantic vs formatting changes.
- [project-profile.md](file:///Users/yuntaepark/Work/database-manager/db-governance/skills/database-governance/references/project-profile.md): Profile TOML schema specification.
- [report-format.md](file:///Users/yuntaepark/Work/database-manager/db-governance/skills/database-governance/references/report-format.md): Report structure and finding code details.
