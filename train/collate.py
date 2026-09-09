"""Right-padding, assistant-only collator for Qwen2.5 chat examples.

The Qwen tokenizer already defines a pad token. Batches are padded on the
right; pad positions and every token through the assistant header receive the
ignore label ``-100``. Examples longer than ``max_length`` are dropped intact
instead of silently truncating their answers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import torch
from transformers import PreTrainedTokenizerBase

from train.render import SYSTEM_PROMPT, get_tokenizer, render_full, render_prompt


IGNORE_INDEX = -100
MAX_LENGTH = 512
END_MARKER = "<|im_end|>"


class AssistantOnlyCollator:
    """Encode raw rows and right-pad batches with assistant-only labels."""

    def __init__(
        self,
        tokenizer: PreTrainedTokenizerBase | None = None,
        *,
        max_length: int = MAX_LENGTH,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        if max_length < 1:
            raise ValueError("max_length must be positive")
        self.tokenizer = tokenizer if tokenizer is not None else get_tokenizer()
        if self.tokenizer.pad_token_id is None:
            if self.tokenizer.eos_token_id is None:
                raise ValueError("tokenizer defines neither a pad token nor an EOS token")
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "right"
        self.max_length = max_length
        self.system_prompt = system_prompt
        self.dropped_overlength = 0

        end_marker_id = self.tokenizer.convert_tokens_to_ids(END_MARKER)
        if not isinstance(end_marker_id, int) or end_marker_id < 0:
            raise ValueError(f"tokenizer does not define {END_MARKER}")
        self.end_marker_id = end_marker_id

    def encode(self, example: Mapping[str, Any]) -> dict[str, list[int]] | None:
        instruction = example.get("instruction")
        response = example.get("response")
        if not isinstance(instruction, str) or not instruction:
            raise ValueError("example instruction must be a nonempty string")
        if not isinstance(response, str) or not response:
            raise ValueError("example response must be a nonempty string")

        prompt = render_prompt(instruction, self.tokenizer, system_prompt=self.system_prompt)
        full = render_full(instruction, response, self.tokenizer, system_prompt=self.system_prompt)
        prompt_ids = self.tokenizer.encode(prompt, add_special_tokens=False)
        input_ids = self.tokenizer.encode(full, add_special_tokens=False)
        if input_ids[: len(prompt_ids)] != prompt_ids or len(input_ids) <= len(prompt_ids):
            raise ValueError("render_prompt token IDs must be a strict prefix of render_full")
        if len(input_ids) > self.max_length:
            self.dropped_overlength += 1
            return None

        try:
            assistant_end = len(input_ids) - 1 - input_ids[::-1].index(self.end_marker_id)
        except ValueError as exc:
            raise ValueError(f"rendered example has no {END_MARKER} token") from exc
        if assistant_end < len(prompt_ids):
            raise ValueError("assistant end marker occurs before the answer boundary")

        labels = [IGNORE_INDEX] * len(input_ids)
        labels[len(prompt_ids) : assistant_end + 1] = input_ids[
            len(prompt_ids) : assistant_end + 1
        ]
        if not any(label != IGNORE_INDEX for label in labels):
            raise ValueError("assistant label span is empty")
        return {
            "input_ids": input_ids,
            "attention_mask": [1] * len(input_ids),
            "labels": labels,
        }

    def __call__(
        self,
        examples: Sequence[Mapping[str, Any]],
    ) -> dict[str, torch.Tensor] | None:
        encoded = [item for example in examples if (item := self.encode(example)) is not None]
        if not encoded:
            return None

        batch_length = max(len(item["input_ids"]) for item in encoded)
        pad_id = self.tokenizer.pad_token_id
        assert pad_id is not None
        batch_input_ids: list[list[int]] = []
        batch_attention_mask: list[list[int]] = []
        batch_labels: list[list[int]] = []
        for item in encoded:
            padding = batch_length - len(item["input_ids"])
            batch_input_ids.append(item["input_ids"] + [pad_id] * padding)
            batch_attention_mask.append(item["attention_mask"] + [0] * padding)
            batch_labels.append(item["labels"] + [IGNORE_INDEX] * padding)

        return {
            "input_ids": torch.tensor(batch_input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(batch_attention_mask, dtype=torch.long),
            "labels": torch.tensor(batch_labels, dtype=torch.long),
        }
