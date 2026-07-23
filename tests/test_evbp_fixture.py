"""EVBP Korean markdown table spec & version series compatibility fixture tests."""

from pathlib import Path
from db_governance.ddl_manage import get_next_migration_version
from db_governance.render import parse_markdown_table_spec


def test_evbp_korean_markdown_table_parser():
    md_content = """# EVBP_MGT.POR_COMMON_CODE

## 테이블 개요

| 항목 | 값 |
|---|---|
| 테이블명 | `por_common_code` |
| 한글명 | 공통코드 |
| 설명 | 공통 코드 |

## 컬럼 명세

| NO | 컬럼명 | 컬럼한글명 | 데이터 타입 | Null | Default | PK | 개인정보 | 암호화 | 표준화 | 설명 | 비고 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `type` | 코드타입 | VARCHAR(30) | | | Y | N | N | N | | |
| 2 | `code` | 코드 | VARCHAR(30) | | | Y | N | N | N | | |
| 3 | `name` | 이름 | VARCHAR(30) | | | | N | N | N | | |
| 4 | `description` | 설명 | VARCHAR(100) | | | | N | N | N | | |
| 5 | `order` | 순서 | INTEGER | | | | N | N | N | | |
"""

    spec = parse_markdown_table_spec(md_content, "POR_COMMON_CODE")
    assert spec.name == "POR_COMMON_CODE"
    assert len(spec.columns) == 5

    cols = {c.name: c for c in spec.columns}
    assert "TYPE" in cols
    assert cols["TYPE"].data_type == "VARCHAR(30)"
    assert cols["TYPE"].is_pk is True

    assert "CODE" in cols
    assert cols["CODE"].data_type == "VARCHAR(30)"
    assert cols["CODE"].is_pk is True

    assert "NAME" in cols
    assert cols["NAME"].data_type == "VARCHAR(30)"
    assert cols["NAME"].is_pk is False


def test_evbp_version_series_resolution(tmp_path: Path):
    from db_governance.config import load_profile

    proj = tmp_path / "evbp"
    (proj / "데이터베이스" / "DDL").mkdir(parents=True)
    (proj / "데이터베이스" / "STG" / "DDL").mkdir(parents=True)

    (proj / "데이터베이스" / "DDL" / "V1_27__last_main.sql").write_text("SELECT 1;\n")
    (proj / "데이터베이스" / "STG" / "DDL" / "V1_03__last_stg.sql").write_text("SELECT 1;\n")

    (proj / ".db-governance.toml").write_text("""version = 1
name = "evbp"
artifact_groups = []
rules = []
[[migration_series]]
name = "main"
directory = "데이터베이스/DDL"
file_pattern = "V1_{number}__{slug}.sql"
[[migration_series]]
name = "stg"
directory = "데이터베이스/STG/DDL"
file_pattern = "V1_{number}__{slug}.sql"
""")

    _, prof, _ = load_profile(proj)

    main_ver, main_dir = get_next_migration_version(proj, prof, series_name="main")
    assert main_ver == "V1_28"
    assert main_dir.relative_to(proj).as_posix() == "데이터베이스/DDL"

    stg_ver, stg_dir = get_next_migration_version(proj, prof, series_name="stg")
    assert stg_ver == "V1_04"
    assert stg_dir.relative_to(proj).as_posix() == "데이터베이스/STG/DDL"
