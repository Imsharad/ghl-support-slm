from copy import deepcopy
import hashlib

import pytest

from eval.paired_v3 import build_sheet, sheet_text, unblind, verify_manifest
from eval.prepare_v3 import KINDS


def fixture():
    cases = [{"id": str(i), "query": f"Question {i}", "acceptable_actions": ["Help"],
              "critical_fail_if": ["Invents"], "intent": "test", "kind": KINDS[i]} for i in range(4)]
    raw = {m: [{"id": str(i), "model": m, "backend": "ollama", "answer": f"{m} reply {i}", "error": None}
               for i in range(4)] for m in ("base", "tuned")}
    return cases, raw


def scored_sheet(raw=None):
    cases, defaults = fixture()
    raw = raw or defaults
    sheet, key = build_sheet(cases, raw["base"], raw["tuned"], seed="abcd")
    for row in sheet:
        for side in ("A", "B"):
            row[f"pass_{side}"] = row[f"pass_{side}"] or "true"
            row[f"critical_{side}"] = row[f"critical_{side}"] or "false"
            row[f"credential_violation_{side}"] = row[f"credential_violation_{side}"] or "false"
        row.update(preferred="tie", notes="Synthetic test fixture, not human evidence")
    return sheet, key


def test_blinding_replays_and_unblinds_without_losing_pairs():
    cases, raw = fixture()
    first = build_sheet(cases, raw["base"], raw["tuned"], seed="abcd")
    assert first == build_sheet(cases, raw["base"], raw["tuned"], seed="abcd")
    sheet, key = scored_sheet()
    result = unblind(sheet, key)
    assert len(result) == 4 and all(r["base"]["pass"] and r["tuned"]["pass"] for r in result)
    assert all("model" not in key for row in first[0] for key in row)


def test_generation_errors_are_retained_as_task_failures():
    _, raw = fixture()
    raw["tuned"][0].update(answer="", error="timeout")
    sheet, key = scored_sheet(raw)
    result = unblind(sheet, key)
    assert result[0]["tuned"]["generation_failure"] and not result[0]["tuned"]["pass"]
    target = next(row for row in sheet if row["item_id"] == "0")
    side = next(s for s, model in key["items"]["0"]["models"].items() if model == "tuned")
    target[f"pass_{side}"] = "true"
    with pytest.raises(ValueError, match="generation failure"):
        unblind(sheet, key)


def test_unblind_rejects_partial_changed_blank_and_contradictory_scores():
    sheet, key = scored_sheet()
    with pytest.raises(ValueError, match="every key ID"):
        unblind(sheet[:-1], key)
    changed = deepcopy(sheet)
    changed[0]["answer_A"] += " changed"
    with pytest.raises(ValueError, match="immutable"):
        unblind(changed, key)
    changed = deepcopy(sheet)
    changed[0]["pass_A"] = ""
    with pytest.raises(ValueError, match="explicitly"):
        unblind(changed, key)
    changed = deepcopy(sheet)
    changed[0]["critical_A"] = "true"
    with pytest.raises(ValueError, match="cannot pass"):
        unblind(changed, key)


def test_manifest_requires_same_prompt_decoding_and_exact_artifact():
    shared = {"backend": "ollama", "decoding": {"seed": 42}, "prompt_sha256": hashlib.sha256(b"prompt").hexdigest(),
              "runner_sha256": "runner", "render_sha256": "render"}
    seal = {"challenge_sha256": "cases", "models": {"base": {"tag": "base", "digest": "digest"}}, "inference": shared}
    manifest = {**shared, "schema": 1, "model": "base", "split_sha256": "cases",
                "identity": seal["models"]["base"], "system_prompt": "prompt"}
    verify_manifest(manifest, seal, "base")
    manifest["decoding"] = {"seed": 43}
    with pytest.raises(ValueError, match="decoding"):
        verify_manifest(manifest, seal, "base")


def test_formula_text_is_inert_in_spreadsheet_exports():
    assert sheet_text("=SUM(1,2)") == "'=SUM(1,2)"
    assert sheet_text("  +1") == "'  +1"
    assert sheet_text("ordinary answer") == "ordinary answer"
