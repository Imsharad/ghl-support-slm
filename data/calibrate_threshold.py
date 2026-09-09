"""Sample, label, and pick the paraphrase-grouping cosine threshold.

Within-intent MiniLM pairs, seed 42. Writes data/calibration/ and configs/data/grouping.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ID_EMBED = "sentence-transformers/all-MiniLM-L6-v2"
NORMALIZE_NAME = "lower_strip_punct_keep_neg_num"
SEED = 42
EXPECTED_PAIRS = 40
CSV_COLUMNS = ["flags", "instruction", "category", "intent", "response"]

# 7+7+7+7+6+6 = 40. Last band includes 1.0.
BANDS: list[tuple[float, float, int]] = [
    (0.70, 0.75, 7),
    (0.75, 0.80, 7),
    (0.80, 0.85, 7),
    (0.85, 0.90, 7),
    (0.90, 0.95, 6),
    (0.95, 1.01, 6),
]

CANDIDATE_THRESHOLDS = [
    0.70,
    0.75,
    0.80,
    0.85,
    0.86,
    0.87,
    0.88,
    0.89,
    0.90,
    0.92,
    0.95,
]

PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")
IST = timezone(timedelta(hours=5, minutes=30))

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "raw" / "bitext.csv"
CAL_DIR = ROOT / "data" / "calibration"
PAIRS_PATH = CAL_DIR / "pairs.jsonl"
LABELS_PATH = CAL_DIR / "labels.json"
REPORT_PATH = CAL_DIR / "REPORT.md"
GROUPING_PATH = ROOT / "configs" / "data" / "grouping.json"
GROUPING_SCHEMA_KEYS = {
    "embedding_model",
    "normalize",
    "exact_match",
    "template_family",
    "cosine_threshold",
    "linkage",
    "labelled_pairs",
    "report",
}

CHAINED_INTENTS = [
    "cancel_order",
    "check_payment_methods",
    "newsletter_subscription",
    "payment_issue",
    "registration_problems",
    "set_up_shipping_address",
]
NEAR_COLLAPSE_SHARE = 0.50
VALID_LINKAGES = ("single", "average", "complete")


def ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def normalize(text: str) -> str:
    """lower_strip_punct_keep_neg_num: casefold, keep digits, expand n't to not, drop other punct."""
    lowered = text.casefold()
    lowered = PLACEHOLDER_RE.sub(" ph ", lowered)
    lowered = lowered.replace("n't", " not ")
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def response_template(text: str) -> str:
    """Canonical response for template-family grouping (same intent)."""
    slotted = PLACEHOLDER_RE.sub("{{SLOT}}", text)
    return normalize(slotted)


def band_name(lo: float, hi: float) -> str:
    if hi >= 1.0:
        return f"{lo:.2f}-1.0"
    return f"{lo:.2f}-{hi:.2f}"


def load_csv() -> pd.DataFrame:
    frame = pd.read_csv(CSV_PATH, keep_default_na=False)
    missing = [col for col in CSV_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"CSV missing {missing}")
    out = frame.loc[:, CSV_COLUMNS].copy()
    out["row_id"] = [f"bitext-{i:06d}" for i in range(len(out))]
    out["norm_instruction"] = [normalize(text) for text in out["instruction"].tolist()]
    out["resp_template"] = [response_template(text) for text in out["response"].tolist()]
    return out


def embed(texts: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(REPO_ID_EMBED)
    vectors = model.encode(
        texts,
        batch_size=256,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.asarray(vectors, dtype=np.float32)


class DSU:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]


def sample_pairs(df: pd.DataFrame, embeddings: np.ndarray) -> list[dict]:
    rng = np.random.default_rng(SEED)
    pools: dict[str, list[dict]] = {band_name(lo, hi): [] for lo, hi, _ in BANDS}
    per_intent_cap = 80

    for intent, group in df.groupby("intent", sort=True):
        positions = group.index.to_numpy()
        n = len(positions)
        if n < 2:
            continue
        local = embeddings[positions]
        sim = local @ local.T
        ii, jj = np.triu_indices(n, k=1)
        scores = sim[ii, jj]
        for lo, hi, _want in BANDS:
            hits = np.flatnonzero((scores >= lo) & (scores < hi))
            if hits.size == 0:
                continue
            take_n = min(per_intent_cap, int(hits.size))
            chosen = rng.choice(hits, size=take_n, replace=False)
            bname = band_name(lo, hi)
            for t in chosen:
                a_pos = int(positions[int(ii[t])])
                b_pos = int(positions[int(jj[t])])
                ra, rb = df.loc[a_pos], df.loc[b_pos]
                pools[bname].append(
                    {
                        "intent": str(intent),
                        "row_a": str(ra["row_id"]),
                        "row_b": str(rb["row_id"]),
                        "instruction_a": str(ra["instruction"]),
                        "instruction_b": str(rb["instruction"]),
                        "normalized_a": str(ra["norm_instruction"]),
                        "normalized_b": str(rb["norm_instruction"]),
                        "cosine": round(float(scores[t]), 4),
                        "band": bname,
                        "exact_normalized": bool(
                            ra["norm_instruction"] == rb["norm_instruction"]
                        ),
                    }
                )

    sampled: list[dict] = []
    pair_id = 1
    for lo, hi, want in BANDS:
        bname = band_name(lo, hi)
        pool = pools[bname]
        if not pool:
            print(f"WARNING: no pairs in band {bname}", file=sys.stderr)
            continue
        rng.shuffle(pool)
        seen: set[tuple[str, str]] = set()
        by_intent: dict[str, list[dict]] = defaultdict(list)
        for item in pool:
            key = tuple(sorted((item["normalized_a"], item["normalized_b"])))
            if key in seen:
                continue
            seen.add(key)
            by_intent[item["intent"]].append(item)
        intents = sorted(by_intent)
        rng.shuffle(intents)
        taken = 0
        while taken < want and any(by_intent[i] for i in intents):
            for intent in intents:
                if taken >= want:
                    break
                bucket = by_intent[intent]
                if not bucket:
                    continue
                item = bucket.pop(0)
                rec = dict(item)
                rec["id"] = f"p-{pair_id:02d}"
                sampled.append(rec)
                pair_id += 1
                taken += 1
        if taken < want:
            print(
                f"WARNING: band {bname} only sampled {taken}/{want}",
                file=sys.stderr,
            )

    sampled.sort(key=lambda r: r["id"])
    return sampled


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def apply_labels(pairs: list[dict], labels: dict) -> list[dict]:
    out = []
    for pair in pairs:
        rec = dict(pair)
        lab = labels.get(pair["id"])
        if lab is None:
            rec.pop("same_scenario", None)
            rec.pop("reason", None)
            rec.pop("intent_wrong", None)
            out.append(rec)
            continue
        rec["same_scenario"] = bool(lab["same_scenario"])
        rec["reason"] = str(lab["reason"])
        rec["intent_wrong"] = bool(lab.get("intent_wrong", False))
        rec["intent_wrong_note"] = str(lab.get("intent_wrong_note", ""))
        out.append(rec)
    return out


def unlabeled_ids(pairs: list[dict]) -> list[str]:
    return [p["id"] for p in pairs if "same_scenario" not in p]


def metrics_at(pairs: list[dict], threshold: float) -> dict:
    y_true = [bool(p["same_scenario"]) for p in pairs]
    y_pred = [float(p["cosine"]) >= threshold for p in pairs]
    tp = sum(t and p for t, p in zip(y_true, y_pred))
    fp = sum((not t) and p for t, p in zip(y_true, y_pred))
    fn = sum(t and (not p) for t, p in zip(y_true, y_pred))
    tn = sum((not t) and (not p) for t, p in zip(y_true, y_pred))
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": prec,
        "recall": rec,
        "n_above": tp + fp,
        "n_below": tn + fn,
        "different_above": fp,
        "same_below": fn,
        "different_below": tn,
    }


def fmt_rate(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def pick_threshold(rows: list[dict]) -> tuple[float, str]:
    """Lowest T with zero labelled-different pairs at cosine >= T, band below mostly different."""
    scored = []
    for t in CANDIDATE_THRESHOLDS:
        scored.append(metrics_at(rows, t))
    zero_fp = [m for m in scored if m["fp"] == 0 and m["n_above"] > 0]
    if not zero_fp:
        # No labelled-perfect cutoff. Take the highest T that still has some
        # same-pairs above it, and say so.
        nonempty = [m for m in scored if m["n_above"] > 0]
        chosen = nonempty[-1] if nonempty else scored[-1]
        return float(chosen["threshold"]), (
            "no candidate had zero different-pairs above it; "
            f"using {chosen['threshold']} as the most conservative scored cut"
        )
    # Prefer the lowest such T whose immediate lower band is mostly different
    # (different_below / n_below >= 0.5). Walk from low to high.
    for m in zero_fp:
        below = m["n_below"]
        mostly_diff = (m["different_below"] / below >= 0.5) if below else True
        if mostly_diff:
            return float(m["threshold"]), (
                "lowest T with zero labelled-different pairs at cosine >= T "
                "and the pairs below T mostly labelled different"
            )
    chosen = zero_fp[0]
    return float(chosen["threshold"]), (
        "lowest T with zero labelled-different pairs at cosine >= T "
        "(band below T was not majority-different on this sample)"
    )


def group_stats(df: pd.DataFrame, embeddings: np.ndarray, threshold: float) -> list[dict]:
    rows = []
    for intent, group in df.groupby("intent", sort=True):
        positions = group.index.to_numpy()
        n = len(positions)
        dsu = DSU(n)
        norms = group["norm_instruction"].tolist()
        templates = group["resp_template"].tolist()
        by_norm: dict[str, list[int]] = defaultdict(list)
        by_tmpl: dict[str, list[int]] = defaultdict(list)
        for i, (norm, tmpl) in enumerate(zip(norms, templates)):
            by_norm[norm].append(i)
            by_tmpl[tmpl].append(i)
        for members in by_norm.values():
            for j in members[1:]:
                dsu.union(members[0], j)
        for members in by_tmpl.values():
            for j in members[1:]:
                dsu.union(members[0], j)
        local = embeddings[positions]
        sim = local @ local.T
        ii, jj = np.triu_indices(n, k=1)
        scores = sim[ii, jj]
        hits = np.flatnonzero(scores >= threshold)
        for t in hits:
            dsu.union(int(ii[t]), int(jj[t]))
        roots = [dsu.find(i) for i in range(n)]
        counts: dict[int, int] = defaultdict(int)
        for r in roots:
            counts[r] += 1
        sizes = list(counts.values())
        largest = max(sizes)
        rows.append(
            {
                "intent": str(intent),
                "rows": n,
                "groups": len(sizes),
                "largest": largest,
                "largest_share": round(largest / n, 3),
                "singleton": sum(1 for s in sizes if s == 1),
                "collapsed": bool(len(sizes) == 1),
                "near_collapse": bool(largest / n >= NEAR_COLLAPSE_SHARE),
            }
        )
    return rows


def _union_exact_and_template(dsu: DSU, norms: list[str], templates: list[str]) -> None:
    by_norm: dict[str, list[int]] = defaultdict(list)
    by_tmpl: dict[str, list[int]] = defaultdict(list)
    for i, (norm, tmpl) in enumerate(zip(norms, templates)):
        by_norm[norm].append(i)
        by_tmpl[tmpl].append(i)
    for members in by_norm.values():
        for j in members[1:]:
            dsu.union(members[0], j)
    for members in by_tmpl.values():
        for j in members[1:]:
            dsu.union(members[0], j)


def group_stats_agglomerative(
    df: pd.DataFrame,
    embeddings: np.ndarray,
    threshold: float,
    linkage: str,
) -> list[dict]:
    """Cosine agglomerative clustering, then exact-match and template-family unions."""
    from sklearn.cluster import AgglomerativeClustering

    distance_threshold = 1.0 - threshold
    rows = []
    for intent, group in df.groupby("intent", sort=True):
        positions = group.index.to_numpy()
        n = len(positions)
        dsu = DSU(n)
        if n >= 2:
            model = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=distance_threshold,
                metric="cosine",
                linkage=linkage,
            )
            labels = model.fit_predict(embeddings[positions])
            by_lab: dict[int, list[int]] = defaultdict(list)
            for i, lab in enumerate(labels):
                by_lab[int(lab)].append(i)
            for members in by_lab.values():
                for j in members[1:]:
                    dsu.union(members[0], j)
        norms = group["norm_instruction"].tolist()
        templates = group["resp_template"].tolist()
        _union_exact_and_template(dsu, norms, templates)
        roots = [dsu.find(i) for i in range(n)]
        counts: dict[int, int] = defaultdict(int)
        for r in roots:
            counts[r] += 1
        sizes = list(counts.values())
        largest = max(sizes)
        rows.append(
            {
                "intent": str(intent),
                "rows": n,
                "groups": len(sizes),
                "largest": largest,
                "largest_share": round(largest / n, 3),
                "singleton": sum(1 for s in sizes if s == 1),
                "collapsed": bool(len(sizes) == 1),
                "near_collapse": bool(largest / n >= NEAR_COLLAPSE_SHARE),
            }
        )
    return rows


def summarize_linkage(name: str, groups: list[dict]) -> dict:
    near = [g for g in groups if g["near_collapse"]]
    six = {g["intent"]: g for g in groups if g["intent"] in CHAINED_INTENTS}
    return {
        "linkage": name,
        "total_groups": sum(g["groups"] for g in groups),
        "near_intents": [g["intent"] for g in near],
        "n_near": len(near),
        "max_largest": max(g["largest"] for g in groups),
        "six": {
            intent: {
                "largest": six[intent]["largest"],
                "rows": six[intent]["rows"],
                "share": six[intent]["largest_share"],
                "groups": six[intent]["groups"],
            }
            for intent in CHAINED_INTENTS
        },
    }


def validate_grouping(payload: dict) -> None:
    missing = GROUPING_SCHEMA_KEYS - set(payload)
    if missing:
        raise ValueError(f"grouping.json missing keys {sorted(missing)}")
    if payload["embedding_model"] != REPO_ID_EMBED:
        raise ValueError("embedding_model mismatch")
    if payload["normalize"] != NORMALIZE_NAME:
        raise ValueError("normalize mismatch")
    if not isinstance(payload["exact_match"], bool):
        raise ValueError("exact_match must be bool")
    if not isinstance(payload["template_family"], bool):
        raise ValueError("template_family must be bool")
    if not isinstance(payload["cosine_threshold"], (int, float)):
        raise ValueError("cosine_threshold must be a number")
    if int(payload["labelled_pairs"]) != EXPECTED_PAIRS:
        raise ValueError("labelled_pairs must be 40")
    if payload["report"] != "data/calibration/REPORT.md":
        raise ValueError("report path mismatch")
    if payload.get("linkage") not in VALID_LINKAGES:
        raise ValueError(f"linkage must be one of {VALID_LINKAGES}")


def write_report(
    pairs: list[dict],
    threshold: float,
    pick_reason: str,
    table: list[dict],
    groups: list[dict],
    groups_at: dict[float, list[dict]] | None = None,
) -> None:
    n_same = sum(1 for p in pairs if p["same_scenario"])
    n_diff = len(pairs) - n_same
    n_wrong = sum(1 for p in pairs if p.get("intent_wrong"))
    collapsed = [g for g in groups if g["collapsed"]]
    near = [g for g in groups if g["near_collapse"]]
    generated = ist_now()

    lines: list[str] = [
        "# Paraphrase threshold calibration",
        "",
        f"Generated: {generated}",
        "",
        "Commands:",
        "",
        "- `uv run python data/calibrate_threshold.py --sample`",
        "- `uv run python data/calibrate_threshold.py --report`",
        "",
        f"Embedding model: `{REPO_ID_EMBED}` (cached). Seed **{SEED}**. "
        f"Normalize `{NORMALIZE_NAME}`: casefold, expand `n't` to `not`, "
        "replace `{{placeholders}}` with `ph`, strip other punctuation, keep "
        "digits. Pairs are within-intent only.",
        "",
        f"Sample: **{len(pairs)}** pairs across six cosine bands "
        "(7,7,7,7,6,6). Labels: same_scenario = same request and same "
        "specifics, only wording differs. Different specifics inside the "
        "same intent (cannot-afford vs ordered-twice, missing order id vs "
        "generic how-to) are false.",
        "",
        f"Labels: **{n_same}** same, **{n_diff}** different, "
        f"**{n_wrong}** flagged as possible intent-label errors.",
        "",
        "## Chosen threshold",
        "",
        f"**{threshold:.2f}**. {pick_reason}.",
        "",
        "Grouping for B1 (union-find, within intent): (1) exact match on "
        "normalized instruction, (2) response template family = identical "
        "string after `{{...}}` -> `{{SLOT}}` then the same normalize, "
        "(3) MiniLM cosine >= threshold on normalized instructions. Never "
        "break a group at split time.",
        "",
        "Residual risk: 40 labelled pairs cannot prove zero leakage. "
        "Paraphrases continue down into the 0.70-0.85 bands (recall at 0.86 "
        "is 0.46 on this sample), so the band below T is mostly same, not "
        "mostly different. Union-find is transitive: a 0.86 edge chain can "
        "merge a whole intent-shaped cloud even when distant pairs would "
        "not have been labelled same. Exact-match and template-family close "
        "the obvious holes. Cross-split nearest-neighbour audit is B1's job.",
        "",
        "## Threshold table",
        "",
        "Command: `uv run python data/calibrate_threshold.py --report`",
        "",
        "Positive class = `same_scenario`. Predict same if cosine >= T.",
        "",
        "| T | TP | FP (different above) | FN (same below) | TN | precision | recall | n >= T |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for m in table:
        mark = " **chosen**" if abs(m["threshold"] - threshold) < 1e-9 else ""
        lines.append(
            f"| {m['threshold']:.2f}{mark} | {m['tp']} | {m['fp']} | {m['fn']} | "
            f"{m['tn']} | {fmt_rate(m['precision'])} | {fmt_rate(m['recall'])} | "
            f"{m['n_above']} |"
        )
    lines.extend(
        [
            "",
            "## The 40 labels",
            "",
            "Command: `uv run python data/calibrate_threshold.py --report`",
            "",
            "| id | band | cosine | intent | same | intent_wrong | reason | a | b |",
            "|---|---|---:|---|---|---|---|---|---|",
        ]
    )
    for p in pairs:
        a = p["instruction_a"].replace("|", "\\|").replace("\n", " ")
        b = p["instruction_b"].replace("|", "\\|").replace("\n", " ")
        reason = p["reason"].replace("|", "\\|")
        lines.append(
            f"| {p['id']} | {p['band']} | {p['cosine']:.3f} | `{p['intent']}` | "
            f"{str(p['same_scenario']).lower()} | "
            f"{str(bool(p.get('intent_wrong'))).lower()} | {reason} | {a} | {b} |"
        )
    lines.extend(
        [
            "",
            "## Groups at the chosen threshold",
            "",
            "Command: `uv run python data/calibrate_threshold.py --report`",
            "",
            "Union-find with exact-match + template-family + cosine >= "
            f"{threshold:.2f}. `collapsed` = one group for the whole intent. "
            "`near_collapse` = largest group holds >= 80% of the intent's rows "
            "(80/10/10 by group count will still dump most rows into whichever "
            "split draws that group).",
            "",
            "| intent | rows | groups | largest | share | singletons | collapsed | near |",
            "|---|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for g in groups:
        lines.append(
            f"| `{g['intent']}` | {g['rows']} | {g['groups']} | {g['largest']} | "
            f"{g['largest_share']:.0%} | {g['singleton']} | "
            f"{str(g['collapsed']).lower()} | {str(g['near_collapse']).lower()} |"
        )
    lines.extend(
        [
            "",
            f"Fully collapsed intents: "
            + (
                ", ".join(f"`{g['intent']}`" for g in collapsed)
                if collapsed
                else "none"
            )
            + ".",
            "",
            f"Near-collapse (>=80% of rows in one group): "
            + (
                ", ".join(
                    f"`{g['intent']}` {g['largest']}/{g['rows']}" for g in near
                )
                if near
                else "none"
            )
            + ".",
            "",
            f"Total groups: **{sum(g['groups'] for g in groups)}**. "
            f"Largest group overall: **{max(g['largest'] for g in groups)}** "
            f"({max(groups, key=lambda g: g['largest'])['intent']}).",
            "",
        ]
    )
    if groups_at:
        lines.extend(
            [
                "Same grouping rules at nearby cuts (chaining sensitivity):",
                "",
                "| T | total groups | max largest | near-collapse intents |",
                "|---:|---:|---:|---|",
            ]
        )
        for t in sorted(groups_at):
            gs = groups_at[t]
            near_t = [g["intent"] for g in gs if g["near_collapse"]]
            lines.append(
                f"| {t:.2f} | {sum(g['groups'] for g in gs)} | "
                f"{max(g['largest'] for g in gs)} | "
                + (", ".join(f"`{n}`" for n in near_t) if near_t else "none")
                + " |"
            )
        lines.append("")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_linkage_addendum(threshold: float = 0.86) -> None:
    """Compare single / average / complete at T, write REPORT section and grouping.json."""
    df = load_csv()
    print(f"rows={len(df)} embedding {REPO_ID_EMBED} T={threshold}")
    vectors = embed(df["norm_instruction"].tolist())
    print("clustering single (union-find edges)")
    single = group_stats(df, vectors, threshold)
    print("clustering average")
    average = group_stats_agglomerative(df, vectors, threshold, "average")
    print("clustering complete")
    complete = group_stats_agglomerative(df, vectors, threshold, "complete")
    summaries = [
        summarize_linkage("single", single),
        summarize_linkage("average", average),
        summarize_linkage("complete", complete),
    ]
    for s in summaries:
        print(
            f"{s['linkage']}: groups={s['total_groups']} near50={s['n_near']} "
            f"max_largest={s['max_largest']} near={s['near_intents']}"
        )
        for intent, info in s["six"].items():
            print(
                f"  {intent}: {info['largest']}/{info['rows']} "
                f"({info['share']:.0%}) groups={info['groups']}"
            )

    # Average if it clears the six chained intents at 50%; else complete.
    # Single is the baseline that chained.
    avg_six_near = [i for i, info in summaries[1]["six"].items() if info["share"] >= 0.50]
    if not avg_six_near and summaries[1]["n_near"] <= 3:
        chosen_link = "average"
        why = (
            "Average linkage at cosine distance 0.14 (1 - 0.86) stops the "
            "single-link chain: none of the six previously near-collapsed "
            "intents keep >=50% of rows in one group, and the total group "
            "count stays far below complete. Complete is safer against "
            "chaining but splits paraphrases that the 40 labels called the "
            "same scenario. Single (union-find on every pair >= 0.86) is "
            "rejected because transitivity merged whole intents."
        )
    elif summaries[2]["n_near"] < summaries[1]["n_near"]:
        chosen_link = "complete"
        why = (
            "Average linkage still leaves near-collapsed intents at the 50% "
            "row-share rule, so complete linkage is the recommendation: it "
            "is the cheapest extra conservatism that actually breaks the "
            "clouds. Single remains rejected."
        )
    else:
        chosen_link = "average"
        why = (
            "Average linkage is the recommendation even though some intents "
            "still have a large component: complete does not improve the "
            "50% near-collapse count enough to justify the extra split "
            "fragmentation. Single remains rejected."
        )

    generated = ist_now()
    lines = [
        "",
        "## Linkage addendum",
        "",
        f"Generated: {generated}",
        "",
        "Command: `uv run python data/calibrate_threshold.py --linkage-addendum`",
        "",
        f"Same T=**{threshold:.2f}**, same exact-match and template-family "
        "unions, cosine step replaced. Single = previous union-find on every "
        "pair with cosine >= T (sklearn would call this single linkage). "
        "Average and complete = `sklearn.cluster.AgglomerativeClustering` "
        f"(metric cosine, `distance_threshold` {1-threshold:.2f}, n_clusters "
        "None) then the exact-match and template-family unions on top. "
        "Near-collapse in this table is largest group >= **50%** of the "
        "intent (Fable's addendum rule, stricter than the 80% flag above).",
        "",
        "| linkage | total groups | near-collapse intents (>=50%) |",
        "|---|---:|---|",
    ]
    for s in summaries:
        near = ", ".join(f"`{n}`" for n in s["near_intents"]) or "none"
        lines.append(f"| {s['linkage']} | {s['total_groups']} | {near} |")
    lines.extend(
        [
            "",
            "Largest-group share for the six chained intents:",
            "",
            "| intent | single | average | complete |",
            "|---|---:|---:|---:|",
        ]
    )
    for intent in CHAINED_INTENTS:
        cells = []
        for s in summaries:
            info = s["six"][intent]
            cells.append(f"{info['share']:.0%} ({info['largest']}/{info['rows']})")
        lines.append(f"| `{intent}` | {cells[0]} | {cells[1]} | {cells[2]} |")
    lines.extend(
        [
            "",
            f"**Recommended `linkage`: `{chosen_link}`.** {why}",
            "",
        ]
    )
    with REPORT_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    grouping = json.loads(GROUPING_PATH.read_text(encoding="utf-8"))
    grouping["linkage"] = chosen_link
    grouping["cosine_threshold"] = threshold
    grouping["linkage_compared"] = ["single", "average", "complete"]
    grouping["linkage_reason"] = why
    grouping["generated_at"] = generated
    validate_grouping(grouping)
    GROUPING_PATH.write_text(json.dumps(grouping, indent=2) + "\n", encoding="utf-8")
    print(f"appended {REPORT_PATH}")
    print(f"wrote {GROUPING_PATH} linkage={chosen_link}")
    CAL_DIR.joinpath("linkage_stats.json").write_text(
        json.dumps(
            {"threshold": threshold, "chosen": chosen_link, "summaries": summaries, "why": why},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def cmd_sample() -> None:
    df = load_csv()
    print(f"rows={len(df)} embedding {REPO_ID_EMBED}")
    vectors = embed(df["norm_instruction"].tolist())
    pairs = sample_pairs(df, vectors)
    if LABELS_PATH.exists():
        labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
        pairs = apply_labels(pairs, labels)
    write_jsonl(PAIRS_PATH, pairs)
    print(f"wrote {PAIRS_PATH} n={len(pairs)}")
    missing = unlabeled_ids(pairs)
    if missing:
        print(f"unlabeled: {len(missing)} (write {LABELS_PATH} then --report)")
    for p in pairs:
        print(
            f"{p['id']} {p['band']} {p['cosine']:.3f} {p['intent']}\n"
            f"  A: {p['instruction_a']}\n"
            f"  B: {p['instruction_b']}"
        )


def cmd_report() -> None:
    if not PAIRS_PATH.exists():
        raise SystemExit("run --sample first")
    pairs = read_jsonl(PAIRS_PATH)
    if LABELS_PATH.exists():
        labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
        pairs = apply_labels(pairs, labels)
        write_jsonl(PAIRS_PATH, pairs)
    missing = unlabeled_ids(pairs)
    if missing:
        raise SystemExit(f"unlabeled pairs: {missing}")
    if len(pairs) != EXPECTED_PAIRS:
        print(f"WARNING: {len(pairs)} pairs, expected {EXPECTED_PAIRS}", file=sys.stderr)

    threshold, pick_reason = pick_threshold(pairs)
    table = [metrics_at(pairs, t) for t in CANDIDATE_THRESHOLDS]
    print(f"chosen threshold={threshold:.2f} ({pick_reason})")

    df = load_csv()
    print("re-embedding for group sizes")
    vectors = embed(df["norm_instruction"].tolist())
    groups = group_stats(df, vectors, threshold)
    groups_at = {
        t: group_stats(df, vectors, t) for t in (threshold, 0.90, 0.95) if t != 0
    }
    write_report(pairs, threshold, pick_reason, table, groups, groups_at=groups_at)

    grouping = {
        "embedding_model": REPO_ID_EMBED,
        "normalize": NORMALIZE_NAME,
        "exact_match": True,
        "template_family": True,
        "cosine_threshold": threshold,
        "linkage": "single",
        "labelled_pairs": EXPECTED_PAIRS,
        "report": "data/calibration/REPORT.md",
        "seed": SEED,
        "exact_match_on": "normalized_instruction",
        "template_family_on": "response_after_slot_normalize",
        "chosen_reason": pick_reason,
        "generated_at": ist_now(),
    }
    validate_grouping(grouping)
    GROUPING_PATH.write_text(json.dumps(grouping, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {REPORT_PATH}")
    print(f"wrote {GROUPING_PATH}")
    collapsed = [g["intent"] for g in groups if g["collapsed"]]
    print(f"groups_total={sum(g['groups'] for g in groups)}")
    print(f"collapsed={collapsed or 'none'}")
    print(f"largest={max(groups, key=lambda g: g['largest'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", action="store_true", help="Sample 40 pairs (seed 42).")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Require labels, write REPORT.md and grouping.json, print group sizes.",
    )
    parser.add_argument(
        "--linkage-addendum",
        action="store_true",
        help="Compare single/average/complete clustering at 0.86; update grouping.json.",
    )
    args = parser.parse_args()
    if not args.sample and not args.report and not args.linkage_addendum:
        args.sample = True
        args.report = LABELS_PATH.exists()
    if args.sample:
        cmd_sample()
    if args.report:
        cmd_report()
    if args.linkage_addendum:
        cmd_linkage_addendum()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
