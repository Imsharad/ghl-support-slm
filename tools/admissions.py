#!/usr/bin/env python3
"""V2 admission rows: generate, lint, leakage, assemble.

The rows teach one behaviour the v1 cleaner deleted: say the fact is not
available, say where it can be obtained, offer one thing that is actually
permitted. Row text is written by a stateless Gemini 3.8 Flash call through
``agy`` from an empty working directory. This module never writes or edits row
text; a row that fails lint or leakage is regenerated, never patched.

Commands
--------
generate   fill the per-intent quota, lint every row, write raw rows + provenance
lint       re-run the lint over a rows file and print the failures
leakage    both text fields against the eval queries and the v2 val/test splits
assemble   ids, group ids, flags, cleaning, n_tokens through the frozen renderer

Usage
-----
uv run python tools/admissions.py generate --out data/v2/admissions_raw.jsonl
uv run python tools/admissions.py generate --intent cancel_order --n 4 --out /tmp/dry.jsonl
uv run python tools/admissions.py lint data/v2/admissions_raw.jsonl
uv run python tools/admissions.py leakage --input data/v2/admissions_raw.jsonl
uv run python tools/admissions.py assemble --input data/v2/admissions_accepted.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

INTENTS_PATH = ROOT / "data" / "intents.json"
V2_DIR = ROOT / "data" / "v2"
PROCESSED_V2 = ROOT / "data" / "processed" / "v2"

RAW_PATH = V2_DIR / "admissions_raw.jsonl"
ACCEPTED_PATH = V2_DIR / "admissions.jsonl"
QUARANTINE_PATH = V2_DIR / "admissions_quarantine.jsonl"
REVIEW_PATH = V2_DIR / "admission_review.jsonl"
LEAKAGE_PATH = V2_DIR / "leakage.json"
PARTIAL_ROWS_PATH = V2_DIR / "admissions_partial.jsonl"
PARTIAL_REVIEW_PATH = V2_DIR / "admission_review_partial.jsonl"
CELL_ORDER_SEED = 42

MODEL = "gemini-3.8-flash-high"
SEED = 42
MAX_LENGTH = 512
FLAG = "SYNTH_ADMISSION"
CLEANING_TAG = "synthetic_admission_v2"
WORD_MIN = 35
WORD_MAX = 75

# eval/check_challenge.py AGAINST_CAP; frozen here before any row is generated.
COSINE_CAP = 0.80
NGRAM_N = 6

# Pre-registered design targets, docs/plans/V2_PLAN.md section 4. Decision 10 in
# docs/v2/PLAN_DECISIONS.md: accepted rows may fall short; every intent must have
# at least one accepted row before assembly.
QUOTAS: dict[str, int] = {
    "cancel_order": 24,
    "change_order": 12,
    "change_shipping_address": 12,
    "check_cancellation_fee": 24,
    "check_invoice": 24,
    "check_payment_methods": 24,
    "check_refund_policy": 24,
    "complaint": 12,
    "contact_customer_service": 24,
    "contact_human_agent": 12,
    "create_account": 8,
    "delete_account": 12,
    "delivery_options": 24,
    "delivery_period": 24,
    "edit_account": 8,
    "get_invoice": 12,
    "get_refund": 24,
    "newsletter_subscription": 8,
    "payment_issue": 24,
    "place_order": 8,
    "recover_password": 12,
    "registration_problems": 12,
    "review": 8,
    "set_up_shipping_address": 8,
    "switch_account": 8,
    "track_order": 24,
    "track_refund": 24,
}

HARD_STYLES = ("typos", "anger", "two_requests", "no_identifier")
STYLES = ("ordinary",) + HARD_STYLES

STYLE_BRIEF = {
    "ordinary": (
        "an ordinary, calm request in plain words, one clear ask, correctly spelled"
    ),
    "typos": (
        "a request with real typing mistakes: transposed letters, missing letters, "
        "lowercase, a missing apostrophe. Still readable. Do not spell out a number"
    ),
    "anger": (
        "an angry, frustrated request. Sharp and short sentences, no profanity, "
        "no threats, no invented history of past contacts"
    ),
    "two_requests": (
        "one message that asks two different things at once, both answerable in "
        "kind, joined naturally"
    ),
    "no_identifier": (
        "a request that never gives an order number, account name, email or any "
        "other identifier, and does not mention having one"
    ),
}

# Scenario sketches. Deterministic from (intent, style, serial); they carry no
# fact, no quantity and no company detail, only a framing so the batch does not
# collapse into one template.
SCENE_WHO = (
    "someone who shops here occasionally",
    "a long-time customer",
    "a first-time customer",
    "someone helping a family member with their account",
    "a customer writing from their phone",
    "a customer who has already looked around the site",
)
SCENE_WHEN = (
    "writing in the middle of the working day",
    "writing late at night",
    "writing while travelling",
    "writing at the weekend",
    "writing straight after opening the account page",
    "writing after giving up on finding it themselves",
)
SCENE_WHY = (
    "they need to decide what to do next",
    "they want to stop guessing",
    "they are planning around this",
    "they have to tell someone else what is happening",
    "they do not want to repeat a mistake",
    "they want it settled today",
)

SCHEMA = {
    "type": "object",
    "properties": {
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "answer": {"type": "string"},
                },
                "required": ["query", "answer"],
            },
        }
    },
    "required": ["rows"],
}

PROMPT = """\
You write single-turn training examples for a customer-support assistant that is \
honest about what it does not know. You are writing {n} examples, all for the same \
intent, all in the same query style. Return them in the required JSON shape and \
write nothing else.

INTENT: {intent}
CATEGORY: {category}
QUERY STYLE: {style_brief}

SCENARIOS, one per example, in order. Use each only as framing; never state a \
scenario detail back as a fact about the account or the order:
{scenes}

Each example is a customer message ("query") and the assistant's reply ("answer").

THE ANSWER MUST DO THREE THINGS, IN THIS ORDER:
1. Say plainly that the specific fact the customer wants is not something you \
have access to. Name the fact.
2. Say where the customer can obtain it: the account portal, the order details, \
the published policy, the official website, or the official contact page. Pick the \
one that fits.
3. Give exactly one concrete thing you can do right now that needs no lookup, no \
account access and no knowledge of this company's rules. Pick one: describe where \
on that page to look and what the customer will see there, draft the message the \
customer should send, or list what information they should have to hand before \
they go. Then stop.

ANSWER LENGTH: between {word_min} and {word_max} words. Count them.

If the query asks two things, address both. Do not refuse a part of the question \
that can honestly be answered from general knowledge of how support works.

FORBIDDEN IN BOTH THE QUERY AND THE ANSWER, without exception:
- Any digit, and any number written as a word, in either field.
- Any clock time, day, date, duration or waiting period.
- Any price, amount, fee, percentage or currency symbol.
- Any URL, domain, email address, phone number or app name.
- The words guarantee, guaranteed, allows, requires, waives, entitles, qualifies, \
within, always, and the phrase twenty-four seven.
- The openers "I'm on it", "I'm on the same wavelength", and the phrase \
"Rest assured".
- Asking for a password, PIN, one-time code, card number or any credential.
- Claiming you have done, checked, processed, cancelled, updated, refunded or \
escalated anything. You have taken no action.
- Offering to look something up, pull up an order, check a status, process a \
request, issue anything, transfer the customer or connect them to a person or a \
team.
- Asserting that a page, button, feature, channel or department exists beyond the \
five places named in point 2.
- Stating what the company's policy or process actually is. You do not know \
whether cancellation stops a shipment, what happens after packing, what a request \
triggers, or what confirmation follows. Never write a sentence of the form "X \
happens when Y". Point at the published policy instead.
- Repeating a sentence, an opening or a closing from another example in this \
batch. Every query must open on a different word and ask in a different shape; \
every answer must be built from different sentences.

Do not open two answers with the same words. Vary the sentence shapes.\
"""


# --------------------------------------------------------------------------- io


def load_intents() -> dict[str, str]:
    rows = json.loads(INTENTS_PATH.read_text(encoding="utf-8"))
    return {str(row["intent"]): str(row["category"]) for row in rows}


def read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def append_jsonl(path: Path, rows: Sequence[dict]) -> None:
    """Append and flush to disk as a cell returns. The final files are still
    written whole at the end; these partials are what a kill or a cutoff keeps."""
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def write_jsonl(path: Path, rows: Sequence[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------------- lint

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")

NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
    "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
    "thousand", "million", "dozen", "couple", "few", "several",
    "first", "second", "third", "fourth", "fifth", "half", "quarter",
}
TIME_WORDS = {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "sunday", "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "minute", "minutes", "hour", "hours", "day", "days", "week", "weeks",
    "month", "months", "year", "years", "am", "pm", "noon", "midnight",
    "today", "tomorrow", "yesterday", "tonight", "immediately", "instantly",
    "asap", "deadline",
}
POLICY_VERBS = {
    "guarantee", "guarantees", "guaranteed", "guaranteeing", "guarantor",
    "allow", "allows", "allowed", "require", "requires", "required",
    "waive", "waives", "waived", "entitle", "entitles", "entitled",
    "qualify", "qualifies", "qualified", "within", "always", "never",
    "ensure", "ensures", "ensured", "promise", "promises", "promised",
}
CURRENCY_WORDS = {
    "price", "prices", "cost", "costs", "fee", "fees", "charge", "charges",
    "amount", "amounts", "refundable", "percent", "percentage", "dollar",
    "dollars", "euro", "euros", "pound", "pounds", "rupee", "rupees", "free",
}
CURRENCY_CHARS = "$€£¥₹¢%"

BITEXT_OPENERS = ("i'm on it", "i am on it", "i'm on the same wavelength", "rest assured")
CREDENTIAL_PAT = re.compile(
    r"(?i)\b(password|passwords|pin|otp|cvv|cvc|passcode|credential|credentials|"
    r"one-time code|security code|verification code|card number|login details)\b"
)
COMPLETED_PAT = re.compile(
    r"(?i)\b(i(?:'ve| have)\s+(?:already\s+)?(?:processed|cancelled|canceled|updated|"
    r"refunded|escalated|checked|located|found|submitted|changed|removed|sent|raised|"
    r"gone ahead|arranged|reset|opened)"
    r"|has been (?:processed|cancelled|canceled|updated|refunded|escalated|raised|reset)"
    r"|have been (?:processed|cancelled|canceled|updated|refunded|escalated|raised|reset))"
)
OFFER_PAT = re.compile(
    r"(?i)("
    r"\b(?:i(?:'ll| will| can)|let me|allow me to|happy to)\s+"
    r"(?:just\s+|quickly\s+|go ahead and\s+)?"
    r"(?:look(?:ing)? up|look into|pull up|check|verify|confirm|track|locate|find|"
    r"retrieve|process|issue|cancel|refund|update|escalate|raise|forward|transfer|"
    r"connect|put you through|reset|open|arrange|submit)"
    r"|\bconnect(?:ing)? you\b|\btransfer(?:ring)? you\b|\bput you through\b"
    r"|\bour (?:team|agents?|department|specialists?)\s+(?:will|can)\b"
    r"|\ba (?:representative|specialist|agent|colleague)\s+(?:will|can)\b"
    r")"
)
URL_PAT = re.compile(r"(?i)(https?://|www\.|\b[a-z0-9-]+\.(?:com|net|org|io|co|in)\b|@[a-z0-9-]+\.)")


def _words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def word_count(text: str) -> int:
    return len(_words(text))


def lint_field(text: str, field: str) -> list[str]:
    """Return the rule ids this field breaks. Applied to query and answer alike."""
    bad: list[str] = []
    lower = text.casefold()
    if any(unicodedata.category(ch) == "Nd" for ch in text):
        bad.append(f"{field}:digit")
    if any(ch in CURRENCY_CHARS for ch in text):
        bad.append(f"{field}:currency_symbol")
    if URL_PAT.search(text):
        bad.append(f"{field}:url_or_address")
    lowered_words = {word.casefold().strip("-'’") for word in _words(text)}
    if lowered_words & NUMBER_WORDS:
        bad.append(f"{field}:number_word")
    if lowered_words & TIME_WORDS:
        bad.append(f"{field}:time_or_duration")
    if lowered_words & POLICY_VERBS:
        bad.append(f"{field}:policy_verb")
    if lowered_words & CURRENCY_WORDS:
        bad.append(f"{field}:price_word")
    if "24/7" in text or "twenty-four seven" in lower or "24x7" in lower:
        bad.append(f"{field}:always_open")
    if CREDENTIAL_PAT.search(text):
        bad.append(f"{field}:credential_request")
    return sorted(set(bad))


def lint_row(row: dict) -> list[str]:
    query = str(row.get("query", ""))
    answer = str(row.get("answer", ""))
    bad = lint_field(query, "query") + lint_field(answer, "answer")
    stripped = answer.lstrip().casefold()
    for opener in BITEXT_OPENERS:
        if stripped.startswith(opener) or opener in stripped:
            bad.append("answer:bitext_opener")
            break
    if COMPLETED_PAT.search(answer):
        bad.append("answer:completed_action")
    if OFFER_PAT.search(answer):
        bad.append("answer:offers_lookup_or_transfer")
    n_words = word_count(answer)
    if n_words < WORD_MIN or n_words > WORD_MAX:
        bad.append(f"answer:word_band({n_words})")
    if word_count(query) < 4:
        bad.append("query:too_short")
    return sorted(set(bad))


# --------------------------------------------------------------------- generate


def style_plan(n: int) -> list[str]:
    """Half ordinary, half hard; every hard style appears at least once."""
    n_ordinary = n // 2
    plan = ["ordinary"] * n_ordinary
    for index in range(n - n_ordinary):
        plan.append(HARD_STYLES[index % len(HARD_STYLES)])
    return plan


def scenario(intent: str, style: str, serial: int) -> str:
    digest = hashlib.sha256(f"{SEED}:{intent}:{style}:{serial}".encode("utf-8")).digest()
    who = SCENE_WHO[digest[0] % len(SCENE_WHO)]
    when = SCENE_WHEN[digest[1] % len(SCENE_WHEN)]
    why = SCENE_WHY[digest[2] % len(SCENE_WHY)]
    return f"{who}, {when}; {why}"


def build_prompt(intent: str, category: str, style: str, scenes: Sequence[str]) -> str:
    numbered = "\n".join(f"{index + 1}. {scene}" for index, scene in enumerate(scenes))
    return PROMPT.format(
        n=len(scenes),
        intent=intent,
        category=category,
        style_brief=STYLE_BRIEF[style],
        scenes=numbered,
        word_min=WORD_MIN,
        word_max=WORD_MAX,
    )


def call_flash(prompt: str, timeout: str = "8m") -> list[dict]:
    """One stateless agy call from an empty cwd. Returns the parsed rows."""
    with tempfile.TemporaryDirectory() as work:
        schema_path = Path(work) / "schema.json"
        schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
        proc = subprocess.run(
            [
                "agy",
                f"-p={prompt}",
                "--model",
                MODEL,
                "--output-format",
                "json",
                "--json-schema",
                "schema.json",
                "--dangerously-skip-permissions",
                "--print-timeout",
                timeout,
            ],
            cwd=work,
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": os.environ.get("HOME", work)},
            # agy ships a KillAll path over its own process group. Sharing our
            # session let one call take python and every sibling call with it,
            # silently. Its own session means a group kill reaches only itself,
            # which surfaces here as batch:call_failed and is retried.
            start_new_session=True,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"agy exit {proc.returncode}: {proc.stderr.strip()[:400]}")
    envelope = json.loads(proc.stdout)
    structured = envelope.get("structured_output") or {}
    rows = structured.get("rows") or []
    return [row for row in rows if isinstance(row, dict)]


def prompt_sha(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def generate_cell(
    intent: str, category: str, style: str, want: int, attempts: int, batch: int
) -> tuple[list[dict], list[dict]]:
    """Fill one (intent, style) cell. Returns (accepted rows, provenance lines)."""
    accepted: list[dict] = []
    review: list[dict] = []
    seen_grams: set[tuple[str, ...]] = set()
    serial = 0
    for attempt in range(attempts):
        missing = want - len(accepted)
        if missing <= 0:
            break
        size = max(1, min(batch, missing))
        scenes = [scenario(intent, style, serial + offset) for offset in range(size)]
        serial += size
        prompt = build_prompt(intent, category, style, scenes)
        digest = prompt_sha(prompt)
        batch_id = f"{intent}:{style}:{attempt}"
        try:
            rows = call_flash(prompt)
        except Exception as error:  # a failed call is retried, never patched
            review.append({
                "batch_id": batch_id,
                "model": MODEL,
                "prompt_sha256": digest,
                "style": style,
                "intent": intent,
                "lint": ["batch:call_failed"],
                "error": str(error)[:200],
                "leakage": None,
                "review_status": "",
            })
            continue
        for index, row in enumerate(rows):
            failures = lint_row(row)
            record = {
                "batch_id": batch_id,
                "batch_index": index,
                "model": MODEL,
                "prompt_sha256": digest,
                "style": style,
                "intent": intent,
                "category": category,
                "lint": failures,
                "leakage": None,
                "review_status": "",
            }
            if failures:
                review.append(record)
                continue
            if len(accepted) >= want:
                record["lint"] = ["batch:over_quota"]
                review.append(record)
                continue
            # Queries only. Answers are supposed to share the admission phrasing;
            # that repetition is the behaviour being taught, not template collapse.
            grams = word_ngrams(str(row["query"]))
            if grams & seen_grams:
                # Template collapse. The row is regenerated, never edited.
                record["lint"] = ["batch:duplicate_6gram"]
                review.append(record)
                continue
            seen_grams |= grams
            keep = {
                "intent": intent,
                "category": category,
                "style": style,
                "query": str(row["query"]).strip(),
                "answer": str(row["answer"]).strip(),
                "batch_id": batch_id,
                "prompt_sha256": digest,
            }
            accepted.append(keep)
            review.append(record)
    return accepted, review


def cmd_generate(args: argparse.Namespace) -> int:
    intents = load_intents()
    if args.intent:
        if args.intent not in intents:
            print(f"unknown intent: {args.intent}", file=sys.stderr)
            return 1
        targets = {args.intent: args.n or QUOTAS[args.intent]}
    else:
        targets = dict(QUOTAS)
        if args.n:
            targets = {name: args.n for name in targets}
    cells: list[tuple[str, str, str, int]] = []
    for intent, total in targets.items():
        plan = style_plan(total)
        for style in STYLES:
            want = plan.count(style)
            if want:
                cells.append((intent, intents[intent], style, want))
    # Interleave the intents so a cutoff leaves every intent with rows rather
    # than the tail intents with none. Seeded, so the order is reproducible.
    random.Random(CELL_ORDER_SEED).shuffle(cells)
    print(
        f"cells={len(cells)} rows_wanted={sum(cell[3] for cell in cells)} "
        f"model={MODEL} parallel={args.parallel} cell_order_seed={CELL_ORDER_SEED}"
    )
    partial_rows = Path(args.partial_rows)
    partial_review = Path(args.partial_review)
    accepted: list[dict] = []
    review: list[dict] = []
    if args.resume and partial_rows.exists():
        # This machine kills the run at unpredictable times. A relaunch keeps the
        # cells an earlier attempt already banked and only redoes what is missing;
        # a cell counts as done only when it has its full quota on disk.
        prior_rows = read_jsonl(partial_rows)
        prior_review = read_jsonl(partial_review) if partial_review.exists() else []
        have: dict[tuple[str, str], int] = {}
        for row in prior_rows:
            key = (str(row["intent"]), str(row["style"]))
            have[key] = have.get(key, 0) + 1
        done_cells = {
            (intent, style)
            for intent, _, style, want in cells
            if have.get((intent, style), 0) >= want
        }
        accepted = [
            row for row in prior_rows
            if (str(row["intent"]), str(row["style"])) in done_cells
        ]
        review = [
            line for line in prior_review
            if (str(line.get("intent")), str(line.get("style"))) in done_cells
        ]
        cells = [cell for cell in cells if (cell[0], cell[2]) not in done_cells]
        print(
            f"resume: {len(done_cells)} cells already banked, {len(accepted)} rows kept, "
            f"{len(cells)} cells left",
            flush=True,
        )
    else:
        for stale in (partial_rows, partial_review):
            if stale.exists():
                stale.unlink()
    done = 0
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        future_cell = {
            pool.submit(generate_cell, intent, category, style, want, args.attempts, args.batch):
                (intent, style, want)
            for intent, category, style, want in cells
        }
        # as_completed, not submission order: a cell is written the moment it
        # returns, so a kill keeps everything finished up to that point.
        for future in as_completed(future_cell):
            intent, style, want = future_cell[future]
            rows, lines = future.result()
            for line in lines:
                line["cell_order_seed"] = CELL_ORDER_SEED
            accepted.extend(rows)
            review.extend(lines)
            append_jsonl(partial_rows, rows)
            append_jsonl(partial_review, lines)
            done += 1
            print(f"{intent:<24} {style:<13} {len(rows)}/{want}  [{done}/{len(cells)}]", flush=True)
    # Cells run in parallel, so a repeat across two cells only shows up here.
    # Cross-cell duplicates are dropped and reported as a shortfall, not patched.
    deduped: list[dict] = []
    seen: set[tuple[str, ...]] = set()
    dropped = 0
    for row in accepted:
        grams = word_ngrams(row["query"])
        if grams & seen:
            dropped += 1
            review.append({
                "batch_id": row["batch_id"],
                "model": MODEL,
                "prompt_sha256": row["prompt_sha256"],
                "style": row["style"],
                "intent": row["intent"],
                "lint": ["batch:duplicate_6gram_cross_cell"],
                "leakage": None,
                "review_status": "",
            })
            continue
        seen |= grams
        deduped.append(row)
    if dropped:
        print(f"cross-cell duplicates dropped: {dropped}")
    accepted = deduped
    out = Path(args.out)
    digest = write_jsonl(out, accepted)
    review_out = Path(args.review)
    write_jsonl(review_out, review)
    linted = [line for line in review if line["lint"]]
    print(
        f"accepted={len(accepted)} lint_rejected={len(linted)} "
        f"batches={len({line['batch_id'] for line in review})}"
    )
    print(f"wrote {out} sha256={digest}")
    print(f"wrote {review_out}")
    short = [
        (intent, targets[intent] - sum(1 for row in accepted if row["intent"] == intent))
        for intent in targets
    ]
    for intent, gap in short:
        if gap:
            print(f"short {intent}: missing {gap}")
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    rows = read_jsonl(Path(args.input))
    failed = 0
    for row in rows:
        failures = lint_row(row)
        if failures:
            failed += 1
            print(f"{row.get('intent')}/{row.get('style')}: {','.join(failures)}")
    print(f"lint: {len(rows) - failed}/{len(rows)} pass")
    return 1 if failed else 0


# ---------------------------------------------------------------------- leakage


def norm_tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.casefold())


def norm_key(text: str) -> str:
    return " ".join(norm_tokens(text))


def word_ngrams(text: str, n: int = NGRAM_N) -> set[tuple[str, ...]]:
    tokens = norm_tokens(text)
    return {tuple(tokens[index : index + n]) for index in range(len(tokens) - n + 1)}


def against_texts() -> tuple[list[str], dict[str, int]]:
    """Every query and processed instruction an admission row must not resemble."""
    sources: dict[str, int] = {}
    texts: list[str] = []
    eval_files = [
        ROOT / "eval" / "challenge.jsonl",
        ROOT / "eval" / "dev.jsonl",
        ROOT / "eval" / "challenge_v2.jsonl",
    ]
    for path in eval_files:
        if not path.exists():
            sources[path.name] = 0
            continue
        rows = read_jsonl(path)
        found = [str(row["query"]) for row in rows]
        texts.extend(found)
        sources[path.name] = len(found)
    for name in ("val", "test"):
        path = PROCESSED_V2 / f"{name}.jsonl"
        if not path.exists():
            sources[f"v2/{name}.jsonl"] = 0
            continue
        rows = read_jsonl(path)
        found = [str(row["instruction"]) for row in rows]
        texts.extend(found)
        sources[f"v2/{name}.jsonl"] = len(found)
    return texts, sources


def cmd_leakage(args: argparse.Namespace) -> int:
    from eval.auto_metrics import EMBED_MODEL, embed_texts

    rows = read_jsonl(Path(args.input))
    texts, sources = against_texts()
    if not texts:
        print("no against-set found; refusing to certify", file=sys.stderr)
        return 1
    against_keys = {norm_key(text) for text in texts}
    against_grams: set[tuple[str, ...]] = set()
    for text in texts:
        against_grams |= word_ngrams(text)
    fields = [(row, field) for row in rows for field in ("query", "answer")]
    field_texts = [str(row[field]) for row, field in fields]
    print(f"embedding {EMBED_MODEL} rows={len(rows)} against={len(texts)}")
    left = embed_texts(field_texts)
    right = embed_texts(list(texts))
    import numpy as np

    max_cos = np.max(left @ right.T, axis=1)
    verdicts: dict[int, dict] = {}
    for index, (row, field) in enumerate(fields):
        row_index = index // 2
        entry = verdicts.setdefault(
            row_index, {"max_cosine": 0.0, "reasons": [], "row": rows[row_index]}
        )
        cosine = float(max_cos[index])
        entry["max_cosine"] = max(entry["max_cosine"], cosine)
        if norm_key(str(row[field])) in against_keys:
            entry["reasons"].append(f"{field}:normalized_equality")
        if cosine >= COSINE_CAP:
            entry["reasons"].append(f"{field}:cosine>={COSINE_CAP:.2f}")
        if word_ngrams(str(row[field])) & against_grams:
            entry["reasons"].append(f"{field}:shared_{NGRAM_N}gram")
    accepted: list[dict] = []
    quarantined: list[dict] = []
    for row_index in sorted(verdicts):
        entry = verdicts[row_index]
        row = dict(entry["row"])
        row["max_leak_cosine"] = round(entry["max_cosine"], 4)
        if entry["reasons"]:
            row["leak_reasons"] = sorted(set(entry["reasons"]))
            quarantined.append(row)
        else:
            accepted.append(row)
    accepted_digest = write_jsonl(Path(args.out), accepted)
    write_jsonl(Path(args.quarantine), quarantined)
    per_intent: dict[str, dict[str, int]] = {}
    for row in accepted:
        per_intent.setdefault(str(row["intent"]), {"accepted": 0, "quarantined": 0})["accepted"] += 1
    for row in quarantined:
        per_intent.setdefault(str(row["intent"]), {"accepted": 0, "quarantined": 0})[
            "quarantined"
        ] += 1
    reason_counts: dict[str, int] = {}
    for row in quarantined:
        for reason in row["leak_reasons"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    payload = {
        "checked_rows": len(rows),
        "accepted": len(accepted),
        "quarantined": len(quarantined),
        "embedding_model": EMBED_MODEL,
        "cosine_cap": COSINE_CAP,
        "ngram_n": NGRAM_N,
        "against_sources": sources,
        "against_texts": len(texts),
        "reason_counts": dict(sorted(reason_counts.items())),
        "per_intent": {name: per_intent[name] for name in sorted(per_intent)},
        "max_cosine_overall": round(float(max_cos.max()), 4),
        "accepted_sha256": accepted_digest,
    }
    Path(args.leakage).parent.mkdir(parents=True, exist_ok=True)
    Path(args.leakage).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in (
        "checked_rows", "accepted", "quarantined", "max_cosine_overall", "reason_counts"
    )}, indent=2))
    print(f"wrote {args.out} sha256={accepted_digest}")
    print(f"wrote {args.leakage}")
    return 0


# --------------------------------------------------------------------- assemble


def cmd_assemble(args: argparse.Namespace) -> int:
    import prepare  # data/prepare.py

    rows = read_jsonl(Path(args.input))
    intents = load_intents()
    collator = prepare.get_collator()
    by_intent: dict[str, int] = {}
    out_rows: list[dict] = []
    overlength: list[str] = []
    for row in rows:
        intent = str(row["intent"])
        style = str(row["style"])
        serial = by_intent.get(intent, 0)
        by_intent[intent] = serial + 1
        instruction = str(row["query"]).strip()
        response = str(row["answer"]).strip()
        n_tokens = prepare.count_tokens(instruction, response, collator)
        row_id = f"adm-v2-{intent}-{serial:03d}"
        if n_tokens is None or int(n_tokens) > MAX_LENGTH:
            overlength.append(row_id)
            continue
        out_rows.append({
            "id": row_id,
            "group_id": f"adm-g-v2-{intent}-{style}",
            "intent": intent,
            "category": intents[intent],
            "flags": FLAG,
            "instruction": instruction,
            "response": response,
            "cleaning": [CLEANING_TAG],
            "n_tokens": int(n_tokens),
        })
    missing = [name for name in QUOTAS if not any(r["intent"] == name for r in out_rows)]
    out_rows.sort(key=lambda row: row["id"])
    digest = write_jsonl(Path(args.out), out_rows)
    print(f"assembled={len(out_rows)} overlength_dropped={len(overlength)}")
    for intent in sorted(QUOTAS):
        count = sum(1 for row in out_rows if row["intent"] == intent)
        print(f"{intent:<24} {count:>3} / {QUOTAS[intent]}")
    print(f"wrote {args.out} sha256={digest}")
    if missing:
        print(f"STOP: intents with no accepted row: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


# ------------------------------------------------------------------------- main


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="fill the quota with linted rows")
    gen.add_argument("--intent", default=None, help="one intent only (dry run)")
    gen.add_argument("--n", type=int, default=None, help="override the quota")
    gen.add_argument("--out", default=str(RAW_PATH))
    gen.add_argument("--review", default=str(REVIEW_PATH))
    gen.add_argument("--batch", type=int, default=10, help="rows per model call (8-12)")
    gen.add_argument("--parallel", type=int, default=4, help="concurrent calls, max 16")
    gen.add_argument("--resume", action="store_true",
                     help="keep cells an earlier attempt banked; redo only what is missing")
    gen.add_argument("--partial-rows", default=str(PARTIAL_ROWS_PATH))
    gen.add_argument("--partial-review", default=str(PARTIAL_REVIEW_PATH))
    gen.add_argument("--attempts", type=int, default=6, help="regeneration rounds per cell")
    gen.set_defaults(func=cmd_generate)

    lint = sub.add_parser("lint", help="re-run the lint over a rows file")
    lint.add_argument("input")
    lint.set_defaults(func=cmd_lint)

    leak = sub.add_parser("leakage", help="check both fields against eval and val/test")
    leak.add_argument("--input", default=str(RAW_PATH))
    leak.add_argument("--out", default=str(V2_DIR / "admissions_accepted.jsonl"))
    leak.add_argument("--quarantine", default=str(QUARANTINE_PATH))
    leak.add_argument("--leakage", default=str(LEAKAGE_PATH))
    leak.set_defaults(func=cmd_leakage)

    asm = sub.add_parser("assemble", help="ids, flags, tokens; write admissions.jsonl")
    asm.add_argument("--input", default=str(V2_DIR / "admissions_accepted.jsonl"))
    asm.add_argument("--out", default=str(ACCEPTED_PATH))
    asm.set_defaults(func=cmd_assemble)

    args = parser.parse_args(argv)
    if getattr(args, "parallel", 1) > 16:
        parser.error("--parallel is capped at 16")
    if getattr(args, "batch", 10) > 12:
        parser.error("--batch is capped at 12")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
