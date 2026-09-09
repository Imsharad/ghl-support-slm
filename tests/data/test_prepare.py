"""Cleaning, grouping, and freeze checks for data/prepare.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
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
    assert inst == "question about cancelling my order"
    assert "your order" in resp
    assert "your your" not in resp
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


def test_id_placeholder_four_frames_both_voices() -> None:
    frames = [
        ("cancel order number {{Order Number}}", "number", "order number"),
        ("cancel order {{Order Number}}", "noun", "order"),
        ("cancel the {{Order Number}}", "the", "order number"),
        ("cancel {{Order Number}}", "standalone", "order number"),
    ]
    for raw, frame, noun in frames:
        counts = prepare.empty_frame_counts()
        inst, resp, _applied, reject_id = prepare.apply_cleaning(
            raw, raw, CLEANING, frame_counts=counts
        )
        assert reject_id is None
        assert inst == f"cancel my {noun}"
        assert resp == f"cancel your {noun}"
        assert counts["instruction"][frame] == 1
        assert counts["response"][frame] == 1
        assert "{{" not in inst
        assert "{{" not in resp

    typo_inst, typo_resp, _, reject_id = prepare.apply_cleaning(
        "cancel oorder {{Order Number}}",
        "cancel oorder {{Order Number}}",
        CLEANING,
    )
    assert reject_id is None
    assert typo_inst == "cancel oorder my order number"
    assert typo_resp == "cancel oorder your order number"

    counts = prepare.empty_frame_counts()
    inst, resp, _, reject_id = prepare.apply_cleaning(
        "cancel with the number {{Order Number}}",
        "cancel with the number {{Order Number}}",
        CLEANING,
        frame_counts=counts,
    )
    assert reject_id is None
    assert inst == "cancel with my order number"
    assert resp == "cancel with your order number"
    assert counts["instruction"]["number"] == 1
    assert counts["response"]["number"] == 1

    counts = prepare.empty_frame_counts()
    inst, resp, _, reject_id = prepare.apply_cleaning(
        "cancel with number {{Order Number}}",
        "cancel with number {{Order Number}}",
        CLEANING,
        frame_counts=counts,
    )
    assert reject_id is None
    assert inst == "cancel with my order number"
    assert resp == "cancel with your order number"
    assert counts["instruction"]["number"] == 1
    assert counts["response"]["number"] == 1

    counts = prepare.empty_frame_counts()
    inst, resp, _, reject_id = prepare.apply_cleaning(
        "remove an item from purchase {{Order Number}}",
        "remove a product from purchase order number {{Order Number}}",
        CLEANING,
        frame_counts=counts,
    )
    assert reject_id is None
    assert inst == "remove an item from my purchase"
    assert resp == "remove a product from your purchase"
    assert counts["instruction"]["noun"] == 1
    assert counts["response"]["noun"] == 1

    inst, resp, _, reject_id = prepare.apply_cleaning(
        "paid {{Currency Symbol}}{{Refund Amount}}",
        "the {{Currency Symbol}}{{Refund Amount}} compensation",
        CLEANING,
    )
    assert reject_id is None
    assert "{{" not in inst and "{{" not in resp
    assert inst == "paid my refund amount"
    assert resp == "your refund amount compensation"
    assert "the your" not in resp


def test_processed_instructions_have_no_assistant_voice_or_double_article() -> None:
    import re

    bad_voice = re.compile(
        r"\b(order|purchase|number)\s+your order number", re.IGNORECASE
    )
    fable_leftover = re.compile(
        r"\b(order|purchase|number)\s+your order number|\bthe (my|your)\b"
    )
    cases = [
        "question about cancelling order {{Order Number}}",
        "question about canceling purchase {{Order Number}}",
        "I can't afford purchase {{Order Number}}",
        "the {{Order Number}} is late",
        "the order number {{Order Number}}",
        "i have a question about cancelling oorder {{Order Number}}",
    ]
    for instruction in cases:
        inst, resp, _, reject_id = prepare.apply_cleaning(
            instruction, "Find order {{Order Number}}.", CLEANING
        )
        assert reject_id is None
        assert bad_voice.search(inst) is None
        assert fable_leftover.search(inst) is None
        assert fable_leftover.search(resp) is None
        assert "your order number" not in inst.lower()

    if (PROCESSED_DIR / "train.jsonl").exists():
        for name in prepare.SPLIT_NAMES:
            for row in prepare.load_jsonl(PROCESSED_DIR / f"{name}.jsonl"):
                inst = row["instruction"]
                blob = inst + "\n" + row["response"]
                assert bad_voice.search(inst) is None, row["id"]
                assert fable_leftover.search(blob) is None, row["id"]


@pytest.mark.skipif(
    not SPLITS_PATH.exists() or not (PROCESSED_DIR / "train.jsonl").exists(),
    reason="run data/prepare.py first",
)
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


# --- v2: substitute instead of reject (V2-B1) --------------------------------


def test_default_mode_split_hashes_match_the_seal() -> None:
    """The regression guard for v1: prepare's default output is the sealed evidence."""
    seal = json.loads((ROOT / "eval" / "SEAL.json").read_text(encoding="utf-8"))
    splits = json.loads(SPLITS_PATH.read_text(encoding="utf-8"))
    expected = seal["split_sha256"]
    for name in prepare.SPLIT_NAMES:
        assert splits[name]["sha256"] == expected[name], name
    if (PROCESSED_DIR / "train.jsonl").exists():
        for name in prepare.SPLIT_NAMES:
            digest = prepare.sha256_file(PROCESSED_DIR / f"{name}.jsonl")
            assert digest == expected[name], name


def test_substitute_mode_is_off_by_default() -> None:
    """A row that v1 rejects still rejects when the flag is absent."""
    response = "We are open during {{Customer Support Hours}}."
    _i, _r, _a, reject_id = prepare.apply_cleaning("when are you open", response, CLEANING)
    assert reject_id == "reject_placeholder_no_neutral_wording"


def test_substitute_mode_recovers_the_row() -> None:
    counts: dict[str, int] = {}
    from collections import defaultdict

    counts = defaultdict(int)
    inst, resp, applied, reject_id = prepare.apply_cleaning(
        "when are you open",
        "We are open during {{Customer Support Hours}}.",
        CLEANING,
        substitute=True,
        substitution_counts=counts,
    )
    assert reject_id is None
    assert resp == "We are open during the hours shown on our contact page."
    assert "substitute_customer_support_hours" in applied
    assert counts["Customer Support Hours"] == 1
    assert "{{" not in inst + resp


def test_substitute_phrases_assert_no_fact() -> None:
    """No number, duration, price, URL, email or policy claim in any phrase."""
    block = json.loads(
        (ROOT / "configs" / "data" / "cleaning.json").read_text(encoding="utf-8")
    )
    entries = block["substitutions"]["entries"]
    assert entries
    for entry in entries:
        prepare.check_substitution_phrase(entry["placeholder"], entry["phrase"])
    with pytest.raises(ValueError):
        prepare.check_substitution_phrase("Delivery Time", "3 to 5 business days")
    with pytest.raises(ValueError):
        prepare.check_substitution_phrase("Website URL", "https://example.com")


def test_substitute_mode_leaves_no_double_determiner() -> None:
    cases = [
        ("contact us during our {{Customer Support Hours}}.",
         "contact us during the hours shown on our contact page."),
        ("the Live Chat feature on our {{Website URL}}.",
         "the Live Chat feature on our website."),
        ("reach us on our website at {{Website URL}}.",
         "reach us on our website."),
        ("Log in to your {{Online Company Portal Info}} using your credentials.",
         "Log in to your online portal using your credentials."),
        ("Collect items from one of our {{Store Location}}.",
         "Collect items from one of our stores."),
        ('Head over to the "{{Login Page URL}}" of our platform.',
         'Head over to the "login page" of our platform.'),
        ("{{Website URL}} is where you start.",
         "Our website is where you start."),
    ]
    for response, expected in cases:
        _i, resp, _a, reject_id = prepare.apply_cleaning(
            "hello", response, CLEANING, substitute=True
        )
        assert reject_id is None, response
        assert resp == expected, (response, resp)


def test_substitute_mode_still_rejects_what_has_no_neutral_phrase() -> None:
    for response in (
        "Delivery takes {{Standard Delivery Time}}.",
        "See our {{Cancellation Policy}}.",
        "Try {{Feature 1}}.",
    ):
        _i, _r, _a, reject_id = prepare.apply_cleaning(
            "hello", response, CLEANING, substitute=True
        )
        assert reject_id == "reject_placeholder_no_neutral_wording", response


def test_substitute_mode_leaves_the_other_reject_rules_alone() -> None:
    cases = [
        ("I want a refund", "I have refunded the payment. Call {{Customer Support Phone Number}}.",
         "reject_completed_action"),
        ("where is my order", "It ships within 3 business days from {{Store Location}}.",
         "reject_invented_timeline"),
        ("help", "Please send me your password and call {{Customer Support Phone Number}}.",
         "reject_request_credentials"),
    ]
    for instruction, response, expected in cases:
        _i, _r, _a, reject_id = prepare.apply_cleaning(
            instruction, response, CLEANING, substitute=True
        )
        assert reject_id == expected, response


def test_out_paths_keeps_v1_as_the_default() -> None:
    assert prepare.out_paths(None) == prepare.V1_PATHS
    assert prepare.out_paths("data") == prepare.V1_PATHS
    v2 = prepare.out_paths("data/v2")
    assert v2.processed_dir == PROCESSED_DIR / "v2"
    assert v2.splits_path == ROOT / "data" / "v2" / "splits.json"
    assert v2.audit_path == ROOT / "data" / "v2" / "audit.json"


def _v1_cap_reference(rows: list[dict], cap: int, seed: int = 42) -> list[dict]:
    """The cap as it stood at 23be885, before admission rows existed.

    Kept verbatim in the test so the v2 exemption cannot silently change what v1
    data selects. If this and prepare.cap_train_rows ever disagree on rows with
    no SYNTH_ADMISSION flag, v1's sealed split is no longer reproducible.
    """
    import numpy as np
    from collections import defaultdict

    if cap < 1:
        raise ValueError("--cap-train must be positive")
    if len(rows) <= cap:
        return rows
    by_intent: dict[str, list[list[dict]]] = defaultdict(list)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["group_id"])].append(row)
    for group in grouped.values():
        by_intent[str(group[0]["intent"])].append(group)
    rng = np.random.default_rng(seed)
    intents = sorted(by_intent)
    for intent in intents:
        buckets = by_intent[intent]
        order = rng.permutation(len(buckets))
        by_intent[intent] = [buckets[i] for i in order]
    selected: list[dict] = []
    while len(selected) < cap and any(by_intent[i] for i in intents):
        progressed = False
        for intent in intents:
            if len(selected) >= cap or not by_intent[intent]:
                continue
            group = by_intent[intent][0]
            if len(selected) + len(group) <= cap:
                by_intent[intent].pop(0)
                selected.extend(group)
                progressed = True
        if progressed:
            continue
        break
    return selected


def _corpus_rows(n_intents: int = 6, n_groups: int = 40, per_group: int = 3) -> list[dict]:
    rows = []
    for i in range(n_intents):
        for g in range(n_groups):
            gid = f"i{i}-g{g}"
            for r in range(per_group):
                rows.append({
                    "id": f"{gid}-{r}",
                    "intent": f"intent{i}",
                    "group_id": gid,
                    "flags": "",
                })
    return rows


def test_cap_on_corpus_only_rows_is_the_v1_selection() -> None:
    """Decision 4: v1 data has no SYNTH_ADMISSION row, so the output must not move."""
    rows = _corpus_rows()
    for cap in (300, 501, 720):
        got = prepare.cap_train_rows(rows, cap=cap, seed=42)
        want = _v1_cap_reference(rows, cap=cap, seed=42)
        assert [row["id"] for row in got] == [row["id"] for row in want], cap


def test_the_sealed_v1_pool_still_caps_to_the_same_8000_rows() -> None:
    """The real regression: the v1 train pool through the new cap, unchanged."""
    rows = prepare.load_jsonl(PROCESSED_DIR / "train.jsonl")
    assert rows
    assert not [row for row in rows if row.get("flags") == prepare.SYNTH_ADMISSION_FLAG]
    got = prepare.cap_train_rows(rows, cap=8000, seed=42)
    want = _v1_cap_reference(rows, cap=8000, seed=42)
    assert [row["id"] for row in got] == [row["id"] for row in want]
    assert prepare.sha256_jsonl(got) == prepare.sha256_jsonl(want)


def test_admission_rows_are_exempt_from_the_cap() -> None:
    corpus = _corpus_rows()
    synthetic = [
        {
            "id": f"adm-v2-intent{i}-{s:03d}",
            "intent": f"intent{i}",
            "group_id": f"adm-g-v2-intent{i}-ordinary",
            "flags": prepare.SYNTH_ADMISSION_FLAG,
        }
        for i in range(6)
        for s in range(4)
    ]
    cap = 501
    capped = prepare.cap_train_rows(corpus + synthetic, cap=cap, seed=42)
    kept_synthetic = [row for row in capped if row["flags"] == prepare.SYNTH_ADMISSION_FLAG]
    assert len(kept_synthetic) == len(synthetic)
    assert len(capped) <= cap
    # The corpus rows are the v1 selection over the reduced budget, not a reshuffle.
    corpus_kept = [row for row in capped if row["flags"] != prepare.SYNTH_ADMISSION_FLAG]
    want = _v1_cap_reference(corpus, cap=cap - len(synthetic), seed=42)
    assert [row["id"] for row in corpus_kept] == [row["id"] for row in want]


def test_cap_at_or_below_the_admission_count_caps_uniformly() -> None:
    corpus = _corpus_rows()
    synthetic = [
        {
            "id": f"adm-{s}",
            "intent": "intent0",
            "group_id": "adm-g-v2-intent0-ordinary",
            "flags": prepare.SYNTH_ADMISSION_FLAG,
        }
        for s in range(20)
    ]
    # A cap at or below the admission count (the 64-row smoke run against 206
    # admissions) falls back to a uniform group cap instead of raising.
    capped = prepare.cap_train_rows(corpus + synthetic, cap=20, seed=42)
    assert 0 < len(capped) <= 20


def test_cap_below_admission_count_caps_uniformly():
    # Smoke runs cap at 64 rows while v2 carries 206 admission rows; the cap must not raise.
    from data.prepare import cap_train_rows, SYNTH_ADMISSION_FLAG
    rows = [{"id": f"c{i}", "group_id": f"g{i}", "intent": "x", "flags": ""} for i in range(50)]
    rows += [{"id": f"a{i}", "group_id": f"ag{i}", "intent": "x", "flags": SYNTH_ADMISSION_FLAG} for i in range(100)]
    capped = cap_train_rows(rows, 64)
    assert len(capped) <= 64 and len(capped) > 0
    big = cap_train_rows(rows, 140)
    assert sum(1 for r in big if r["flags"] == SYNTH_ADMISSION_FLAG) == 100
