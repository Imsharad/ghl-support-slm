"""Use google-colab-cli's authenticated client with an existing browser runtime.

Run with the Python interpreter that has google-colab-cli installed. No new
assignment, local session-state edits, kernel creation/restart, or shutdown.
Credentials stay in memory; transport errors omit credential-bearing URLs.
"""

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import logging
from pathlib import Path
import sys
from urllib.parse import quote


def select_assignment(assignments, endpoint):
    matches = [a for a in assignments if a.endpoint == endpoint]
    if len(matches) != 1:
        raise ValueError("Expected exactly one matching live runtime; no allocation attempted")
    return matches[0]


def select_kernel(kernels):
    if len(kernels) != 1 or not kernels[0].get("id"):
        raise ValueError("Expected exactly one existing kernel; refusing to create or guess")
    return kernels[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    read = sub.add_parser("read")
    read.add_argument("remote")
    read.add_argument("--tail", type=int, default=3000)
    execute = sub.add_parser("exec")
    execute.add_argument("--code", required=True)
    execute.add_argument("--timeout", type=float, default=60)
    download = sub.add_parser("download")
    download.add_argument("remote")
    download.add_argument("local", type=Path)
    chunks = sub.add_parser("download-chunks")
    chunks.add_argument("remote", help="Remote directory containing manifest.json and numbered parts")
    chunks.add_argument("local", type=Path)
    args = parser.parse_args()
    # The upstream debug logger may include authorization headers. Never enable it.
    logging.disable(logging.CRITICAL)
    import requests
    from colab_cli.common import State
    from colab_cli.runtime import ColabRuntime

    assignment = select_assignment(State().client.list_assignments(), args.endpoint)
    proxy = assignment.runtime_proxy_info

    def get(path, **params):
        response = requests.get(proxy.url.rstrip("/") + "/" + path,
                                params={"authuser": "0", "colab-runtime-proxy-token": proxy.token,
                                        **params}, timeout=60)
        if not response.ok:
            raise RuntimeError(f"Remote request failed: HTTP {response.status_code}")
        return response.json()

    if args.action == "read":
        data = get("api/contents/" + quote(args.remote.strip("/"), safe="/"), content="1")
        if data.get("type") != "file" or data.get("format") != "text":
            raise ValueError("Not a text file")
        print(data["content"][-args.tail:])
        return

    def file_bytes(remote):
        data = get("api/contents/" + quote(remote.strip("/"), safe="/"), content="1")
        if data.get("type") != "file":
            raise ValueError("Not a remote file")
        if data.get("format") == "base64":
            # Jupyter may return MIME-wrapped base64 with line breaks.
            payload = base64.b64decode("".join(data["content"].split()), validate=True)
        elif data.get("format") == "text":
            payload = data["content"].encode("utf-8")
        else:
            raise ValueError("Unsupported remote content format")
        return payload

    if args.action == "download-chunks":
        manifest_bytes = file_bytes(args.remote.rstrip("/") + "/manifest.json")
        manifest = json.loads(manifest_bytes)
        parts = manifest["chunks"]
        if manifest.get("schema") != 1 or not parts:
            raise ValueError("Invalid chunk manifest")
        for index, part in enumerate(parts):
            if part["name"] != f"part-{index:05d}" or not 0 < part["bytes"] <= 16 * 1024 * 1024:
                raise ValueError("Invalid chunk path or size")
        args.local.mkdir(parents=True, exist_ok=True)
        manifest_path = args.local / "manifest.json"
        if manifest_path.exists():
            if manifest_path.read_bytes() != manifest_bytes:
                raise ValueError("Preserve different existing manifest")
        else:
            with manifest_path.open("xb") as handle:
                handle.write(manifest_bytes)

        def fetch(part):
            path = args.local / part["name"]
            if path.is_symlink():
                raise ValueError("Refusing symlink destination")
            payload = path.read_bytes() if path.exists() else file_bytes(args.remote.rstrip("/") + "/" + part["name"])
            if len(payload) != part["bytes"] or hashlib.sha256(payload).hexdigest() != part["sha256"]:
                raise ValueError("Chunk verification failed; preserve existing bytes")
            if not path.exists():
                with path.open("xb") as handle:
                    handle.write(payload)
            return part["name"]

        with ThreadPoolExecutor(max_workers=2) as executor:
            for number, name in enumerate(executor.map(fetch, parts), start=1):
                print(f"Verified {name} ({number}/{len(parts)})", flush=True)
        return

    if args.action == "download":
        if args.local.exists():
            raise ValueError("Local destination exists; refusing overwrite")
        payload = file_bytes(args.remote)
        args.local.parent.mkdir(parents=True, exist_ok=True)
        with args.local.open("xb") as handle:
            handle.write(payload)
        print(json.dumps({"path": str(args.local), "bytes": len(payload),
                          "sha256": hashlib.sha256(payload).hexdigest()}))
        return

    kernel = select_kernel(get("api/kernels"))
    print(json.dumps({"endpoint": assignment.endpoint, "hardware": assignment.accelerator.value,
                      "kernel": kernel["id"], "state": kernel.get("execution_state")}), flush=True)
    if args.action == "status":
        return
    if kernel.get("execution_state") != "idle":
        raise ValueError("Existing kernel is busy; inspect before submitting more code")
    runtime = ColabRuntime(proxy.url, proxy.token, kernel_id=kernel["id"])

    def output(item):
        if item.get("output_type") == "stream":
            print(item.get("text", ""), end="", flush=True)
        elif item.get("output_type") == "error":
            print(item.get("ename", "Error") + ": " + item.get("evalue", ""), flush=True)
        elif "text/plain" in item.get("data", {}):
            print(item["data"]["text/plain"], flush=True)

    try:
        outputs = runtime.execute_code(args.code, output_hook=output, timeout=args.timeout)
        if any(item.get("output_type") == "error" for item in outputs):
            raise RuntimeError("Remote execution failed; inspect retained remote logs")
    finally:
        runtime.stop(shutdown_kernel=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # requests and websocket exception messages can contain proxy-token URLs.
        print(f"Connection/action failed ({type(exc).__name__}); runtime was not stopped. "
              "Check status and remote logs before retrying.", file=sys.stderr)
        raise SystemExit(1)
