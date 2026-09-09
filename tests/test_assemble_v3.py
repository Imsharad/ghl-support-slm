import json
from pathlib import Path

import pytest

from data.assemble_v3 import assemble, checked_augmentation, load_targets, unique_object
from train.repro import sha256_file


def test_duplicate_target_json_keys_are_rejected():
    with pytest.raises(ValueError, match="duplicate JSON"):
        json.loads('{"a":1,"a":2}', object_pairs_hook=unique_object)


def test_assembler_checks_ids_references_and_preserves_original():
    row = dict(id="a", group_id="g", intent="invoice", category="INVOICE",
               instruction="Find invoice 00108", response="original")
    class Collator:
        def encode(self, item): return {"input_ids": [1, 2, 3]}
    with pytest.raises(ValueError, match="reference"):
        assemble([row], {"a": "Ask support"}, Collator())
    with pytest.raises(ValueError, match="IDs"):
        assemble([row], {"b": "Ask support about 00108"}, Collator())
    result, stats = assemble([row], {"a": "Check invoice 00108 in your records."}, Collator())
    assert result[0]["original_response"] == "original"
    assert row["response"] == "original"
    assert result[0]["response"] != "original"
    assert stats["max_tokens"] == 3


def test_all_authored_target_ids_are_unique():
    root = Path(__file__).resolve().parents[1] / "data/v3/targets"
    train = load_targets(sorted(root.glob("train_part*.json")))
    val = load_targets([root / "val.json"])
    assert len(train) == 216 and len(val) == 54
    assert not train.keys() & val.keys()


def test_augmentation_requires_exact_input_and_full_holdout_audit(tmp_path):
    path = tmp_path / "aug.json"
    path.write_text(json.dumps({"rows": [{"id": "a", "group_id": "g"}]}))
    report = {"input_sha256": sha256_file(path), "pass": True, "threshold": .86,
              "against_sha256": {"v": "val-hash", "t": "test-hash"},
              "results": [{"id": "a", "pass": True, "max_cosine": .7, "shared_sixgrams": []}]}
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps(report))
    source = {"source_sha256": {"val": "val-hash", "test": "test-hash"}}
    assert checked_augmentation(path, audit, source)[0]["id"] == "a"
    report["against_sha256"].pop("t")
    audit.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="incomplete"):
        checked_augmentation(path, audit, source)
