"""Real optimizer/checkpoint replay on a tiny CPU fixture, not a Qwen/GPU smoke."""

import json
from pathlib import Path
from types import SimpleNamespace

import torch
from safetensors.torch import load_file, save_file

from train.train import run_smoke


def test_full_training_loop_resume_replays_dropout_weights_and_losses(monkeypatch, tmp_path):
    class Tokenizer:
        pad_token_id = 0
        chat_template = "fixture template"
        def save_pretrained(self, path):
            (Path(path) / "tokenizer_config.json").write_text('{"fixture":true}\n')

    class Collator:
        tokenizer = Tokenizer()
        dropped_overlength = 0
        def __init__(self, **kwargs): self.max_length = kwargs["max_length"]
        def encode(self, row):
            n = int(row["id"].split("-")[-1]) % 5 + 1
            return {"input_ids": [n, 2, 3, 4], "attention_mask": [1] * 4,
                    "labels": [-100, -100, n, 4]}

    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = torch.nn.Embedding(8, 4)
            self.dropout = torch.nn.Dropout(.25)
            self.head = torch.nn.Linear(4, 8)
        def forward(self, input_ids, attention_mask, labels):
            logits = self.head(self.dropout(self.embedding(input_ids)))
            loss = torch.nn.functional.cross_entropy(logits[:, :-1].reshape(-1, 8),
                                                     labels[:, 1:].reshape(-1), ignore_index=-100)
            return SimpleNamespace(loss=loss)
        def save_pretrained(self, path):
            save_file(self.state_dict(), str(Path(path) / "adapter_model.safetensors"))

    def attach(model, config, resume_dir):
        if resume_dir:
            model.load_state_dict(load_file(str(resume_dir / "adapter_model.safetensors")))
        model.train()
        return model

    monkeypatch.setattr("train.train.AssistantOnlyCollator", Collator)
    monkeypatch.setattr("train.train.build_model", lambda *a: (None, Model()))
    monkeypatch.setattr("train.train.attach_adapter", attach)
    # Tiny dense layers are faster and reproducible with one CPU worker.
    prior_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for split in ("train", "val"):
        rows = [{"id": f"{split}-{i}", "intent": "fixture", "instruction": "fixture",
                 "response": "fixture"} for i in range(7)]
        (data_dir / f"{split}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Fixture system\n")
    config = {
        "run_name": "toy", "seed": 42, "prompt_file": str(prompt), "strict_reproducibility": True,
        "data": {"dir": str(data_dir), "train_file": "train.jsonl", "val_file": "val.jsonl", "max_length": 16},
        "model": {}, "lora": {}, "optim": {"lr": .01, "warmup_ratio": .1},
        "train": {"micro_batch_size": 2, "grad_accum": 2, "log_every": 2, "save_every": 2,
                  "val_batches": 3, "max_steps": 8},
        "hub": {"push_checkpoints": False}, "smoke": {"resume_from": 4, "resume_tolerance": 0},
    }
    run_dir = tmp_path / "run"
    try:
        assert run_smoke(config, "cpu", run_dir) == 0
    finally:
        torch.set_num_threads(prior_threads)
    original = load_file(str(run_dir / "checkpoint-8/adapter_model.safetensors"))
    resumed = load_file(str(run_dir / "resume-proof/checkpoint-8/adapter_model.safetensors"))
    assert original.keys() == resumed.keys()
    assert all(torch.equal(original[k], resumed[k]) for k in original)
    assert (run_dir / "checkpoint-8/prompt.txt").read_text() == "Fixture system\n"
    report = json.loads((run_dir / "smoke.json").read_text())
    assert report["max_abs_diff"] == 0 and report["compared_steps"] == [6, 8]
