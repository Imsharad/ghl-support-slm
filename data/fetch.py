"""Download, pin, and profile the Bitext customer-support dataset.

Public Hugging Face mirror of the Kaggle Bitext set. No Kaggle credentials.
Pinned by dataset-repo commit. CSV itself is gitignored under data/raw/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ID = "bitext/Bitext-customer-support-llm-chatbot-training-dataset"
REVISION = "430d1a89bd93bd1fa23c16f29dd53e73f0087443"
SOURCE_FILENAME = "Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv"
EXPECTED_ROWS = 26872
EXPECTED_INTENTS = 27
EXPECTED_CATEGORIES = 10
EXPECTED_COLUMNS = ["flags", "instruction", "category", "intent", "response"]
TOKENIZER_ID = "Qwen/Qwen2.5-1.5B-Instruct"
MAX_TRAIN_TOKENS = 512

SYSTEM_PROMPT = (
    "You are a customer support assistant. Answer clearly and helpfully. "
    "Do not invent company policy, account details, or completed actions. "
    "Ask for missing context when needed. Never ask for passwords or full "
    "payment card details."
)

FLAG_SOURCE = (
    "https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset"
    "#language-generation-tags"
)
FLAG_LETTERS = {
    "M": "Morphological variation (inflectional and derivational)",
    "L": "Semantic variations (synonyms, hyphens, compounding)",
    "B": "Basic syntactic structure",
    "I": "Interrogative structure",
    "C": "Coordinated syntactic structure",
    "N": "Negation",
    "P": "Politeness variation",
    "Q": "Colloquial variation",
    "W": "Offensive language",
    "K": "Keyword mode",
    "E": "Use of abbreviations",
    "Z": "Errors and Typos",
}
FLAG_UNUSED_IN_DATASET = {
    "D": "Indirect speech",
    "G": "Regional variations",
    "R": "Respect structures",
    "Y": "Code switching",
}

LICENSE = {
    "spdx": "CDLA-Sharing-1.0",
    "hf_id": "cdla-sharing-1.0",
    "url": "https://cdla.dev/sharing-1-0/",
    "pdf": "https://cdla.io/wp-content/uploads/sites/52/2017/10/CDLA-Sharing-v1.0.pdf",
    "dataset_card": (
        "https://huggingface.co/datasets/bitext/"
        "Bitext-customer-support-llm-chatbot-training-dataset"
    ),
    "text": (
        "Community Data License Agreement – Sharing, Version 1.0. "
        "Data is provided under this Agreement by each of the Data Providers. "
        "Section 2 grants a worldwide, non-exclusive, irrevocable right to Use "
        "and Publish Data, subject to Section 3: if You Publish Data You Receive "
        "or Enhanced Data, it must be Published under this same unmodified "
        "Agreement, with attribution preserved, and without further restrictions. "
        "Results of Computational Use are not required to be shared (Section 3.5). "
        "Full text: https://cdla.dev/sharing-1-0/"
    ),
}

PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")
IST = timezone(timedelta(hours=5, minutes=30))

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
CSV_PATH = RAW_DIR / "bitext.csv"
SHA_PATH = RAW_DIR / "bitext.csv.sha256"
SOURCES_PATH = ROOT / "artifacts" / "sources.json"
PROFILE_PATH = ROOT / "data" / "PROFILE.md"
INTENTS_PATH = ROOT / "data" / "intents.json"


def ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha_sidecar(digest: str) -> None:
    SHA_PATH.write_text(f"{digest}  bitext.csv\n", encoding="utf-8")


def load_sources() -> dict | None:
    if not SOURCES_PATH.exists():
        return None
    return json.loads(SOURCES_PATH.read_text(encoding="utf-8"))


def save_sources(payload: dict) -> None:
    SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    SOURCES_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def already_present() -> tuple[bool, str | None]:
    if not CSV_PATH.exists():
        return False, None
    digest = sha256_file(CSV_PATH)
    sources = load_sources()
    if (
        sources
        and sources.get("sha256") == digest
        and sources.get("revision") == REVISION
        and sources.get("repo_id") == REPO_ID
    ):
        return True, digest
    return False, digest


def count_rows(path: Path) -> int:
    import pandas as pd

    frame = pd.read_csv(path, keep_default_na=False)
    return int(len(frame))


def fetch() -> dict:
    present, digest = already_present()
    if present and digest is not None:
        print("already present, sha256 matches")
        print(f"path={CSV_PATH}")
        print(f"sha256={digest}")
        sources = load_sources()
        assert sources is not None
        return sources

    from huggingface_hub import snapshot_download

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"downloading {REPO_ID} @ {REVISION}")
    cache_dir = snapshot_download(
        repo_id=REPO_ID,
        repo_type="dataset",
        revision=REVISION,
        allow_patterns=[SOURCE_FILENAME],
    )
    src = Path(cache_dir) / SOURCE_FILENAME
    if not src.exists():
        raise FileNotFoundError(f"snapshot missing {SOURCE_FILENAME} under {cache_dir}")
    shutil.copy2(src, CSV_PATH)
    digest = sha256_file(CSV_PATH)
    write_sha_sidecar(digest)
    row_count = count_rows(CSV_PATH)
    downloaded_at = ist_now()
    mismatch = row_count != EXPECTED_ROWS
    if mismatch:
        print(
            f"WARNING: row_count={row_count} differs from expected {EXPECTED_ROWS}",
            file=sys.stderr,
        )
    sources = {
        "repo_id": REPO_ID,
        "revision": REVISION,
        "source_filename": SOURCE_FILENAME,
        "local_path": "data/raw/bitext.csv",
        "sha256": digest,
        "row_count": row_count,
        "row_count_expected": EXPECTED_ROWS,
        "row_count_matches_expected": not mismatch,
        "downloaded_at": downloaded_at,
        "columns": EXPECTED_COLUMNS,
        "license": LICENSE,
        "mirror_of": "kaggle.com/datasets/bitext/bitext-gen-ai-chatbot-customer-support-dataset",
    }
    if mismatch:
        sources["warning"] = (
            f"row_count {row_count} != expected {EXPECTED_ROWS}; "
            "do not treat this pin as the assignment's 26,872-row set without review"
        )
    save_sources(sources)
    print(f"wrote {CSV_PATH}")
    print(f"sha256={digest}")
    print(f"row_count={row_count}")
    print(f"revision={REVISION}")
    print(f"downloaded_at={downloaded_at}")
    return sources


def _pct(values: list[int]) -> dict[str, float | int]:
    import numpy as np

    arr = np.asarray(values, dtype=np.float64)
    out: dict[str, float | int] = {}
    for label, q in (("p50", 50), ("p90", 90), ("p99", 99)):
        raw = float(np.percentile(arr, q))
        out[label] = int(raw) if raw.is_integer() else round(raw, 1)
    out["max"] = int(arr.max())
    mean = float(arr.mean())
    out["mean"] = int(mean) if mean.is_integer() else round(mean, 1)
    return out


def _md_pct_row(name: str, stats: dict[str, float | int]) -> str:
    return (
        f"| {name} | {stats['p50']} | {stats['p90']} | {stats['p99']} | "
        f"{stats['max']} | {stats['mean']} |"
    )


def _dup_report(series) -> dict[str, int]:
    counts = series.value_counts()
    duplicated_values = counts[counts > 1]
    extra_rows = int((duplicated_values - 1).sum()) if len(duplicated_values) else 0
    return {
        "unique": int(series.nunique()),
        "values_with_duplicates": int(len(duplicated_values)),
        "rows_in_duplicate_groups": int(duplicated_values.sum()) if len(duplicated_values) else 0,
        "extra_rows_beyond_first": extra_rows,
    }


def _token_lengths(texts: list[str], tokenizer, batch_size: int = 512) -> list[int]:
    lengths: list[int] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        encoded = tokenizer(batch, add_special_tokens=False, padding=False)
        lengths.extend(len(ids) for ids in encoded["input_ids"])
    return lengths


def profile(sources: dict) -> None:
    import pandas as pd
    from transformers import AutoTokenizer

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    df = pd.read_csv(CSV_PATH, keep_default_na=False)
    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"CSV missing columns {missing}; have {list(df.columns)}")

    row_count = int(len(df))
    intent_counts = df["intent"].value_counts()
    category_counts = df["category"].value_counts()
    n_intents = int(intent_counts.shape[0])
    n_categories = int(category_counts.shape[0])

    instr_words = [len(text.split()) for text in df["instruction"].tolist()]
    resp_words = [len(text.split()) for text in df["response"].tolist()]

    print(f"loading tokenizer {TOKENIZER_ID}")
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_ID, use_fast=True)
    instr_tokens = _token_lengths(df["instruction"].tolist(), tokenizer)
    resp_tokens = _token_lengths(df["response"].tolist(), tokenizer)

    rendered: list[str] = []
    for instruction, response in zip(df["instruction"].tolist(), df["response"].tolist()):
        rendered.append(
            tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": instruction},
                    {"role": "assistant", "content": response},
                ],
                tokenize=False,
                add_generation_prompt=False,
            )
        )
    total_tokens = _token_lengths(rendered, tokenizer)
    n_over_512 = int(sum(n > MAX_TRAIN_TOKENS for n in total_tokens))

    instr_dups = _dup_report(df["instruction"])
    resp_dups = _dup_report(df["response"])
    full_dups = _dup_report(df.astype(str).agg("\t".join, axis=1))

    placeholder_counts: Counter[str] = Counter()
    for text in df["response"].tolist():
        placeholder_counts.update(PLACEHOLDER_RE.findall(text))

    template_counts: Counter[str] = Counter()
    for text in df["response"].tolist():
        words = text.split()
        template_counts[" ".join(words[:8])] += 1

    letter_counts: Counter[str] = Counter()
    combo_counts = df["flags"].value_counts()
    unknown_letters: Counter[str] = Counter()
    for flags in df["flags"].tolist():
        for letter in str(flags):
            letter_counts[letter] += 1
            if letter not in FLAG_LETTERS and letter not in FLAG_UNUSED_IN_DATASET:
                unknown_letters[letter] += 1

    intents: list[dict[str, str]] = []
    for intent, group in df.groupby("intent", sort=True):
        basic = group[group["flags"] == "B"]
        pick = basic.iloc[0] if len(basic) else group.iloc[0]
        intents.append(
            {
                "intent": str(intent),
                "category": str(pick["category"]),
                "example": str(pick["instruction"]),
            }
        )
    INTENTS_PATH.write_text(json.dumps(intents, indent=2) + "\n", encoding="utf-8")

    generated_at = ist_now()
    instr_word_pct = _pct(instr_words)
    resp_word_pct = _pct(resp_words)
    instr_tok_pct = _pct(instr_tokens)
    resp_tok_pct = _pct(resp_tokens)
    total_tok_pct = _pct(total_tokens)

    def count_table(title: str, counts, expected: int) -> list[str]:
        lines = [
            f"### {title}",
            "",
            f"Command: `uv run python data/fetch.py --profile`",
            "",
            f"Distinct: **{len(counts)}** (expected {expected}"
            + (
                "; MATCHES"
                if len(counts) == expected
                else f"; DIFFERS from expected {expected}"
            )
            + ").",
            "",
            "| name | rows | share |",
            "|---|---:|---:|",
        ]
        for name, n in counts.items():
            share = 100.0 * n / row_count
            lines.append(f"| `{name}` | {int(n)} | {share:.2f}% |")
        lines.append("")
        return lines

    mismatch_lines: list[str] = []
    if row_count != EXPECTED_ROWS:
        mismatch_lines.append(
            f"**Row-count mismatch:** CSV has **{row_count}** rows; assignment "
            f"and dataset card say **{EXPECTED_ROWS}**. Recorded in "
            f"`artifacts/sources.json` as `row_count_matches_expected: false`."
        )
    if n_intents != EXPECTED_INTENTS:
        mismatch_lines.append(
            f"**Intent-count mismatch:** {n_intents} distinct intents; expected {EXPECTED_INTENTS}."
        )
    if n_categories != EXPECTED_CATEGORIES:
        mismatch_lines.append(
            f"**Category-count mismatch:** {n_categories} distinct categories; "
            f"expected {EXPECTED_CATEGORIES}."
        )

    lines: list[str] = [
        "# Bitext dataset profile",
        "",
        f"Generated: {generated_at}",
        "",
        "Commands:",
        "",
        "- `uv run python data/fetch.py` — download/pin (idempotent)",
        "- `uv run python data/fetch.py --profile` — this file, `data/intents.json`",
        "",
        "Source: Hugging Face "
        f"`{REPO_ID}` revision `{REVISION}` "
        f"({SOURCE_FILENAME}). Local copy `data/raw/bitext.csv` "
        f"(gitignored). SHA-256 `{sources['sha256']}`.",
        "",
        "License: CDLA-Sharing-1.0 "
        "(https://cdla.dev/sharing-1-0/). Publishing the CSV requires sharing "
        "under the same agreement; computational results do not. Raw file is "
        "gitignored; this pin records how to re-fetch it.",
        "",
        "## Row count",
        "",
        "Command: `uv run python data/fetch.py --profile`",
        "",
        f"- rows: **{row_count}**",
        f"- expected: **{EXPECTED_ROWS}**",
        f"- match: **{'yes' if row_count == EXPECTED_ROWS else 'NO'}**",
        f"- columns: `{', '.join(EXPECTED_COLUMNS)}`",
        "",
    ]
    if mismatch_lines:
        lines.append("### Mismatches vs assignment card")
        lines.append("")
        lines.extend(f"- {item}" for item in mismatch_lines)
        lines.append("")

    lines.extend(count_table("Per-intent counts", intent_counts, EXPECTED_INTENTS))
    lines.extend(count_table("Per-category counts", category_counts, EXPECTED_CATEGORIES))
    lines.extend(
        [
            "The assignment/card list of 10 omits `CONTACT` (1999 rows: "
            "`contact_customer_service` + `contact_human_agent`). CSV names also "
            "differ from the card: `CANCEL` = card `CANCELLATION_FEE`, "
            "`SHIPPING` = `SHIPPING_ADDRESS`, `SUBSCRIPTION` = `NEWSLETTER`. "
            "Each intent maps to exactly one category.",
            "",
        ]
    )

    lines.extend(
        [
            "## Length distributions",
            "",
            "Command: `uv run python data/fetch.py --profile`",
            "",
            "Words = `str.split()` whitespace tokens. Qwen tokens = "
            f"`{TOKENIZER_ID}` via `transformers.AutoTokenizer`, "
            "`add_special_tokens=False`.",
            "",
            "| series | p50 | p90 | p99 | max | mean |",
            "|---|---:|---:|---:|---:|---:|",
            _md_pct_row("instruction words", instr_word_pct),
            _md_pct_row("response words", resp_word_pct),
            _md_pct_row("instruction Qwen tokens", instr_tok_pct),
            _md_pct_row("response Qwen tokens", resp_tok_pct),
            _md_pct_row("full ChatML Qwen tokens", total_tok_pct),
            "",
            "Full ChatML = native Qwen2.5 template with one system turn "
            "(exact `configs/prompt.txt` text), user = instruction, "
            "assistant = response, `add_generation_prompt=False`. This is the "
            f"training example. Rows with total tokens > {MAX_TRAIN_TOKENS} "
            f"(train max length): **{n_over_512}** / {row_count} "
            f"({100.0 * n_over_512 / row_count:.2f}%).",
            "",
            "## Exact duplicates",
            "",
            "Command: `uv run python data/fetch.py --profile`",
            "",
            "| field | unique values | values with dups | rows in dup groups | extra rows beyond first |",
            "|---|---:|---:|---:|---:|",
            (
                f"| instruction | {instr_dups['unique']} | "
                f"{instr_dups['values_with_duplicates']} | "
                f"{instr_dups['rows_in_duplicate_groups']} | "
                f"{instr_dups['extra_rows_beyond_first']} |"
            ),
            (
                f"| response | {resp_dups['unique']} | "
                f"{resp_dups['values_with_duplicates']} | "
                f"{resp_dups['rows_in_duplicate_groups']} | "
                f"{resp_dups['extra_rows_beyond_first']} |"
            ),
            (
                f"| full row (all columns) | {full_dups['unique']} | "
                f"{full_dups['values_with_duplicates']} | "
                f"{full_dups['rows_in_duplicate_groups']} | "
                f"{full_dups['extra_rows_beyond_first']} |"
            ),
            "",
            "## Flags column",
            "",
            "Command: `uv run python data/fetch.py --profile`",
            "",
            "Bitext Language Generation Tags. Each `flags` value is a string of "
            "letters; a row can carry several. Source: "
            f"{FLAG_SOURCE} (dataset card, retrieved 2026-09-05).",
            "",
            "| letter | meaning (Bitext) | rows with letter |",
            "|---|---|---:|",
        ]
    )
    for letter, meaning in FLAG_LETTERS.items():
        lines.append(f"| {letter} | {meaning} | {letter_counts.get(letter, 0)} |")
    lines.extend(
        [
            "",
            "Documented by Bitext as not used in this dataset: "
            + ", ".join(
                f"{letter} ({meaning})"
                for letter, meaning in FLAG_UNUSED_IN_DATASET.items()
            )
            + ".",
            "",
        ]
    )
    unused_seen = [
        f"{letter}={letter_counts[letter]}"
        for letter in FLAG_UNUSED_IN_DATASET
        if letter_counts[letter]
    ]
    if unused_seen:
        lines.append(
            "Observed despite 'not in use' note: " + ", ".join(unused_seen) + "."
        )
        lines.append("")
    if unknown_letters:
        lines.append(
            "Unknown letters not in the Bitext tag list: "
            + ", ".join(f"{k}={v}" for k, v in sorted(unknown_letters.items()))
            + "."
        )
        lines.append("")
    lines.extend(
        [
            f"Distinct flag combinations: **{int(combo_counts.shape[0])}**.",
            "",
            "Top 15 combinations:",
            "",
            "| flags | rows |",
            "|---|---:|",
        ]
    )
    for flags, n in combo_counts.head(15).items():
        lines.append(f"| `{flags}` | {int(n)} |")
    lines.extend(
        [
            "",
            "## Placeholder tokens in responses",
            "",
            "Command: `uv run python data/fetch.py --profile`",
            "",
            "Pattern: `{{...}}` (no nested braces). Counts are occurrence totals "
            "across all response strings, not distinct rows.",
            "",
            f"Distinct placeholders: **{len(placeholder_counts)}**. "
            f"Total occurrences: **{sum(placeholder_counts.values())}**. "
            f"{sum(1 for n in placeholder_counts.values() if n >= 10)} names "
            f"occur >= 10 times; "
            f"{sum(1 for n in placeholder_counts.values() if n <= 3)} names "
            "occur <= 3 times (free-typed variants, not a closed inventory). "
            "B1 should treat the long tail as noise.",
            "",
            "| placeholder | occurrences |",
            "|---|---:|",
        ]
    )
    for token, n in placeholder_counts.most_common():
        lines.append(f"| `{token}` | {n} |")
    lines.extend(
        [
            "",
            "## Most common response templates (first 8 words)",
            "",
            "Command: `uv run python data/fetch.py --profile`",
            "",
            "Template = first eight whitespace-separated words of `response`, "
            "original casing, single spaces.",
            "",
            "| rank | first 8 words | rows |",
            "|---:|---|---:|",
        ]
    )
    for rank, (tmpl, n) in enumerate(template_counts.most_common(20), start=1):
        safe = tmpl.replace("|", "\\|")
        lines.append(f"| {rank} | {safe} | {n} |")
    lines.extend(
        [
            "",
            "## Intent examples",
            "",
            f"One instruction per intent in `data/intents.json` ({len(intents)} "
            "objects `{intent, category, example}`). Prefers a row with "
            "`flags == \"B\"` (basic syntactic structure) when one exists.",
            "",
            "Command: `uv run python data/fetch.py --profile`",
            "",
        ]
    )
    PROFILE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    sources = dict(sources)
    sources["profiled_at"] = generated_at
    sources["n_intents"] = n_intents
    sources["n_categories"] = n_categories
    sources["n_over_512_chatml_tokens"] = n_over_512
    sources["tokenizer_id"] = TOKENIZER_ID
    save_sources(sources)

    print(f"wrote {PROFILE_PATH}")
    print(f"wrote {INTENTS_PATH}")
    print(f"rows={row_count} intents={n_intents} categories={n_categories}")
    print(f"over_512={n_over_512}")
    print(f"placeholders={len(placeholder_counts)}")
    print(f"instr_dups_extra={instr_dups['extra_rows_beyond_first']}")
    print(f"resp_dups_extra={resp_dups['extra_rows_beyond_first']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Write data/PROFILE.md and data/intents.json after ensuring the CSV is present.",
    )
    args = parser.parse_args()
    sources = fetch()
    if args.profile:
        profile(sources)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
