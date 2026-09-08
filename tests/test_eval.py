"""Tests for raw evaluation, blind integrity, and paired final scoring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval import blind
from eval import check_challenge
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
            "acceptable_actions": [f"ask for detail {i}"],
            "critical_fail_if": [f"invent detail {i}"],
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
    rubric = blind.scoring_rubric(scenarios)
    page = blind.html_document(rows_a, rubric)
    assert "Blind challenge scoring" in page
    for row in rows_a:
        assert row["answer_A"] in page and row["answer_B"] in page
        assert f"ask for detail {int(row['item_id'][3:])}" in page
        assert f"invent detail {int(row['item_id'][3:])}" in page
    # A newline escape inside the emitted JS must stay escaped. Writing it as a real
    # newline breaks the string literal, and the whole sheet renders blank.
    script = page.split("<script>", 1)[1].split("</script>", 1)[0]
    assert "join('\\n')" in script
    assert "join('\n')" not in script


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


def test_adapter_argument_validation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="--adapter requires --backend transformers"):
        eval_run.validate_run_args(
            backend="ollama",
            model="tuned",
            adapter=tmp_path / "adapter",
        )
    with pytest.raises(ValueError, match="--adapter requires --model tuned"):
        eval_run.validate_run_args(
            backend="transformers",
            model="base",
            adapter=tmp_path / "adapter",
        )
    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError, match="adapter directory not found"):
        eval_run.validate_run_args(
            backend="transformers",
            model="tuned",
            adapter=missing,
        )
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="adapter_config.json"):
        eval_run.validate_run_args(
            backend="transformers",
            model="tuned",
            adapter=empty,
        )
    (empty / "adapter_config.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="adapter_model.safetensors"):
        eval_run.validate_run_args(
            backend="transformers",
            model="tuned",
            adapter=empty,
        )


def _build_zero_effect_adapter(directory: Path) -> Path:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM

    from train.render import load_base_pin

    repo_id, revision = load_base_pin()
    model = AutoModelForCausalLM.from_pretrained(
        repo_id,
        revision=revision,
        local_files_only=True,
        dtype=torch.float16,
        low_cpu_mem_usage=True,
    )
    config = LoraConfig(
        r=1,
        lora_alpha=1,
        lora_dropout=0.0,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj"],
        init_lora_weights=True,
    )
    adapted = get_peft_model(model, config)
    for name, parameter in adapted.named_parameters():
        if "lora_" in name:
            parameter.data.zero_()
    adapted.save_pretrained(directory)
    return directory


def test_zero_effect_adapter_matches_base_greedy_cpu(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("peft", reason="install the train extra first")
    # Test adapter identity on a bounded greedy prefix, not support-answer quality.
    # BF16 CPU fallback can take minutes for four full 256-token generations.
    # This changes only this test's cap; sealed evaluation remains at 256.
    monkeypatch.setattr(eval_run, "MAX_NEW_TOKENS", 8)
    adapter_dir = _build_zero_effect_adapter(tmp_path / "zero-lora")
    sha = eval_run.adapter_weights_sha256(adapter_dir)
    assert len(sha) == 64
    items = eval_run.load_jsonl(eval_run.SPLIT_PATHS["dev"])[:2]
    assert len(items) == 2

    base_runner = eval_run.TransformersRunner(model="base", requested_device="cpu")
    adapter_runner = eval_run.TransformersRunner(
        model="tuned",
        requested_device="cpu",
        adapter_dir=adapter_dir,
    )
    output = tmp_path / "tuned-dev-raw.jsonl"
    for item in items:
        base = base_runner(eval_run.query_for(item))
        adapted = adapter_runner(eval_run.query_for(item))
        assert adapted.answer == base.answer
        eval_run.append_jsonl(
            output,
            eval_run.result_row(
                item,
                model="tuned",
                backend="transformers",
                tag="ghl-support",
                generate=lambda _query, _gen=adapted: _gen,
                adapter_dir=adapter_dir,
                adapter_sha256=sha,
            ),
        )
    rows = eval_run.load_jsonl(output)
    assert rows[0]["adapter_dir"] == str(adapter_dir)
    assert rows[0]["adapter_sha256"] == sha
    print(json.dumps(rows[0], ensure_ascii=False)[:500])


def test_red_list_partitions_every_critical_line_of_the_sealed_set() -> None:
    # The reference panel on the sheet is generated, not hand-written. Every
    # critical-fail line in the sealed set must land in exactly one family, or
    # the panel quietly stops being the full list it claims to be.
    scenarios = blind.load_jsonl(Path(__file__).resolve().parents[1] / "eval" / "challenge.jsonl")
    rubric = blind.scoring_rubric(scenarios)
    families = blind.red_list(rubric)
    grouped = [entry["line"] for family in families for entry in family["lines"]]
    expected = [line for scenario in scenarios for line in scenario["critical_fail_if"]]
    assert sorted(grouped) == sorted(expected)
    assert len(grouped) == len(expected)
    ids = {entry["item"] for family in families for entry in family["lines"]}
    assert ids == {str(scenario["id"]) for scenario in scenarios}

    page = blind.html_document([], rubric)
    assert "The full red list" in page
    for line in expected:
        assert line in page


def test_challenge_schema_accepts_the_v1_sealed_set() -> None:
    root = Path(__file__).resolve().parents[1]
    rows = check_challenge.load_jsonl(root / "eval" / "challenge.jsonl")
    errors = check_challenge.schema_errors(
        rows,
        check_challenge.load_intents(),
        require_v1_cosine=False,
    )
    assert errors == []


def test_challenge_schema_requires_v1_cosine_for_comparison() -> None:
    root = Path(__file__).resolve().parents[1]
    rows = check_challenge.load_jsonl(root / "eval" / "challenge.jsonl")
    errors = check_challenge.schema_errors(
        rows,
        check_challenge.load_intents(),
        require_v1_cosine=True,
    )
    assert any("max_v1_cosine" in error for error in errors)


def test_challenge_schema_accepts_the_v2_draft() -> None:
    root = Path(__file__).resolve().parents[1]
    rows = check_challenge.load_jsonl(root / "eval" / "challenge_v2_draft.jsonl")
    errors = check_challenge.schema_errors(
        rows,
        check_challenge.load_intents(),
        require_v1_cosine=True,
    )
    assert errors == []


def test_challenge_shared_six_grams_normalizes_case_and_punctuation() -> None:
    hits = check_challenge.shared_ngrams(
        "Please STOP this tent order, before it ships now.",
        ["please stop this tent order before it gets labelled"],
    )
    assert ("please", "stop", "this", "tent", "order", "before") in hits


def test_challenge_metric_caps_and_six_grams_are_failures() -> None:
    rows = [{"id": "ch2-001", "max_bitext_cosine": 0.85, "max_v1_cosine": 0.80}]
    metrics = [{
        "id": "ch2-001",
        "bitext_cosine": 0.85,
        "v1_cosine": 0.80,
        "six_gram_hits": 1,
        "six_gram_sources": {"one two three four five six": ["ch-001"]},
    }]
    errors = check_challenge.metric_errors(rows, metrics)
    assert any("Bitext cosine" in error for error in errors)
    assert any("v1 cosine" in error for error in errors)
    assert any("six-gram" in error for error in errors)


def test_custom_challenge_path_is_checked_against_custom_seal(tmp_path: Path) -> None:
    challenge = tmp_path / "challenge-v2.jsonl"
    challenge.write_text('{"id":"ch2-001"}\n', encoding="utf-8")
    seal = tmp_path / "seal-v2.json"
    seal.write_text(
        json.dumps({"challenge_sha256": check_challenge.file_sha256(challenge)}),
        encoding="utf-8",
    )
    assert (
        eval_run.split_path_for(split="challenge", challenge=challenge, seal=seal)
        == challenge
    )


def test_seal_challenge_copies_draft_bytes_and_records_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = tmp_path / "draft.jsonl"
    draft.write_bytes(b'{"id":"ch2-001"}\n')
    against = tmp_path / "against.jsonl"
    against.write_bytes(b'{"id":"ch-001"}\n')
    challenge = tmp_path / "challenge_v2.jsonl"
    seal_path = tmp_path / "SEAL_v2.json"
    monkeypatch.setattr(check_challenge, "SEALED_CHALLENGE_PATH", challenge)
    monkeypatch.setattr(check_challenge, "SEAL_PATH", seal_path)
    seal = check_challenge.seal_challenge(
        draft,
        [{"id": "ch2-001"}],
        [against],
        approval_event="a" * 64,
        provenance="fresh set drafted before v2 answers",
    )
    assert challenge.read_bytes() == draft.read_bytes()
    assert seal["challenge_sha256"] == check_challenge.file_sha256(challenge)
    assert seal["approval_event"] == "a" * 64
    assert json.loads(seal_path.read_text(encoding="utf-8")) == seal
    with pytest.raises(ValueError, match="refusing to overwrite sealed output"):
        check_challenge.seal_challenge(
            draft,
            [{"id": "ch2-001"}],
            [against],
            approval_event="a" * 64,
            provenance="fresh set drafted before v2 answers",
        )
