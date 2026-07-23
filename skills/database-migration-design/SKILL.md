---
name: database-migration-design
description: Design database migrations, data backfills, transactional validations, and rollback plans from deterministic dbg context and live catalog evidence.
---

# Database Migration Design Skill

Use this skill whenever a database schema migration, table specification update, column modification, or DDL version creation is required.

## Core Rules

1. **Never generate quick unverified DDL directly from Markdown specs.**
   Migrations require compatibility analysis, deterministic backfills, transactional verification, and rollback planning.

2. **Always gather deterministic context first:**
   ```bash
   dbg migration-context --project . --table <TABLE_NAME> --base origin/main --format json
   ```

3. **Request Live Catalog Evidence:**
   If live catalog evidence is missing, state it explicitly before producing destructive DDL or constraint tightening statements.

## Required Deliverable Structure

When designing a migration, your output artifact or plan MUST include:

### 1. Change Intent & Compatibility Assumptions
- Business rationale and backward compatibility assumptions (e.g. active API versions, legacy data presence).

### 2. Migration Step Plan
- Sequential order of migration operations (e.g. Add nullable column -> Backfill existing rows -> Set NOT NULL / Add constraint).

### 3. Data Backfill / Bridge Population Plan
- Explicit SQL statements to copy, transform, or backfill existing production rows before applying destructive or tightening changes.

### 4. Verification SQL Suite
- **Preflight Check**: Catalog SELECTs to verify preconditions.
- **Transaction Block**: Idempotent DDL/DML statements (`BEGIN; ... COMMIT;`).
- **Post-Apply Audit**: Integrity checks verifying zero invalid rows.

### 5. Rollback & Non-Reversibility Statement
- Safe rollback SQL steps or explicit non-reversibility declaration.

### 6. Companion Artifact & API Lineage Summary
- List of synchronized table docs, DBML files, change history, and downstream API services impacted.
