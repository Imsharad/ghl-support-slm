import csv
import io
import json

import pytest

from eval.terra_remaining_v3 import prepare, FIELDS
from eval.paired_v3 import COLUMNS, IMMUTABLE
from eval import terra_judge_v3 as judge


def fixture():
    rows = [{k: (f"synthetic-{i}-{k}" if k in IMMUTABLE else "") for k in COLUMNS} for i in range(3)]
    for k in FIELDS:
        rows[0][k] = "false"
    rows[0].update(preferred="tie", notes="Synthetic human explanation")
    rows[1]["pass_A"] = "false"  # Partial row must also be preserved.
    data = {"source_sha256": "fixture", "rows": [{**r, **{k: "" for k in FIELDS}} for r in rows],
            "pass_criteria": ["Be useful"], "critical_failure": ["No invented status"]}
    return rows, data


def encode(rows):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def test_only_untouched_rows_and_complete_calibration(tmp_path):
    rows, data = fixture()
    selected, fixed, provenance = prepare(encode(rows), data)
    assert [r["item_id"] for r in selected["rows"]] == [rows[2]["item_id"]]
    assert provenance["human_complete_ids"] == [rows[0]["item_id"]]
    assert provenance["human_partial_ids"] == [rows[1]["item_id"]]
    assert rows[0]["notes"] in fixed
    assert rows[1]["item_id"] not in fixed
    assert rows[2]["item_id"] not in fixed
    calls = []
    def transport(request, key):
        calls.append(request)
        raise RuntimeError("Synthetic offline failure")
    with pytest.raises(ValueError, match="Stopped"):
        judge.run(selected, tmp_path, limit=1, subscription=True, transport=transport,
                  fixed_instructions=fixed, provenance=provenance)
    assert calls[0]["instructions"] == fixed
    assert json.loads(calls[0]["input"][0]["content"])["item_id"] == rows[2]["item_id"]
    assert json.loads((tmp_path / "manifest.json").read_text())["binding"]["provenance"] == provenance


@pytest.mark.parametrize("change", [
    lambda rows: rows[0].update(answer_A="tampered"),
    lambda rows: rows[0].update(pass_A="true", critical_A="true"),
    lambda rows: rows[0].update(credential_violation_B="true", critical_B="false"),
    lambda rows: rows.append(rows[0]),
    lambda rows: rows[0].update(preferred="base"),
])
def test_invalid_progress_rejected(change):
    rows, data = fixture()
    change(rows)
    with pytest.raises(ValueError):
        prepare(encode(rows), data)


def test_absent_notes_do_not_invent_human_evidence():
    rows, data = fixture()
    rows[0]["notes"] = ""
    selected, fixed, provenance = prepare(encode(rows), data)
    assert provenance["human_complete_ids"] == []
    assert provenance["human_calibration_ids"] == [rows[0]["item_id"]]
    assert rows[0]["item_id"] in provenance["human_missing_notes_ids"]
    assert len(selected["rows"]) == 1
    assert '"notes":""' in fixed
    assert "do not invent one" in fixed
