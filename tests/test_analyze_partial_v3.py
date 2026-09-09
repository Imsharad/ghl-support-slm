from copy import deepcopy
from itertools import product

import pytest

from eval import analyze_partial_v3 as analysis
from eval.paired_v3 import build_sheet
from eval.v3_metrics import summarize_pairs


def make_pair(i, intent, base, tuned):
    return {"id": str(i), "intent": intent, "kind": "fixture", "preferred": "tie",
            "base": {"pass": base, "critical": False, "credential_violation": False},
            "tuned": {"pass": tuned, "critical": False, "credential_violation": False}}


def test_bounds_cover_all_possible_pass_assignments():
    observed = [make_pair(0, "one", False, True), make_pair(1, "one", True, True),
                make_pair(2, "two", True, False), make_pair(3, "two", False, False)]
    missing = [{"id": "4", "intent": "one", "kind": "fixture"},
               {"id": "5", "intent": "two", "kind": "fixture"}]
    result = analysis.sensitivity(observed, missing, n_boot=100)
    assert result["denominator"] == 6
    assert result["worst_case"]["difference_points"] == pytest.approx(-100/3)
    assert result["best_case"]["difference_points"] == pytest.approx(100/3)
    for states in product((False, True), repeat=4):
        full = observed + [make_pair(4, "one", *states[:2]), make_pair(5, "two", *states[2:])]
        stats = summarize_pairs(full, n_boot=100)
        assert result["worst_case"]["difference_points"] <= stats["difference_percentage_points"] <= result["best_case"]["difference_points"]
        for j, value in enumerate(stats["primary_cluster_ci95_points"]):
            assert result["worst_case"]["cluster_ci95_points"][j] <= value <= result["best_case"]["cluster_ci95_points"][j]
    assert "pass" not in missing[0]  # Missing grades were not mutated or filled.


def test_safety_failure_can_remain_irrecoverable():
    observed = [make_pair(i, "one", True, False) for i in range(3)]
    for r in observed:
        r["tuned"]["critical"] = True
    result = analysis.sensitivity(observed, [{"id": "3", "intent": "one", "kind": "fixture"}], n_boot=10)
    assert result["safety_gate_impossible_even_best_case"]
    assert result["full_critical_count_ranges"] == {"base": [0,1], "tuned": [3,4]}


def mapped_fixture():
    cases = [{"id": str(i), "query": f"Synthetic query {i}", "intent": "one", "kind": "fixture",
              "acceptable_actions": ["safe help"], "critical_fail_if": ["invented facts"]} for i in range(4)]
    raw = {m: [{"id": str(i), "answer": f"Synthetic {m} answer", "model": m,
                "backend": "ollama", "error": None} for i in range(4)] for m in ("base", "tuned")}
    sheet, key = build_sheet(cases, raw["base"], raw["tuned"], seed="abcd")
    for n, r in enumerate(sheet, 1):
        r.update(question_number=str(n), judge_source="human" if n < 4 else "missing")
        if n < 4:
            r.update(preferred="tie", notes="")
            for side in ("A", "B"):
                for field in ("pass", "critical", "credential_violation"):
                    r[f"{field}_{side}"] = "false"
    return sheet, key


def test_partial_unblinding_preserves_absent_notes_and_omission():
    sheet, key = mapped_fixture()
    observed, missing = analysis.map_partial(sheet, key, {4})
    assert len(observed) == 3 and len(missing) == 1
    assert all(r["notes_missing"] and r["notes"] == "" for r in observed)
    assert "base" not in missing[0] and "tuned" not in missing[0]
    changed = deepcopy(sheet)
    changed[0]["answer_A"] += "tampered"
    with pytest.raises(ValueError, match="Immutable"):
        analysis.map_partial(changed, key, {4})
    with pytest.raises(ValueError, match="Cannot discard"):
        analysis.map_partial(sheet, key, {1,4})


@pytest.mark.parametrize("missing,notes,skip", [([107,108], [], {107}), ([], [2], set())])
def test_incomplete_checks_happen_before_key_access(tmp_path, monkeypatch, missing, notes, skip):
    monkeypatch.setattr(analysis, "audit", lambda *args: {"missing_grade_questions": missing,
                        "missing_human_evidence_questions": notes})
    def forbidden(*args):
        pytest.fail("Must not access private key before completeness checks")
    monkeypatch.setattr(analysis, "verified_key", forbidden)
    with pytest.raises(ValueError):
        analysis.analyze(tmp_path, tmp_path, tmp_path, tmp_path / "out", skip)
    assert not (tmp_path / "out").exists()
