#!/usr/bin/env python3
"""Live side-by-side demo: base vs tuned on two challenge queries and one policy probe.

No arguments. Reads sealed eval/challenge.jsonl (ch-017, ch-025, ch-014), calls
Ollama tags ghl-base and ghl-support, then prints the headline row from
eval/results/summary.jsonl and the ch-017 failure from docs/FAILURES.md.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from serve.inference import (  # noqa: E402
    DEFAULT_OLLAMA_URL,
    InferenceResult,
    infer_ollama,
    load_system_prompt,
)

CHALLENGE_PATH = ROOT / "eval" / "challenge.jsonl"
SUMMARY_PATH = ROOT / "eval" / "results" / "summary.jsonl"
FAILURES_PATH = ROOT / "docs" / "FAILURES.md"
BASE_TAG = "ghl-base"
TUNED_TAG = "ghl-support"
# Two assignment demo queries, then one policy probe, all from the sealed set.
DEMO_IDS = ("ch-017", "ch-025", "ch-014")
POLICY_PROBE_ID = "ch-014"
FAILURE_ID = "ch-017"
RULE = "=" * 78
THIN = "-" * 78


def load_challenge_items(path: Path, ids: tuple[str, ...]) -> list[dict[str, Any]]:
    wanted = set(ids)
    found: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise RuntimeError(f"{path}:{line_number} is not a JSON object")
            item_id = row.get("id")
            if item_id in wanted:
                found[item_id] = row
            if len(found) == len(wanted):
                break
    missing = [item_id for item_id in ids if item_id not in found]
    if missing:
        raise RuntimeError(f"{path} is missing sealed items: {', '.join(missing)}")
    return [found[item_id] for item_id in ids]


def load_summary(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError(f"summary is empty: {path}")
    row = json.loads(text.splitlines()[0])
    if not isinstance(row, dict):
        raise RuntimeError(f"{path} first line is not a JSON object")
    return row


def extract_failure(path: Path, item_id: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()

    def is_h2(line: str) -> bool:
        return line.startswith("## ") and not line.startswith("###")

    start: int | None = None
    for index, line in enumerate(lines):
        if is_h2(line) and item_id in line:
            start = index
            break
    if start is None:
        raise RuntimeError(f"{path} has no heading for {item_id}")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if is_h2(lines[index]):
            end = index
            break
    block = "\n".join(lines[start:end]).strip()
    if not block:
        raise RuntimeError(f"{path} heading for {item_id} is empty")
    return block


def get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"request to {url} returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"request to {url} failed: {exc.reason}") from exc
    if not isinstance(result, dict):
        raise RuntimeError(f"request to {url} returned a non-object response")
    return result


def require_tags(base_url: str, tags: tuple[str, ...]) -> None:
    payload = get_json(f"{base_url.rstrip('/')}/api/tags")
    models = payload.get("models")
    names: set[str] = set()
    if isinstance(models, list):
        for model in models:
            if not isinstance(model, dict):
                continue
            raw = model.get("name")
            if isinstance(raw, str) and raw:
                names.add(raw.split(":", 1)[0])
    missing = [tag for tag in tags if tag not in names]
    if missing:
        raise RuntimeError(
            "Ollama is missing tags: "
            + ", ".join(missing)
            + ". Create them with serve/Modelfile.base and serve/Modelfile."
        )


def fmt_ci(bounds: Any) -> str:
    if not (isinstance(bounds, list) and len(bounds) == 2):
        raise RuntimeError("summary ci95 must be a two-element list")
    lo, hi = bounds

    def one(value: Any) -> str:
        number = float(value)
        if abs(number) < 1e-12:
            return "+0.0"
        return f"{number:.1f}"

    return f"[{one(lo)}, {one(hi)}]"


def pass_line(rate: Any, n: Any) -> str:
    count_n = int(n)
    count = int(round(float(rate) * count_n))
    return f"{count}/{count_n} = {100.0 * float(rate):.1f}%"


def print_header() -> None:
    prompt = load_system_prompt()
    print(RULE)
    print("GHL support demo")
    print(f"backend: ollama  {DEFAULT_OLLAMA_URL}")
    print(f"tags:    {BASE_TAG} vs {TUNED_TAG}")
    print("decode:  temperature 0, top_p 1, max_tokens 256, seed 42")
    print(f"system:  {prompt}")
    print(RULE)
    sys.stdout.flush()


def print_result(tag: str, result: InferenceResult) -> None:
    print(THIN)
    print(f"{tag}  {result.latency_ms:.1f} ms  gen_tokens={result.generated_tokens}")
    print(THIN)
    print(result.answer)
    print()
    sys.stdout.flush()


def run_pair(item: dict[str, Any]) -> None:
    item_id = item["id"]
    intent = item.get("intent", "")
    kind = item.get("kind", "")
    query = item["query"]
    role = "policy probe" if item_id == POLICY_PROBE_ID else "demo query"
    print(RULE)
    print(f"{item_id}  {intent}  {kind}  ({role})")
    print(f"Query: {query}")
    print(RULE)
    sys.stdout.flush()
    for tag in (BASE_TAG, TUNED_TAG):
        result = infer_ollama(query, model=tag, base_url=DEFAULT_OLLAMA_URL)
        print_result(tag, result)


def print_headline(row: dict[str, Any]) -> None:
    n = row["n"]
    print(RULE)
    print("HEADLINE  eval/results/summary.jsonl")
    print(RULE)
    print(f"verdict:    {row['verdict']}")
    print(f"n:          {n}")
    print(f"base pass:  {pass_line(row['base_pass_rate'], n)}")
    print(f"tuned pass: {pass_line(row['tuned_pass_rate'], n)}")
    print(f"diff:       {float(row['diff_points']):.1f} points")
    print(f"ci95:       {fmt_ci(row['ci95'])}")
    print(f"criticals:  base {row['base_critical']}  tuned {row['tuned_critical']}")
    print(
        "preferred:  "
        f"tuned {row['win']} / tie {row['tie']} / base {row['loss']}"
    )
    print()
    sys.stdout.flush()


def print_failure(block: str) -> None:
    print(RULE)
    print(f"FAILURE (Loom pick)  docs/FAILURES.md  {FAILURE_ID}")
    print(RULE)
    print(block)
    print()
    sys.stdout.flush()


def main() -> int:
    require_tags(DEFAULT_OLLAMA_URL, (BASE_TAG, TUNED_TAG))
    items = load_challenge_items(CHALLENGE_PATH, DEMO_IDS)
    summary = load_summary(SUMMARY_PATH)
    failure = extract_failure(FAILURES_PATH, FAILURE_ID)
    print_header()
    for item in items:
        run_pair(item)
    print_headline(summary)
    print_failure(failure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
