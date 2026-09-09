"""Freeze a verified v3 candidate, then generate final pairs under that seal.

Seal creation is a pre-inference operation, not a claim of model improvement.
This launcher never selects a checkpoint or assigns human grades. Do not reseal
after inspecting final outputs to keep iterating on the same test set.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.blind import index_by_id, load_jsonl
from eval.paired_v3 import verify_manifest, verify_seal
from eval.prepare_v3 import EMBEDDER, REVISION, THRESHOLD, read_json
from eval.run import (OllamaRunner, append_jsonl, ensure_run_manifest, inference_manifest,
                      ollama_digest, result_row)
from tools.merge import artifact_hashes
from tools.check_run import check_losses, check_smoke
from train.render import load_system_prompt
from train.repro import sha256_file


def verify_screening(report: dict, cases: Path, protocol: Path, data_dir: Path) -> None:
    sources = [data_dir / "train.jsonl", data_dir / "val.jsonl",
               ROOT / "eval/challenge.jsonl", ROOT / "eval/challenge_v2.jsonl"]
    if (report.get("pass") is not True or report.get("status") != "screened_not_sealed"
            or report.get("cases_sha256") != sha256_file(cases)
            or report.get("protocol_sha256") != sha256_file(protocol)
            or report.get("embedding_model") != EMBEDDER or report.get("embedding_revision") != REVISION
            or report.get("threshold") != THRESHOLD
            or report.get("screening_code_sha256") != sha256_file(ROOT / "eval/prepare_v3.py")
            or report.get("normalization_code_sha256") != sha256_file(ROOT / "data/audit_overlap_v3.py")):
        raise ValueError("missing or mismatched passing screening evidence")
    recorded = report.get("against_sha256", {})
    if sorted(recorded.values()) != sorted(sha256_file(path) for path in sources):
        raise ValueError("screening was not against the actual training, validation and historical challenges")
    cases_by = index_by_id(load_jsonl(cases), "cases")
    results_by = index_by_id(report["results"], "screening")
    if set(cases_by) != set(results_by) or not all(row.get("pass") is True for row in results_by.values()):
        raise ValueError("screening does not cover every final case")


def verify_candidate(run: Path, adapter: Path, data_dir: Path, prompt: str, versions: dict) -> dict:
    summary = read_json(run / "config.json")
    state = read_json(adapter / "trainer_state.json")
    base = {key: versions["base_model"][key] for key in ("repo_id", "revision")}
    if (summary.get("base_model") != base or summary.get("device") != "cuda"
            or not summary.get("finished_at") or summary.get("final_step") != summary.get("steps", {}).get("max_steps")
            or summary.get("hub", {}).get("pushed") is not False):
        raise ValueError("candidate must come from the completed unpublished pinned-base CUDA run")
    if adapter.resolve().parent != run.resolve() or adapter.name != f"checkpoint-{state['step']}":
        raise ValueError("selected checkpoint must belong to the supplied run")
    if state["step"] > summary["final_step"] or state["step"] < 1:
        raise ValueError("selected checkpoint step is invalid")
    inputs = summary["inputs"]
    if (inputs["base_pin"] != [base["repo_id"], base["revision"]]
            or inputs["files"]["train"] != sha256_file(data_dir / "train.jsonl")
            or inputs["files"]["val"] != sha256_file(data_dir / "val.jsonl")
            or inputs["prompt_sha256"] != hashlib.sha256(prompt.encode()).hexdigest()
            or summary["system_prompt"] != prompt or load_system_prompt(adapter / "prompt.txt") != prompt):
        raise ValueError("selected run data/base/prompt does not match the evaluated experiment")
    if not (adapter / "adapter_model.safetensors").is_file():
        raise ValueError("missing trained adapter weights")
    failures = []
    check_losses(run, failures)
    if failures:
        raise ValueError("candidate loss validation failed: " + "; ".join(failures))
    return summary


def verify_export(export: dict, gguf: Path, adapter: Path, prompt: str, versions: dict) -> None:
    base = {key: versions["base_model"][key] for key in ("repo_id", "revision")}
    if (export.get("schema") != 1 or export.get("base_model") != base
            or export.get("adapter_files_sha256") != artifact_hashes(adapter)
            or export.get("prompt_sha256") != hashlib.sha256(prompt.encode()).hexdigest()
            or export.get("quantization") != "Q8_0"
            or export.get("converter_commit") != versions["llama_cpp_converter"]["commit"]
            or export.get("gguf_sha256") != sha256_file(gguf)
            or export.get("gguf_bytes") != gguf.stat().st_size):
        raise ValueError("tuned export lineage does not match the selected adapter and GGUF")


def ollama_show(tag: str, field: str) -> str:
    return subprocess.check_output(["ollama", "show", tag, f"--{field}"], text=True,
                                   env={**os.environ, "OLLAMA_HOST": "http://127.0.0.1:11434"})


def local_model(tag: str, gguf_hash: str) -> dict:
    # The manifest digest binds template/system/parameters as well as weights.
    # Resolve the actual local GGUF too, so a tag name alone is not provenance.
    digest = ollama_digest("http://127.0.0.1:11434", tag, 30)
    modelfile = ollama_show(tag, "modelfile")
    matches = re.findall(r"^FROM (.+)$", modelfile, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError("cannot resolve local model weight path")
    weight_path = Path(matches[0].strip().strip('"'))
    if not weight_path.is_file() or sha256_file(weight_path) != gguf_hash:
        raise ValueError("Ollama model does not use the selected GGUF")
    if ollama_digest("http://127.0.0.1:11434", tag, 30) != digest:
        raise ValueError("Ollama model changed during identity check")
    return {"tag": tag, "digest": digest}


def checked_generation(runner, tag: str, expected: str, *, resolve=None):
    resolve = resolve or ollama_digest
    def generate(query: str):
        if resolve("http://127.0.0.1:11434", tag, 30) != expected:
            raise ValueError("sealed model identity changed before generation")
        answer = runner(query)
        if resolve("http://127.0.0.1:11434", tag, 30) != expected:
            raise ValueError("sealed model identity changed during generation; answer discarded")
        return answer
    return generate


def create_seal(args):
    if args.output_dir.exists():
        raise ValueError("seal/output directory already exists; never overwrite final evidence")
    versions = read_json(ROOT / "configs/versions.json")
    prompt = load_system_prompt(args.prompt_file)
    audit = read_json(args.screening)
    verify_screening(audit, args.cases, args.protocol, args.data_dir)
    summary = verify_candidate(args.run, args.adapter, args.data_dir, prompt, versions)
    smoke_failures = []
    check_smoke(args.smoke_run, smoke_failures, required=True)
    smoke_summary = read_json(args.smoke_run / "config.json")
    if (smoke_failures or not summary.get("bundle_sha256")
            or smoke_summary.get("bundle_sha256") != summary["bundle_sha256"]
            or smoke_summary.get("device") != "cuda"):
        raise ValueError("passing same-bundle CUDA smoke is required")
    export = read_json(args.export)
    verify_export(export, args.tuned_gguf, args.adapter, prompt, versions)
    # Reuse only the exact historically recorded base, not an arbitrary supplied file.
    base_entries = [r for r in read_json(ROOT / "artifacts/manifest.json")["artifacts"]
                    if r["path"] == "artifacts/base-q8.gguf"]
    base_hash = sha256_file(args.base_gguf)
    if (len(base_entries) != 1 or base_entries[0]["sha256"] != base_hash
            or base_entries[0]["base_revision"] != versions["base_model"]["revision"]
            or base_entries[0]["converter_commit"] != versions["llama_cpp_converter"]["commit"]):
        raise ValueError("base GGUF differs from the recorded pinned-base export")
    models = {"base": local_model(args.base_tag, base_hash),
              "tuned": local_model(args.tuned_tag, export["gguf_sha256"])}
    templates = [ollama_show(models[m]["tag"], "template") for m in ("base", "tuned")]
    parameters = [ollama_show(models[m]["tag"], "parameters") for m in ("base", "tuned")]
    if templates[0] != templates[1] or parameters[0] != parameters[1]:
        raise ValueError("base and tuned Ollama templates/parameters differ")
    selection = args.selection_note.read_text().strip()
    if not selection:
        raise ValueError("development-only checkpoint selection rationale is required")
    manifest = inference_manifest(split_path=args.cases, system_prompt=prompt, model="base",
                                  backend="ollama", identity=models["base"])
    seal = {"schema": 3, "status": "frozen_before_final_inference",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "challenge_sha256": sha256_file(args.cases), "protocol_sha256": sha256_file(args.protocol),
            "metrics_code_sha256": sha256_file(ROOT / "eval/v3_metrics.py"),
            "grading_code_sha256": sha256_file(ROOT / "eval/paired_v3.py"),
            "launcher_sha256": sha256_file(Path(__file__)),
            "models": models, "inference": {field: manifest[field] for field in
              ("backend", "decoding", "prompt_sha256", "runner_sha256", "render_sha256")},
            "system_prompt": prompt, "chat_template": templates[0], "model_parameters": parameters[0],
            "screening_sha256": sha256_file(args.screening), "screening": audit,
            "base_gguf_sha256": base_hash, "tuned_export": export,
            "selected_run_summary": summary, "selected_checkpoint": args.adapter.name,
            "smoke_summary_sha256": sha256_file(args.smoke_run / "config.json"),
            "smoke_report_sha256": sha256_file(args.smoke_run / "smoke.json"),
            "selection_note": selection, "selection_note_sha256": sha256_file(args.selection_note),
            "limitation": "The selection note is an operator record, not independent proof of no prior inspection. Preserve all attempts; never reuse inspected final data for candidate tuning."}
    verify_seal(seal, args.cases, args.protocol)
    args.output_dir.mkdir(parents=True)
    with (args.output_dir / "SEAL.json").open("x") as handle:
        json.dump(seal, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"seal": str(args.output_dir / "SEAL.json"), "status": seal["status"]}))


def generate_pairs(args):
    seal_path = args.output_dir / "SEAL.json"
    seal = read_json(seal_path)
    seal_hash = sha256_file(seal_path)
    cases, _ = verify_seal(seal, args.cases, args.protocol)
    if seal.get("launcher_sha256") != sha256_file(Path(__file__)):
        raise ValueError("final launcher differs from sealed implementation")
    expected_ids = {row["id"] for row in cases}
    for model in ("base", "tuned"):
        identity = seal["models"][model]
        manifest = inference_manifest(split_path=args.cases, system_prompt=seal["system_prompt"],
                                      model=model, backend="ollama", identity=identity)
        manifest["final_seal_sha256"] = seal_hash
        verify_manifest(manifest, seal, model)
        if ollama_digest("http://127.0.0.1:11434", identity["tag"], 30) != identity["digest"]:
            raise ValueError("model no longer matches seal")
        output = args.output_dir / f"{model}-raw.jsonl"
        ensure_run_manifest(output, manifest)
        existing = index_by_id(load_jsonl(output), model) if output.exists() else {}
        if not set(existing) <= expected_ids or any(r.get("model") != model or r.get("tag") != identity["tag"]
                                                   or r.get("final_seal_sha256") != seal_hash
                                                   or r.get("backend") != "ollama" for r in existing.values()):
            raise ValueError("existing final rows have stale IDs or model metadata")
        runner = OllamaRunner(tag=identity["tag"], base_url="http://127.0.0.1:11434",
                              timeout=600, system_prompt=seal["system_prompt"])
        generate = checked_generation(runner, identity["tag"], identity["digest"])
        for case in cases:
            if case["id"] in existing:
                continue
            row = result_row(case, model=model, backend="ollama", tag=identity["tag"], generate=generate)
            row["final_seal_sha256"] = seal_hash
            append_jsonl(output, row)
            print(f"{model} {case['id']} {'FAIL' if row['error'] else 'OK'}", flush=True)
        final = index_by_id(load_jsonl(output), model)
        if set(final) != expected_ids:
            raise ValueError("final generation is incomplete")
    # Error rows are preserved and not automatically retried or discarded.
    failures = {m: [r["id"] for r in load_jsonl(args.output_dir / f"{m}-raw.jsonl") if r.get("error")]
                for m in ("base", "tuned")}
    print(json.dumps({"output_dir": str(args.output_dir), "generation_failure_ids": failures,
                      "next": "Create the blind grading sheet; do not inspect answers for checkpoint reselection."}))
    if any(failures.values()):
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("seal", "generate"):
        child = sub.add_parser(mode)
        child.add_argument("--cases", type=Path, required=True)
        child.add_argument("--protocol", type=Path, default=ROOT / "eval/v3/protocol.json")
        child.add_argument("--output-dir", type=Path, required=True)
        if mode == "seal":
            for name in ("screening", "run", "smoke-run", "adapter", "export", "base-gguf", "tuned-gguf", "selection-note"):
                child.add_argument(f"--{name}", type=Path, required=True)
            child.add_argument("--data-dir", type=Path, default=ROOT / "data/processed/v3-candidate03")
            child.add_argument("--prompt-file", type=Path, default=ROOT / "configs/prompt-v3.txt")
            child.add_argument("--base-tag", required=True)
            child.add_argument("--tuned-tag", required=True)
    args = parser.parse_args()
    (create_seal if args.mode == "seal" else generate_pairs)(args)


if __name__ == "__main__":
    main()
