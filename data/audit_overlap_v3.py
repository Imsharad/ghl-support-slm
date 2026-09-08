"""Measure all-intent query overlap and hypothetical whole-group purging.

This audit never rewrites a split or reads model answers. Its cosine threshold is
a screening rule, not a claim that embeddings prove semantic independence.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from train.repro import sha256_file

EMBEDDER = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold().replace("’", "'")
    text = re.sub(r"\{\{[^{}]+\}\}", " placeholder ", text)
    return " ".join(re.findall(r"[\w]+(?:'[\w]+)*", text, flags=re.UNICODE))


def grams(text: str, n: int = 6) -> set[str]:
    words = normalize(text).split()
    return {" ".join(words[i:i+n]) for i in range(len(words)-n+1)}


def nearest(left: np.ndarray, right: np.ndarray, chunk: int = 256) -> np.ndarray:
    if not len(left) or not len(right):
        raise ValueError("nearest-neighbor comparison requires nonempty sources")
    return np.concatenate([np.max(left[i:i+chunk] @ right.T, axis=1)
                           for i in range(0, len(left), chunk)])


def summarize(values: np.ndarray, threshold: float) -> dict:
    return {"n": len(values), "min": float(values.min()), "p50": float(np.median(values)),
            "p95": float(np.quantile(values, .95)), "max": float(values.max()),
            "at_or_above_threshold": int(np.sum(values >= threshold))}


def audit(rows: dict[str, list[dict]], embeddings: dict[str, np.ndarray], threshold: float) -> dict:
    normalized = {name: {normalize(r["instruction"]) for r in pool} for name, pool in rows.items()}
    ids = {name: {r["id"] for r in pool} for name, pool in rows.items()}
    groups = {name: {r["group_id"] for r in pool} for name, pool in rows.items()}
    comparisons = {}
    for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
        comparisons[f"{a}_{b}"] = {
            "duplicate_ids": len(ids[a] & ids[b]),
            "shared_groups": len(groups[a] & groups[b]),
            "normalized_query_overlap": len(normalized[a] & normalized[b]),
            f"{b}_nearest_{a}": summarize(nearest(embeddings[b], embeddings[a]), threshold),
        }
    held = rows["val"] + rows["test"]
    held_embeddings = np.concatenate([embeddings["val"], embeddings["test"]])
    train_nearest = nearest(embeddings["train"], held_embeddings)
    held_grams = set().union(*(grams(r["instruction"]) for r in held))
    held_normalized = normalized["val"] | normalized["test"]
    bad_groups = {
        r["group_id"] for r, sim in zip(rows["train"], train_nearest)
        if sim >= threshold or normalize(r["instruction"]) in held_normalized
        or grams(r["instruction"]) & held_grams
    }
    surviving = [r for r in rows["train"] if r["group_id"] not in bad_groups]
    return {
        "scope": "all intents; instructions only; no response or model output used",
        "threshold": threshold, "sixgram_rule": "zero shared normalized six-word sequences",
        "comparisons": comparisons,
        "hypothetical_train_group_purge": {
            "not_applied": True, "input_rows": len(rows["train"]), "retained_rows": len(surviving),
            "retained_by_intent": dict(sorted(Counter(r["intent"] for r in surviving).items())),
            "retained_groups_by_intent": {
                intent: len({r["group_id"] for r in surviving if r["intent"] == intent})
                for intent in sorted({r["intent"] for r in rows["train"]})},
            "excluded_groups": sorted(bad_groups),
        },
        "limitation": "Similarity screening reduces known overlap; no numeric threshold proves zero semantic leakage.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=.86)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".scratch/v3-embeddings")
    parser.add_argument("--allow-download", action="store_true",
                        help="Fetch the pinned embedding model if not already cached")
    args = parser.parse_args()
    if not 0 < args.threshold < 1:
        parser.error("threshold must lie strictly between zero and one")
    if args.output.exists():
        parser.error("output already exists; use a new path to preserve the audit")
    rows, embeddings, sources = {}, {}, {}
    from sentence_transformers import SentenceTransformer
    model = None
    for name in ("train", "val", "test"):
        path = args.source_dir / f"{name}.jsonl"
        sources[name] = sha256_file(path)
        rows[name] = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if len({r["id"] for r in rows[name]}) != len(rows[name]):
            raise ValueError(f"duplicate source ID inside {name}")
        cache_id = hashlib.sha256((sources[name]+EMBEDDER+REVISION).encode()).hexdigest()
        cache = args.cache_dir / f"{cache_id}.npy"
        if cache.exists():
            embeddings[name] = np.load(cache, allow_pickle=False)
        else:
            if model is None:
                model = SentenceTransformer(EMBEDDER, revision=REVISION,
                                            local_files_only=not args.allow_download, device="cpu")
            embeddings[name] = model.encode([r["instruction"] for r in rows[name]],
                                            normalize_embeddings=True, show_progress_bar=True,
                                            batch_size=128, convert_to_numpy=True)
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.save(cache, embeddings[name], allow_pickle=False)
        if len(embeddings[name]) != len(rows[name]):
            raise ValueError("embedding cache row count mismatch")
    report = audit(rows, embeddings, args.threshold)
    report.update(source_sha256=sources, embedding_model=EMBEDDER, embedding_revision=REVISION)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    proposal = report["hypothetical_train_group_purge"]
    print(json.dumps({"output": str(args.output),
                      **{k: v for k, v in proposal.items() if k != "excluded_groups"},
                      "excluded_group_count": len(proposal["excluded_groups"])}, indent=2))


if __name__ == "__main__":
    main()
