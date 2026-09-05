#!/usr/bin/env python3
"""Check Qwen prompt/tokenizer/output parity between Hugging Face and Ollama."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
VERSIONS_PATH = ROOT / "configs" / "versions.json"
PROMPT_PATH = ROOT / "configs" / "prompt.txt"
DEFAULT_DEV_PATH = ROOT / "eval" / "dev.jsonl"
DEFAULT_GGUF_PATH = ROOT / "artifacts" / "base-q8.gguf"
DEFAULT_OUTPUT_PATH = ROOT / "docs" / "CONVERSION.md"
DEFAULT_TOKENIZER_BIN = ROOT / ".scratch" / "llama.cpp" / "build" / "bin" / "llama-tokenize"
OPTIONS = {
    "temperature": 0,
    "top_p": 1.0,
    "repeat_penalty": 1.0,
    "num_predict": 256,
    "num_ctx": 2048,
    "seed": 42,
}


@dataclass(frozen=True)
class ParityRow:
    item_id: str
    prompt_tokens: int
    tokenizer_match: bool
    answer_tokens: int
    answer_match: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", type=Path, default=DEFAULT_DEV_PATH)
    parser.add_argument("--gguf", type=Path, default=DEFAULT_GGUF_PATH)
    parser.add_argument("--model", default="ghl-base")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--tokenizer-bin", type=Path, default=DEFAULT_TOKENIZER_BIN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--limit", type=int, default=5)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def load_dev(path: Path, limit: int) -> list[dict[str, Any]]:
    if limit < 1:
        raise ValueError("--limit must be at least 1")
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            if "id" not in row or "query" not in row:
                raise ValueError(f"{path}:{line_number} must contain id and query")
            rows.append(row)
            if len(rows) == limit:
                break
    if len(rows) < limit:
        raise ValueError(f"{path} has {len(rows)} usable rows; need {limit}")
    return rows


def ollama_post(base_url: str, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama {endpoint} returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama is not reachable at {base_url}: {exc.reason}") from exc
    if not isinstance(result, dict):
        raise RuntimeError(f"Ollama {endpoint} returned a non-object response")
    return result


def llama_token_ids(binary: Path, gguf: Path, prompt: str) -> list[int]:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as handle:
        handle.write(prompt)
        prompt_path = Path(handle.name)
    try:
        result = subprocess.run(
            [
                str(binary),
                "--model",
                str(gguf),
                "--file",
                str(prompt_path),
                "--ids",
                "--no-bos",
                "--no-escape",
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=60,
        )
    finally:
        prompt_path.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"llama-tokenize failed: {result.stderr.strip()}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"llama-tokenize returned invalid IDs: {result.stdout!r}") from exc
    if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
        raise RuntimeError("llama-tokenize output is not a list of integer IDs")
    return value


def generate_raw(base_url: str, model: str, prompt: str) -> str:
    result = ollama_post(
        base_url,
        "/api/generate",
        {
            "model": model,
            "prompt": prompt,
            "raw": True,
            "stream": False,
            "options": OPTIONS,
        },
    )
    answer = result.get("response")
    if not isinstance(answer, str) or not answer:
        raise RuntimeError("Ollama /api/generate returned an empty answer")
    return answer


def generate_chat(base_url: str, model: str, system: str, query: str) -> str:
    result = ollama_post(
        base_url,
        "/api/chat",
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": query},
            ],
            "stream": False,
            "options": OPTIONS,
        },
    )
    message = result.get("message")
    answer = message.get("content") if isinstance(message, dict) else None
    if not isinstance(answer, str) or not answer:
        raise RuntimeError("Ollama /api/chat returned an empty answer")
    return answer


def markdown_report(
    rows: list[ParityRow],
    *,
    gguf: Path,
    converter_commit: str,
    model_revision: str,
) -> str:
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    all_match = all(row.tokenizer_match and row.answer_match for row in rows)
    lines = [
        "# Base-model GGUF conversion and parity",
        "",
        f"Verified: {now:%Y-%m-%d %H:%M:%S IST}",
        f"Verdict: **{'PASS' if all_match else 'FAIL'}**",
        "",
        "## Artifact",
        "",
        f"- Base model revision: `{model_revision}`",
        f"- llama.cpp converter commit: `{converter_commit}`",
        "- Quantization: `Q8_0`",
        f"- File: `{gguf.relative_to(ROOT)}`",
        f"- Size: {gguf.stat().st_size:,} bytes",
        f"- SHA-256: `{sha256(gguf)}`",
        "",
        "The GGUF was produced by `tools/convert.sh`, which validates the pinned llama.cpp checkout and uses its isolated uv-created converter environment.",
        "",
        "## Five-item parity check",
        "",
        "`tokenizer_match` compares Hugging Face token IDs with the pinned llama.cpp `llama-tokenize` binary for the exact rendered prompt. `answer_match` compares generated token IDs from Ollama `/api/generate` with `raw: true` against Ollama `/api/chat`, both using greedy decoding and the same rendered item.",
        "",
        "| Item | Prompt tokens | Tokenizer IDs | Answer tokens | Raw vs chat |",
        "|---|---:|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.item_id} | {row.prompt_tokens} | "
            f"{'match' if row.tokenizer_match else 'MISMATCH'} | {row.answer_tokens} | "
            f"{'match' if row.answer_match else 'MISMATCH'} |"
        )
    lines.extend(
        [
            "",
            "The Modelfile applies `configs/prompt.txt` once as the system turn and uses the native Qwen2.5 ChatML markers. Ollama remained running after verification for downstream evaluation tasks.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    from train.render import render_prompt

    versions = load_json(VERSIONS_PATH)
    base_model = versions["base_model"]
    converter = versions["llama_cpp_converter"]
    if not isinstance(base_model, dict) or not isinstance(converter, dict):
        raise ValueError("configs/versions.json has invalid model or converter entries")

    for path, label in (
        (args.gguf, "GGUF"),
        (args.tokenizer_bin, "llama-tokenize binary"),
        (args.dev, "development set"),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"{label} not found: {path}")

    repo_id = str(base_model["repo_id"])
    revision = str(base_model["revision"])
    tokenizer = AutoTokenizer.from_pretrained(repo_id, revision=revision, local_files_only=True)
    system = PROMPT_PATH.read_text(encoding="utf-8").strip()
    dev_rows = load_dev(args.dev, args.limit)

    parity_rows: list[ParityRow] = []
    for dev_row in dev_rows:
        item_id = str(dev_row["id"])
        query = str(dev_row["query"])
        prompt = render_prompt(query)
        hf_prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
        gguf_prompt_ids = llama_token_ids(args.tokenizer_bin, args.gguf, prompt)

        raw_answer = generate_raw(args.ollama_url, args.model, prompt)
        chat_answer = generate_chat(args.ollama_url, args.model, system, query)
        raw_answer_ids = tokenizer.encode(raw_answer, add_special_tokens=False)
        chat_answer_ids = tokenizer.encode(chat_answer, add_special_tokens=False)

        parity_rows.append(
            ParityRow(
                item_id=item_id,
                prompt_tokens=len(hf_prompt_ids),
                tokenizer_match=hf_prompt_ids == gguf_prompt_ids,
                answer_tokens=len(raw_answer_ids),
                answer_match=raw_answer_ids == chat_answer_ids,
            )
        )

    report = markdown_report(
        parity_rows,
        gguf=args.gguf.resolve(),
        converter_commit=str(converter["commit"]),
        model_revision=revision,
    )
    args.output.write_text(report, encoding="utf-8")
    print(report)
    return 0 if all(row.tokenizer_match and row.answer_match for row in parity_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
