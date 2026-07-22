"""Git change set discovery and explicit path resolution."""

from pathlib import Path
import subprocess
from db_governance.errors import GovernanceError


def _run_git_nul(args: list[str], cwd: Path) -> list[str]:
    """Runs a git command expecting NUL-terminated output tokens.

    Args:
        args: Command argument list starting with 'git'.
        cwd: Working directory for git command.

    Returns:
        List of non-empty decoded string tokens.

    Raises:
        GovernanceError: If git command exits non-zero (DBG003).
    """
    try:
        proc = subprocess.run(
            args, cwd=cwd, capture_output=True, check=False, shell=False
        )
    except FileNotFoundError as exc:
        raise GovernanceError("[DBG003] 'git' executable not found in system PATH.", exit_code=2) from exc

    if proc.returncode != 0:
        err_msg = proc.stderr.decode("utf-8", errors="replace").strip()
        raise GovernanceError(f"[DBG003] Git command failed ({' '.join(args)}): {err_msg}", exit_code=2)

    tokens = [t.decode("utf-8", errors="replace") for t in proc.stdout.split(b"\x00") if t]
    return tokens


def _parse_name_status_tokens(tokens: list[str]) -> list[str]:
    """Parses NUL-terminated git diff name-status tokens into path strings."""
    paths: set[str] = set()
    i = 0
    n = len(tokens)
    while i < n:
        status = tokens[i]
        if status.startswith("R") or status.startswith("C"):
            # Rename or Copy: followed by old_path and new_path
            if i + 2 < n:
                paths.add(tokens[i + 1])
                paths.add(tokens[i + 2])
                i += 3
            else:
                break
        else:
            # Modified, Added, Deleted, etc.
            if i + 1 < n:
                paths.add(tokens[i + 1])
                i += 2
            else:
                break
    return list(paths)


def resolve_changed_files(
    project_root: Path,
    base: str | None = None,
    explicit: list[Path] | None = None,
) -> list[str]:
    """Resolves all changed relative paths via explicit argument or Git change set.

    Args:
        project_root: Path to project root.
        base: Optional Git commit/branch ref to compare against.
        explicit: Optional explicit list of changed file paths.

    Returns:
        Sorted list of project-relative POSIX path strings.

    Raises:
        GovernanceError: If arguments conflict or paths escape project root (DBG003).
    """
    resolved_root = project_root.resolve()

    if base is not None and explicit is not None and len(explicit) > 0:
        raise GovernanceError(
            "[DBG003] Cannot specify both --base and explicit changed files.", exit_code=2
        )

    if explicit is not None and len(explicit) > 0:
        rel_paths: set[str] = set()
        for exp in explicit:
            res_exp = exp.resolve()
            if not res_exp.is_relative_to(resolved_root):
                raise GovernanceError(
                    f"[DBG003] Explicit changed file '{exp}' resolves outside project root: {res_exp}",
                    exit_code=2,
                )
            rel_paths.add(res_exp.relative_to(resolved_root).as_posix())
        return sorted(rel_paths)

    # Git change set discovery
    all_changed: set[str] = set()

    # 1. Base diff (if specified)
    if base is not None:
        diff_base_tokens = _run_git_nul(["git", "diff", "-z", "--name-status", f"{base}...HEAD"], resolved_root)
        all_changed.update(_parse_name_status_tokens(diff_base_tokens))

    # 2. Unstaged diff
    unstaged_tokens = _run_git_nul(["git", "diff", "-z", "--name-status"], resolved_root)
    all_changed.update(_parse_name_status_tokens(unstaged_tokens))

    # 3. Staged diff
    staged_tokens = _run_git_nul(["git", "diff", "-z", "--name-status", "--cached"], resolved_root)
    all_changed.update(_parse_name_status_tokens(staged_tokens))

    # 4. Untracked files
    untracked = _run_git_nul(["git", "ls-files", "-z", "--others", "--exclude-standard"], resolved_root)
    all_changed.update(untracked)

    # Sanity check safety for all discovered paths
    safe_paths: set[str] = set()
    for rel in all_changed:
        full = (resolved_root / rel).resolve()
        # Path can be deleted file so check parent or is_relative_to
        try:
            if full.is_relative_to(resolved_root):
                safe_paths.add(Path(rel).as_posix())
        except ValueError:
            continue

    return sorted(safe_paths)
