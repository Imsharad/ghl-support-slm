import pytest

from eval.v3_metrics import summarize_pairs, validate_pairs


def fixtures():
    return [{"id": f"{i}-{j}", "intent": str(i),
             "base": {"pass": j < 2, "critical": False, "credential_violation": False},
             "tuned": {"pass": j < 3, "critical": False, "credential_violation": False},
             "preferred": "tuned"} for i in range(27) for j in range(4)]


def test_cluster_analysis_matches_known_paired_improvement():
    rows = fixtures()
    validate_pairs(rows, intents={str(i) for i in range(27)})
    result = summarize_pairs(rows)
    assert result["difference_percentage_points"] == 25
    assert result["primary_cluster_ci95_points"] == [25, 25]
    assert result["paired_task_outcomes"] == {"tuned_only_pass": 27, "base_only_pass": 0, "same_pass_result": 81}
    assert result["verdict"] == "positive"
    assert result == summarize_pairs(rows)


def test_zero_change_is_not_an_improvement_and_safety_can_block_success():
    rows = fixtures()
    for row in rows:
        row["tuned"]["pass"] = row["base"]["pass"]
    assert summarize_pairs(rows)["verdict"] == "not_demonstrated"
    rows = fixtures()
    rows[0]["tuned"]["pass"] = False
    rows[0]["tuned"]["credential_violation"] = True
    rows[0]["tuned"]["critical"] = True
    assert summarize_pairs(rows)["difference_percentage_points"] > 5
    assert summarize_pairs(rows)["verdict"] == "not_demonstrated"


def test_validation_rejects_partial_duplicate_and_inconsistent_scores():
    rows = fixtures()
    expected = {str(i) for i in range(27)}
    with pytest.raises(ValueError, match="quota"):
        validate_pairs(rows[:-1], intents=expected)
    with pytest.raises(ValueError, match="duplicate"):
        validate_pairs(rows + [rows[0]], intents=expected)
    rows[0]["tuned"]["critical"] = True
    with pytest.raises(ValueError, match="cannot pass"):
        validate_pairs(rows, intents=expected)
