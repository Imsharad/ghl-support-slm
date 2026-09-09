"""Package tracked source and the exact evaluated v3 weights without publishing.

Extract source, adapter and Ollama archives into the same repository directory.
Only inference adapter files are included; optimizer state and blind keys are not.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = Path('train/runs/v3-candidate03-runpod/checkpoint-120')
GGUF = Path('artifacts/v3/candidate03-step120-q8_0.gguf')
BASE = Path('artifacts/base-q8.gguf')
BASE_SHA = 'eb2837d6dd3d8724fe51f80796e2dd16ba3bb38dd4301b43a4704d0c1219e7a5'


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base-gguf', type=Path, help='base GGUF if stored outside artifact-root')
    args = parser.parse_args()
    artifact_root = args.artifact_root.resolve()
    output = args.output.resolve()
    if output.exists():
        parser.error('output must be a new directory; existing releases are never overwritten')
    export = json.loads((ROOT / (str(GGUF) + '.export.json')).read_text())
    adapter_files = [(artifact_root / ADAPTER / name, str(ADAPTER / name), sha)
                     for name, sha in export['adapter_files_sha256'].items()]
    weights = [(artifact_root / GGUF, str(GGUF), export['gguf_sha256']),
               (args.base_gguf or artifact_root / BASE, str(BASE), BASE_SHA)]
    # Verify all large inputs before producing any release files.
    for path, _, expected in adapter_files + weights:
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f'missing or changed evaluated artifact: {path}')
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    names = sorted(set(filter(None, tracked)) | {'tools/package_v3_submission.py', 'artifacts/v3/LICENSE-QWEN', 'artifacts/v3/MODEL-NOTICE.txt'})
    source = []
    for name in names:
        if 'blind-key' in name or name.endswith('/.lock'):
            raise ValueError(f'private or transient file in source inventory: {name}')
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'source must be a regular file: {name}')
        source.append((path, name, digest(path)))
    notices = [(ROOT / name, name, digest(ROOT / name)) for name in
               ['artifacts/v3/LICENSE-QWEN', 'artifacts/v3/MODEL-NOTICE.txt', 'artifacts/v3/MODEL_CARD.md']]
    adapter_files += notices
    weights += notices
    output.mkdir(parents=True)
    manifest = {
        'schema': 1, 'candidate': 'v3-candidate03-step120',
        'parent_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        'source_identity': 'working files; per-file SHA-256 is authoritative',
        'safety_gate': 'failed', 'publication_status': 'local_only',
        'archives': {},
    }
    for label, files in [('source', source), ('adapter', adapter_files), ('ollama', weights)]:
        target = output / f'v3-{label}.zip'
        inventory = {name: {'sha256': sha, 'bytes': path.stat().st_size}
                     for path, name, sha in files}
        with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for path, name, _ in files:
                archive.write(path, name)
            archive.writestr(f'v3-{label}-inventory.json', json.dumps(inventory, indent=2) + '\n')
        # Verify the archived bytes against the inventory, including large weights.
        with zipfile.ZipFile(target) as archive:
            for name, item in inventory.items():
                with archive.open(name) as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != item['sha256']:
                        raise ValueError(f'archive content mismatch: {name}')
        manifest['archives'][target.name] = {
            'sha256': digest(target), 'bytes': target.stat().st_size, 'files': inventory}
        print(f'verified {target.name}: {len(files)} files', flush=True)
    (output / 'release-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(output, flush=True)


if __name__ == '__main__':
    main()
