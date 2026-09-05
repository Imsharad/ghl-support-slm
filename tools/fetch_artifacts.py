#!/usr/bin/env python3
"""Download manifest artifacts from public Hub URLs and verify their hashes."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

try:
    from tools.check_artifacts import (
        DEFAULT_MANIFEST,
        ROOT,
        Artifact,
        ManifestError,
        load_manifest,
        resolve_local_path,
        select_artifacts,
        verify_artifact,
    )
except ModuleNotFoundError:
    from check_artifacts import (  # type: ignore[no-redef]
        DEFAULT_MANIFEST,
        ROOT,
        Artifact,
        ManifestError,
        load_manifest,
        resolve_local_path,
        select_artifacts,
        verify_artifact,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--target",
        choices=("all", "serve"),
        default="all",
        help="fetch every entry, or only GGUF serving artifacts",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def download(artifact: Artifact, root: Path) -> None:
    destination = resolve_local_path(root, artifact.path)
    existing_failure = verify_artifact(artifact, root)
    if existing_failure is None:
        print(f"SKIP {artifact.path} already verified")
        return
    if artifact.hub_url is None:
        raise RuntimeError(f"{artifact.path} has no hub_url; upload is still pending")

    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"FETCH {artifact.path} <- {artifact.hub_url}", flush=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{destination.name}.",
            suffix=".part",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            digest = hashlib.sha256()
            size = 0
            request = urllib.request.Request(
                artifact.hub_url,
                headers={"User-Agent": "ghl-support-slm-artifact-fetch/1"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                final_url = urlparse(response.geturl())
                if final_url.scheme not in ("http", "https"):
                    raise RuntimeError(f"unsafe redirect scheme for {artifact.path}")
                while chunk := response.read(1024 * 1024):
                    temporary.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            temporary.flush()
            os.fsync(temporary.fileno())

        actual_sha = digest.hexdigest()
        if size != artifact.bytes:
            raise RuntimeError(
                f"size mismatch for {artifact.path}: expected {artifact.bytes}, got {size}"
            )
        if actual_sha != artifact.sha256:
            raise RuntimeError(
                f"sha256 mismatch for {artifact.path}: expected {artifact.sha256}, got {actual_sha}"
            )
        os.replace(temporary_path, destination)
        temporary_path = None
        print(f"FETCHED {artifact.path} bytes={size} sha256={actual_sha}")
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main() -> int:
    args = parse_args()
    try:
        artifacts = select_artifacts(load_manifest(args.manifest), args.target)
    except ManifestError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2

    failures: list[str] = []
    for artifact in artifacts:
        try:
            download(artifact, args.root)
        except (ManifestError, OSError, RuntimeError, urllib.error.URLError) as exc:
            failures.append(f"ERROR {exc}")
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print(f"verified={len(artifacts)} target={args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
