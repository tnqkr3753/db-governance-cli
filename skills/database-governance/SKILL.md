---
name: database-governance
description: Inspect, audit, and maintain database contract synchronization, semantic history events, and migration context across repositories.
---

# Database Governance Skill (dbg v0.4.0)

Use this skill whenever doing any database task (e.g. adding columns, modifying tables, inspecting schemas, auditing contract synchronization, or managing DDL versions).

## Core Governance Principles & Safety Boundaries

1. **Audit & Evidence Boundary:**
   `dbg` is strictly a contract audit, semantic history, and context evidence tool.
   - It **NEVER** connects to live databases or executes DDL on a live database.
   - `AuditReport.live_database_state` is always `"not_checked"`.
   - `dbg` does NOT automatically generate executable `CREATE TABLE` / `ALTER TABLE` DDL SQL.

2. **Migration Authoring Routing:**
   To design a migration, use `dbg migration-context` to gather structured evidence, and delegate DDL, backfill, and validation planning to the **`database-migration-design`** skill.

3. **Immutable History Events:**
   When `require_event_for_semantic_changes = true` in profile, every semantic change MUST have a recorded history event under `.db-governance/history/`.

## Mandatory Workflow Steps

### Step 1: Inspect & Gather Context
```bash
dbg inspect --project . --format text
dbg migration-context --project . --table <TABLE_NAME> --base origin/main --format json
```

### Step 2: Edit Specification (Dry-Run Preview first)
```bash
dbg edit-spec add-column --project . --table <TABLE> --name <COL> --type "<TYPE>" --write
```

### Step 3: Scaffold Migration Version File
```bash
dbg ddl-manage --project . --series main --create --slug <SLUG>
```

### Step 4: Record History Event & Audit Contract
```bash
dbg history record --staged --write
dbg check --project . --base origin/main --change-type semantic --run-project-validators
```
