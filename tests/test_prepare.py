"""Cleaning, grouping, and freeze checks for data/prepare.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

import prepare  # noqa: E402

CLEANING = prepare.load_cleaning()
SPLITS_PATH = ROOT / "data" / "splits.json"
PROCESSED_DIR = ROOT / "data" / "processed"


def test_rejected_rows_carry_a_rule_id() -> None:
    cases = [
        (
            "I want a refund",
            "I have refunded the payment to your card.",
            "reject_completed_action",
        ),
        (
            "unlock my account",
            "Your account is now unlocked. You can sign in.",
            "reject_completed_action",
        ),
        (
            "when do I get my money back",
            "Refunds arrive within 24 hours of approval.",
            "reject_invented_timeline",
        ),
        (
            "I cannot sign in",
            "Please send me your password so I can check the account.",
            "reject_request_credentials",
        ),
        (
            "call support",
            "Reach us at {{Customer Support Phone Number}} during {{Customer Support Hours}}.",
            "reject_placeholder_no_neutral_wording",
        ),
    ]
    for instruction, response, expected in cases:
        _inst, _resp, _applied, reject_id = prepare.apply_cleaning(
            instruction, response, CLEANING
        )
        assert reject_id is not None, (instruction, response)
        assert reject_id == expected
        assert isinstance(reject_id, str) and reject_id


def test_timeline_allowed_when_instruction_supplies_it() -> None:
    instruction = "You said delivery takes 2-3 business days. Is that right?"
    response = "Delivery is typically 2-3 business days once the order ships."
    inst, resp, applied, reject_id = prepare.apply_cleaning(instruction, response, CLEANING)
    assert reject_id is None
    assert inst
    assert resp


def test_placeholder_tokens_absent_from_outputs() -> None:
    instruction = "question about cancelling order {{Order Number}}"
    response = (
        "Please open Orders and find your order {{Order Number}}. "
        "Use Cancel if you still want to stop it."
    )
    inst, resp, applied, reject_id = prepare.apply_cleaning(instruction, response, CLEANING)
    assert reject_id is None
    assert "{{" not in inst
    assert "{{" not in resp
    assert "your order number" in inst
    assert "placeholder_order_number" in applied
    assert "replace_placeholders" in applied

    if (PROCESSED_DIR / "train.jsonl").exists():
        for name in prepare.SPLIT_NAMES:
            for row in prepare.load_jsonl(PROCESSED_DIR / f"{name}.jsonl"):
                assert "{{" not in row["instruction"]
                assert "{{" not in row["response"]


def test_group_never_straddles_splits() -> None:
    records = []
    intents = ["cancel_order", "get_refund"]
    for intent in intents:
        for g in range(1, 6):
            for r in range(3):
                records.append(
                    {
                        "id": f"{intent}-{g}-{r}",
                        "intent": intent,
                        "group_id": f"g-{intent}-{g:02d}",
                    }
                )
    splits, coverage = prepare.split_groups(records, seed=42)
    owners: dict[str, set[str]] = {}
    for name, gids in splits.items():
        for gid in gids:
            owners.setdefault(gid, set()).add(name)
    assert all(len(names) == 1 for names in owners.values())
    assert all(not item["missing_splits"] for item in coverage)

    assigned = {gid: name for name, gids in splits.items() for gid in gids}
    split_rows = {name: [] for name in prepare.SPLIT_NAMES}
    for rec in records:
        split_rows[assigned[rec["group_id"]]].append(rec)
    assert prepare.group_straddles(split_rows) == []


def test_single_group_intent_is_kept_and_reported() -> None:
    records = [
        {"id": "a-0", "intent": "tiny", "group_id": "g-1"},
        {"id": "a-1", "intent": "tiny", "group_id": "g-1"},
        {"id": "b-0", "intent": "wide", "group_id": "g-2"},
        {"id": "b-1", "intent": "wide", "group_id": "g-3"},
        {"id": "b-2", "intent": "wide", "group_id": "g-4"},
    ]
    splits, coverage = prepare.split_groups(records, seed=42)
    tiny = next(item for item in coverage if item["intent"] == "tiny")
    assert tiny["missing_splits"]
    assert splits["train"] or splits["val"] or splits["test"]
    owners: dict[str, set[str]] = {}
    for name, gids in splits.items():
        for gid in gids:
            owners.setdefault(gid, set()).add(name)
    assert owners["g-1"] == {"train"}


def test_cap_train_keeps_whole_groups_and_balances_intents() -> None:
    rows = []
    for intent, n_groups in (("a", 4), ("b", 4)):
        for g in range(n_groups):
            gid = f"{intent}-{g}"
            for r in range(3):
                rows.append(
                    {
                        "id": f"{gid}-{r}",
                        "intent": intent,
                        "group_id": gid,
                    }
                )
    capped = prepare.cap_train_rows(rows, cap=12, seed=42)
    assert len(capped) == 12
    by_intent = {}
    by_group: dict[str, int] = {}
    for row in capped:
        by_intent[row["intent"]] = by_intent.get(row["intent"], 0) + 1
        by_group[row["group_id"]] = by_group.get(row["group_id"], 0) + 1
    assert by_intent["a"] == 6
    assert by_intent["b"] == 6
    assert all(count == 3 for count in by_group.values())


@pytest.mark.skipif(not SPLITS_PATH.exists(), reason="run data/prepare.py first")
def test_frozen_splits_have_no_group_leakage() -> None:
    splits = json.loads(SPLITS_PATH.read_text(encoding="utf-8"))
    split_rows = {
        name: prepare.load_jsonl(PROCESSED_DIR / f"{name}.jsonl")
        for name in prepare.SPLIT_NAMES
    }
    assert prepare.group_straddles(split_rows) == []
    cross = prepare.intersections(split_rows)
    assert cross["group_id_empty"]
    assert cross["normalized_instruction_empty"]
    for name in prepare.SPLIT_NAMES:
        digest = prepare.sha256_file(PROCESSED_DIR / f"{name}.jsonl")
        assert digest == splits[name]["sha256"]
        assert len(split_rows[name]) == splits[name]["rows"]
        assert {row["group_id"] for row in split_rows[name]} == set(splits[name]["groups"])
        for row in split_rows[name]:
            assert "{{" not in row["instruction"]
            assert "{{" not in row["response"]
            assert row["n_tokens"] <= prepare.MAX_LENGTH
