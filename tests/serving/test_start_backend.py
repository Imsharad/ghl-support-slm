"""Lifecycle checks that do not download or load models."""
import socket
import subprocess
import sys

import pytest

from tools.runtime.start_backend import free_port, stop_children, wait_ready


def test_occupied_port_does_not_disturb_listener():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        with pytest.raises(RuntimeError, match='occupied'):
            free_port(listener.getsockname()[1])
        assert listener.fileno() >= 0


def test_dead_service_fails_without_waiting_for_timeout():
    child = subprocess.Popen([sys.executable, '-c', 'raise SystemExit(7)'], start_new_session=True)
    child.wait()
    with pytest.raises(RuntimeError, match='code 7'):
        wait_ready('http://127.0.0.1:1/health', child)


def test_cleanup_stops_only_owned_children():
    command = [sys.executable, '-c', 'import time; time.sleep(60)']
    owned = subprocess.Popen(command, start_new_session=True)
    unrelated = subprocess.Popen(command, start_new_session=True)
    try:
        stop_children([owned])
        assert owned.poll() is not None
        assert unrelated.poll() is None
        stop_children([owned])  # idempotent cleanup
    finally:
        unrelated.terminate()
        unrelated.wait()


def test_manifest_accepts_local_path_but_rejects_changed_weights():
    import hashlib
    import json
    from tools.runtime.start_backend import verify_manifest
    expected = {'layers': [{'digest': 'sha256:expected'}]}
    raw = json.dumps({'layers': [{'digest': 'sha256:expected', 'from': '/another/machine'}]}).encode()
    verify_manifest(raw, expected, hashlib.sha256(raw).hexdigest())
    changed = raw.replace(b'expected', b'modified')
    with pytest.raises(RuntimeError):
        verify_manifest(changed, expected, hashlib.sha256(changed).hexdigest())
    with pytest.raises(RuntimeError):
        verify_manifest(raw, expected, 'wrong-local-digest')


def test_recently_closed_server_port_can_be_reused():
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        listener.listen()
        with socket.create_connection(('127.0.0.1', port)) as client:
            conn, _ = listener.accept()
            conn.close()
            assert client.recv(1) == b''
    free_port(port)
