# Safety Boundary & Non-Mutation Declaration

## Core System Boundaries

1. **Zero Database Connectivity in v0.1**:
   - `db-governance` contains no JDBC, DB-API, `psql`, `sqlalchemy`, or socket connection code.
   - It performs zero database operations (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`).
   - `AuditReport.live_database_state` is hard-coded as `Literal["not_checked"] = "not_checked"`.

2. **Read-Only Filesystem Guarantee**:
   - The CLI only reads repository files during `doctor`, `inspect`, `check`, and dry `init`.
   - Filesystem writes occur **only** when `--write` (for `dbg init`) or `--output` (for `dbg evidence`) is explicitly supplied.

3. **Subprocess Isolation**:
   - Configured project validators are invoked via `subprocess.run(argv, cwd=spec_cwd, shell=False)`.
   - `dbg` does not execute shell strings or interpolate environment variables into shell interpreters.
   - Any live database mutations or external network side-effects initiated by profile-declared external validators are outside `dbg`'s core guarantee scope.
