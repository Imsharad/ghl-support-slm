"""Build an audited Bitext-only candidate pool, NOT an approved training corpus.

Historical responses are preserved verbatim for target-quality review. Historical
validation/test pools remain diagnostics; neither is a fresh final evaluation.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.audit_overlap_v3 import EMBEDDER, REVISION, audit, grams, nearest, normalize
from train.repro import sha256_file


def filter_sources(rows: dict[str, list[dict]], embeddings: dict[str, np.ndarray],
                   excluded_train_groups: set[str], threshold: float) -> tuple[dict, dict, dict]:
    """Test-first priority; remove whole validation groups near diagnostic test."""
    test_grams = set().union(*(grams(r["instruction"]) for r in rows["test"]))
    test_normalized = {normalize(r["instruction"]) for r in rows["test"]}
    val_scores = nearest(embeddings["val"], embeddings["test"])
    excluded_val_groups = {
        r["group_id"] for r, sim in zip(rows["val"], val_scores)
        if sim >= threshold or normalize(r["instruction"]) in test_normalized
        or grams(r["instruction"]) & test_grams}
    excluded = {"train": excluded_train_groups, "val": excluded_val_groups, "test": set()}
    pools, vectors, removals = {}, {}, {}
    for split, source in rows.items():
        keep = [i for i, r in enumerate(source)
                if r["id"].startswith("bitext-") and r["group_id"] not in excluded[split]]
        pools[split] = [source[i] for i in keep]
        vectors[split] = embeddings[split][keep]
        removals[split] = {"source": len(source), "retained": len(keep),
                           "retained_by_intent": dict(sorted(Counter(
                               r["intent"] for r in pools[split]).items())),
                           "excluded_groups": sorted(excluded[split])}
    return pools, vectors, removals


def verify_audit(report: dict) -> None:
    for name, comparison in report["comparisons"].items():
        for key in ("duplicate_ids", "shared_groups", "normalized_query_overlap"):
            if comparison[key]:
                raise ValueError(f"overlap remains: {name}/{key}")
        scores = next(v for k, v in comparison.items() if "_nearest_" in k)
        if scores["at_or_above_threshold"]:
            raise ValueError(f"semantic screening threshold violated: {name}")
    if report["hypothetical_train_group_purge"]["excluded_groups"]:
        raise ValueError("training six-gram/group overlap remains")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".scratch/v3-embeddings")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("output directory already exists; preserve it and use a new path")
    source_audit = json.loads(args.source_audit.read_text())
    if (source_audit["embedding_model"], source_audit["embedding_revision"]) != (EMBEDDER, REVISION):
        raise ValueError("source audit uses a different embedder")
    threshold = float(source_audit["threshold"])
    rows, embeddings = {}, {}
    for split in ("train", "val", "test"):
        path = args.source_dir / f"{split}.jsonl"
        source_hash = sha256_file(path)
        if source_hash != source_audit["source_sha256"][split]:
            raise ValueError(f"source changed since audit: {split}")
        rows[split] = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        cache_id = hashlib.sha256((source_hash + EMBEDDER + REVISION).encode()).hexdigest()
        embeddings[split] = np.load(args.cache_dir / f"{cache_id}.npy", allow_pickle=False)
        array = embeddings[split]
        if (array.ndim != 2 or len(array) != len(rows[split]) or not np.isfinite(array).all()
                or not np.allclose(np.linalg.norm(array, axis=1), 1, atol=1e-5)):
            raise ValueError(f"invalid embedding cache for {split}")
    pools, vectors, removals = filter_sources(rows, embeddings,
        set(source_audit["hypothetical_train_group_purge"]["excluded_groups"]), threshold)
    report = audit(pools, vectors, threshold)
    verify_audit(report)
    test_grams = set().union(*(grams(t["instruction"]) for t in pools["test"]))
    if any(grams(r["instruction"]) & test_grams for r in pools["val"]):
        raise ValueError("validation/test six-gram overlap remains")
    expected_intents = {r["intent"] for r in rows["train"]}
    for name, pool in pools.items():
        if {r["intent"] for r in pool} != expected_intents:
            raise ValueError(f"intent coverage lost in {name}")
    args.output_dir.mkdir(parents=True)
    outputs = {}
    for name, pool in pools.items():
        path = args.output_dir / f"{name}.jsonl"
        with path.open("x") as handle:
            for row in pool:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        outputs[name] = sha256_file(path)
    manifest = {
        "schema": 1, "ready_for_training": False,
        "reason": "Original targets contain unsupported claims; target-quality review is still required.",
        "final_evaluation": False,
        "split_usage": "train candidates; historical val/test for development diagnostics only",
        "source_audit_sha256": sha256_file(args.source_audit),
        "source_sha256": source_audit["source_sha256"], "output_sha256": outputs,
        "embedding_model": EMBEDDER, "embedding_revision": REVISION,
        "script_sha256": sha256_file(Path(__file__)),
        "target_handling": "unchanged historical processed Bitext responses; no new targets",
        "synthetic_handling": "exclude every non-bitext source ID, including v2 admissions",
        "filtering": removals, "post_filter_audit": report,
    }
    with (args.output_dir / "manifest.json").open("x") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(args.output_dir), "ready_for_training": False,
                      "rows": {k: len(v) for k, v in pools.items()}}, indent=2))


if __name__ == "__main__":
    main()
