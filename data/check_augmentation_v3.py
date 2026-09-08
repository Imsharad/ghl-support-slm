"""Screen authored training queries against the complete historical holdouts."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.audit_overlap_v3 import EMBEDDER, REVISION, grams, normalize
from train.repro import sha256_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--against", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=.86)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".scratch/v3-embeddings")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refusing to overwrite an existing screening report")
    if not 0 < args.threshold < 1:
        parser.error("threshold must be between zero and one")
    rows = json.loads(args.input.read_text())["rows"]
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("augmentation must have nonempty, unique IDs")
    held, embeddings, sources = [], [], {}
    for path in args.against:
        digest = sha256_file(path)
        sources[str(path)] = digest
        pool = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        held.extend(pool)
        key = hashlib.sha256((digest + EMBEDDER + REVISION).encode()).hexdigest()
        vectors = np.load(args.cache_dir / f"{key}.npy", allow_pickle=False)
        if len(vectors) != len(pool) or not np.isfinite(vectors).all():
            raise ValueError(f"invalid embedding cache: {path}")
        embeddings.append(vectors)
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer(EMBEDDER, revision=REVISION, local_files_only=True, device="cpu")
    vectors = embedder.encode([r["instruction"] for r in rows], normalize_embeddings=True,
                              convert_to_numpy=True, show_progress_bar=False)
    similarities = vectors @ np.concatenate(embeddings).T
    held_grams = set().union(*(grams(r["instruction"]) for r in held))
    held_normalized = {normalize(r["instruction"]) for r in held}
    held_ids = {r["id"] for r in held}
    held_groups = {r["group_id"] for r in held}
    results = []
    for row, scores in zip(rows, similarities):
        nearest_index = int(np.argmax(scores))
        collisions = sorted(grams(row["instruction"]) & held_grams)
        failed = (float(scores[nearest_index]) >= args.threshold or bool(collisions)
                  or normalize(row["instruction"]) in held_normalized
                  or row["id"] in held_ids or row["group_id"] in held_groups)
        results.append({"id": row["id"], "max_cosine": float(scores[nearest_index]),
                        "nearest_id": held[nearest_index]["id"], "shared_sixgrams": collisions,
                        "pass": not failed})
    report = {"input_sha256": sha256_file(args.input), "against_sha256": sources,
              "threshold": args.threshold, "embedding_model": EMBEDDER,
              "embedding_revision": REVISION, "results": results,
              "pass": all(r["pass"] for r in results),
              "scope": "training augmentation instructions versus all supplied holdout instructions",
              "limitation": "Automated similarity screening, not proof of semantic independence"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "pass": report["pass"],
                      "failed_ids": [r["id"] for r in results if not r["pass"]],
                      "max_cosine": max(r["max_cosine"] for r in results)}))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
