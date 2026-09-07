"""Quota, style, lint and leakage checks for tools/admissions.py."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

from tools import admissions  # noqa: E402
import prepare  # noqa: E402

GOOD_ANSWER = (
    "I do not have access to the cancellation status on your order, so I cannot tell "
    "you where it stands. The order details in your account portal show that, and the "
    "published policy explains what happens next. What I can do here is walk you through "
    "what each label on that page means so you know exactly what you are looking at."
)


def test_quota_table_matches_the_plan_target() -> None:
    intents = [row["intent"] for row in json.loads((ROOT / "data" / "intents.json").read_text())]
    assert sorted(admissions.QUOTAS) == sorted(intents)
    assert sum(admissions.QUOTAS.values()) == 440


def test_every_intent_gets_half_ordinary_and_every_hard_style() -> None:
    for intent, total in admissions.QUOTAS.items():
        plan = admissions.style_plan(total)
        assert len(plan) == total, intent
        assert plan.count("ordinary") == total // 2, intent
        for style in admissions.HARD_STYLES:
            assert plan.count(style) >= 1, f"{intent} missing {style}"


def test_a_clean_row_passes_the_lint() -> None:
    row = {"query": "Can you tell me where my cancellation request stands?", "answer": GOOD_ANSWER}
    assert admissions.lint_row(row) == []


@pytest.mark.parametrize(
    "text,rule",
    [
        ("Check order 4821 for me please", "query:digit"),
        ("It should arrive in three days from now", "query:number_word"),
        ("Will it ship on Monday or later", "query:time_or_duration"),
        ("Does the refund cost me anything at all", "query:price_word"),
        ("Visit support.example.com to sort it out", "query:url_or_address"),
        ("We guarantee the parcel reaches you soon", "query:policy_verb"),
        ("Support is open 24/7 for everyone here", "query:always_open"),
        ("Please confirm your password before we start", "query:credential_request"),
        ("The charge was 50% of the order value", "query:currency_symbol"),
    ],
)
def test_lint_refuses_the_banned_content(text: str, rule: str) -> None:
    assert rule in admissions.lint_field(text, "query")


def test_lint_refuses_completed_actions_and_offered_lookups() -> None:
    completed = {"query": "Where is my refund at the moment?", "answer": GOOD_ANSWER.replace(
        "What I can do here is walk you through", "I have processed it and I can also walk you through"
    )}
    assert "answer:completed_action" in admissions.lint_row(completed)
    offered = {"query": "Where is my refund at the moment?", "answer": GOOD_ANSWER.replace(
        "What I can do here is walk you through", "Let me check the record and then walk you through"
    )}
    assert "answer:offers_lookup_or_transfer" in admissions.lint_row(offered)


def test_lint_enforces_the_word_band() -> None:
    short = {"query": "Where is my refund at the moment?", "answer": "I cannot see that here."}
    assert any(rule.startswith("answer:word_band") for rule in admissions.lint_row(short))
    long_answer = {"query": "Where is my refund at the moment?", "answer": GOOD_ANSWER * 3}
    assert any(rule.startswith("answer:word_band") for rule in admissions.lint_row(long_answer))


def test_bitext_openers_are_refused() -> None:
    row = {"query": "Where is my refund at the moment?", "answer": "Rest assured, " + GOOD_ANSWER}
    assert "answer:bitext_opener" in admissions.lint_row(row)


def test_scenarios_are_deterministic_and_carry_no_digits() -> None:
    first = admissions.scenario("get_refund", "anger", 3)
    assert first == admissions.scenario("get_refund", "anger", 3)
    assert first != admissions.scenario("get_refund", "anger", 4)
    assert admissions.lint_field(first, "scene") == []


def test_the_prompt_carries_no_eval_text() -> None:
    prompt = admissions.build_prompt(
        "get_refund", "REFUND", "ordinary", [admissions.scenario("get_refund", "ordinary", 0)]
    )
    assert "get_refund" in prompt and "REFUND" in prompt
    for name in ("challenge.jsonl", "dev.jsonl"):
        path = ROOT / "eval" / name
        for row in admissions.read_jsonl(path):
            assert str(row["query"]) not in prompt


def test_six_gram_and_normalisation_match_the_checker() -> None:
    from eval import check_challenge

    text = "I would like to know where my cancellation request stands right now"
    assert admissions.word_ngrams(text) == check_challenge.word_ngrams(text)
    assert admissions.norm_key("  Where's  MY refund? ") == "where's my refund"


def test_assembled_rows_use_the_processed_schema() -> None:
    row = {
        "id": "adm-v2-get_refund-000",
        "group_id": "adm-g-v2-get_refund-ordinary",
        "intent": "get_refund",
        "category": "REFUND",
        "flags": admissions.FLAG,
        "instruction": "q",
        "response": "a",
        "cleaning": [admissions.CLEANING_TAG],
        "n_tokens": 12,
    }
    assert sorted(row) == sorted(prepare.ROW_KEYS)
    assert admissions.FLAG == prepare.SYNTH_ADMISSION_FLAG


def test_append_jsonl_appends_and_survives_partial_run(tmp_path):
    """A cell written on return must still be on disk if the run never ends."""
    path = tmp_path / "partial.jsonl"
    admissions.append_jsonl(path, [{"intent": "cancel_order", "query": "a"}])
    admissions.append_jsonl(path, [{"intent": "get_refund", "query": "b"}])
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["intent"] for line in lines] == ["cancel_order", "get_refund"]


def test_append_jsonl_no_rows_creates_nothing(tmp_path):
    path = tmp_path / "partial.jsonl"
    admissions.append_jsonl(path, [])
    assert not path.exists()


def test_cell_order_shuffle_is_seeded_and_interleaves_intents():
    """The seeded shuffle must be reproducible and must not leave one intent last."""
    cells = [(intent, "CAT", style, 1) for intent in "abcdefghij" for style in admissions.STYLES]
    first = list(cells)
    second = list(cells)
    random.Random(admissions.CELL_ORDER_SEED).shuffle(first)
    random.Random(admissions.CELL_ORDER_SEED).shuffle(second)
    assert first == second
    assert first != cells
    # The first tenth of the shuffled order should touch more than one intent.
    head = {cell[0] for cell in first[: len(first) // 10]}
    assert len(head) > 1


def test_intent_noun_exemption_is_narrow():
    # Decision 12: the intent's own noun passes; everything else in the rule still fails.
    assert admissions.lint_field("What is the cancellation fee?", "query", "check_cancellation_fee") == []
    assert "query:price_word" in admissions.lint_field("What is the cancellation fee?", "query", "cancel_order")
    assert "answer:price_word" in admissions.lint_field("The fee is a small amount.", "answer", "check_cancellation_fee")
    assert admissions.lint_field("I forgot my password.", "query", "recover_password") == []
    assert "query:credential_request" in admissions.lint_field("I forgot my password.", "query", "edit_account")
    assert "answer:credential_request" in admissions.lint_field("Tell me your password and PIN.", "answer", "recover_password")
    row = {"query": "I forgot my password.", "answer": "x", "intent": "recover_password"}
    assert "query:credential_request" not in admissions.lint_row(row)
