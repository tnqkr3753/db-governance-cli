# Audit Report Format & Finding Codes

## Finding Code Table

| Code | Severity | Description | Exit Code Effect |
| --- | --- | --- | --- |
| `DBG001` | ERROR | Profile file not found | 2 |
| `DBG002` | ERROR | Profile syntax or schema invalid / unsupported version | 2 |
| `DBG003` | ERROR | Project root invalid or path escapes project root | 2 |
| `DBG101` | ERROR | Required artifact group has no matching files | 1 |
| `DBG201` | ERROR | Synchronization requirement missing from changed files | 1 |
| `DBG202` | WARNING | Change type is unknown; conservative rules applied | 0 |
| `DBG301` | ERROR | Project validator returned non-zero exit code | 1 |
| `DBG302` | ERROR | Project validator could not execute or timed out | 2 |
| `DBG401` | ERROR | Evidence output destination already exists | 2 |

## JSON Audit Report Model

```json
{
  "schema_version": 1,
  "project_name": "example-project",
  "project_root": "/path/to/project",
  "profile_path": "/path/to/project/.db-governance.toml",
  "profile_hash": "a1b2c3d4...",
  "change_type": "semantic",
  "changed_files": [
    "database/tables/USERS.md"
  ],
  "artifacts": {
    "table-docs": ["database/tables/USERS.md"]
  },
  "findings": [
    {
      "code": "DBG201",
      "severity": "error",
      "message": "Rule DBDOC-001: change requires updating migration.",
      "paths": ["database/tables/USERS.md"],
      "rule_id": "DBDOC-001"
    }
  ],
  "validators": [],
  "documentation_state": "findings_detected",
  "live_database_state": "not_checked"
}
```
