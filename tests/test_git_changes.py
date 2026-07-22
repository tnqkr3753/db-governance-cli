"""Tests for Git change set resolution."""

from pathlib import Path
import subprocess
import pytest

from db_governance.errors import GovernanceError
from db_governance.git_changes import resolve_changed_files


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "git_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)

    # Initial commit
    (repo / "README.md").write_text("Hello")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo, check=True)
    return repo


def test_resolve_explicit_files(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    f1 = proj / "database" / "tables" / "USERS.md"
    f1.parent.mkdir(parents=True)
    f1.write_text("doc")

    res = resolve_changed_files(proj, base=None, explicit=[f1])
    assert res == ["database/tables/USERS.md"]


def test_resolve_explicit_file_escaping_rejected(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("outside")

    with pytest.raises(GovernanceError) as exc_info:
        resolve_changed_files(proj, base=None, explicit=[outside])
    assert exc_info.value.exit_code == 2
    assert "DBG003" in str(exc_info.value)


def test_resolve_both_base_and_explicit_rejected(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    f1 = proj / "file.txt"
    f1.write_text("a")
    with pytest.raises(GovernanceError) as exc_info:
        resolve_changed_files(proj, base="HEAD", explicit=[f1])
    assert exc_info.value.exit_code == 2


def test_resolve_git_working_tree_changes(temp_git_repo: Path):
    # Create staged file, unstaged file, and untracked file
    (temp_git_repo / "staged.txt").write_text("staged")
    subprocess.run(["git", "add", "staged.txt"], cwd=temp_git_repo, check=True)

    (temp_git_repo / "README.md").write_text("Modified")  # unstaged

    (temp_git_repo / "untracked.txt").write_text("untracked")

    changed = resolve_changed_files(temp_git_repo, base=None, explicit=None)
    assert sorted(changed) == ["README.md", "staged.txt", "untracked.txt"]
