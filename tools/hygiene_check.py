#!/usr/bin/env python3
"""Refuse commits that would ship personal material or secrets.

Runs from .git/hooks/pre-commit as `python3 tools/hygiene_check.py --staged`
(stdlib only, so the system python is fine). `--tree` scans every tracked file
instead, for a full audit. Exit 1 blocks the commit.
"""
import argparse
import re
import subprocess
import sys

BLOCKED_PATHS = re.compile(
    r"^(docs/career|docs/interview|docs/analysis)/"
    r"|(^|/)(cv|resume|cover[-_]?letter|interview)[^/]*\.(html|pdf|md|docx)$"
    r"|\.comments\.json$"
    r"|^(index\.html|docs/index\.html|docs/eval)$",
    re.I,
)
SECRET = re.compile(
    r"hf_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}"
    r"|AKIA[0-9A-Z]{16}|xox[bp]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|AIza[0-9A-Za-z_-]{30,}"
)
PHONE = re.compile(r"(?<![\w/#-])(\+91[\s-]?[6-9]\d{4}[\s-]?\d{5}|\+1[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{4})(?![\w-])")
ALLOWED_EMAIL = {"im.sharad.jain@gmail.com"}
# The tuned model invented this number on ch-017/018; docs quote it as evidence.
ALLOWED_PHONES = {"+1-800-123-4567"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}")
SKIP_CONTENT = re.compile(r"\.(png|jpg|jpeg|gif|gguf|safetensors|lock|ipynb)$|^uv\.lock$")
# Model outputs and judge sheets under eval/results contain invented phone numbers and
# emails by design (that is the evidence). Secrets are still scanned there; PII rules are not.
MODEL_OUTPUT = re.compile(r"^eval/results/")


def git(*args):
    # Binary artifacts can contain invalid UTF-8. Match tree_blob's tolerant
    # decoding while retaining ASCII secret detection, rather than skipping video.
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          errors="replace", check=False).stdout


def staged_paths():
    out = git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [p for p in out.splitlines() if p]


def staged_blob(path):
    return git("show", f":{path}")


def tree_paths():
    return [p for p in git("ls-files").splitlines() if p]


def tree_blob(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--tree", action="store_true")
    a = ap.parse_args()
    if a.tree:
        paths, read = tree_paths(), tree_blob
    else:
        paths, read = staged_paths(), staged_blob
    problems = []
    for p in paths:
        if BLOCKED_PATHS.search(p):
            problems.append(f"{p}: personal or prep material; keep it out of the repo")
            continue
        if SKIP_CONTENT.search(p):
            continue
        text = read(p)
        for n, line in enumerate(text.splitlines(), 1):
            if SECRET.search(line):
                problems.append(f"{p}:{n}: looks like a secret token")
            if MODEL_OUTPUT.match(p):
                continue
            for m in PHONE.findall(line):
                if m not in ALLOWED_PHONES:
                    problems.append(f"{p}:{n}: looks like a phone number")
            for m in EMAIL.findall(line):
                if m.lower() not in ALLOWED_EMAIL and not m.lower().endswith(("example.com", "example.org")):
                    problems.append(f"{p}:{n}: email address {m}")
    if problems:
        print("hygiene_check: refusing", file=sys.stderr)
        for pr in problems:
            print("  " + pr, file=sys.stderr)
        print("Fix the file or unstage it. Bypass only with an explicit human go: git commit --no-verify", file=sys.stderr)
        return 1
    print(f"hygiene_check: ok ({len(paths)} paths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
