#!/usr/bin/env python3
"""Render the pinned Qwen2.5 native chat template for training and inference."""

from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from transformers import AutoTokenizer, PreTrainedTokenizerBase


ROOT = Path(__file__).resolve().parents[1]
VERSIONS_PATH = ROOT / "configs" / "versions.json"
PROMPT_PATH = ROOT / "configs" / "prompt.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").removesuffix("\n")
SAMPLE_INSTRUCTION = "I forgot my password and cannot sign in. What should I do?"
SAMPLE_RESPONSE = (
    "Use the password-reset option on the sign-in page. If the reset message does not "
    "arrive, check your spam folder and contact support without sharing your password."
)


def load_base_pin() -> tuple[str, str]:
    value: Any = json.loads(VERSIONS_PATH.read_text(encoding="utf-8"))
    try:
        base = value["base_model"]
        repo_id = base["repo_id"]
        revision = base["revision"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid base_model entry in {VERSIONS_PATH}: {exc}") from exc
    if not isinstance(repo_id, str) or not isinstance(revision, str):
        raise ValueError("base_model repo_id and revision must be strings")
    return repo_id, revision


@lru_cache(maxsize=2)
def get_tokenizer(*, local_files_only: bool = True) -> PreTrainedTokenizerBase:
    repo_id, revision = load_base_pin()
    return AutoTokenizer.from_pretrained(
        repo_id,
        revision=revision,
        local_files_only=local_files_only,
    )


def _tokenizer(tokenizer: PreTrainedTokenizerBase | None) -> PreTrainedTokenizerBase:
    return tokenizer if tokenizer is not None else get_tokenizer()


def render_prompt(
    instruction: str,
    tokenizer: PreTrainedTokenizerBase | None = None,
) -> str:
    """Render through the assistant header, ready for greedy generation."""
    if not isinstance(instruction, str) or not instruction:
        raise ValueError("instruction must be a nonempty string")
    rendered = _tokenizer(tokenizer).apply_chat_template(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ],
        tokenize=False,
        add_generation_prompt=True,
    )
    if not isinstance(rendered, str):
        raise TypeError("tokenizer.apply_chat_template did not return text")
    return rendered


def render_full(
    instruction: str,
    response: str,
    tokenizer: PreTrainedTokenizerBase | None = None,
) -> str:
    """Render a complete training exchange including Qwen's end marker."""
    if not isinstance(instruction, str) or not instruction:
        raise ValueError("instruction must be a nonempty string")
    if not isinstance(response, str) or not response:
        raise ValueError("response must be a nonempty string")
    rendered = _tokenizer(tokenizer).apply_chat_template(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": response},
        ],
        tokenize=False,
        add_generation_prompt=False,
    )
    if not isinstance(rendered, str):
        raise TypeError("tokenizer.apply_chat_template did not return text")
    return rendered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instruction", default=SAMPLE_INSTRUCTION)
    parser.add_argument("--response", default=SAMPLE_RESPONSE)
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="allow fetching the pinned tokenizer when it is not cached",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tokenizer = get_tokenizer(local_files_only=not args.allow_download)
    rendered = render_full(args.instruction, args.response, tokenizer)
    token_ids = tokenizer.encode(rendered, add_special_tokens=False)
    print("Rendered text:")
    print(rendered, end="" if rendered.endswith("\n") else "\n")
    print("Token IDs:")
    print(json.dumps(token_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
