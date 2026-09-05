#!/usr/bin/env python3
"""Regenerate deterministic C2 prompt token and label-mask fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from train.collate import AssistantOnlyCollator  # noqa: E402
from train.render import get_tokenizer, load_base_pin, render_full, render_prompt  # noqa: E402


EXAMPLES = [
    {
        "name": "password_recovery",
        "instruction": "I forgot my password and cannot sign in. What should I do?",
        "response": "Use the password-reset option on the sign-in page. Do not share your password.",
    },
    {
        "name": "duplicate_charge_multiline",
        "instruction": "I was charged twice for order #42.\nCan you help?",
        "response": "Please share the order ID and the dates of both charges so support can investigate.",
    },
    {
        "name": "refund_policy_unknown",
        "instruction": "My order is late. Can you guarantee a refund today?",
        "response": "I cannot guarantee a refund without the applicable policy. Please provide the order ID.",
    },
]


def main() -> int:
    tokenizer = get_tokenizer()
    collator = AssistantOnlyCollator(tokenizer)
    repo_id, revision = load_base_pin()
    fixtures: list[dict[str, object]] = []
    for example in EXAMPLES:
        encoded = collator.encode(example)
        assert encoded is not None
        prompt_ids = tokenizer.encode(
            render_prompt(example["instruction"], tokenizer),
            add_special_tokens=False,
        )
        full_ids = tokenizer.encode(
            render_full(example["instruction"], example["response"], tokenizer),
            add_special_tokens=False,
        )
        fixtures.append(
            {
                **example,
                "prompt_ids": prompt_ids,
                "input_ids": full_ids,
                "labels": encoded["labels"],
                "label_mask": [int(label != -100) for label in encoded["labels"]],
            }
        )

    payload = {
        "base_model": repo_id,
        "revision": revision,
        "fixtures": fixtures,
    }
    output = Path(__file__).with_name("prompt_examples.json")
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote={output.relative_to(ROOT)} fixtures={len(fixtures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
