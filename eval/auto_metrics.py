"""Bitext-test automated metrics: ROUGE-L, MiniLM cosine, placeholders, length, group bootstrap."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
from rouge_score import rouge_scorer

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
N_BOOT = 2000
SEED = 42
TOKEN_CAP = 256
PLACEHOLDER_MARK = "{{"
IST = timezone(timedelta(hours=5, minutes=30))

_ROUGE = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
_encoder = None


def ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid json") from exc
    return rows


def rouge_l_f1(hypothesis: str, reference: str) -> float:
    hyp = hypothesis or ""
    ref = reference or ""
    if hyp == ref:
        return 1.0
    if not hyp.strip() or not ref.strip():
        return 0.0
    return float(_ROUGE.score(ref, hyp)["rougeL"].fmeasure)


def has_placeholder(text: str) -> bool:
    return PLACEHOLDER_MARK in (text or "")


def token_length(row: dict) -> int:
    gen = row.get("gen_tokens")
    if isinstance(gen, (int, float)) and not isinstance(gen, bool) and math.isfinite(gen):
        return int(gen)
    return len((row.get("answer") or "").split())


def is_empty(row: dict) -> bool:
    if row.get("error"):
        return True
    return not (row.get("answer") or "").strip()


def is_truncated(row: dict) -> bool:
    if row.get("truncated") is True:
        return True
    gen = row.get("gen_tokens")
    if isinstance(gen, (int, float)) and gen >= TOKEN_CAP:
        return True
    return False


def encoder():
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer

        _encoder = SentenceTransformer(EMBED_MODEL)
    return _encoder


def embed_texts(texts: list[str]) -> np.ndarray:
    vectors = encoder().encode(
        texts,
        batch_size=64,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.asarray(vectors, dtype=np.float32)


def index_by_id(rows: list[dict], label: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in rows:
        rid = row.get("id")
        if not rid:
            raise ValueError(f"{label} row missing id: {row!r}")
        if rid in out:
            raise ValueError(f"{label} duplicate id: {rid}")
        out[str(rid)] = row
    return out


def align(raw_rows: list[dict], ref_rows: list[dict]) -> list[dict]:
    raw_by = index_by_id(raw_rows, "raw")
    ref_by = index_by_id(ref_rows, "refs")
    raw_ids = set(raw_by)
    ref_ids = set(ref_by)
    missing_in_raw = sorted(ref_ids - raw_ids)
    missing_in_refs = sorted(raw_ids - ref_ids)
    if missing_in_raw or missing_in_refs:
        parts = []
        if missing_in_raw:
            parts.append(f"missing in raw: {missing_in_raw}")
        if missing_in_refs:
            parts.append(f"missing in refs: {missing_in_refs}")
        raise ValueError("; ".join(parts))
    aligned = []
    for rid in sorted(ref_ids):
        ref = ref_by[rid]
        raw = raw_by[rid]
        if "response" not in ref:
            raise ValueError(f"refs {rid} missing response")
        if "group_id" not in ref:
            raise ValueError(f"refs {rid} missing group_id")
        aligned.append(
            {
                "id": rid,
                "group_id": str(ref["group_id"]),
                "intent": str(ref.get("intent") or "unknown"),
                "reference": str(ref["response"]),
                "answer": str(raw.get("answer") or ""),
                "raw": raw,
            }
        )
    return aligned


def _mean_median(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(arr.mean()) if arr.size else 0.0,
        "median": float(np.median(arr)) if arr.size else 0.0,
    }


def score_aligned(aligned: list[dict], with_embeddings: bool = True) -> list[dict]:
    answers = [row["answer"] for row in aligned]
    refs = [row["reference"] for row in aligned]
    cosines = [0.0] * len(aligned)
    if with_embeddings and aligned:
        ans_vec = embed_texts(answers)
        ref_vec = embed_texts(refs)
        dots = np.sum(ans_vec * ref_vec, axis=1)
        cosines = [float(x) for x in dots]
    scored = []
    for row, cosine in zip(aligned, cosines):
        raw = row["raw"]
        scored.append(
            {
                "id": row["id"],
                "group_id": row["group_id"],
                "intent": row["intent"],
                "rouge_l_f1": rouge_l_f1(row["answer"], row["reference"]),
                "embedding_cosine": cosine,
                "placeholder": has_placeholder(row["answer"]),
                "n_tokens": token_length(raw),
                "empty": is_empty(raw),
                "truncated": is_truncated(raw),
            }
        )
    return scored


def summarize(scored: list[dict], nest_intent: bool = True) -> dict[str, Any]:
    n = len(scored)
    groups = sorted({row["group_id"] for row in scored})
    payload: dict[str, Any] = {
        "n": n,
        "n_groups": len(groups),
        "rouge_l_f1": _mean_median([row["rouge_l_f1"] for row in scored]),
        "embedding_cosine": _mean_median([row["embedding_cosine"] for row in scored]),
        "placeholder_rate": float(np.mean([row["placeholder"] for row in scored])) if n else 0.0,
        "length_tokens": _mean_median([float(row["n_tokens"]) for row in scored]),
        "empty_rate": float(np.mean([row["empty"] for row in scored])) if n else 0.0,
        "truncated_rate": float(np.mean([row["truncated"] for row in scored])) if n else 0.0,
    }
    if nest_intent:
        by_intent: dict[str, list[dict]] = defaultdict(list)
        for row in scored:
            by_intent[row["intent"]].append(row)
        payload["per_intent"] = {
            intent: summarize(rows, nest_intent=False) for intent, rows in sorted(by_intent.items())
        }
    return payload


def bootstrap_group_mean(
    values: list[float],
    group_ids: list[str],
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> tuple[float, float, float]:
    """Percentile 95% CI of the item-mean, resampling groups with replacement."""
    if not values:
        return 0.0, 0.0, 0.0
    buckets: dict[str, list[float]] = defaultdict(list)
    for value, gid in zip(values, group_ids):
        buckets[gid].append(float(value))
    keys = list(buckets)
    point = float(np.mean(values))
    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot, dtype=np.float64)
    for i in range(n_boot):
        draw = rng.choice(keys, size=len(keys), replace=True)
        sample = np.concatenate([np.asarray(buckets[k], dtype=np.float64) for k in draw])
        boot[i] = sample.mean()
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return point, float(lo), float(hi)


def compare_scored(
    base: list[dict],
    tuned: list[dict],
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> dict[str, Any]:
    base_by = {row["id"]: row for row in base}
    tuned_by = {row["id"]: row for row in tuned}
    if set(base_by) != set(tuned_by):
        raise ValueError("compare: raw files do not cover the same ids")
    ids = sorted(base_by)
    group_ids = [base_by[i]["group_id"] for i in ids]
    if [base_by[i]["group_id"] for i in ids] != [tuned_by[i]["group_id"] for i in ids]:
        raise ValueError("compare: group_id mismatch on paired ids")
    out: dict[str, Any] = {"n": len(ids), "n_groups": len(set(group_ids)), "n_boot": n_boot, "seed": seed}
    for metric in ("rouge_l_f1", "embedding_cosine"):
        diffs = [tuned_by[i][metric] - base_by[i][metric] for i in ids]
        point, lo, hi = bootstrap_group_mean(diffs, group_ids, n_boot=n_boot, seed=seed)
        out[metric] = {"point": point, "ci95": [lo, hi]}
    return out


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def infer_compare_out(compare_raw: Path, out_path: Path) -> Path:
    name = compare_raw.name
    if name.endswith("-raw.jsonl"):
        return compare_raw.with_name(name[: -len("-raw.jsonl")] + "-auto.json")
    return out_path.with_name(out_path.stem + "-compare.json")


def run(
    raw_path: Path,
    refs_path: Path,
    out_path: Path,
    compare_path: Path | None = None,
    compare_out: Path | None = None,
    n_boot: int = N_BOOT,
    seed: int = SEED,
    with_embeddings: bool = True,
) -> dict:
    aligned = align(load_jsonl(raw_path), load_jsonl(refs_path))
    scored = score_aligned(aligned, with_embeddings=with_embeddings)
    payload = summarize(scored)
    payload.update(
        {
            "raw": str(raw_path),
            "refs": str(refs_path),
            "seed": seed,
            "n_boot": n_boot,
            "embedding_model": EMBED_MODEL,
            "generated_at": ist_now(),
        }
    )
    if compare_path is not None:
        other_aligned = align(load_jsonl(compare_path), load_jsonl(refs_path))
        other_scored = score_aligned(other_aligned, with_embeddings=with_embeddings)
        other_payload = summarize(other_scored)
        other_out = compare_out or infer_compare_out(compare_path, out_path)
        other_payload.update(
            {
                "raw": str(compare_path),
                "refs": str(refs_path),
                "seed": seed,
                "n_boot": n_boot,
                "embedding_model": EMBED_MODEL,
                "generated_at": ist_now(),
            }
        )
        diff = compare_scored(scored, other_scored, n_boot=n_boot, seed=seed)
        payload["compare"] = {
            "other_raw": str(compare_path),
            "other_out": str(other_out),
            "diff": diff,
        }
        other_payload["compare"] = {
            "other_raw": str(raw_path),
            "other_out": str(out_path),
            "diff": {
                "n": diff["n"],
                "n_groups": diff["n_groups"],
                "n_boot": diff["n_boot"],
                "seed": diff["seed"],
                "rouge_l_f1": {
                    "point": -diff["rouge_l_f1"]["point"],
                    "ci95": [-diff["rouge_l_f1"]["ci95"][1], -diff["rouge_l_f1"]["ci95"][0]],
                },
                "embedding_cosine": {
                    "point": -diff["embedding_cosine"]["point"],
                    "ci95": [
                        -diff["embedding_cosine"]["ci95"][1],
                        -diff["embedding_cosine"]["ci95"][0],
                    ],
                },
            },
        }
        write_json(other_out, other_payload)
    write_json(out_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--refs", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--compare", type=Path, default=None, help="Second raw jsonl (tuned).")
    parser.add_argument("--out-compare", type=Path, default=None)
    parser.add_argument("--n-boot", type=int, default=N_BOOT)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    payload = run(
        raw_path=args.raw,
        refs_path=args.refs,
        out_path=args.out,
        compare_path=args.compare,
        compare_out=args.out_compare,
        n_boot=args.n_boot,
        seed=args.seed,
    )
    print(f"n={payload['n']} groups={payload['n_groups']}")
    print(f"rouge_l_f1_mean={payload['rouge_l_f1']['mean']:.4f}")
    print(f"cosine_mean={payload['embedding_cosine']['mean']:.4f}")
    print(f"placeholder_rate={payload['placeholder_rate']:.4f}")
    print(f"empty_rate={payload['empty_rate']:.4f} truncated_rate={payload['truncated_rate']:.4f}")
    print(f"wrote {args.out}")
    if args.compare:
        print(f"compare rouge point={payload['compare']['diff']['rouge_l_f1']['point']:.4f} "
              f"ci95={payload['compare']['diff']['rouge_l_f1']['ci95']}")
        print(f"wrote {payload['compare']['other_out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
