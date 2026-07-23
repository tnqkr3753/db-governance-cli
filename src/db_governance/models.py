"""Domain models and data schemas for db-governance v0.4.0."""

from enum import StrEnum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class ChangeType(StrEnum):
    SEMANTIC = "semantic"
    FORMATTING = "formatting"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AgentType(StrEnum):
    GEMINI = "gemini"
    CODEX = "codex"
    CLAUDE = "claude"
    ALL = "all"


class ArtifactRole(StrEnum):
    SOURCE = "source"
    DERIVED = "derived"
    MIGRATION = "migration"
    HISTORY = "history"
    OTHER = "other"


class ArtifactGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    role: ArtifactRole = ArtifactRole.OTHER
    patterns: list[str] = Field(min_length=1)
    required: bool = True


class RequireChangedSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    match_any: list[str]


ChangeRequirement = RequireChangedSpec


class SyncRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    description: str
    when_changed_any: list[str]
    applies_to: list[ChangeType] = Field(
        default_factory=lambda: [ChangeType.SEMANTIC, ChangeType.UNKNOWN]
    )
    severity: Severity = Severity.ERROR
    require_changed: list[RequireChangedSpec] = Field(default_factory=list)


class ValidatorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    argv: list[str] = Field(min_length=1)
    cwd: str = "."
    timeout_seconds: int = Field(default=120, ge=1, le=1800)
    max_output_bytes: int = Field(default=1_048_576, ge=1024, le=10_485_760)


class MigrationSeriesSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    directory: str
    file_pattern: str = "V1_{number}__{slug}.sql"
    number_start: int = 1


class TableSpecAdapterSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column_section_heading: str = "컬럼 명세"
    name_header: str = "컬럼명"
    type_header: str = "데이터 타입"
    nullable_header: str = "Null"
    primary_key_header: str = "PK"
    description_header: str = "설명"


class HistoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    directory: str = ".db-governance/history"
    require_event_for_semantic_changes: bool = True


class ProjectProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = 1
    name: str
    artifact_groups: list[ArtifactGroup] = Field(default_factory=list)
    rules: list[SyncRule] = Field(default_factory=list)
    validators: list[ValidatorSpec] = Field(default_factory=list)
    migration_series: list[MigrationSeriesSpec] = Field(default_factory=list)
    table_spec_adapter: TableSpecAdapterSpec | None = None
    history: HistoryConfig = Field(default_factory=HistoryConfig)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    severity: Severity
    message: str
    paths: list[str] = Field(default_factory=list)
    rule_id: str | None = None


class ValidatorResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


class AuditReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    project_name: str
    project_root: str
    profile_path: str
    profile_hash: str
    change_type: ChangeType
    changed_files: list[str]
    artifacts: dict[str, list[str]]
    findings: list[Finding]
    validators: list[ValidatorResult] = Field(default_factory=list)
    documentation_state: str
    live_database_state: Literal["not_checked"] = "not_checked"


class HistoryOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    column: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


class HistoryArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table_docs: list[str] = Field(default_factory=list)
    dbml: list[str] = Field(default_factory=list)
    migrations: list[str] = Field(default_factory=list)
    change_history: list[str] = Field(default_factory=list)


class HistoryValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    check_verdict: str
    project_validators: list[str] = Field(default_factory=list)


class HistoryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    recorded_at: str
    tool_version: str = "0.4.0"
    base_commit: str
    table: str
    operations: list[HistoryOperation] = Field(default_factory=list)
    artifacts: HistoryArtifacts = Field(default_factory=HistoryArtifacts)
    validation: HistoryValidation


class MigrationContextReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table: str
    base_ref: str
    delta: dict[str, Any]
    history_events: list[HistoryEvent] = Field(default_factory=list)
    migration_files: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list)
