#!/bin/sh
# Convert a local Hugging Face checkpoint to Q8_0 GGUF with the pinned llama.cpp.

set -eu

if [ "$#" -ne 2 ]; then
    echo "usage: tools/artifacts/convert.sh <hf_dir> <out.gguf>" >&2
    exit 2
fi

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
HF_DIR=$1
OUT_FILE=$2
LLAMA_DIR="$ROOT_DIR/.scratch/llama.cpp"
CONVERTER_VENV="$LLAMA_DIR/.venv-convert"
VERSIONS_FILE="$ROOT_DIR/configs/models/versions.json"

if [ ! -d "$HF_DIR" ]; then
    echo "error: Hugging Face directory does not exist: $HF_DIR" >&2
    exit 1
fi
if [ -e "$OUT_FILE" ]; then
    echo "error: output already exists; choose a new path to preserve historical artifacts: $OUT_FILE" >&2
    exit 1
fi

LLAMA_REPO=$(uv run python -c 'import json,sys; print(json.load(open(sys.argv[1]))["llama_cpp_converter"]["repo"])' "$VERSIONS_FILE")
LLAMA_COMMIT=$(uv run python -c 'import json,sys; print(json.load(open(sys.argv[1]))["llama_cpp_converter"]["commit"])' "$VERSIONS_FILE")

if [ ! -d "$LLAMA_DIR/.git" ]; then
    git clone --filter=blob:none "$LLAMA_REPO" "$LLAMA_DIR"
fi

if ! git -C "$LLAMA_DIR" cat-file -e "$LLAMA_COMMIT^{commit}" 2>/dev/null; then
    git -C "$LLAMA_DIR" fetch --depth 1 origin "$LLAMA_COMMIT"
fi
if ! git -C "$LLAMA_DIR" diff --quiet || ! git -C "$LLAMA_DIR" diff --cached --quiet; then
    echo "error: converter checkout has tracked changes; preserve them before converting" >&2
    exit 1
fi
git -C "$LLAMA_DIR" checkout --quiet --detach "$LLAMA_COMMIT"

ACTUAL_COMMIT=$(git -C "$LLAMA_DIR" rev-parse HEAD)
if [ "$ACTUAL_COMMIT" != "$LLAMA_COMMIT" ]; then
    echo "error: llama.cpp checkout $ACTUAL_COMMIT does not match pin $LLAMA_COMMIT" >&2
    exit 1
fi

# parity_check.py uses this exact checkout's tokenizer executable. Build only
# that target so conversion remains lightweight and reproducible.
if [ ! -x "$LLAMA_DIR/build/bin/llama-tokenize" ]; then
    cmake -S "$LLAMA_DIR" -B "$LLAMA_DIR/build" \
        -DLLAMA_BUILD_TESTS=OFF \
        -DLLAMA_BUILD_EXAMPLES=ON \
        -DLLAMA_BUILD_SERVER=OFF \
        -DLLAMA_CURL=OFF
    cmake --build "$LLAMA_DIR/build" --target llama-tokenize --parallel
fi

if [ ! -x "$CONVERTER_VENV/bin/python" ]; then
    uv venv "$CONVERTER_VENV" --python 3.11
    uv pip install \
        --python "$CONVERTER_VENV/bin/python" \
        -r "$LLAMA_DIR/requirements/requirements-convert_hf_to_gguf.txt"
fi

mkdir -p "$(dirname -- "$OUT_FILE")"
"$CONVERTER_VENV/bin/python" "$LLAMA_DIR/convert_hf_to_gguf.py" \
    "$HF_DIR" \
    --outfile "$OUT_FILE" \
    --outtype q8_0

if [ ! -s "$OUT_FILE" ]; then
    echo "error: converter did not produce a nonempty GGUF: $OUT_FILE" >&2
    exit 1
fi

echo "converter_commit=$ACTUAL_COMMIT"
echo "output=$OUT_FILE"
shasum -a 256 "$OUT_FILE"
