from copy import deepcopy

import numpy as np
import pytest

from eval.prepare_v3 import KINDS, compile_drafts, screen


def draft():
    return {"status": "unsealed_draft_no_model_outputs_generated", "intents": [
        {"intent": "one", "cases": [{"kind": kind, "query": f"Question {i} about something distinct",
         "acceptable_actions": ["Help"], "critical_fail_if": ["Invents"]} for i, kind in enumerate(KINDS)]}]}


def test_compile_requires_complete_unique_coverage_and_checklists():
    source = draft()
    rows = compile_drafts([source], {"one": "TEST"})
    assert len(rows) == 4 and len({row["id"] for row in rows}) == 4
    with pytest.raises(ValueError, match="duplicate intent"):
        compile_drafts([source, source], {"one": "TEST"})
    with pytest.raises(ValueError, match="every expected intent"):
        compile_drafts([source], {"one": "TEST", "two": "TEST"})
    source["intents"][0]["cases"].pop()
    with pytest.raises(ValueError, match="each kind"):
        compile_drafts([source], {"one": "TEST"})
    source = draft()
    source["intents"][0]["cases"][0]["acceptable_actions"] = []
    with pytest.raises(ValueError, match="checklist"):
        compile_drafts([source], {"one": "TEST"})


def test_revisions_preserve_original_and_require_reason_and_same_kind():
    source = draft()
    original = deepcopy(source)
    case = dict(source["intents"][0]["cases"][0], query="Replacement with new scenario")
    changes = {"v3-final-one-01": {"reason": "Six-gram collision before inference", "case": case}}
    rows = compile_drafts([source], {"one": "TEST"}, changes)
    assert rows[0]["query"] == case["query"] and source == original
    changes["v3-final-one-01"]["case"]["kind"] = KINDS[1]
    with pytest.raises(ValueError, match="cannot change"):
        compile_drafts([source], {"one": "TEST"}, changes)


def test_screen_rejects_each_overlap_channel_and_invalid_vectors():
    source = [{"id": "training", "source": "train", "query": "one two three four five six seven"}]
    rows = [{"id": "final1", "query": "completely different wording"},
            {"id": "final2", "query": "zero one two three four five six"},
            {"id": "training", "query": "another distinct question"}]
    left = np.array([[1., 0.], [0., 1.], [0., 1.]])
    right = np.array([[1., 0.]])
    report = screen(rows, source, left, right)
    assert not report["pass"]
    assert report["results"][0]["max_cosine"] == 1
    assert report["results"][1]["shared_sixgrams"]
    assert report["results"][2]["duplicate_source_id"]
    assert not any(row["pass"] for row in report["results"])
    with pytest.raises(ValueError, match="unit-normalized"):
        screen(rows, source, left * .5, right)


def test_screen_passes_distinct_queries_and_reports_internal_similarity():
    report = screen([{"id": "a", "query": "refund clarification"},
                     {"id": "b", "query": "invoice clarification"}],
                    [{"id": "c", "source": "val", "query": "password problem"}],
                    np.array([[0., 1.], [0., 1.]]), np.array([[1., 0.]]))
    assert report["pass"]
    assert len(report["within_final_pairs_at_threshold"]) == 1
