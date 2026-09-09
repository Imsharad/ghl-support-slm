#!/usr/bin/env python3
"""Own the reviewer backend lifecycle; invoked through start.sh."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.runtime'


def request(url, body=None, timeout=10):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def free_port(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('127.0.0.1', port))
        except OSError as exc:
            raise RuntimeError(f'Port {port} is occupied. Stop its service or choose another --port/--ollama-port.') from exc


def wait_ready(url, child, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError(f'Service exited with code {child.returncode}; inspect .runtime/logs/')
        try:
            result = request(url, timeout=2)
            if child.poll() is None:
                return result
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(.25)
    raise RuntimeError(f'Timed out waiting for {url}; inspect .runtime/logs/')


def stop_children(children):
    for child in reversed(children):
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


def install_ollama():
    config = json.loads((ROOT / 'configs/bootstrap.json').read_text())
    key = f'{platform.system().lower()}-{platform.machine().lower()}'
    spec = config['platforms'][key]
    destination = STATE / 'tools' / f"ollama-{config['ollama_version']}"
    binary = destination / spec['binary']
    if binary.is_file():
        return binary
    print('[setup] Downloading and verifying pinned Ollama...', flush=True)
    with tempfile.TemporaryDirectory(dir=STATE, prefix='ollama-install-') as tmp:
        tmp = Path(tmp)
        archive = tmp / spec['archive']
        subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--connect-timeout', '20', spec['url'], '-o', str(archive)], check=True)
        with archive.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != spec['sha256']:
            raise RuntimeError('Ollama checksum mismatch; refusing to execute it.')
        unpacked = tmp / 'unpacked'
        unpacked.mkdir()
        if archive.name.endswith('.zst'):
            import zstandard
            with archive.open('rb') as source, zstandard.ZstdDecompressor().stream_reader(source) as decoded:
                with tarfile.open(fileobj=decoded, mode='r|') as tar:
                    tar.extractall(unpacked, filter='data')
        else:
            with tarfile.open(archive) as tar:
                tar.extractall(unpacked, filter='data')
        if not (unpacked / spec['binary']).is_file():
            raise RuntimeError('Unexpected Ollama archive layout')
        unpacked.rename(destination)
    return binary


def verify_manifest(raw, expected, local_digest):
    manifest = json.loads(raw)
    # Ollama hashes absolute local 'from' paths. All other content must match.
    for layer in manifest['layers']:
        layer.pop('from', None)
    if manifest != expected or hashlib.sha256(raw).hexdigest() != local_digest:
        raise RuntimeError('Model content or local tag identity differs from the verified manifest')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8013)
    parser.add_argument('--ollama-port', type=int, default=11435)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not all(1024 <= p <= 65535 for p in (args.port, args.ollama_port)) or args.port == args.ollama_port:
        parser.error('Choose two distinct ports between 1024 and 65535')
    STATE.mkdir(exist_ok=True)
    (STATE / 'logs').mkdir(exist_ok=True)
    lock = (STATE / 'backend.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError('This checkout already has a running launcher. Use its API or stop it with Ctrl+C.') from None
    free_port(args.port)
    free_port(args.ollama_port)
    children, logs = [], []
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        binary = install_ollama()
        subprocess.run([sys.executable, 'tools/fetch_artifacts.py', '--manifest', 'artifacts/v3/manifest.json', '--target', 'serve'], cwd=ROOT, check=True)
        env = os.environ.copy()
        env.update(HF_HOME=str(STATE / 'huggingface'), HF_HUB_CACHE=str(STATE / 'huggingface/hub'),
                   OLLAMA_HOST=f'127.0.0.1:{args.ollama_port}', OLLAMA_MODELS=str(STATE / 'ollama/models'),
                   OLLAMA_MAX_LOADED_MODELS='1', OLLAMA_NUM_PARALLEL='1',
                   SUPPORT_OLLAMA_URL=f'http://127.0.0.1:{args.ollama_port}', SUPPORT_BASE_TAG='ghl-base',
                   SUPPORT_TUNED_TAG='ghl-support-v3-c03-s120', SUPPORT_PROMPT_FILE=str(ROOT / 'configs/prompt-v3.txt'))
        env.pop('HF_HUB_OFFLINE', None)
        env.pop('TRANSFORMERS_OFFLINE', None)
        print('[setup] Caching the pinned tokenizer in this checkout...', flush=True)
        subprocess.run([sys.executable, '-c', 'from train.render import get_tokenizer\ntry: get_tokenizer()\nexcept OSError: get_tokenizer(local_files_only=False)'], cwd=ROOT, env=env, check=True)
        env['HF_HUB_OFFLINE'] = '1'
        def launch(command, name):
            log = (STATE / 'logs' / f'{name}.log').open('w')
            logs.append(log)
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            children.append(child)
            return child
        ollama = launch([str(binary), 'serve'], 'ollama')
        wait_ready(f'http://127.0.0.1:{args.ollama_port}/api/version', ollama)
        for tag, modelfile in [('ghl-base', 'serve/Modelfile.base'), ('ghl-support-v3-c03-s120', 'serve/Modelfile.v3-candidate03-step120')]:
            print(f'[setup] Importing {tag} into the private model store...', flush=True)
            subprocess.run([str(binary), 'create', tag, '-f', modelfile], cwd=ROOT, env=env, check=True, stdout=logs[0], stderr=subprocess.STDOUT)
        api = launch([sys.executable, '-m', 'uvicorn', 'serve.api:create_app', '--factory', '--host', '127.0.0.1', '--port', str(args.port), '--no-access-log'], 'api')
        url = f'http://127.0.0.1:{args.port}'
        health = wait_ready(url + '/health', api)
        manifests = json.loads((ROOT / 'configs/bootstrap.json').read_text())['model_manifests']
        for model, identity in health['models'].items():
            tag = identity['tag']
            manifest_path = STATE / 'ollama/models/manifests/registry.ollama.ai/library' / tag / 'latest'
            raw = manifest_path.read_bytes()
            verify_manifest(raw, manifests[tag], identity['digest'])
        expected = hashlib.sha256((ROOT / 'configs/prompt-v3.txt').read_text().removesuffix('\n').encode()).hexdigest()
        if health['prompt_sha256'] != expected:
            raise RuntimeError('Prompt identity mismatch')
        checks = {}
        for model in ('base', 'tuned'):
            print(f'[check] Real {model} inference (first load can take a minute)...', flush=True)
            result = request(url + '/support', {'model': model, 'query': 'I forgot my password. What should I do?'}, timeout=180)
            if not result.get('answer', '').strip() or result['model_digest'] != health['models'][model]['digest'] or result['prompt_sha256'] != expected:
                raise RuntimeError(f'{model} inference returned empty text or mismatched identity')
            checks[model] = result
        (STATE / 'last-check.json').write_text(json.dumps({'health': health, 'responses': checks, 'checked_at': time.time()}, indent=2) + '\n')
        print(f'READY: {url} | API docs: {url}/docs\nBoth models passed real inference. Logs: {STATE / "logs"}\nCtrl+C stops the services started by this launcher.', flush=True)
        if args.check:
            return 0
        while True:
            if any(child.poll() is not None for child in children):
                raise RuntimeError('A backend service exited; inspect .runtime/logs/')
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nStopping local backend...', flush=True)
        return 130
    finally:
        stop_children(children)
        for log in logs:
            log.close()
        lock.close()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
