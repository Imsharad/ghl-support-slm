"""Regression tests for resumed inputs, RNG, masks, and non-destructive smoke."""

import json
import random
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from tools.training.check_run import check_smoke
from train.collate import AssistantOnlyCollator, IGNORE_INDEX
from train.render import get_tokenizer, load_system_prompt, render_prompt
from train.repro import capture_rng, fingerprint, require_same_inputs, restore_rng
from train.train import evaluate, micro_batches, run_smoke, validation_rows


def test_explicit_prompt_masks_and_preserves_historical_default():
    tokenizer = get_tokenizer()
    card = load_system_prompt(Path("configs/prompt-v3.txt"))
    row = {"instruction": "I forgot my password.", "response": "Use the password reset option."}
    rendered = render_prompt(row["instruction"], tokenizer, system_prompt=card)
    assert rendered.count("<|im_start|>system\n") == 1
    assert rendered.count(card) == 1
    custom = AssistantOnlyCollator(tokenizer, max_length=768, system_prompt=card).encode(row)
    original = AssistantOnlyCollator(tokenizer).encode(row)
    assert custom["input_ids"] != original["input_ids"]
    n = len(tokenizer.encode(rendered, add_special_tokens=False))
    assert all(x == IGNORE_INDEX for x in custom["labels"][:n])
    assert custom["labels"][n] != IGNORE_INDEX
    assert custom["labels"][-2] == tokenizer.convert_tokens_to_ids("<|im_end|>")


def test_fingerprint_detects_same_path_content_and_order_changes(tmp_path):
    source = tmp_path / "train.jsonl"
    source.write_text("original")
    config = {k: {} for k in ("model", "lora", "optim", "train")}
    config.update(seed=42, data={"max_length": 768})
    def make(ids=None, prompt="card"):
        return fingerprint(config, {"train": source}, prompt, ids or ["a", "b"], ("model", "revision"))
    first = make()
    require_same_inputs(first, make())
    for changed in (make(["b", "a"]), make(prompt="other")):
        with pytest.raises(ValueError, match="fingerprint"):
            require_same_inputs(first, changed)
    source.write_text("changed")
    with pytest.raises(ValueError, match="fingerprint"):
        require_same_inputs(first, make())


def test_rng_restore_replays_python_numpy_and_torch():
    state = capture_rng(torch)
    expected = (random.random(), np.random.random(), torch.rand(3))
    restore_rng(state, torch)
    assert random.random() == expected[0]
    assert np.random.random() == expected[1]
    assert torch.equal(torch.rand(3), expected[2])


def test_fingerprint_detects_effective_schedule_and_runtime_changes(tmp_path):
    source = tmp_path / "source"
    source.write_text("fixed")
    config = {k: {} for k in ("model", "lora", "optim", "train")}
    config.update(seed=42, data={"max_length": 768})
    args = (config, {"train": source}, "card", ["a"], ("repo", "revision"))
    first = fingerprint(*args, runtime={"effective_max_steps": 20, "device": "cpu"})
    for runtime in ({"effective_max_steps": 30, "device": "cpu"},
                    {"effective_max_steps": 20, "device": "cuda"}):
        with pytest.raises(ValueError, match="fingerprint"):
            require_same_inputs(first, fingerprint(*args, runtime=runtime))


def test_resumed_sample_stream_is_exact_suffix_across_epoch_boundary():
    rows = [{"input_ids": [i], "attention_mask": [1], "labels": [i]} for i in range(7)]
    kwargs = dict(micro_batch_size=1, seed=42, pad_id=0, torch=torch)
    full = micro_batches(rows, start_index=0, **kwargs)
    expected = [next(full)["input_ids"].item() for _ in range(20)]
    resumed = micro_batches(rows, start_index=9, **kwargs)
    assert [next(resumed)["input_ids"].item() for _ in range(11)] == expected[9:]


def test_evaluation_restores_mode_and_rng_even_on_error():
    class Model:
        training = False
        def eval(self): self.training = False
        def train(self, mode=True): self.training = mode
        def __call__(self, **kwargs):
            torch.rand(1)
            raise RuntimeError("fixture failure")
    model = Model()
    before = torch.get_rng_state().clone()
    with pytest.raises(RuntimeError, match="fixture failure"):
        evaluate(model, [{"input_ids": torch.tensor([[1]])}], "cpu", torch)
    assert model.training is False
    assert torch.equal(before, torch.get_rng_state())


def test_smoke_preserves_original_checkpoints_and_separates_resume(monkeypatch, tmp_path):
    calls = []
    def fake_train(config, *, device, resume, run_dir):
        calls.append((resume, run_dir))
        for step in (10, 20):
            folder = run_dir / f"checkpoint-{step}"
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "state.pt").write_bytes(b"fixture")
        return {"logged": {20: {"train_loss": 1.0}}, "final_step": 20}
    monkeypatch.setattr("train.train.train", fake_train)
    assert run_smoke({"train": {"max_steps": 20}}, "cpu", tmp_path) == 0
    assert (tmp_path / "checkpoint-20/state.pt").read_bytes() == b"fixture"
    assert calls == [(False, tmp_path), (True, tmp_path / "resume-proof")]
    assert json.loads((tmp_path / "smoke.json").read_text())["ok"]


def test_required_smoke_fails_when_missing(tmp_path):
    failures = []
    check_smoke(tmp_path, failures, required=True)
    assert failures and "missing" in failures[0]


def test_validation_sampling_covers_intents_despite_sorted_sources():
    rows = [{"id": f"{intent}-{i}", "intent": intent} for intent in ("a", "b", "c")
            for i in range(10)]
    sample = validation_rows(rows, 6, 42)
    assert [r["intent"] for r in sample] == ["a", "b", "c", "a", "b", "c"]
    assert sample == validation_rows(rows, 6, 42)
    assert len(validation_rows(rows, 40, 42)) == len(rows)


def test_validation_loss_is_weighted_by_predicted_target_tokens():
    class Model:
        training = True
        def eval(self): self.training = False
        def train(self, mode=True): self.training = mode
        def __call__(self, **kwargs):
            return SimpleNamespace(loss=torch.tensor(float(kwargs["input_ids"][0, 0])))
    batches = [
        {"input_ids": torch.tensor([[2, 0, 0]]), "labels": torch.tensor([[-100, 1, -100]])},
        {"input_ids": torch.tensor([[4, 0, 0]]), "labels": torch.tensor([[-100, 1, 1]])}]
    model = Model()
    assert evaluate(model, batches, "cpu", torch) == pytest.approx(10/3)
    assert model.training
