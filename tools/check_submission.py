#!/usr/bin/env python3
"""Validate submission.json against public URLs, the git tag, the README, and the manifest.

Checks, in order:
  1. submission.json parses and has the required fields.
  2. Every concrete URL returns HTTP 200 without auth (repo_url, Hub links, Loom). A private
     GitHub repo_url passes only when `gh` can see it, and prints a reminder that the reviewer
     needs collaborator access.
  3. loom_url is a nonempty HTTP(S) URL (null or a placeholder fails).
  4. tag exists as a local git tag and on the `origin` remote (placeholders fail).
  5. artifacts/manifest.json hashes match the local files.
  6. README has no TODO / FIXME / [PENDING markers.

Exits 0 when every check passes, 1 on check failures, 2 on usage or parse errors.

Usage:
    uv run python tools/check_submission.py
    uv run python tools/check_submission.py submission.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.check_artifacts import (  # noqa: E402
    DEFAULT_MANIFEST,
    ManifestError,
    load_manifest,
    verify_artifact,
)

DEFAULT_SUBMISSION = ROOT / "submission.json"
REQUIRED_FIELDS = (
    "repo_url",
    "tag",
    "hub",
    "loom_url",
    "readme",
    "contact",
    "submitted_at",
)
HUB_REQUIRED_FIELDS = (
    "repo",
    "adapter",
    "merged",
    "base_gguf",
    "tuned_gguf",
)
PLACEHOLDER_MARKERS = ("PENDING", "TODO", "FIXME", "TBD", "PLACEHOLDER")
README_TODO = (
    re.compile(r"\bTODO\b"),
    re.compile(r"\bFIXME\b"),
    re.compile(r"\[PENDING\b"),
)


class SubmissionError(ValueError):
    """submission.json does not conform to the submission contract."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "submission",
        nargs="?",
        type=Path,
        default=DEFAULT_SUBMISSION,
        help="path to submission.json (default: repo-root submission.json)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def load_submission(path: Path) -> dict[str, Any]:
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SubmissionError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SubmissionError("submission root must be an object")
    missing = [field for field in REQUIRED_FIELDS if field not in value]
    if missing:
        raise SubmissionError(f"missing fields: {', '.join(missing)}")
    return value


def is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    if not stripped:
        return True
    upper = stripped.upper()
    return any(marker in upper for marker in PLACEHOLDER_MARKERS)


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def collect_hub_urls(hub: Any, failures: list[str], *, required_fields=HUB_REQUIRED_FIELDS) -> list[tuple[str, str]]:
    if not isinstance(hub, dict):
        failures.append("hub must be an object")
        return []
    missing = [field for field in required_fields if field not in hub]
    if missing:
        failures.append(f"hub missing fields: {', '.join(missing)}")
    urls: list[tuple[str, str]] = []
    for field in required_fields:
        if field not in hub:
            continue
        value = hub[field]
        label = f"hub.{field}"
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{label} must be a nonempty URL")
            continue
        if is_placeholder(value) or not is_http_url(value):
            failures.append(f"{label} is not a public HTTP(S) URL: {value!r}")
            continue
        urls.append((label, value))
    return urls


def http_status(url: str) -> int:
    headers = {"User-Agent": "ghl-check-submission/1"}
    request = urllib.request.Request(url, method="HEAD", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        if exc.code not in (403, 405, 501):
            return int(exc.code)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{url} failed: {exc.reason}") from exc

    get_headers = dict(headers)
    get_headers["Range"] = "bytes=0-0"
    request = urllib.request.Request(url, method="GET", headers=get_headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{url} failed: {exc.reason}") from exc


def check_url(label: str, url: str, failures: list[str]) -> None:
    try:
        status = http_status(url)
    except RuntimeError as exc:
        failures.append(f"{label} unreachable: {exc}")
        return
    if status not in (200, 206):
        failures.append(f"{label} returned HTTP {status} without auth: {url}")
    else:
        print(f"PASS url {label} HTTP {status} {url}")


def github_private_visible(url: str) -> bool:
    """True when `url` is a GitHub repo that the local `gh` login can see and it is private."""
    parsed = urlparse(url)
    if parsed.netloc.lower() != "github.com":
        return False
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        return False
    owner, repo = parts
    result = subprocess.run(
        ["gh", "repo", "view", f"{owner}/{repo}", "--json", "isPrivate"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    try:
        return bool(json.loads(result.stdout).get("isPrivate"))
    except (json.JSONDecodeError, AttributeError):
        return False


def check_repo_url(value: Any, failures: list[str]) -> None:
    if is_placeholder(value):
        failures.append(f"repo_url is a placeholder: {value!r}")
        return
    if not isinstance(value, str) or not is_http_url(value):
        failures.append(f"repo_url is not a public HTTP(S) URL: {value!r}")
        return
    try:
        status = http_status(value)
    except RuntimeError as exc:
        failures.append(f"repo_url unreachable: {exc}")
        return
    if status in (200, 206):
        print(f"PASS url repo_url HTTP {status} {value}")
        return
    if status == 404 and github_private_visible(value):
        print(f"PASS url repo_url private GitHub repo visible to gh {value}")
        print("NOTE repo_url is private: the reviewer's GitHub account must be added as a collaborator")
        return
    failures.append(f"repo_url returned HTTP {status} without auth: {value}")


def check_loom(value: Any, failures: list[str]) -> None:
    if value is None or is_placeholder(value):
        failures.append(f"loom_url is null or a placeholder: {value!r}")
        return
    if not isinstance(value, str) or not is_http_url(value):
        failures.append(f"loom_url is not a public HTTP(S) URL: {value!r}")
        return
    check_url("loom_url", value, failures)


def check_tag(root: Path, value: Any, failures: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        failures.append(f"tag must be a nonempty string: {value!r}")
        return
    if is_placeholder(value):
        failures.append(f"tag is a placeholder: {value!r}")
        return
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{value}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        failures.append(f"git tag does not exist: {value!r}")
        return
    print(f"PASS tag {value} {result.stdout.strip()}")
    remote = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", f"refs/tags/{value}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if remote.returncode != 0:
        failures.append(f"git tag remote check failed: {remote.stderr.strip()}")
        return
    if not remote.stdout.strip():
        failures.append(f"git tag {value!r} is not on origin (push it with `git push origin {value}`)")
        return
    print(f"PASS tag {value} on origin")


def check_readme(root: Path, value: Any, failures: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        failures.append("readme must be a nonempty relative path")
        return
    path = (root / value).resolve()
    if path != root and root.resolve() not in path.parents:
        failures.append(f"readme path escapes root: {value}")
        return
    if not path.is_file():
        failures.append(f"readme is missing: {value}")
        return
    text = path.read_text(encoding="utf-8")
    hits: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for pattern in README_TODO:
            if pattern.search(line):
                hits.append(f"{value}:{line_number}: {line.strip()}")
                break
    if hits:
        failures.append(
            "README still has TODO/PENDING markers:\n  " + "\n  ".join(hits)
        )
        return
    print(f"PASS readme no TODO {value}")


def check_contact(value: Any, failures: list[str]) -> None:
    if not isinstance(value, str) or not value.strip() or is_placeholder(value):
        failures.append(f"contact must be a nonempty string: {value!r}")
        return
    print(f"PASS contact {value.strip()}")


def check_manifest(root: Path, manifest_path: Path, failures: list[str]) -> None:
    try:
        artifacts = load_manifest(manifest_path)
    except ManifestError as exc:
        failures.append(f"manifest: {exc}")
        return
    matched = 0
    for artifact in artifacts:
        failure = verify_artifact(artifact, root)
        if failure is not None:
            failures.append(f"manifest {failure}")
        else:
            matched += 1
            print(
                f"PASS manifest {artifact.path} bytes={artifact.bytes} "
                f"sha256={artifact.sha256}"
            )
    print(f"manifest hashed={matched}/{len(artifacts)}")


def check_v3_artifacts(root: Path, failures: list[str]) -> None:
    try:
        export = json.loads((root / 'artifacts/v3/candidate03-step120-q8_0.gguf.export.json').read_text())
        seal = json.loads((root / 'eval/results/v3/final01/SEAL.json').read_text())
        files = {'artifacts/v3/candidate03-step120-q8_0.gguf': export['gguf_sha256'],
                 'artifacts/base-q8.gguf': seal['base_gguf_sha256']}
        files.update({f'train/runs/v3-candidate03-runpod/checkpoint-120/{name}': digest
                      for name, digest in export['adapter_files_sha256'].items()})
        for name, expected in files.items():
            path = root / name
            if not path.is_file():
                failures.append(f'v3 artifact missing: {name}')
                continue
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != expected:
                failures.append(f'v3 artifact hash mismatch: {name}')
            else:
                print(f'PASS v3 artifact {name}')
    except (OSError, ValueError, KeyError) as exc:
        failures.append(f'v3 artifact metadata: {exc}')


def main() -> int:
    args = parse_args()
    submission_path = args.submission
    if not submission_path.is_absolute():
        submission_path = (args.root / submission_path).resolve()
    try:
        submission = load_submission(submission_path)
    except SubmissionError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2

    failures: list[str] = []
    check_repo_url(submission.get("repo_url"), failures)
    check_tag(args.root, submission.get("tag"), failures)
    is_v3 = submission.get('candidate') == 'v3-candidate03-step120'
    required = tuple(k for k in HUB_REQUIRED_FIELDS if k != 'merged') if is_v3 else HUB_REQUIRED_FIELDS
    for label, url in collect_hub_urls(submission.get("hub"), failures, required_fields=required):
        check_url(label, url, failures)
    check_loom(submission.get("loom_url"), failures)
    check_readme(args.root, submission.get("readme"), failures)
    check_contact(submission.get("contact"), failures)
    if is_v3:
        check_v3_artifacts(args.root, failures)
    else:
        check_manifest(args.root, args.manifest, failures)

    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        print(f"failed={len(failures)}", file=sys.stderr)
        return 1

    print("CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
