import csv
import io

import pytest

from eval.audit_mixed_v3 import combine
from eval.paired_v3 import COLUMNS, IMMUTABLE
from eval.terra_remaining_v3 import FIELDS


def test_provenance_missing_notes_and_human_precedence():
    source = [{k: f"fixture-{i}-{k}" if k in IMMUTABLE else "" for k in COLUMNS} for i in range(3)]
    human = [dict(r) for r in source]
    human[0].update({k: "false" for k in FIELDS if k not in ("preferred", "notes")})
    human[0]["preferred"] = "tie"
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(human)
    def g(item_id):
        return {"item_id": item_id, "A": {"pass": True, "critical": False,
            "credential_violation": False, "evidence": "Synthetic explanation A"},
            "B": {"pass": False, "critical": False, "credential_violation": False,
                  "evidence": "Synthetic explanation B"}, "preferred": "A",
            "preference_evidence": "Synthetic preference", "needs_review": False, "uncertainty": ""}
    grades = {r["item_id"]: g(r["item_id"]) for r in source[:2]}
    data = {"rows": source, "pass_criteria": [], "critical_failure": []}
    rows, summary = combine(data, out.getvalue().encode(), grades)
    assert all(rows[0][k] == human[0][k] for k in FIELDS)
    assert rows[0]["notes"] == ""  # Never invent evidence to make a row complete.
    assert rows[1]["judge_source"] == "terra_human_calibrated_unreviewed"
    assert rows[2]["judge_source"] == "missing"
    assert summary["missing_grade_questions"] == [3]
    assert summary["missing_human_evidence_questions"] == [1]
    assert summary["human_precedence_overlap_questions"] == [1]
    assert not summary["models_unblinded"]
    assert not summary["primary_all_human_evaluation_complete"]
    grades[source[1]["item_id"]]["A"]["critical"] = True
    with pytest.raises(ValueError):
        combine(data, out.getvalue().encode(), grades)
