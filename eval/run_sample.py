#!/usr/bin/env python3
"""Generate answers for an explicit list of ids, not a whole split.

`eval/run.py --limit N` takes the first N rows of a split, so it cannot produce the
270-row stratified test sample. This wraps the same machinery for an id list: the
generation path, the row shape, the resume-by-id behaviour and the completeness check
are `eval/run.py`'s, imported rather than copied, so the two outputs stay comparable.

Usage:
    # timing probe, first 10 sampled rows
    uv run python eval/run_sample.py --model tuned --backend transformers \
        --adapter train/runs/local-t4/checkpoint-500 --device mps --limit 10 \
        --output eval/results/tuned-test-raw.jsonl

    # full 270
    uv run python eval/run_sample.py --model tuned --backend transformers \
        --adapter train/runs/local-t4/checkpoint-500 --device mps --check-complete \
        --output eval/results/tuned-test-raw.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.run import (  # noqa: E402
    Generation,
    OllamaRunner,
    TransformersRunner,
    adapter_weights_sha256,
    append_jsonl,
    assert_complete,
    load_config,
    load_existing,
    load_jsonl,
    result_row,
    validate_run_args,
)

TEST_PATH = ROOT / "data" / "processed" / "test.jsonl"
SAMPLE_JSON = ROOT / "eval" / "results" / "test-sample.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=("base", "tuned"))
    parser.add_argument("--backend", required=True, choices=("ollama", "transformers"))
    parser.add_argument("--ids", type=Path, default=SAMPLE_JSON, help="json with an 'ids' list")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit", type=int, help="only the first N sampled ids, for timing")
    parser.add_argument("--check-complete", action="store_true")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--device", choices=("auto", "cpu", "mps", "cuda"), default="auto")
    parser.add_argument("--adapter", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be at least 1")

    adapter_dir = validate_run_args(
        backend=args.backend, model=args.model, adapter=args.adapter
    )
    adapter_sha = adapter_weights_sha256(adapter_dir) if adapter_dir is not None else None

    wanted = list(json.loads(args.ids.read_text(encoding="utf-8"))["ids"])
    by_id = {str(row["id"]): row for row in load_jsonl(TEST_PATH)}
    missing = [i for i in wanted if i not in by_id]
    if missing:
        raise ValueError(f"ids not present in {TEST_PATH}: {missing[:5]}")

    items = [by_id[i] for i in wanted]
    selected = items[: args.limit] if args.limit is not None else items

    config = load_config()
    tag = str(config["models"][args.model]["tag"])
    base_url = str(config["backends"]["ollama"]["base_url"])

    output = args.output if args.output.is_absolute() else ROOT / args.output
    existing = load_existing(
        output,
        model=args.model,
        backend=args.backend,
        all_ids=set(wanted),
        adapter_sha256=adapter_sha,
    )

    generate: Callable[[str], Generation]
    if args.backend == "ollama":
        generate = OllamaRunner(tag=tag, base_url=base_url, timeout=args.timeout)
    else:
        generate = TransformersRunner(
            model=args.model, requested_device=args.device, adapter_dir=adapter_dir
        )

    written = 0
    for index, item in enumerate(selected, 1):
        item_id = str(item["id"])
        if item_id in existing:
            print(f"SKIP {item_id} already present")
            continue
        row: dict[str, Any] = result_row(
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
        print(f"{index}/{len(selected)} {item_id} {status} {row['latency_ms']:.0f} ms", flush=True)

    output_rows = load_jsonl(output)
    expected_ids = {str(item["id"]) for item in selected}
    if args.check_complete:
        try:
            assert_complete(expected_ids, output_rows)
        except ValueError as exc:
            print(f"CHECK FAIL: {exc}")
            return 1
    failures = sum(
        1 for row in output_rows if row.get("id") in expected_ids and row.get("error")
    )
    print(f"wrote={written} present={len(expected_ids)} failures={failures} output={output}")
    if args.check_complete:
        print("CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
