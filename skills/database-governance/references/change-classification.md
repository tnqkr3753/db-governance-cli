# Change Classification Guide

Changes to database artifacts are classified into three types:

## 1. `semantic`
A semantic change alters the logical structure, contract, or behavior of the database schema.

### Examples:
- Adding, dropping, or renaming a table, view, or column.
- Changing a column data type (e.g. `VARCHAR(50)` to `VARCHAR(100)`).
- Modifying nullability, default values, primary keys, or foreign keys.
- Changing index definitions or constraint rules.

### Rule Evaluation:
- All profile `SyncRule` definitions apply.
- Companion artifacts (migration SQL, change history update, DBML update) are strictly required if specified by rules.

## 2. `formatting`
A formatting change affects presentation or non-functional text without modifying schema contracts.

### Examples:
- Fixing typos in documentation descriptions or markdown comments.
- Re-aligning markdown tables or adjusting line breaks/indentation.
- Updating documentation headers or editorial text.

### Rule Evaluation:
- Semantic synchronization rules are bypassed.
- No new migration or change history entry is demanded.

## 3. `unknown`
Default fallback when change intent is unverified or ambiguous.

### Rule Evaluation:
- Applies semantic synchronization rules conservatively.
- Emits a `DBG202` warning finding to inform the user that conservative checks were applied.
