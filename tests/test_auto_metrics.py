"""Fixtures for eval/auto_metrics.py. Tiny on-disk rows, no processed split required."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
import auto_metrics  # noqa: E402


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def test_identical_answer_scores_rouge_l_one() -> None:
    text = "Please sign in and open Orders to cancel purchase GL-4419."
    assert auto_metrics.rouge_l_f1(text, text) == 1.0
    assert auto_metrics.rouge_l_f1("", "") == 1.0
    assert auto_metrics.rouge_l_f1("hello world", "hello world") == 1.0
    assert auto_metrics.rouge_l_f1("", "hello") == 0.0


def test_placeholder_detection() -> None:
    assert auto_metrics.has_placeholder("Cancel {{Order Number}} for me.") is True
    assert auto_metrics.has_placeholder("Cancel order GL-4419 for me.") is False
    assert auto_metrics.has_placeholder("") is False
    assert auto_metrics.has_placeholder("{{") is True


def test_bootstrap_interval_contains_point_estimate() -> None:
    # Two groups, constant per-group diffs. Percentile CI of the item-mean
    # must contain the observed mean (here they coincide).
    values = [0.2, 0.2, 0.4, 0.4]
    groups = ["g-1", "g-1", "g-2", "g-2"]
    point, lo, hi = auto_metrics.bootstrap_group_mean(values, groups, n_boot=2000, seed=42)
    assert point == pytest.approx(0.3)
    assert lo <= point <= hi
    # Degenerate case: every item the same.
    point0, lo0, hi0 = auto_metrics.bootstrap_group_mean([0.1, 0.1], ["a", "b"], n_boot=200, seed=42)
    assert point0 == pytest.approx(0.1)
    assert lo0 == pytest.approx(0.1)
    assert hi0 == pytest.approx(0.1)


def test_missing_ids_raise(tmp_path: Path) -> None:
    refs = _write_jsonl(
        tmp_path / "refs.jsonl",
        [
            {"id": "bitext-000001", "group_id": "g-1", "intent": "cancel_order", "response": "a"},
            {"id": "bitext-000002", "group_id": "g-1", "intent": "cancel_order", "response": "b"},
        ],
    )
    raw = _write_jsonl(
        tmp_path / "raw.jsonl",
        [
            {"id": "bitext-000001", "answer": "a", "truncated": False, "gen_tokens": 1, "error": None},
            {"id": "bitext-000003", "answer": "c", "truncated": False, "gen_tokens": 1, "error": None},
        ],
    )
    with pytest.raises(ValueError, match="missing in raw") as exc:
        auto_metrics.align(auto_metrics.load_jsonl(raw), auto_metrics.load_jsonl(refs))
    msg = str(exc.value)
    assert "bitext-000002" in msg
    assert "bitext-000003" in msg
    assert "missing in refs" in msg


def test_end_to_end_compare_writes_interval(tmp_path: Path) -> None:
    refs = [
        {
            "id": "bitext-000001",
            "group_id": "g-0042",
            "intent": "cancel_order",
            "response": "Please give your order number so I can help you cancel.",
        },
        {
            "id": "bitext-000002",
            "group_id": "g-0042",
            "intent": "cancel_order",
            "response": "Please give your order number so I can help you cancel.",
        },
        {
            "id": "bitext-000003",
            "group_id": "g-0099",
            "intent": "get_refund",
            "response": "Refunds go back to the original payment method after we receive the return.",
        },
    ]
    base = [
        {
            "id": "bitext-000001",
            "model": "base",
            "answer": "Contact support.",
            "truncated": False,
            "gen_tokens": 2,
            "error": None,
        },
        {
            "id": "bitext-000002",
            "model": "base",
            "answer": "Please give your order number so I can help you cancel.",
            "truncated": False,
            "gen_tokens": 12,
            "error": None,
        },
        {
            "id": "bitext-000003",
            "model": "base",
            "answer": "I have refunded you {{Refund Amount}} already.",
            "truncated": True,
            "gen_tokens": 256,
            "error": None,
        },
    ]
    tuned = [
        {
            "id": "bitext-000001",
            "model": "tuned",
            "answer": "Please give your order number so I can help you cancel.",
            "truncated": False,
            "gen_tokens": 12,
            "error": None,
        },
        {
            "id": "bitext-000002",
            "model": "tuned",
            "answer": "Please give your order number so I can help you cancel.",
            "truncated": False,
            "gen_tokens": 12,
            "error": None,
        },
        {
            "id": "bitext-000003",
            "model": "tuned",
            "answer": "Refunds go back to the original payment method after we receive the return.",
            "truncated": False,
            "gen_tokens": 14,
            "error": None,
        },
    ]
    refs_path = _write_jsonl(tmp_path / "refs.jsonl", refs)
    base_path = _write_jsonl(tmp_path / "base-test-raw.jsonl", base)
    tuned_path = _write_jsonl(tmp_path / "tuned-test-raw.jsonl", tuned)
    out_path = tmp_path / "base-test-auto.json"
    payload = auto_metrics.run(
        raw_path=base_path,
        refs_path=refs_path,
        out_path=out_path,
        compare_path=tuned_path,
        n_boot=200,
        seed=42,
        with_embeddings=True,
    )
    assert out_path.exists()
    tuned_out = tmp_path / "tuned-test-auto.json"
    assert tuned_out.exists()
    assert payload["n"] == 3
    assert payload["n_groups"] == 2
    assert payload["placeholder_rate"] == pytest.approx(1 / 3)
    assert payload["truncated_rate"] == pytest.approx(1 / 3)
    assert payload["per_intent"]["cancel_order"]["n"] == 2
    ident = [row for row in auto_metrics.score_aligned(auto_metrics.align(
        auto_metrics.load_jsonl(tuned_path), auto_metrics.load_jsonl(refs_path)
    ), with_embeddings=False) if row["id"] == "bitext-000002"][0]
    assert ident["rouge_l_f1"] == 1.0
    diff = payload["compare"]["diff"]["rouge_l_f1"]
    assert diff["ci95"][0] <= diff["point"] <= diff["ci95"][1]
    assert diff["point"] > 0
