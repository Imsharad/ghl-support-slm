#!/usr/bin/env bash
# Bootstrap everything inside this checkout; no system Python, uv or Ollama needed.
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
case "${1:-}" in
  -h|--help)
    cat <<'HELP'
Usage: ./start.sh [--port 8013] [--ollama-port 11435] [--check]

Installs pinned uv, Python, dependencies and Ollama locally; downloads the
verified v3 models/tokenizer; starts both services and tests real inference.
Default: keep running until Ctrl+C. --check: verify startup, then stop.
Supported: macOS Apple Silicon, Linux x86_64 (glibc). State/logs: .runtime/
No sudo, cloud inference, paid services, account, or existing model cache needed.
HELP
    exit 0 ;;
esac
case "$(uname -s):$(uname -m)" in
  Darwin:arm64)
    UV_ASSET=uv-aarch64-apple-darwin.tar.gz
    UV_SHA=9de9365997d7579d27cdbc132883343b3c47add16804f11be679375037dec33a ;;
  Linux:x86_64)
    UV_ASSET=uv-x86_64-unknown-linux-gnu.tar.gz
    UV_SHA=ecc2e39de86afea661c145f33f6a89a45b1d2427d51a22b458e2c64238794180 ;;
  *) printf '%s\n' 'Unsupported platform. Use macOS Apple Silicon or Linux x86_64 (glibc; WSL2 qualifies).'; exit 2 ;;
esac
for required in curl tar; do
  command -v "$required" >/dev/null || { printf 'Missing prerequisite: %s\n' "$required" >&2; exit 2; }
done
STATE="$ROOT/.runtime"
mkdir -p "$STATE/tools" "$STATE/logs"
BOOT_LOCK="$STATE/bootstrap.lock"
if ! mkdir "$BOOT_LOCK" 2>/dev/null; then
  owner=$(cat "$BOOT_LOCK/pid" 2>/dev/null || true)
  if [[ "$owner" =~ ^[0-9]+$ ]] && ! kill -0 "$owner" 2>/dev/null; then
    rm -f "$BOOT_LOCK/pid"
    rmdir "$BOOT_LOCK" 2>/dev/null || true
    mkdir "$BOOT_LOCK" 2>/dev/null || { printf '%s\n' 'Another bootstrap is active. Retry shortly.'; exit 2; }
  else
    printf '%s\n' 'Another bootstrap is active. Retry shortly.' >&2
    exit 2
  fi
fi
printf '%s\n' "$$" > "$BOOT_LOCK/pid"
WORK=""
cleanup_bootstrap() {
  if [[ -n "$WORK" && -d "$WORK" ]]; then rm -rf "$WORK"; fi
  rm -f "$BOOT_LOCK/pid"
  rmdir "$BOOT_LOCK" 2>/dev/null || true
}
trap cleanup_bootstrap EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
UV="$STATE/tools/uv-0.8.8/uv"
if [[ ! -x "$UV" ]]; then
  printf '%s\n' '[setup] Installing pinned uv 0.8.8 locally...'
  WORK=$(mktemp -d "$STATE/uv-install.XXXXXX")
  curl --fail --location --retry 3 --connect-timeout 20 \
    "https://github.com/astral-sh/uv/releases/download/0.8.8/$UV_ASSET" -o "$WORK/uv.tar.gz"
  if command -v sha256sum >/dev/null; then
    actual=$(sha256sum "$WORK/uv.tar.gz" | cut -d ' ' -f 1)
  elif command -v shasum >/dev/null; then
    actual=$(shasum -a 256 "$WORK/uv.tar.gz" | cut -d ' ' -f 1)
  else
    printf '%s\n' 'A SHA-256 tool is required: sha256sum (Linux) or shasum (macOS).' >&2; exit 2
  fi
  [[ "$actual" == "$UV_SHA" ]] || { printf '%s\n' 'uv download checksum mismatch; refusing to execute it.' >&2; exit 1; }
  mkdir "$WORK/unpacked"
  tar -xzf "$WORK/uv.tar.gz" -C "$WORK/unpacked" --strip-components=1
  mv "$WORK/unpacked" "$STATE/tools/uv-0.8.8"
fi
export UV_PYTHON_INSTALL_DIR="$STATE/python"
export UV_CACHE_DIR="$STATE/uv-cache"
export UV_PROJECT_ENVIRONMENT="$ROOT/.venv"
unset VIRTUAL_ENV PYTHONHOME PYTHONPATH
printf '%s\n' '[setup] Ensuring Python 3.11.11 and locked dependencies...'
"$UV" python install --no-bin 3.11.11
"$UV" sync --quiet --frozen --extra serve --python 3.11.11 --managed-python
cleanup_bootstrap
trap - EXIT INT TERM
exec "$ROOT/.venv/bin/python" "$ROOT/tools/start_backend.py" "$@"
