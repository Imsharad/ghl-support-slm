"""Tests for raw evaluation, blind integrity, and paired final scoring."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval import blind
from eval import run as eval_run
from eval import score


def _key_item(
    answer_a: str,
    answer_b: str,
    *,
    model_a: str = "base",
    model_b: str = "tuned",
    intent: str = "cancel_order",
    kind: str = "ordinary",
) -> dict:
    return {
        "model_A": model_a,
        "model_B": model_b,
        "answer_A_sha256": score.answer_sha256(answer_a),
        "answer_B_sha256": score.answer_sha256(answer_b),
        "intent": intent,
        "kind": kind,
    }


def _sheet_row(
    item_id: str,
    answer_a: str,
    answer_b: str,
    *,
    pass_a: str,
    pass_b: str,
    critical_a: str = "false",
    critical_b: str = "false",
    preferred: str = "tie",
) -> dict[str, str]:
    return {
        "item_id": item_id,
        "query": "Please cancel my order.",
        "facts": "order id unknown",
        "answer_A": answer_a,
        "answer_B": answer_b,
        "pass_A": pass_a,
        "pass_B": pass_b,
        "critical_A": critical_a,
        "critical_B": critical_b,
        "preferred": preferred,
        "notes": "fixture",
    }


def test_good_bad_pairs_unblind_and_score_as_expected() -> None:
    bad = "Done, your order is cancelled."
    good = "Please provide the order ID so I can explain the cancellation steps."
    key = {
        "schema_version": 1,
        "split": "challenge",
        "items": {
            "ch-001": _key_item(bad, good),
            "ch-002": _key_item(good, bad, model_a="tuned", model_b="base", kind="hard"),
        },
    }
    sheet = [
        _sheet_row(
            "ch-001",
            bad,
            good,
            pass_a="false",
            pass_b="true",
            critical_a="true",
            preferred="B",
        ),
        _sheet_row(
            "ch-002",
            good,
            bad,
            pass_a="true",
            pass_b="false",
            critical_b="true",
            preferred="A",
        ),
    ]
    scores, paired = score.unblind(sheet, key, require_complete=True)
    assert len(scores) == 4
    assert all(item["tuned"]["pass"] for item in paired)
    assert all(not item["base"]["pass"] for item in paired)
    summary = score.summarize(paired, n_boot=500, seed=42)
    assert summary["base_pass_rate"] == 0.0
    assert summary["tuned_pass_rate"] == 1.0
    assert summary["diff_points"] == 100.0
    assert summary["verdict"] == "positive"
    assert summary["win"] == 2


def test_swapped_answer_columns_are_detected() -> None:
    answer_a = "Answer originally shown as A"
    answer_b = "Answer originally shown as B"
    key = {
        "schema_version": 1,
        "split": "challenge",
        "items": {"ch-001": _key_item(answer_a, answer_b)},
    }
    swapped = _sheet_row(
        "ch-001",
        answer_b,
        answer_a,
        pass_a="true",
        pass_b="false",
        preferred="A",
    )
    with pytest.raises(ValueError, match="answer_A order/content"):
        score.unblind([swapped], key, require_complete=True)


def test_missing_outputs_fail_check_complete() -> None:
    with pytest.raises(ValueError, match="missing output ids") as exc:
        eval_run.assert_complete({"dv-001", "dv-002"}, [{"id": "dv-001"}])
    assert "dv-002" in str(exc.value)


def test_bootstrap_interval_contains_point_estimate() -> None:
    point, lo, hi = score.paired_bootstrap(
        [True, False, True, False],
        [True, True, False, True],
        n_boot=2000,
        seed=42,
    )
    assert point == pytest.approx(25.0)
    assert lo <= point <= hi


def test_blind_rows_are_deterministic_balanced_and_render_in_html() -> None:
    scenarios = [
        {
            "id": f"ch-{i:03d}",
            "query": f"query {i}",
            "facts": "facts",
            "intent": "x",
            "kind": "ordinary",
        }
        for i in range(1, 5)
    ]
    base = [
        {"id": item["id"], "answer": f"base {item['id']}", "error": None}
        for item in scenarios
    ]
    tuned = [
        {"id": item["id"], "answer": f"tuned {item['id']}", "error": None}
        for item in scenarios
    ]
    rows_a, key_a = blind.build_rows(scenarios, base, tuned, seed_hash="a" * 64)
    rows_b, key_b = blind.build_rows(scenarios, base, tuned, seed_hash="a" * 64)
    assert rows_a == rows_b
    assert key_a == key_b
    assert sum(item["model_A"] == "base" for item in key_a["items"].values()) == 2
    page = blind.html_document(rows_a)
    assert "Blind challenge scoring" in page
    for row in rows_a:
        assert row["answer_A"] in page and row["answer_B"] in page


def test_run_records_failure_then_resumes_by_id(tmp_path: Path) -> None:
    output = tmp_path / "raw.jsonl"
    items = [
        {"id": "dv-001", "query": "one"},
        {"id": "dv-002", "query": "two"},
    ]

    def fake_generate(query: str) -> eval_run.Generation:
        if query == "two":
            raise TimeoutError("fixture timeout")
        return eval_run.Generation("answer", 3, 1, 10.0, 100.0, False)

    for item in items:
        eval_run.append_jsonl(
            output,
            eval_run.result_row(
                item,
                model="base",
                backend="ollama",
                tag="ghl-base",
                generate=fake_generate,
            ),
        )
    rows = eval_run.load_jsonl(output)
    assert rows[0]["error"] is None
    assert rows[1]["answer"] == ""
    assert rows[1]["gen_tokens"] == 0
    assert "TimeoutError" in rows[1]["error"]
    resumed = eval_run.load_existing(
        output,
        model="base",
        backend="ollama",
        all_ids={"dv-001", "dv-002"},
    )
    assert set(resumed) == {"dv-001", "dv-002"}
