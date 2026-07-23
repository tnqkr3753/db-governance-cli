"""DDL Migration version series parser and scaffold creator (dbg ddl-manage)."""

from datetime import datetime, timezone
import re
from pathlib import Path

from db_governance.errors import GovernanceError
from db_governance.models import ProjectProfile


def get_next_migration_version(
    project_root: Path,
    profile: ProjectProfile,
    series_name: str = "main",
) -> tuple[str, Path]:
    """Computes next migration version string (e.g. 'V1_28') and target directory path."""
    resolved_root = project_root.resolve()

    target_series = next((s for s in profile.migration_series if s.name.lower() == series_name.lower()), None)
    if not target_series:
        if profile.migration_series:
            available = ", ".join(s.name for s in profile.migration_series)
            raise GovernanceError(
                f"[DBG003] Migration series '{series_name}' not defined in profile. Available series: {available}",
                exit_code=2,
            )
        mig_dir = resolved_root / "database" / "migrations"
        for group in profile.artifact_groups:
            if group.role.value == "migration" and group.patterns:
                pat = group.patterns[0]
                pat_dir = Path(pat.split("*")[0]).parent if "*" in pat else Path(pat).parent
                mig_dir = (resolved_root / pat_dir).resolve()
                break
    else:
        mig_dir = (resolved_root / target_series.directory).resolve()

    mig_files: list[Path] = list(mig_dir.glob("*.sql")) if mig_dir.exists() else []

    max_major = 1
    max_minor = 0
    has_minor_format = False

    version_pattern = re.compile(r"^V(\d+)(?:_(\d+))?__", re.IGNORECASE)

    for f in mig_files:
        m = version_pattern.match(f.name)
        if m:
            major = int(m.group(1))
            minor = int(m.group(2)) if m.group(2) is not None else 0
            if m.group(2) is not None:
                has_minor_format = True
            if (major, minor) > (max_major, max_minor):
                max_major, max_minor = major, minor

    if has_minor_format:
        next_minor = max_minor + 1
        next_ver_str = f"V{max_major}_{next_minor:02d}"
    else:
        next_major = max_major + 1 if mig_files else 1
        next_ver_str = f"V{next_major}"

    mig_dir.mkdir(parents=True, exist_ok=True)
    return next_ver_str, mig_dir


def create_migration_file(
    project_root: Path,
    profile: ProjectProfile,
    slug: str,
    series_name: str = "main",
) -> Path:
    """Creates a new comment-headered empty migration SQL file."""
    ver_str, mig_dir = get_next_migration_version(project_root, profile, series_name=series_name)
    file_name = f"{ver_str}__{slug.lower()}.sql"
    target_file = mig_dir / file_name

    if target_file.exists():
        raise GovernanceError(
            f"[DBG401] Target migration file already exists: {target_file.relative_to(project_root.resolve())}",
            exit_code=2,
        )

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    header_content = (
        f"-- Migration: {ver_str}__{slug}\n"
        f"-- Migration Series: {series_name}\n"
        f"-- Version: {ver_str}\n"
        f"-- Created: {now_utc}\n"
        f"-- Slug: {slug}\n"
        "-- Note: Design DDL, data backfill, and transactional validation plans using the 'database-migration-design' skill.\n\n"
    )

    target_file.write_text(header_content, encoding="utf-8")
    return target_file
