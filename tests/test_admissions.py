"""Quota, style, lint and leakage checks for tools/admissions.py."""

from __future__ import annotations

import json
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
