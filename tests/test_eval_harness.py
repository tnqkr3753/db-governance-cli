"""Test harness for skill evaluations and trigger accuracy."""

import json
from pathlib import Path

from db_governance.config import load_profile
from db_governance.discovery import discover_artifacts
from db_governance.models import ChangeType
from db_governance.rules import evaluate_rules


def test_evals_json_schema_and_execution(tmp_path: Path):
    evals_path = Path("skills/database-governance/evals/evals.json").resolve()
    assert evals_path.exists()

    with open(evals_path, "r", encoding="utf-8") as f:
        evals = json.load(f)

    assert len(evals) == 3

    for item in evals:
        assert "id" in item
        assert "name" in item
        assert "prompt" in item
        assert "expected_output" in item
        assert "files" in item

        # Test building and executing fixture workspace from eval
        eval_dir = tmp_path / f"eval_{item['id']}"
        eval_dir.mkdir()

        for rel_file, content in item["files"].items():
            full_path = eval_dir / rel_file
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        prof_path, profile, prof_hash = load_profile(eval_dir, None)
        artifacts = discover_artifacts(eval_dir, profile)
        assert len(artifacts) > 0

        # Execute check logic depending on eval scenario
        if item["id"] == 1:
            changed = ["데이터베이스/MGT/TB_MGT_USERS.md", "데이터베이스/DDL/V1__tb_mgt_users.sql"]
            findings = evaluate_rules(profile, changed, ChangeType.SEMANTIC)
            assert len(findings) == 1
            assert findings[0].code == "DBG201"
            assert "change history" in findings[0].message
        elif item["id"] == 3:
            changed = ["db/docs/orders.md"]
            findings = evaluate_rules(profile, changed, ChangeType.FORMATTING)
            assert len(findings) == 0


def test_trigger_evals_json_schema():
    triggers_path = Path("skills/database-governance/evals/trigger-evals.json").resolve()
    assert triggers_path.exists()

    with open(triggers_path, "r", encoding="utf-8") as f:
        triggers = json.load(f)

    assert len(triggers) == 20

    positives = [t for t in triggers if t["should_trigger"] is True]
    negatives = [t for t in triggers if t["should_trigger"] is False]

    assert len(positives) == 10
    assert len(negatives) == 10

    for item in triggers:
        assert "id" in item
        assert "query" in item
        assert "should_trigger" in item
        assert "reason" in item
