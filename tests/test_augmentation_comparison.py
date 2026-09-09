import json

import pytest

from data.check_augmentation_v3 import comparison_rows


def test_comparison_reads_queries_not_answers(tmp_path):
    path = tmp_path / "dev.jsonl"
    path.write_text(json.dumps({"id": "dev-a", "query": "Actual question",
                                "answer": "Do not use this", "response": "Nor this"}) + "\n")
    assert comparison_rows(path) == [{"id": "dev-a", "group_id": "dev-a",
                                      "instruction": "Actual question"}]


def test_comparison_preserves_source_group_and_instruction(tmp_path):
    path = tmp_path / "source.jsonl"
    path.write_text(json.dumps({"id": "a", "group_id": "family", "instruction": "source",
                                "query": "ignored alternate"}) + "\n")
    assert comparison_rows(path) == [{"id": "a", "group_id": "family", "instruction": "source"}]


@pytest.mark.parametrize("rows", [[], [{"id": "a", "answer": "No query"}],
    [{"id": "a", "query": "q"}, {"id": "a", "query": "different"}],
    [{"id": "", "query": "q"}], [{"id": "a", "query": " "}],
    [{"id": "a", "query": "q", "group_id": None}]])
def test_comparison_rejects_invalid_inputs(tmp_path, rows):
    path = tmp_path / "bad.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(ValueError):
        comparison_rows(path)
