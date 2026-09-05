# License review

Reviewed on 2026-09-05 IST. This is an engineering compliance note, not legal advice.

## Base model: Qwen2.5-1.5B-Instruct

The pinned model is [`Qwen/Qwen2.5-1.5B-Instruct` at `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306). Its cached `LICENSE` is the Apache License 2.0 and the repository contains no `NOTICE` file at that revision. Apache-2.0 grants the rights needed to use, modify, self-host, and commercially distribute the model, subject to its conditions.

For redistribution of the original or adapted model, include a copy of Apache-2.0; mark files that we changed; retain applicable copyright, patent, trademark, and attribution notices; and reproduce upstream `NOTICE` contents if a future pinned revision includes such a file. Do not imply Alibaba Cloud endorses this derivative. The exact offline source reviewed is:

`~/.cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/989aa7980e4cf806f80c7fef2b1adb7bc71aa306/LICENSE`

## Dataset: Bitext customer support

The pinned dataset is [`bitext/Bitext-customer-support-llm-chatbot-training-dataset` at `430d1a89bd93bd1fa23c16f29dd53e73f0087443`](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset/tree/430d1a89bd93bd1fa23c16f29dd53e73f0087443). Its pinned dataset-card metadata declares [`CDLA-Sharing-1.0`](https://cdla.dev/sharing-1-0/).

CDLA-Sharing-1.0 permits computational use, including model training. If we publish raw Bitext rows or enhanced/processed versions of those rows, we must publish that data under the same unmodified license, include the license text/name/link, preserve Bitext credit and attribution that arrived with the data, prominently mark changed data files, and add no downstream restrictions. The license states that these conditions do not attach to “Results” of computational use. This review therefore treats trained weights and aggregate metrics as Results, while raw or processed rows remain Data or Enhanced Data; confirm that classification with counsel before relying on it for a commercial release. The safest repository practice is to publish fetch/prepare code and hashes, not dataset rows.

## Why this 1.5B instruct model

Qwen2.5-1.5B-Instruct is small enough for Q8 local serving within this Mac's 16 GB unified-memory envelope, uses the permissive Apache-2.0 license, and ships a native chat template with explicit system, user, and assistant turns. Those properties satisfy the assignment's local-serving and prompt-parity constraints without making an unsupported quality claim.

## Verification record

- Model revision and declared license: Hugging Face model API plus the cached `LICENSE` at the exact revision above.
- Dataset revision and declared license: Hugging Face dataset API and the pinned README frontmatter at the exact revision above.
- Dataset redistribution terms: official CDLA-Sharing-1.0 text, especially sections 3.1 through 3.5.
- Converter pin for later GGUF export: [`ggml-org/llama.cpp@6a1a922d269908a29cbd4b49c27e6a8e7fd10fae`](https://github.com/ggml-org/llama.cpp/commit/6a1a922d269908a29cbd4b49c27e6a8e7fd10fae).
