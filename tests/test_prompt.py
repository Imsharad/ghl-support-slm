"""Tests for native Qwen rendering and assistant-only loss labels."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from train.collate import IGNORE_INDEX, AssistantOnlyCollator
from train.render import SYSTEM_PROMPT, get_tokenizer, render_full, render_prompt


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "prompt_examples.json"


@pytest.fixture(scope="module")
def tokenizer():
    return get_tokenizer()


@pytest.fixture(scope="module")
def fixture_rows() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["fixtures"]


def test_committed_token_and_label_fixtures_match(tokenizer, fixture_rows) -> None:
    collator = AssistantOnlyCollator(tokenizer)
    for fixture in fixture_rows:
        encoded = collator.encode(fixture)
        assert encoded is not None
        prompt_ids = tokenizer.encode(
            render_prompt(fixture["instruction"], tokenizer),
            add_special_tokens=False,
        )
        assert prompt_ids == fixture["prompt_ids"]
        assert encoded["input_ids"] == fixture["input_ids"]
        assert encoded["labels"] == fixture["labels"]
        assert [int(label != IGNORE_INDEX) for label in encoded["labels"]] == fixture[
            "label_mask"
        ]


def test_system_prompt_appears_once(tokenizer, fixture_rows) -> None:
    rendered = render_full(
        fixture_rows[0]["instruction"],
        fixture_rows[0]["response"],
        tokenizer,
    )
    assert rendered.count(SYSTEM_PROMPT) == 1
    assert rendered.count("<|im_start|>system\n") == 1
    assert rendered.count("<|im_start|>user\n") == 1
    assert rendered.count("<|im_start|>assistant\n") == 1


def test_user_and_header_are_ignored_but_assistant_and_end_are_labelled(
    tokenizer,
    fixture_rows,
) -> None:
    collator = AssistantOnlyCollator(tokenizer)
    encoded = collator.encode(fixture_rows[0])
    assert encoded is not None
    prompt_length = len(fixture_rows[0]["prompt_ids"])
    assert all(label == IGNORE_INDEX for label in encoded["labels"][:prompt_length])
    assistant_labels = [label for label in encoded["labels"] if label != IGNORE_INDEX]
    assert assistant_labels
    assert assistant_labels[-1] == tokenizer.convert_tokens_to_ids("<|im_end|>")


def test_render_prompt_is_strict_token_prefix_of_full(tokenizer, fixture_rows) -> None:
    for fixture in fixture_rows:
        prompt_ids = tokenizer.encode(
            render_prompt(fixture["instruction"], tokenizer),
            add_special_tokens=False,
        )
        full_ids = tokenizer.encode(
            render_full(fixture["instruction"], fixture["response"], tokenizer),
            add_special_tokens=False,
        )
        assert len(prompt_ids) < len(full_ids)
        assert full_ids[: len(prompt_ids)] == prompt_ids


def test_overlength_example_is_dropped_and_counted(tokenizer) -> None:
    collator = AssistantOnlyCollator(tokenizer, max_length=512)
    encoded = collator.encode(
        {
            "instruction": "word " * 600,
            "response": "Please provide a shorter summary.",
        }
    )
    assert encoded is None
    assert collator.dropped_overlength == 1


def test_batch_is_right_padded_and_padding_labels_are_ignored(tokenizer, fixture_rows) -> None:
    collator = AssistantOnlyCollator(tokenizer)
    batch = collator(fixture_rows[:2])
    assert batch is not None
    assert tokenizer.padding_side == "right"
    assert batch["input_ids"].shape == batch["attention_mask"].shape == batch["labels"].shape
    shorter = 0 if len(fixture_rows[0]["input_ids"]) < len(fixture_rows[1]["input_ids"]) else 1
    padding = batch["attention_mask"][shorter] == 0
    assert padding.any()
    assert (batch["labels"][shorter][padding] == IGNORE_INDEX).all()
    assert (batch["input_ids"][shorter][padding] == tokenizer.pad_token_id).all()
