#!/usr/bin/env python3
"""Validate an artifact manifest and verify local files byte-for-byte."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "artifacts" / "manifest.json"
HEX_40 = re.compile(r"^[0-9a-f]{40}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
IST_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})? IST$")
REQUIRED_FIELDS = {
    "path",
    "sha256",
    "bytes",
    "hub_url",
    "base_revision",
    "converter_commit",
    "tokenizer_sha",
    "prompt_sha",
    "ollama_version",
    "created_at",
}


class ManifestError(ValueError):
    """The manifest does not conform to the artifact contract."""


@dataclass(frozen=True)
class Artifact:
    path: str
    sha256: str
    bytes: int
    hub_url: str | None
    base_revision: str
    converter_commit: str
    tokenizer_sha: str
    prompt_sha: str
    ollama_version: str
    created_at: str

    @property
    def is_serving_artifact(self) -> bool:
        return self.path.endswith(".gguf")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--target",
        choices=("all", "serve"),
        default="all",
        help="verify every entry, or only GGUF serving artifacts",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def require_string(entry: dict[str, Any], field: str, index: int) -> str:
    value = entry[field]
    if not isinstance(value, str) or not value:
        raise ManifestError(f"artifacts[{index}].{field} must be a nonempty string")
    return value


def validate_relative_path(value: str, index: int) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value in ("", "."):
        raise ManifestError(f"artifacts[{index}].path must be a safe relative path")
    if "\\" in value:
        raise ManifestError(f"artifacts[{index}].path must use forward slashes")


def parse_artifact(value: Any, index: int) -> Artifact:
    if not isinstance(value, dict):
        raise ManifestError(f"artifacts[{index}] must be an object")
    missing = sorted(REQUIRED_FIELDS - value.keys())
    if missing:
        raise ManifestError(f"artifacts[{index}] missing fields: {', '.join(missing)}")

    path = require_string(value, "path", index)
    validate_relative_path(path, index)
    sha256 = require_string(value, "sha256", index)
    if not HEX_64.fullmatch(sha256):
        raise ManifestError(f"artifacts[{index}].sha256 must be 64 lowercase hex characters")
    size = value["bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise ManifestError(f"artifacts[{index}].bytes must be a positive integer")

    hub_url = value["hub_url"]
    if hub_url is not None:
        if not isinstance(hub_url, str) or not hub_url:
            raise ManifestError(f"artifacts[{index}].hub_url must be null or a nonempty URL")
        parsed = urlparse(hub_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ManifestError(f"artifacts[{index}].hub_url must be an HTTP(S) URL")

    base_revision = require_string(value, "base_revision", index)
    converter_commit = require_string(value, "converter_commit", index)
    tokenizer_sha = require_string(value, "tokenizer_sha", index)
    prompt_sha = require_string(value, "prompt_sha", index)
    if not HEX_40.fullmatch(base_revision):
        raise ManifestError(f"artifacts[{index}].base_revision must be a 40-character commit")
    if not HEX_40.fullmatch(converter_commit):
        raise ManifestError(f"artifacts[{index}].converter_commit must be a 40-character commit")
    if not HEX_64.fullmatch(tokenizer_sha):
        raise ManifestError(f"artifacts[{index}].tokenizer_sha must be a SHA-256 digest")
    if not HEX_64.fullmatch(prompt_sha):
        raise ManifestError(f"artifacts[{index}].prompt_sha must be a SHA-256 digest")

    ollama_version = require_string(value, "ollama_version", index)
    created_at = require_string(value, "created_at", index)
    if not IST_TIMESTAMP.fullmatch(created_at):
        raise ManifestError(
            f"artifacts[{index}].created_at must be YYYY-MM-DD HH:MM[:SS] IST"
        )

    return Artifact(
        path=path,
        sha256=sha256,
        bytes=size,
        hub_url=hub_url,
        base_revision=base_revision,
        converter_commit=converter_commit,
        tokenizer_sha=tokenizer_sha,
        prompt_sha=prompt_sha,
        ollama_version=ollama_version,
        created_at=created_at,
    )


def load_manifest(path: Path) -> list[Artifact]:
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestError("manifest root must be an object")
    if value.get("schema_version") != 1:
        raise ManifestError("manifest schema_version must be 1")
    raw_artifacts = value.get("artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise ManifestError("manifest artifacts must be a nonempty array")
    artifacts = [parse_artifact(item, index) for index, item in enumerate(raw_artifacts)]
    paths = [artifact.path for artifact in artifacts]
    if len(paths) != len(set(paths)):
        raise ManifestError("manifest artifact paths must be unique")
    return artifacts


def select_artifacts(artifacts: Iterable[Artifact], target: str) -> list[Artifact]:
    selected = [
        artifact
        for artifact in artifacts
        if target == "all" or artifact.is_serving_artifact
    ]
    if not selected:
        raise ManifestError(f"manifest has no artifacts for target {target!r}")
    return selected


def resolve_local_path(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    path = (root / relative_path).resolve()
    if path != root and root not in path.parents:
        raise ManifestError(f"artifact path escapes root: {relative_path}")
    return path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(artifact: Artifact, root: Path) -> str | None:
    path = resolve_local_path(root, artifact.path)
    if not path.is_file():
        return f"MISSING {artifact.path}"
    actual_size = path.stat().st_size
    if actual_size != artifact.bytes:
        return f"SIZE MISMATCH {artifact.path}: expected {artifact.bytes}, got {actual_size}"
    actual_sha = file_sha256(path)
    if actual_sha != artifact.sha256:
        return f"SHA256 MISMATCH {artifact.path}: expected {artifact.sha256}, got {actual_sha}"
    return None


def main() -> int:
    args = parse_args()
    try:
        artifacts = select_artifacts(load_manifest(args.manifest), args.target)
        failures = [
            failure
            for artifact in artifacts
            if (failure := verify_artifact(artifact, args.root)) is not None
        ]
    except ManifestError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    for artifact in artifacts:
        print(f"PASS {artifact.path} bytes={artifact.bytes} sha256={artifact.sha256}")
    print(f"verified={len(artifacts)} target={args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
