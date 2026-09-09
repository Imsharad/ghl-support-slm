import pytest
from data.select_targets_v3 import select


def test_selection_is_deterministic_balanced_group_distinct_and_nonmutating():
    rows = [{"id": f"{intent}-{i}", "group_id": f"{intent}-{i//2}",
             "intent": intent, "instruction": f"Help with {intent}", "response": "original"}
            for intent in ("refund", "order") for i in range(8)]
    selected, excluded = select(rows, 3, 42)
    assert len(selected) == 6
    assert len({r["group_id"] for r in selected}) == 6
    assert select(rows[::-1], 3, 42) == (selected, excluded)
    assert all(r["response"] == "original" for r in rows)


def test_selection_rejects_placeholder_artifacts_and_insufficient_coverage():
    row = {"id": "a", "group_id": "a", "intent": "account",
           "instruction": "create my account type account"}
    with pytest.raises(ValueError, match="insufficient"):
        select([row], 1, 42)
