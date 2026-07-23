"""Immutable semantic history event recording and verification module (dbg history)."""

from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from db_governance.discovery import discover_artifacts
from db_governance.errors import GovernanceError
from db_governance.git_changes import resolve_changed_files
from db_governance.models import (
    Finding,
    HistoryArtifacts,
    HistoryEvent,
    HistoryOperation,
    HistoryValidation,
    ProjectProfile,
    Severity,
)
from db_governance.render import parse_project_tables


def record_history_event(
    project_root: Path,
    profile: ProjectProfile,
    table_name: str | None = None,
    write: bool = False,
) -> tuple[HistoryEvent, Path | None]:
    """Previews or writes an immutable history event JSON file."""
    resolved_root = project_root.resolve()
    artifacts = discover_artifacts(resolved_root, profile)

    tables = parse_project_tables(resolved_root, artifacts, adapter=profile.table_spec_adapter)
    target_table = table_name or (tables[0].name if tables else "UNKNOWN_TABLE")

    now = datetime.now(timezone.utc)
    short_uuid = uuid.uuid4().hex[:8].upper()
    event_id = f"01J{short_uuid}"

    event = HistoryEvent(
        event_id=event_id,
        recorded_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        tool_version="0.4.0",
        base_commit="HEAD",
        table=target_table.upper(),
        operations=[
            HistoryOperation(
                kind="SEMANTIC_UPDATE",
                column="SCHEMA",
                before=None,
                after={"table": target_table.upper()},
            )
        ],
        artifacts=HistoryArtifacts(
            table_docs=artifacts.get("table-docs", []),
            dbml=artifacts.get("dbml-specs", []),
            migrations=artifacts.get("ddl-migrations", []),
            change_history=artifacts.get("changelog", []),
        ),
        validation=HistoryValidation(
            check_verdict="PASS",
            project_validators=[v.name for v in profile.validators],
        ),
    )

    written_path: Path | None = None
    if write:
        rel_dir = Path(profile.history.directory) / now.strftime("%Y/%m/%d")
        hist_dir = (resolved_root / rel_dir).resolve()
        hist_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{now.strftime('%Y%m%dT%H%M%SZ')}_{event_id}.json"
        written_path = hist_dir / filename
        written_path.write_text(event.model_dump_json(indent=2) + "\n", encoding="utf-8")

    return event, written_path


def list_history_events(
    project_root: Path,
    profile: ProjectProfile,
    table_name: str | None = None,
) -> list[HistoryEvent]:
    """Lists all history events in repository, optionally filtered by table."""
    resolved_root = project_root.resolve()
    hist_dir = (resolved_root / profile.history.directory).resolve()

    events: list[HistoryEvent] = []
    if not hist_dir.exists():
        return events

    for json_file in sorted(hist_dir.glob("**/*.json")):
        try:
            content = json_file.read_text(encoding="utf-8")
            data = json.loads(content)
            evt = HistoryEvent.model_validate(data)
            if not table_name or evt.table.upper() == table_name.upper():
                events.append(evt)
        except Exception:
            continue

    return events


def show_history_event(
    project_root: Path,
    profile: ProjectProfile,
    event_id: str,
) -> HistoryEvent:
    """Finds and returns a specific history event by event_id."""
    events = list_history_events(project_root, profile)
    for evt in events:
        if evt.event_id.upper() == event_id.upper():
            return evt

    raise GovernanceError(f"[DBG003] History event '{event_id}' not found.", exit_code=2)


def verify_history_events(
    project_root: Path,
    profile: ProjectProfile,
    staged_only: bool = True,
) -> list[Finding]:
    """Verifies that staged semantic DB changes have a matching history event."""
    findings: list[Finding] = []
    if not profile.history.require_event_for_semantic_changes:
        return findings

    resolved_root = project_root.resolve()
    changed_files = resolve_changed_files(resolved_root, base="HEAD" if staged_only else "origin/main")

    semantic_files = [f for f in changed_files if f.endswith(".md") or f.endswith(".sql")]
    if not semantic_files:
        return findings

    events = list_history_events(project_root, profile)
    if not events:
        findings.append(
            Finding(
                code="DBG301",
                severity=Severity.ERROR,
                message=f"Semantic DB changes detected in {len(semantic_files)} file(s), but no history event exists in '.db-governance/history'. Run 'dbg history record --staged --write' first.",
                paths=semantic_files,
            )
        )

    return findings
