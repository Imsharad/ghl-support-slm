#!/usr/bin/env python3
"""Run resumable deterministic evaluation through Ollama or Transformers."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import yaml

from eval.blind import sealed_hash
from train.render import PROMPT_PATH, SYSTEM_PROMPT, load_system_prompt, render_prompt
from train.repro import sha256_file


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "eval.yaml"
VERSIONS_PATH = ROOT / "configs" / "versions.json"
RESULTS_DIR = ROOT / "eval" / "results"
CHALLENGE_PATH = ROOT / "eval" / "challenge.jsonl"
SEAL_PATH = ROOT / "eval" / "SEAL.json"
SPLIT_PATHS = {
    "dev": ROOT / "eval" / "dev.jsonl",
    "challenge": CHALLENGE_PATH,
    "test": ROOT / "data" / "processed" / "test.jsonl",
}
MAX_NEW_TOKENS = 256
NUM_CTX = 2048
IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class Generation:
    answer: str
    prompt_tokens: int | None
    gen_tokens: int | None
    latency_ms: float
    tokens_per_s: float | None
    truncated: bool
    device: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=("base", "tuned"))
    parser.add_argument("--backend", required=True, choices=("ollama", "transformers"))
    parser.add_argument("--split", required=True, choices=tuple(SPLIT_PATHS))
    parser.add_argument("--input", type=Path, help="Custom development input; requires --split dev")
    parser.add_argument("--challenge", type=Path, default=CHALLENGE_PATH)
    parser.add_argument("--seal", type=Path, default=SEAL_PATH)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--check-complete", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prompt-file", type=Path, help="Exact system prompt for both models")
    parser.add_argument("--tag", help="Explicit Ollama model tag; recorded with its digest")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--device", choices=("auto", "cpu", "mps", "cuda"), default="auto")
    parser.add_argument(
        "--adapter",
        type=Path,
        default=None,
        help="PEFT adapter directory. transformers backend only; loads the pinned base.",
    )
    return parser.parse_args()


def adapter_weights_sha256(adapter_dir: Path) -> str:
    weights = adapter_dir / "adapter_model.safetensors"
    if not weights.is_file():
        raise FileNotFoundError(f"adapter_model.safetensors not found in {adapter_dir}")
    digest = hashlib.sha256()
    with weights.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def validate_run_args(*, backend: str, model: str, adapter: Path | None) -> Path | None:
    if adapter is None:
        return None
    if backend != "transformers":
        raise ValueError("--adapter requires --backend transformers")
    if model != "tuned":
        raise ValueError("--adapter requires --model tuned")
    adapter_dir = adapter.expanduser().resolve()
    if not adapter_dir.is_dir():
        raise FileNotFoundError(f"adapter directory not found: {adapter_dir}")
    if not (adapter_dir / "adapter_config.json").is_file():
        raise FileNotFoundError(f"adapter_config.json not found in {adapter_dir}")
    if not (adapter_dir / "adapter_model.safetensors").is_file():
        raise FileNotFoundError(f"adapter_model.safetensors not found in {adapter_dir}")
    return adapter_dir


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            item_id = value.get("id")
            if not isinstance(item_id, str) or not item_id:
                raise ValueError(f"{path}:{line_number}: missing string id")
            if item_id in seen:
                raise ValueError(f"{path}:{line_number}: duplicate id {item_id}")
            seen.add(item_id)
            rows.append(value)
    return rows


def query_for(row: dict[str, Any]) -> str:
    query = row.get("query", row.get("instruction"))
    if not isinstance(query, str) or not query.strip():
        raise ValueError(f"split item {row.get('id')!r} has no query or instruction")
    return query.strip()


def load_config() -> dict[str, Any]:
    value = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected an object in {CONFIG_PATH}")
    return value


def ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama request failed: {exc.reason}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Ollama returned a non-object response")
    return value


class OllamaRunner:
    def __init__(self, *, tag: str, base_url: str, timeout: float,
                 system_prompt: str | None = None) -> None:
        self.tag = tag
        self.url = f"{base_url.rstrip('/')}/api/chat"
        self.timeout = timeout
        self.system_prompt = system_prompt

    def __call__(self, query: str) -> Generation:
        system = self.system_prompt if self.system_prompt is not None else (
            ROOT / "configs" / "prompt.txt").read_text(encoding="utf-8").removesuffix("\n")
        payload = {
            "model": self.tag,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": query},
            ],
            "stream": False,
            "options": {
                "temperature": 0,
                "top_p": 1.0,
                "repeat_penalty": 1.0,
                "num_predict": MAX_NEW_TOKENS,
                "num_ctx": NUM_CTX,
                "seed": 42,
            },
        }
        started = time.perf_counter()
        value = post_json(self.url, payload, self.timeout)
        latency_ms = (time.perf_counter() - started) * 1000
        message = value.get("message")
        answer = message.get("content") if isinstance(message, dict) else None
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("Ollama returned an empty answer")
        prompt_tokens = optional_int(value.get("prompt_eval_count"))
        gen_tokens = optional_int(value.get("eval_count"))
        eval_duration = value.get("eval_duration")
        tokens_per_s = None
        if gen_tokens is not None and isinstance(eval_duration, int) and eval_duration > 0:
            tokens_per_s = gen_tokens / (eval_duration / 1_000_000_000)
        truncated = value.get("done_reason") == "length" or (
            gen_tokens is not None and gen_tokens >= MAX_NEW_TOKENS
        )
        return Generation(
            answer=answer.strip(),
            prompt_tokens=prompt_tokens,
            gen_tokens=gen_tokens,
            latency_ms=latency_ms,
            tokens_per_s=tokens_per_s,
            truncated=truncated,
        )


def optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class TransformersRunner:
    """Load the selected fp16 source once, then serve serial eval queries."""

    def __init__(
        self,
        *,
        model: str,
        requested_device: str,
        adapter_dir: Path | None = None,
        system_prompt: str | None = None,
    ) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        versions = load_json(VERSIONS_PATH)
        base = versions.get("base_model")
        if not isinstance(base, dict):
            raise ValueError("configs/versions.json has no base_model object")
        repo_id = str(base["repo_id"])
        revision = str(base["revision"])
        self.system_prompt = SYSTEM_PROMPT if system_prompt is None else system_prompt

        common: dict[str, Any] = {"local_files_only": True, "dtype": "auto"}
        if adapter_dir is not None:
            from peft import PeftModel

            tokenizer_source: str | Path = adapter_dir
            tokenizer_kwargs: dict[str, Any] = {"local_files_only": True}
            if not (
                (adapter_dir / "tokenizer_config.json").is_file()
                or (adapter_dir / "tokenizer.json").is_file()
            ):
                tokenizer_source = repo_id
                tokenizer_kwargs["revision"] = revision
            self.tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_source, **tokenizer_kwargs
            )
            prompt_file = adapter_dir / "prompt.txt"
            if prompt_file.is_file() and system_prompt is None:
                self.system_prompt = prompt_file.read_text(encoding="utf-8").removesuffix(
                    "\n"
                )
            self.device = self._select_device(requested_device, torch)
            self.model = AutoModelForCausalLM.from_pretrained(
                repo_id,
                revision=revision,
                local_files_only=True,
                dtype="auto",
            )
            self.model = PeftModel.from_pretrained(
                self.model, str(adapter_dir), is_trainable=False
            )
        elif model == "base":
            self.tokenizer = AutoTokenizer.from_pretrained(
                repo_id, revision=revision, local_files_only=True
            )
            self.device = self._select_device(requested_device, torch)
            self.model = AutoModelForCausalLM.from_pretrained(
                repo_id, revision=revision, **common
            )
        else:
            source = ROOT / "artifacts" / "merged"
            if not (source / "config.json").is_file():
                raise FileNotFoundError(f"tuned merged model not found: {source}")
            self.tokenizer = AutoTokenizer.from_pretrained(source, local_files_only=True)
            self.device = self._select_device(requested_device, torch)
            self.model = AutoModelForCausalLM.from_pretrained(source, **common)

        self.model.to(self.device)
        self.model.eval()
        self.torch = torch

        end_id = self.tokenizer.convert_tokens_to_ids("<|im_end|>")
        self.eos_ids = [self.tokenizer.eos_token_id]
        if isinstance(end_id, int) and end_id >= 0 and end_id not in self.eos_ids:
            self.eos_ids.append(end_id)

    def _render_prompt(self, instruction: str) -> str:
        if self.system_prompt == SYSTEM_PROMPT:
            return render_prompt(instruction, self.tokenizer)
        rendered = self.tokenizer.apply_chat_template(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": instruction},
            ],
            tokenize=False,
            add_generation_prompt=True,
        )
        if not isinstance(rendered, str):
            raise TypeError("tokenizer.apply_chat_template did not return text")
        return rendered

    @staticmethod
    def _select_device(requested: str, torch_module: Any) -> str:
        if requested == "cuda" and not torch_module.cuda.is_available():
            raise RuntimeError("CUDA was requested but is not available")
        if requested == "mps" and not torch_module.backends.mps.is_available():
            raise RuntimeError("MPS was requested but is not available")
        if requested != "auto":
            return requested
        if torch_module.cuda.is_available():
            return "cuda"
        if torch_module.backends.mps.is_available():
            return "mps"
        return "cpu"

    def __call__(self, query: str) -> Generation:
        prompt = self._render_prompt(query)
        encoded = self.tokenizer(
            prompt,
            return_tensors="pt",
            add_special_tokens=False,
            truncation=True,
            max_length=NUM_CTX - MAX_NEW_TOKENS,
        )
        inputs = {name: tensor.to(self.device) for name, tensor in encoded.items()}
        prompt_tokens = int(inputs["input_ids"].shape[-1])
        self.torch.manual_seed(42)
        if self.device == "cuda":
            self.torch.cuda.manual_seed_all(42)
        started = time.perf_counter()
        with self.torch.inference_mode():
            output = self.model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=MAX_NEW_TOKENS,
                repetition_penalty=1.0,
                eos_token_id=self.eos_ids,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        latency_ms = (time.perf_counter() - started) * 1000
        generated = output[0, prompt_tokens:]
        gen_tokens = int(generated.shape[-1])
        answer = self.tokenizer.decode(generated, skip_special_tokens=True).strip()
        if not answer:
            raise RuntimeError("Transformers returned an empty answer")
        final_id = int(generated[-1]) if gen_tokens else None
        truncated = gen_tokens >= MAX_NEW_TOKENS and final_id not in self.eos_ids
        return Generation(
            answer=answer,
            prompt_tokens=prompt_tokens,
            gen_tokens=gen_tokens,
            latency_ms=latency_ms,
            tokens_per_s=gen_tokens / (latency_ms / 1000) if latency_ms > 0 else None,
            truncated=truncated,
            device=self.device,
        )


def load_existing(
    path: Path,
    *,
    model: str,
    backend: str,
    all_ids: set[str],
    adapter_sha256: str | None = None,
) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = load_jsonl(path)
    by_id: dict[str, dict] = {}
    for row in rows:
        item_id = str(row["id"])
        if item_id not in all_ids:
            raise ValueError(f"existing output has stale id {item_id}: {path}")
        if row.get("model") != model or row.get("backend") != backend:
            raise ValueError(f"existing output metadata mismatch for {item_id}: {path}")
        if adapter_sha256 is not None and row.get("adapter_sha256") != adapter_sha256:
            raise ValueError(
                f"existing output adapter hash mismatch for {item_id}: {path}"
            )
        by_id[item_id] = row
    return by_id


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def ensure_run_manifest(output: Path, manifest: dict[str, Any]) -> None:
    """Never combine outputs made with different data, prompts, or model weights."""
    path = output.with_suffix(output.suffix + ".manifest.json")
    if path.exists():
        if load_json(path) != manifest:
            raise ValueError("evaluation manifest mismatch; choose a new output path")
        return
    if output.exists() and output.stat().st_size:
        raise ValueError("existing evaluation has no manifest; preserve it and use a new output path")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")


def ollama_digest(base_url: str, tag: str, timeout: float) -> str:
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=timeout) as response:
        models = json.load(response).get("models", [])
    matches = [m for m in models if tag in (m.get("name"), m.get("model"))
               or (":" not in tag and m.get("name") == tag + ":latest")]
    if len(matches) != 1 or not matches[0].get("digest"):
        raise ValueError(f"cannot resolve a unique local Ollama digest for {tag}")
    return str(matches[0]["digest"])


def inference_manifest(*, split_path: Path, system_prompt: str, model: str,
                       backend: str, identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": 1, "split_sha256": sha256_file(split_path),
        "system_prompt": system_prompt,
        "prompt_sha256": hashlib.sha256(system_prompt.encode()).hexdigest(),
        "model": model, "backend": backend, "identity": identity,
        "decoding": {"temperature": 0, "top_p": 1.0, "repeat_penalty": 1.0,
                     "seed": 42, "max_new_tokens": MAX_NEW_TOKENS, "num_ctx": NUM_CTX},
        "runner_sha256": sha256_file(Path(__file__)),
        "render_sha256": sha256_file(ROOT / "train/render.py"),
    }


def result_row(
    item: dict[str, Any],
    *,
    model: str,
    backend: str,
    tag: str,
    generate: Callable[[str], Generation],
    adapter_dir: Path | None = None,
    adapter_sha256: str | None = None,
) -> dict[str, Any]:
    item_id = str(item["id"])
    started = time.perf_counter()
    extra: dict[str, Any] = {}
    if adapter_dir is not None:
        extra["adapter_dir"] = str(adapter_dir)
        extra["adapter_sha256"] = adapter_sha256
    try:
        generated = generate(query_for(item))
        return {
            "id": item_id,
            "model": model,
            "backend": backend,
            "tag": tag,
            "answer": generated.answer,
            "prompt_tokens": generated.prompt_tokens,
            "gen_tokens": generated.gen_tokens,
            "latency_ms": round(generated.latency_ms, 3),
            "tokens_per_s": (
                round(generated.tokens_per_s, 3)
                if generated.tokens_per_s is not None
                else None
            ),
            "truncated": generated.truncated,
            "error": None,
            "ts": ist_now(),
            **extra,
        }
    except Exception as exc:
        return {
            "id": item_id,
            "model": model,
            "backend": backend,
            "tag": tag,
            "answer": "",
            "prompt_tokens": None,
            "gen_tokens": 0,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "tokens_per_s": 0.0,
            "truncated": False,
            "error": f"{type(exc).__name__}: {exc}",
            "ts": ist_now(),
            **extra,
        }


def assert_complete(expected_ids: set[str], output_rows: list[dict[str, Any]]) -> None:
    actual_ids = {str(row.get("id")) for row in output_rows}
    missing = sorted(expected_ids - actual_ids)
    if missing:
        raise ValueError(f"missing output ids: {missing}")


def split_path_for(*, split: str, challenge: Path, seal: Path) -> Path:
    """Resolve the requested split and verify a challenge against its seal."""
    if split != "challenge":
        return SPLIT_PATHS[split]
    sealed_hash(seal, challenge)
    return challenge


def main() -> int:
    args = parse_args()
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be at least 1")
    adapter_dir = validate_run_args(
        backend=args.backend, model=args.model, adapter=args.adapter
    )
    adapter_sha = adapter_weights_sha256(adapter_dir) if adapter_dir is not None else None
    config = load_config()
    split_path = split_path_for(
        split=args.split,
        challenge=args.challenge,
        seal=args.seal,
    )
    if args.input:
        if args.split != "dev":
            raise ValueError("--input is for development only; final challenges require --challenge and --seal")
        split_path = args.input
    all_items = load_jsonl(split_path)
    selected = all_items[: args.limit] if args.limit is not None else all_items
    if not selected:
        raise ValueError(f"split {args.split} has no items")

    try:
        tag = str(config["models"][args.model]["tag"])
        base_url = str(config["backends"]["ollama"]["base_url"])
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid model/backend config in {CONFIG_PATH}: {exc}") from exc
    output = args.output or RESULTS_DIR / f"{args.model}-{args.split}-raw.jsonl"
    if args.tag:
        if args.backend != "ollama":
            raise ValueError("--tag is only supported for Ollama")
        tag = args.tag
    prompt_path = args.prompt_file or (
        adapter_dir / "prompt.txt" if adapter_dir and (adapter_dir / "prompt.txt").is_file()
        else PROMPT_PATH)
    system_prompt = load_system_prompt(prompt_path)
    if args.backend == "ollama":
        identity = {"tag": tag, "digest": ollama_digest(base_url, tag, args.timeout)}
    else:
        identity = {"base": load_json(VERSIONS_PATH)["base_model"],
                    "requested_device": args.device}
        artifact_dir = adapter_dir or (ROOT / "artifacts/merged" if args.model == "tuned" else None)
        if artifact_dir:
            identity["artifact_files"] = {
                str(p.relative_to(artifact_dir)): sha256_file(p)
                for p in sorted(artifact_dir.rglob("*")) if p.is_file() and p.name != "state.pt"}
    ensure_run_manifest(output, inference_manifest(
        split_path=split_path, system_prompt=system_prompt, model=args.model,
        backend=args.backend, identity=identity))
    existing = load_existing(
        output,
        model=args.model,
        backend=args.backend,
        all_ids={str(item["id"]) for item in all_items},
        adapter_sha256=adapter_sha,
    )
    if args.backend == "ollama":
        generate: Callable[[str], Generation] = OllamaRunner(
            tag=tag,
            base_url=base_url,
            timeout=args.timeout,
            system_prompt=system_prompt,
        )
    else:
        generate = TransformersRunner(
            model=args.model,
            requested_device=args.device,
            adapter_dir=adapter_dir,
            system_prompt=system_prompt,
        )

    written = 0
    for index, item in enumerate(selected, 1):
        item_id = str(item["id"])
        if item_id in existing:
            print(f"SKIP {item_id} already present")
            continue
        row = result_row(
            item,
            model=args.model,
            backend=args.backend,
            tag=tag,
            generate=generate,
            adapter_dir=adapter_dir,
            adapter_sha256=adapter_sha,
        )
        append_jsonl(output, row)
        existing[item_id] = row
        written += 1
        status = "FAIL" if row["error"] else "OK"
        print(f"{index}/{len(selected)} {item_id} {status}")

    output_rows = load_jsonl(output)
    expected_ids = {str(item["id"]) for item in selected}
    if args.check_complete:
        try:
            assert_complete(expected_ids, output_rows)
        except ValueError as exc:
            print(f"CHECK FAIL: {exc}")
            return 1
    failures = sum(1 for row in output_rows if row.get("id") in expected_ids and row.get("error"))
    print(
        f"wrote={written} present={len(expected_ids)} failures={failures} "
        f"output={output.relative_to(ROOT) if output.is_relative_to(ROOT) else output}"
    )
    if args.check_complete:
        print("CHECK PASS" if not failures else "CHECK FAIL: generation errors remain")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
