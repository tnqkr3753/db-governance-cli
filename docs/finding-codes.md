# Finding Codes Reference

| Code | Severity | Category | Trigger Condition | Exit Code Effect |
| --- | --- | --- | --- | --- |
| `DBG001` | ERROR | Config | Profile file `.db-governance.toml` does not exist | 2 |
| `DBG002` | ERROR | Config | Profile TOML syntax error, schema validation failure, or version != 1 | 2 |
| `DBG003` | ERROR | Path | Project root invalid, path traversal attempt (`../`), or symlink escape | 2 |
| `DBG101` | ERROR | Discovery | Required artifact group (`required = true`) matched zero files | 1 |
| `DBG201` | ERROR | Rule | Synchronization rule requirement missing from changed files | 1 |
| `DBG202` | WARNING | Rule | `--change-type unknown` fallback: conservative semantic checks applied | 0 |
| `DBG301` | ERROR | Validator | Project validator exited with non-zero exit code | 1 |
| `DBG302` | ERROR | Validator | Project validator process execution failed or timed out | 2 |
| `DBG401` | ERROR | Evidence | Evidence output destination files already exist without `--overwrite` | 2 |
