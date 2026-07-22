# Architecture & Technical Design

`db-governance` is built as a deterministic Python 3.12 CLI and thin Agent Skill layer for database contract synchronization governance.

## Component Breakdown

```
[ Agent / User ]
       │
       ▼
[ Skill: database-governance ] (SKILL.md + references)
       │
       ▼
[ CLI: dbg ] (Typer CLI app)
       │
   ┌───┴─────────────────────────────────────────┐
   │                                             │
   ▼                                             ▼
[ Config & Discovery ]                   [ Git Changes ]
(load_profile, discover_artifacts)       (NUL -z diff/ls-files parser)
   │                                             │
   └─────────────────┬───────────────────────────┘
                     │
                     ▼
            [ Rule Engine ]
            (evaluate_rules, evaluate_required_artifacts)
                     │
                     ▼
           [ Validator Runner ]
           (subprocess.run, shell=False, secret masking)
                     │
                     ▼
           [ Report & Evidence ]
           (render_text, render_json, write_evidence atomic write)
```

## Core Design Principles

1. **Deterministic Rule Execution**: Core Python logic contains no project-specific hardcoding (no EVBP paths, Korean identifiers, or PostgreSQL commands). All project rules are declared in `.db-governance.toml`.
2. **Explicit Security Boundaries**: Path resolution checks (`resolve()`) prevent directory traversal (`../`) and symlink escapes (`DBG003`). External validators execute with `shell=False`.
3. **Decoupled Live DB State**: Documentation verdict (`clean` vs `findings_detected`) is evaluated solely from version-controlled files. Live database connectivity is out of scope and reported as `not_checked`.
