"""Pydantic data models for database governance."""

from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ChangeType(StrEnum):
    SEMANTIC = "semantic"
    FORMATTING = "formatting"
    UNKNOWN = "unknown"


class AgentType(StrEnum):
    GEMINI = "gemini"
    CODEX = "codex"
    CLAUDE = "claude"
    ALL = "all"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ArtifactRole(StrEnum):
    SOURCE = "source"
    DERIVED = "derived"
    MIGRATION = "migration"
    HISTORY = "history"
    REFERENCE = "reference"


class ArtifactGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    role: ArtifactRole
    patterns: list[str] = Field(min_length=1)
    required: bool = True


class ChangeRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    match_any: list[str] = Field(min_length=1)


class SyncRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    description: str
    when_changed_any: list[str] = Field(min_length=1)
    applies_to: set[ChangeType] = Field(
        default_factory=lambda: {ChangeType.SEMANTIC, ChangeType.UNKNOWN}
    )
    require_changed: list[ChangeRequirement] = Field(min_length=1)
    severity: Severity = Severity.ERROR


class ValidatorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    argv: list[str] = Field(min_length=1)
    cwd: str = "."
    timeout_seconds: int = Field(default=120, ge=1, le=1800)
    max_output_bytes: int = Field(default=1_048_576, ge=1024, le=10_485_760)


class ProjectProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    name: str
    artifact_groups: list[ArtifactGroup]
    rules: list[SyncRule]
    validators: list[ValidatorSpec] = Field(default_factory=list)


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
