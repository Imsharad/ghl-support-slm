"""Select a balanced, group-distinct target-curation queue without model scores."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from train.repro import sha256_file

# These phrases are artifacts of historical placeholder substitution. Exclusion
# is deliberately conservative, and applies to this curation queue only.
PLACEHOLDER_ARTIFACT = re.compile(
    r"\b(?:your|my) (?:account type|delivery city|refund amount|order number|invoice number|order status)\b",
    re.I)


def select(rows: list[dict], per_intent: int, seed: int) -> tuple[list[dict], list[str]]:
    if per_intent < 1:
        raise ValueError("per-intent quota must be positive")
    pools = defaultdict(list)
    excluded = []
    for row in rows:
        if PLACEHOLDER_ARTIFACT.search(row["instruction"]):
            excluded.append(row["id"])
        else:
            pools[row["intent"]].append(row)
    selected = []
    for intent in sorted({r["intent"] for r in rows}):
        pool = sorted(pools[intent], key=lambda r: hashlib.sha256(
            f"v3-curation:{seed}:{r['id']}".encode()).hexdigest())
        seen_groups = set()
        for row in pool:
            if row["group_id"] in seen_groups:
                continue
            seen_groups.add(row["group_id"])
            selected.append(row)
            if len(seen_groups) == per_intent:
                break
        if len(seen_groups) != per_intent:
            raise ValueError(f"insufficient distinct groups for {intent}: {len(seen_groups)}")
    return selected, sorted(excluded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--train-per-intent", type=int, default=8)
    parser.add_argument("--val-per-intent", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("refusing to overwrite an existing curation queue")
    manifest = json.loads((args.source_dir / "manifest.json").read_text())
    outputs, audit = {}, {}
    for split, quota in (("train", args.train_per_intent), ("val", args.val_per_intent)):
        path = args.source_dir / f"{split}.jsonl"
        if sha256_file(path) != manifest["output_sha256"][split]:
            raise ValueError(f"candidate source hash mismatch: {split}")
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        selected, excluded = select(rows, quota, args.seed)
        outputs[split] = [{"id": r["id"], "group_id": r["group_id"], "intent": r["intent"],
                           "category": r["category"], "instruction": r["instruction"],
                           "original_response": r["response"], "response": None,
                           "status": "needs_authored_target"} for r in selected]
        audit[split] = {"quota": quota, "selected_ids": [r["id"] for r in selected],
                        "placeholder_excluded_ids": excluded}
    args.output_dir.mkdir(parents=True)
    for split, rows in outputs.items():
        with (args.output_dir / f"{split}.jsonl").open("x") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (args.output_dir / "selection.json").open("x") as handle:
        json.dump({"seed": args.seed, "ready_for_training": False,
                   "source_manifest_sha256": sha256_file(args.source_dir / "manifest.json"),
                   "script_sha256": sha256_file(Path(__file__)), "selection": audit}, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(args.output_dir), "rows": {s: len(r) for s, r in outputs.items()}}))


if __name__ == "__main__":
    main()
