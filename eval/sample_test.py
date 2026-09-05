#!/usr/bin/env python3
"""Draw the fixed 270-row Bitext test sample used for the base/tuned comparison.

The rule is intent balance first, group diversity always:

  1. Every sampled row comes from a distinct similarity group. `auto_metrics.py`
     resamples groups, not rows, for its confidence interval, so one row per group
     keeps the bootstrap clusters independent and the interval honest.
  2. Take up to 10 rows per intent, each from a different group.
  3. Five intents do not have 10 distinct groups in the test split, so step 2 yields
     250 rows. Backfill the remaining 20 round-robin over the intents that still have
     unused groups, richest first, so the top-up spreads instead of landing on one intent.

Deterministic: seeded shuffles over sorted keys only.

Usage:
    uv run python eval/sample_test.py
    uv run python eval/sample_test.py --check    # verify the committed files still match
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = ROOT / "data" / "processed" / "test.jsonl"
SPLITS_PATH = ROOT / "data" / "splits.json"
SAMPLE_JSON = ROOT / "eval" / "results" / "test-sample.json"
REFS_JSONL = ROOT / "eval" / "results" / "test-sample-refs.jsonl"
IST = ZoneInfo("Asia/Kolkata")

TARGET = 270
PER_INTENT = 10
SEED = 42


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def choose(rows: list[dict[str, Any]], seed: int = SEED) -> tuple[list[str], dict[str, Any]]:
    """Return the sampled ids (sorted) and a record of how they were chosen."""
    by_intent: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_intent[str(row["intent"])][str(row["group_id"])].append(row)

    rng = random.Random(seed)
    picked: dict[str, str] = {}          # id -> intent
    used_groups: set[str] = set()
    per_intent: dict[str, int] = {}
    remaining: dict[str, list[str]] = {}

    for intent in sorted(by_intent):
        groups = sorted(by_intent[intent])
        rng.shuffle(groups)
        take, spare = groups[:PER_INTENT], groups[PER_INTENT:]
        for group in take:
            candidates = sorted(by_intent[intent][group], key=lambda r: str(r["id"]))
            row = candidates[rng.randrange(len(candidates))]
            picked[str(row["id"])] = intent
            used_groups.add(group)
        per_intent[intent] = len(take)
        remaining[intent] = spare

    base_count = len(picked)

    # Backfill: round-robin over intents with unused groups, richest first, until TARGET.
    topped_up: dict[str, int] = defaultdict(int)
    while len(picked) < TARGET:
        order = sorted(remaining, key=lambda i: (-len(remaining[i]), i))
        order = [i for i in order if remaining[i]]
        if not order:
            raise RuntimeError(
                f"cannot reach {TARGET} distinct groups: only {len(picked)} available"
            )
        for intent in order:
            if len(picked) >= TARGET:
                break
            group = remaining[intent].pop(0)
            if group in used_groups:
                continue
            candidates = sorted(by_intent[intent][group], key=lambda r: str(r["id"]))
            row = candidates[rng.randrange(len(candidates))]
            picked[str(row["id"])] = intent
            used_groups.add(group)
            per_intent[intent] += 1
            topped_up[intent] += 1

    ids = sorted(picked)
    record = {
        "seed": seed,
        "target": TARGET,
        "per_intent_cap": PER_INTENT,
        "rule": (
            "one row per distinct group; up to 10 rows per intent; "
            "deficit backfilled round-robin over intents with unused groups, richest first"
        ),
        "n": len(ids),
        "n_groups": len(used_groups),
        "n_intents": len(per_intent),
        "from_per_intent_cap": base_count,
        "backfilled": sum(topped_up.values()),
        "backfilled_by_intent": dict(sorted(topped_up.items())),
        "rows_per_intent": dict(sorted(per_intent.items())),
        "source": "data/processed/test.jsonl",
        "source_sha256": json.loads(SPLITS_PATH.read_text(encoding="utf-8"))["test"]["sha256"],
        "ids": ids,
    }
    return ids, record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="recompute and compare against the files on disk; do not write",
    )
    args = parser.parse_args()

    rows = load_jsonl(TEST_PATH)
    ids, record = choose(rows)
    by_id = {str(row["id"]): row for row in rows}

    if args.check:
        if not SAMPLE_JSON.is_file():
            print(f"FAIL: missing {SAMPLE_JSON}")
            return 1
        on_disk = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
        if on_disk.get("ids") != ids:
            print("FAIL: recomputed ids differ from test-sample.json")
            return 1
        refs = [str(r["id"]) for r in load_jsonl(REFS_JSONL)]
        if sorted(refs) != ids:
            print("FAIL: test-sample-refs.jsonl ids differ from the sample")
            return 1
        print(f"CHECK PASS: {len(ids)} ids reproduce, refs match")
        return 0

    record["written_at"] = ist_now()
    SAMPLE_JSON.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE_JSON.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    with REFS_JSONL.open("w", encoding="utf-8") as handle:
        for item_id in ids:
            handle.write(json.dumps(by_id[item_id], ensure_ascii=False) + "\n")

    print(f"wrote {SAMPLE_JSON.relative_to(ROOT)} and {REFS_JSONL.relative_to(ROOT)}")
    print(
        f"{record['n']} rows, {record['n_groups']} distinct groups, "
        f"{record['n_intents']} intents, {record['backfilled']} backfilled"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
