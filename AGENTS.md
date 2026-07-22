# AGENTS.md — AI Agent & Contributor Guidelines for `db-governance-cli`

Welcome to `db-governance-cli` (`dbg`). This repository houses a standalone, read-only-first database contract governance CLI and reusable AI Agent Skill.

All AI agents (Antigravity, Codex, Claude, etc.) and human contributors working on this codebase **MUST** strictly follow the guidelines below.

---

## 1. Project Boundaries & Absolute Rules

> [!IMPORTANT]
> **Safety Boundary & Zero Live DB Connection**
> - **v0.1 & v0.2 Scope**: `dbg` core NEVER connects to a database, executes SQL, applies migrations, or infers live deployment status.
> - `AuditReport.live_database_state` MUST remain hardcoded as `Literal["not_checked"] = "not_checked"`.
> - External project validators (`--run-project-validators`) run only when explicitly requested, using `subprocess.run(..., shell=False)`.

> [!IMPORTANT]
> **Profile-Driven Generic Architecture**
> - Core Python code under `src/db_governance/` MUST NEVER contain hardcoded project-specific paths, repository names (e.g. `evbp-etl`), Korean table identifiers, DBML assumptions, or PostgreSQL commands.
> - All repository-specific rules, patterns, and validator specs MUST be defined in TOML profiles (`.db-governance.toml` or `examples/*.toml`).

---

## 2. Security & Path Execution Rules

1. **Path Resolution & Jailbreak Protection**:
   - All input paths must be resolved via `Path.resolve()`.
   - Paths must be checked against `project_root.resolve()` using `.is_relative_to()`. Path traversal attempts (`../`) or symlinks escaping `project_root` must fail closed with exit code `2` (`DBG003`).
2. **Subprocess Isolation**:
   - Never use `shell=True` or string shell command execution. Pass argument vectors `list[str]` to `subprocess.run(shell=False)`.
3. **Environment Secret Masking**:
   - Command outputs captured in validator results must automatically redact values matching environment variables ending in `_PASSWORD`, `_SECRET`, `_TOKEN`, or `_KEY` with `***REDACTED***`.

---

## 3. Exit Code Contract

| Code | Meaning | Triggers |
| --- | --- | --- |
| `0` | Audit Clean / Pass | No error findings (`documentation_state: "clean"`) |
| `1` | Governance Finding | Missing companion change (`DBG201`), missing required group (`DBG101`), validator failure (`DBG301`), dictionary violation (`DBG501`) |
| `2` | Execution / Config Error | Missing config (`DBG001`), invalid TOML (`DBG002`), path escape (`DBG003`), validator timeout (`DBG302`), evidence existing destination (`DBG401`) |

---

## 4. Development Workflow & Quality Gate

When adding new features or fixing bugs:

### 1) Issue & Branch Strategy
- Create a GitHub Issue first: `gh issue create`
- Branch naming convention: `feat/issue-#-short-name` (e.g., `feat/issue-1-render-erd`)

### 2) TDD Workflow
- Write unit tests under `tests/` before implementing the feature.
- Ensure all tests pass: `uv run pytest -q`

### 3) Quality & Typing Checks
Before committing code, run the full automated gate:
```bash
uv run ruff check .
uv run basedpyright src
uv run pytest --cov=db_governance --cov-report=term-missing
uv build
```

### 4) Agent Skill Synchronization
Whenever CLI commands or references change, update `skills/database-governance/` and sync the skill:
```bash
uv run dbg install-skill --overwrite
```

---

## 5. File Structure Reference

```text
db-governance/
├── AGENTS.md                   # AI Agent & Contributor guidelines (this file)
├── README.md                   # Public usage documentation
├── pyproject.toml              # Hatchling packaging & tools configuration
├── src/db_governance/          # Core package
│   ├── cli.py                  # Typer CLI commands (doctor, init, inspect, check, evidence, install-skill, ...)
│   ├── config.py               # TOML profile loader & validator
│   ├── discovery.py            # Glob artifact inventory collector
│   ├── errors.py               # Exception hierarchy (GovernanceError, ProfileError)
│   ├── git_changes.py          # NUL-terminated git diff/ls-files parser
│   ├── models.py               # Pydantic v2 data models
│   ├── render.py               # ERD (Mermaid) & DBML diagram renderer
│   ├── report.py               # Text/JSON/Markdown report renderer & atomic evidence writer
│   ├── rules.py                # Rule evaluation & regex glob matcher
│   ├── runner.py               # Subprocess validator runner with secret masking
│   └── templates.py            # Candidate TOML profile template generator
├── tests/                      # Pytest suite & fixtures
├── examples/                   # Reference profiles (generic.toml, evbp-etl.toml)
├── docs/                       # Architecture, finding codes, profile spec, safety boundary
└── skills/database-governance/ # Reusable Agent Skill & Evals
```
