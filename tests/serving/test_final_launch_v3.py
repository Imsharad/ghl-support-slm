from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from eval.final_v3 import checked_generation, verify_candidate, verify_export, verify_screening
from eval.run import Generation
from tools.artifacts.convert_verified import verify_merged
from tools.artifacts.merge import artifact_hashes
from train.repro import sha256_file
from train.render import load_system_prompt

ROOT = Path(__file__).resolve().parents[2]


def test_screening_must_cover_actual_data_and_unchanged_protocol(tmp_path, monkeypatch):
    from eval import final_v3
    monkeypatch.setattr(final_v3, "ROOT", tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    (tmp_path / "eval").mkdir()
    paths = [data / "train.jsonl", data / "val.jsonl", tmp_path / "eval/challenge.jsonl",
             tmp_path / "eval/challenge_v2.jsonl"]
    for i, path in enumerate(paths):
        path.write_text(f"fixture {i}")
    for path in (tmp_path / "eval/prepare_v3.py", tmp_path / "data/audit_overlap_v3.py"):
        path.write_text("fixture source")
    cases = tmp_path / "cases.jsonl"
    cases.write_text(json.dumps({"id": "test"}) + "\n")
    protocol = tmp_path / "protocol.json"
    protocol.write_text("fixture protocol")
    report = {"pass": True, "status": "screened_not_sealed", "cases_sha256": sha256_file(cases),
              "protocol_sha256": sha256_file(protocol), "embedding_model": final_v3.EMBEDDER,
              "embedding_revision": final_v3.REVISION, "threshold": final_v3.THRESHOLD,
              "screening_code_sha256": sha256_file(tmp_path / "eval/prepare_v3.py"),
              "normalization_code_sha256": sha256_file(tmp_path / "data/audit_overlap_v3.py"),
              "against_sha256": {str(path): sha256_file(path) for path in paths},
              "results": [{"id": "test", "pass": True}]}
    verify_screening(report, cases, protocol, data)
    changed = deepcopy(report)
    changed["results"].pop()
    with pytest.raises(ValueError, match="every final case"):
        verify_screening(changed, cases, protocol, data)
    changed = deepcopy(report)
    changed["against_sha256"] = {"wrong": "not the training hash"}
    with pytest.raises(ValueError, match="actual training"):
        verify_screening(changed, cases, protocol, data)


def test_tag_mutation_before_or_during_generation_never_returns_answer():
    generated = []
    def runner(query):
        generated.append(query)
        return Generation("answer", 1, 1, 1, 1, False)
    before = checked_generation(runner, "model", "sealed", resolve=lambda *_: "changed")
    with pytest.raises(ValueError, match="before generation"):
        before("query")
    assert not generated
    states = iter(["sealed", "changed"])
    during = checked_generation(runner, "model", "sealed", resolve=lambda *_: next(states))
    with pytest.raises(ValueError, match="discarded"):
        during("query")
    assert generated == ["query"]
    assert checked_generation(runner, "model", "sealed", resolve=lambda *_: "sealed")("query").answer == "answer"


def candidate_fixture(tmp_path):
    run = tmp_path / "run"
    adapter = run / "checkpoint-30"
    adapter.mkdir(parents=True)
    data = tmp_path / "data"
    data.mkdir()
    for split in ("train", "val"):
        (data / f"{split}.jsonl").write_text(split)
    base = {"repo_id": "fixture/base", "revision": "a" * 40}
    versions = {"base_model": base, "llama_cpp_converter": {"commit": "b" * 40}}
    prompt = "Fixture prompt, not a real training run"
    (adapter / "prompt.txt").write_text(prompt + "\n")
    (adapter / "adapter_model.safetensors").write_bytes(b"synthetic fixture")
    (adapter / "trainer_state.json").write_text(json.dumps({"step": 30}))
    (run / "loss.csv").write_text("step,train_loss,val_loss\n30,1.1,1.2\n")
    summary = {"base_model": base, "device": "cuda", "finished_at": "fixture",
               "final_step": 120, "steps": {"max_steps": 120}, "hub": {"pushed": False},
               "system_prompt": prompt, "inputs": {
                   "base_pin": [base["repo_id"], base["revision"]],
                   "files": {s: sha256_file(data / f"{s}.jsonl") for s in ("train", "val")},
                   "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}}
    (run / "config.json").write_text(json.dumps(summary))
    return run, adapter, data, prompt, versions, summary


def test_selected_checkpoint_requires_finished_run_correct_data_and_prompt(tmp_path):
    run, adapter, data, prompt, versions, summary = candidate_fixture(tmp_path)
    assert verify_candidate(run, adapter, data, prompt, versions) == summary
    (adapter / "prompt.txt").write_text("wrong prompt")
    with pytest.raises(ValueError, match="data/base/prompt"):
        verify_candidate(run, adapter, data, prompt, versions)
    (adapter / "prompt.txt").write_text(prompt)
    summary["final_step"] = 119
    (run / "config.json").write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="completed"):
        verify_candidate(run, adapter, data, prompt, versions)


def test_export_must_bind_same_adapter_prompt_base_converter_and_gguf(tmp_path):
    _, adapter, _, prompt, versions, _ = candidate_fixture(tmp_path)
    gguf = tmp_path / "model.gguf"
    gguf.write_bytes(b"not a real model: verification fixture")
    export = {"schema": 1, "base_model": versions["base_model"],
              "adapter_files_sha256": artifact_hashes(adapter),
              "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
              "quantization": "Q8_0", "converter_commit": versions["llama_cpp_converter"]["commit"],
              "gguf_sha256": sha256_file(gguf), "gguf_bytes": gguf.stat().st_size}
    verify_export(export, gguf, adapter, prompt, versions)
    gguf.write_bytes(b"changed")
    with pytest.raises(ValueError, match="lineage"):
        verify_export(export, gguf, adapter, prompt, versions)


def test_conversion_refuses_modified_merged_inputs(tmp_path):
    versions = {"base_model": {"repo_id": "base", "revision": "pin"}}
    weights = tmp_path / "model.safetensors"
    weights.write_bytes(b"fixture")
    manifest = {"base_model": versions["base_model"], "safe_merge": True,
                "adapter_files_sha256": {"adapter_model.safetensors": "adapter"},
                "output_files_sha256": artifact_hashes(tmp_path)}
    (tmp_path / "merge_manifest.json").write_text(json.dumps(manifest))
    assert verify_merged(tmp_path, versions) == manifest
    weights.write_bytes(b"changed")
    with pytest.raises(ValueError, match="differ"):
        verify_merged(tmp_path, versions)


def test_complete_final_generation_resume_uses_synthetic_fixtures_only(tmp_path, monkeypatch):
    from eval import final_v3
    from eval.prepare_v3 import KINDS
    from eval.run import inference_manifest
    intents = json.loads((ROOT / "data/intents.json").read_text())
    cases = [{"id": f"fixture-{i}-{j}", "intent": item["intent"], "kind": kind,
              "query": f"Synthetic plumbing fixture {i} {j}; not an evaluation question.",
              "acceptable_actions": ["Synthetic fixture"], "critical_fail_if": ["Synthetic fixture"]}
             for i, item in enumerate(intents) for j, kind in enumerate(KINDS)]
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text("".join(json.dumps(row) + "\n" for row in cases))
    out = tmp_path / "final"
    out.mkdir()
    prompt = load_system_prompt(ROOT / "configs/prompt-v3.txt")
    models = {"base": {"tag": "fixture-base", "digest": "a" * 64},
              "tuned": {"tag": "fixture-tuned", "digest": "b" * 64}}
    manifest = inference_manifest(split_path=cases_path, system_prompt=prompt, model="base",
                                  backend="ollama", identity=models["base"])
    seal = {"schema": 3, "status": "frozen_before_final_inference", "models": models,
            "challenge_sha256": sha256_file(cases_path),
            "protocol_sha256": sha256_file(ROOT / "eval/v3/protocol.json"),
            "metrics_code_sha256": sha256_file(ROOT / "eval/v3_metrics.py"),
            "grading_code_sha256": sha256_file(ROOT / "eval/paired_v3.py"),
            "launcher_sha256": sha256_file(ROOT / "eval/final_v3.py"), "system_prompt": prompt,
            "inference": {field: manifest[field] for field in
                          ("backend", "decoding", "prompt_sha256", "runner_sha256", "render_sha256")}}
    (out / "SEAL.json").write_text(json.dumps(seal))
    by_tag = {identity["tag"]: identity["digest"] for identity in models.values()}
    calls = []
    def fixture_runner(**kwargs):
        def generate(query):
            calls.append((kwargs["tag"], query))
            return Generation("Synthetic plumbing answer, not model evidence.", 10, 5, 2, 2.5, False)
        return generate
    monkeypatch.setattr(final_v3, "OllamaRunner", fixture_runner)
    monkeypatch.setattr(final_v3, "ollama_digest", lambda url, tag, timeout: by_tag[tag])
    args = SimpleNamespace(output_dir=out, cases=cases_path, protocol=ROOT / "eval/v3/protocol.json")
    final_v3.generate_pairs(args)
    assert len(calls) == 216
    before = {m: (out / f"{m}-raw.jsonl").read_bytes() for m in models}
    final_v3.generate_pairs(args)
    assert len(calls) == 216  # Completed pairs are never generated again on resume.
    for model in models:
        path = out / f"{model}-raw.jsonl"
        assert path.read_bytes() == before[model]
        raw = [json.loads(line) for line in path.read_text().splitlines()]
        assert len(raw) == 108 and all(row["final_seal_sha256"] == sha256_file(out / "SEAL.json") for row in raw)
    tampered = json.loads((out / "base-raw.jsonl").read_text().splitlines()[0])
    tampered["tag"] = "wrong-model"
    (out / "base-raw.jsonl").write_text(json.dumps(tampered) + "\n")
    with pytest.raises(ValueError, match="metadata"):
        final_v3.generate_pairs(args)
    assert len(calls) == 216
