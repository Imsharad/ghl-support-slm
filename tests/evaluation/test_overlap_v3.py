import numpy as np
import pytest
from data.audit_overlap_v3 import audit, grams, nearest, normalize
from data.prepare_source_v3 import filter_sources, verify_audit


def test_normalization_and_sixgrams_are_query_based():
    assert normalize("  DON’T  change {{Order Number}}! ") == "don't change placeholder"
    assert grams("one two three four five six seven") == {"one two three four five six", "two three four five six seven"}


def test_nearest_checks_across_all_rows_and_rejects_empty():
    left = np.array([[1., 0.], [0., 1.]])
    assert nearest(left, left[::-1], chunk=1).tolist() == [1., 1.]
    with pytest.raises(ValueError): nearest(left, np.empty((0, 2)))


def test_collision_removes_entire_train_group_in_proposal_only():
    def row(i, group, text):
        return dict(id=i, group_id=group, instruction=text, intent="refund")
    rows = {"train": [row("a", "g1", "same request"), row("b", "g1", "different request"), row("c", "g2", "unrelated")],
            "val": [row("v", "g3", "same request")], "test": [row("t", "g4", "test request")]}
    emb = {"train": np.array([[1.,0.,0.], [0.,1.,0.], [-1.,0.,0.]]),
           "val": np.array([[1.,0.,0.]]), "test": np.array([[0.,0.,1.]])}
    result = audit(rows, emb, .86)
    proposal = result["hypothetical_train_group_purge"]
    assert proposal["excluded_groups"] == ["g1"]
    assert proposal["retained_rows"] == 1
    assert proposal["not_applied"]
    assert len(rows["train"]) == 3


def test_filter_removes_synthetics_and_entire_colliding_validation_group():
    def row(i, group, text):
        return dict(id=i, group_id=group, instruction=text, intent="refund", response="unchanged")
    rows = {
        "train": [row("bitext-a", "a", "train"), row("adm-b", "b", "synthetic")],
        "val": [row("bitext-c", "c", "close"), row("bitext-d", "c", "different"),
                row("bitext-e", "e", "survivor")],
        "test": [row("bitext-f", "f", "test")]}
    embeddings = {"train": np.array([[1.,0.,0.], [1.,0.,0.]]),
                  "val": np.array([[0.,0.,1.], [1.,0.,0.], [0.,1.,0.]]),
                  "test": np.array([[0.,0.,1.]])}
    pools, vectors, removals = filter_sources(rows, embeddings, set(), .86)
    assert [r["id"] for r in pools["train"]] == ["bitext-a"]
    assert [r["id"] for r in pools["val"]] == ["bitext-e"]
    assert pools["train"][0]["response"] == "unchanged"
    assert removals["val"]["excluded_groups"] == ["c"]
    verify_audit(audit(pools, vectors, .86))
    with pytest.raises(ValueError, match="semantic screening"):
        verify_audit(audit(rows, embeddings, .86))
