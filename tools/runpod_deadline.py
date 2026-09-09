"""Terminate exactly one explicitly named pod at a UTC deadline; never delete storage.

Run as a detached process. This is a best-effort watchdog, not a provider spending cap.
The operator must verify checkpoints are on a separate network volume before arming.
"""
import argparse
from datetime import datetime, timezone
import json
import subprocess
import time


def invoke(cli, action, pod_id):
    result = subprocess.run([cli, "pod", action, pod_id], text=True,
                            capture_output=True, timeout=45)
    if result.returncode:
        try:
            error = json.loads(result.stderr)
        except ValueError:
            error = {"code": "unparsed_cli_error"}
        if error.get("code") == "not_found":
            return None
        raise RuntimeError(f"pod {action}: {error.get('code', 'unknown_error')}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def verify_identity(pod, pod_id, name, volume_id):
    if pod is not None and (pod.get("id") != pod_id or pod.get("name") != name
                            or pod.get("networkVolumeId") != volume_id):
        raise ValueError("pod identity differs from the explicitly armed target")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cli", required=True)
    ap.add_argument("--pod-id", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--volume-id", required=True)
    ap.add_argument("--deadline", required=True, help="ISO-8601 timestamp with timezone")
    args = ap.parse_args()
    deadline = datetime.fromisoformat(args.deadline)
    if deadline.tzinfo is None:
        ap.error("deadline must include timezone")
    target = deadline.timestamp()
    pod = invoke(args.cli, "get", args.pod_id)
    verify_identity(pod, args.pod_id, args.name, args.volume_id)
    if pod is None:
        print("already_absent", flush=True)
        return
    print(json.dumps({"status": "armed", "pod_id": args.pod_id,
                      "deadline": deadline.isoformat()}), flush=True)
    while True:
        remaining = target - time.time()
        if remaining <= 0:
            break
        time.sleep(min(30, remaining))
    for attempt in range(6):
        try:
            pod = invoke(args.cli, "get", args.pod_id)
            verify_identity(pod, args.pod_id, args.name, args.volume_id)
            if pod is None:
                print("confirmed_absent", flush=True)
                return
            invoke(args.cli, "delete", args.pod_id)
            print(json.dumps({"status": "delete_requested", "attempt": attempt + 1,
                              "time": datetime.now(timezone.utc).isoformat()}), flush=True)
        except ValueError:
            raise  # Never delete an identity that no longer matches.
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            print(type(exc).__name__ + ": cleanup retry required", flush=True)
        time.sleep(10)
    if invoke(args.cli, "get", args.pod_id) is not None:
        raise SystemExit("cleanup_unconfirmed: operator must inspect the exact pod immediately")


if __name__ == "__main__":
    main()
