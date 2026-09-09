# Fresh-clone smoke transcript

Run on an Apple M1 Pro Mac on 2026-09-06 IST. The source repository was at commit
`ba88a4141971480b73f0533cc66b4ec88daa24c3`. Command output below is copied from the run; ANSI
spinner frames from `ollama create` and curl's transfer-progress meter are omitted, but their final
output, exit status, and timings are preserved.

## Deviations and known conditions

- **Deviation: no published repository or submission tag existed.** The clone source was the local
  path `/Users/sharad/Projects/agents-hq/gohighlevel-assignement-1`, and `main` was checked out at
  `ba88a4141971480b73f0533cc66b4ec88daa24c3`.
- **Deviation: README section 8's test command does not pass after the documented serving-only
  install.** `uv run pytest -q` returned 2 failures and 27 passes. The `serve` extra does not install
  `peft`, which `tests/evaluation/test_eval.py::test_zero_effect_adapter_matches_base_greedy_cpu` imports, and
  the gitignored `data/processed/train.jsonl` file needed by
  `tests/data/test_prepare.py::test_frozen_splits_have_no_group_leakage` is absent in a fresh clone. No
  file in the temporary clone was fixed or changed to work around either failure; the serving smoke
  continued because neither failure is on that path.
- **Known condition, not a deviation:** README line 54 contained `[PENDING remote]`, as expected.
- **Known condition, not a deviation:** Ollama was already running, so `ollama serve` was omitted as
  the README permits. The existing `ghl-support` tag was recreated from the freshly fetched,
  hash-verified `serve/Modelfile`.

No other step required a deviation.

## Transcript

### Create the temporary clone

```console
$ mktemp -d /tmp/ghl-g2-fresh-clone.XXXXXX
/tmp/ghl-g2-fresh-clone.O4MqZt

$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:04:27 IST
$ /usr/bin/time -p git clone /Users/sharad/Projects/agents-hq/gohighlevel-assignement-1 /tmp/ghl-g2-fresh-clone.O4MqZt/ghl-slm
Cloning into '/tmp/ghl-g2-fresh-clone.O4MqZt/ghl-slm'...
done.
real 0.15
user 0.01
sys 0.08
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:04:27 IST

$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:04:36 IST
$ /usr/bin/time -p git checkout main
Already on 'main'
Your branch is up to date with 'origin/main'.
real 0.05
user 0.01
sys 0.01
$ git rev-parse HEAD
ba88a4141971480b73f0533cc66b4ec88daa24c3
$ git status --short --branch
## main...origin/main
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:04:37 IST
```

### Install the locked serving environment

```console
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:04:45 IST
$ /usr/bin/time -p uv sync --frozen --extra serve
Using CPython 3.11.11 interpreter at: /opt/homebrew/opt/python@3.11/bin/python3.11
Creating virtual environment at: .venv
   Building ghl-support-slm @ file:///private/tmp/ghl-g2-fresh-clone.O4MqZt/ghl-slm
      Built ghl-support-slm @ file:///private/tmp/ghl-g2-fresh-clone.O4MqZt/ghl-slm
Prepared 1 package in 418ms
Installed 82 packages in 1.17s
 + absl-py==2.5.0
 + aiohappyeyeballs==2.7.1
 + aiohttp==3.14.3
 + aiosignal==1.4.0
 + annotated-doc==0.0.5
 + annotated-types==0.8.0
 + anyio==4.15.1
 + attrs==26.1.0
 + certifi==2026.7.22
 + charset-normalizer==3.5.1
 + click==8.5.0
 + cloudpickle==3.1.2
 + contourpy==1.3.3
 + cycler==0.12.1
 + datasets==5.0.1
 + defusedxml==0.7.1
 + dill==0.4.1
 + fastapi==0.141.1
 + filelock==3.32.5
 + fonttools==4.64.0
 + frozenlist==1.8.0
 + fsspec==2026.6.0
 + ghl-support-slm==0.1.0 (from file:///private/tmp/ghl-g2-fresh-clone.O4MqZt/ghl-slm)
 + h11==0.16.0
 + hf-xet==1.6.0
 + httpcore==1.0.9
 + httpx==0.28.1
 + huggingface-hub==1.30.0
 + idna==3.19
 + iniconfig==2.3.0
 + jinja2==3.1.6
 + joblib==1.6.0
 + kiwisolver==1.5.1
 + markdown-it-py==4.2.0
 + markupsafe==3.0.3
 + matplotlib==3.11.1
 + mdurl==0.1.2
 + mpmath==1.3.0
 + multidict==6.7.1
 + multiprocess==0.70.19
 + narwhals==2.25.0
 + networkx==3.6.1
 + nltk==3.10.3
 + numpy==2.4.6
 + packaging==26.3
 + pandas==3.0.5
 + pillow==12.3.0
 + pluggy==1.6.0
 + propcache==0.5.2
 + pyarrow==25.0.1
 + pydantic==2.13.5
 + pydantic-core==2.46.5
 + pygments==2.21.0
 + pyparsing==3.3.2
 + pytest==9.1.1
 + python-dateutil==2.9.0.post0
 + pyyaml==6.0.3
 + regex==2026.9.3
 + requests==2.34.2
 + rich==15.0.0
 + rouge-score==0.1.2
 + safetensors==0.8.0
 + scikit-learn==1.9.0
 + scipy==1.17.1
 + sentence-transformers==6.0.1
 + setuptools==84.0.0
 + shellingham==1.5.4
 + six==1.17.0
 + starlette==1.6.0
 + sympy==1.14.0
 + threadpoolctl==3.6.0
 + tokenizers==0.23.2
 + torch==2.14.0
 + tqdm==4.70.0
 + transformers==5.16.1
 + typer==0.27.2
 + typing-extensions==4.16.0
 + typing-inspection==0.4.4
 + urllib3==2.7.0
 + uvicorn==0.52.4
 + xxhash==4.0.1
 + yarl==1.24.5
real 1.91
user 0.19
sys 0.77
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:04:47 IST
```

### Run the README test gate

```console
$ /usr/bin/time -p uv run pytest -q
........F.........F......                                            [100%]
=================================== FAILURES ===================================
_______________ test_zero_effect_adapter_matches_base_greedy_cpu _______________

tmp_path = PosixPath('/private/var/folders/1f/glzj2c6d0fg0lfjnwfrrhrg80000gn/T/pytest-of-sharad/pytest-67/test_zero_effect_adapter_match0')

    def test_zero_effect_adapter_matches_base_greedy_cpu(tmp_path: Path) -> None:
>       adapter_dir = _build_zero_effect_adapter(tmp_path / "zero-lora")
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests/evaluation/test_eval.py:287:

directory = PosixPath('/private/var/folders/1f/glzj2c6d0fg0lfjnwfrrhrg80000gn/T/pytest-of-sharad/pytest-67/test_zero_effect_adapter_match0/zero-lora')

    def _build_zero_effect_adapter(directory: Path) -> Path:
        import torch
>       from peft import LoraConfig, get_peft_model
E       ModuleNotFoundError: No module named 'peft'

tests/evaluation/test_eval.py:256: ModuleNotFoundError
___________________ test_frozen_splits_have_no_group_leakage ___________________

    @pytest.mark.skipif(not SPLITS_PATH.exists(), reason="run data/prepare.py first")
    def test_frozen_splits_have_no_group_leakage() -> None:
        splits = json.loads(SPLITS_PATH.read_text(encoding="utf-8"))
>       split_rows = {
            name: prepare.load_jsonl(PROCESSED_DIR / f"{name}.jsonl")
            for name in prepare.SPLIT_NAMES
        }

tests/data/test_prepare.py:282: in test_frozen_splits_have_no_group_leakage
tests/data/test_prepare.py:283: in <dictcomp>
    name: prepare.load_jsonl(PROCESSED_DIR / f"{name}.jsonl")
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
data/prepare.py:617: in load_jsonl
    with path.open(encoding="utf-8") as handle:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

self = PosixPath('/private/tmp/ghl-g2-fresh-clone.O4MqZt/ghl-slm/data/processed/train.jsonl')
mode = 'r', buffering = -1, encoding = 'utf-8', errors = None, newline = None

    def open(self, mode='r', buffering=-1, encoding=None,
             errors=None, newline=None):
        """
        Open the file pointed by this path and return a file object as a stream.
        """
        if "b" not in mode:
            encoding = io.text_encoding(encoding)
>       return io.open(self, mode, buffering, encoding, errors, newline)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       FileNotFoundError: [Errno 2] No such file or directory:
E       '/private/tmp/ghl-g2-fresh-clone.O4MqZt/ghl-slm/data/processed/train.jsonl'

/opt/homebrew/Cellar/python@3.11/3.11.11/Frameworks/Python.framework/Versions/3.11/lib/python3.11/pathlib.py:1044: FileNotFoundError
=========================== short test summary info ============================
FAILED tests/evaluation/test_eval.py::test_zero_effect_adapter_matches_base_greedy_cpu
FAILED tests/data/test_prepare.py::test_frozen_splits_have_no_group_leakage
2 failed, 27 passed in 33.82s
real 35.36
user 9.23
sys 2.76
```

### Fetch and verify the served artifacts

```console
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:06:18 IST
$ /usr/bin/time -p uv run python tools/artifacts/fetch_artifacts.py --manifest artifacts/manifest.json --target serve
FETCH artifacts/base-q8.gguf <- https://huggingface.co/seekingtroooth/ghl-support-qlora-t4/resolve/main/artifacts/base-q8.gguf
FETCHED artifacts/base-q8.gguf bytes=1646572704 sha256=eb2837d6dd3d8724fe51f80796e2dd16ba3bb38dd4301b43a4704d0c1219e7a5
FETCH artifacts/tuned-q8.gguf <- https://huggingface.co/seekingtroooth/ghl-support-qlora-t4/resolve/main/artifacts/tuned-q8.gguf
FETCHED artifacts/tuned-q8.gguf bytes=1646572576 sha256=03ba912ba0e87269d58556769d17d922262aa2c84a3f91fdc1a40455fd8bf2a9
verified=2 target=serve
real 359.04
user 9.36
sys 10.19
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:12:17 IST

$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:12:24 IST
$ /usr/bin/time -p uv run python tools/artifacts/check_artifacts.py --manifest artifacts/manifest.json --target serve
PASS artifacts/base-q8.gguf bytes=1646572704 sha256=eb2837d6dd3d8724fe51f80796e2dd16ba3bb38dd4301b43a4704d0c1219e7a5
PASS artifacts/tuned-q8.gguf bytes=1646572576 sha256=03ba912ba0e87269d58556769d17d922262aa2c84a3f91fdc1a40455fd8bf2a9
verified=2 target=serve
real 2.06
user 1.43
sys 0.49
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:12:26 IST
```

### Recreate the tuned Ollama tag

```console
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:12:35 IST
$ /usr/bin/time -p ollama create ghl-support -f serve/Modelfile
gathering model components
copying file sha256:03ba912ba0e87269d58556769d17d922262aa2c84a3f91fdc1a40455fd8bf2a9 100%
parsing GGUF
using existing layer sha256:03ba912ba0e87269d58556769d17d922262aa2c84a3f91fdc1a40455fd8bf2a9
using existing layer sha256:004333215bcf4b4854deb857981bddec37a1cb0b18fd5ebf8c7c4bb4ff3e39b4
using existing layer sha256:2bacca1da2c59077ed208851967f5bfff4eef053c537584961c00ad16d3a76c4
using existing layer sha256:0273f3ba4c84c721ad59b980f3d5c25fd5c7b690b2f546a8c8adbc709051ed2c
writing manifest
success
real 1.14
user 0.70
sys 0.15
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:12:36 IST
```

### Run the wrapper self-test

```console
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:12:43 IST
$ /usr/bin/time -p uv run python serve/inference.py --backend ollama --model ghl-support --self-test
{
  "backend": "ollama",
  "model": "ghl-support",
  "answer": "I'm sorry to hear that you're having trouble signing in due to a forgotten password. Don't worry, I'm here to help you resolve this issue. To reset your password, please follow these steps:\n\n1. Visit our website and navigate to the login page.\n2. Look for the \"Forgot Password\" or \"Reset Password\" option and click on it.\n3. You will be prompted to provide your registered email address associated with your account. Make sure to enter the correct email address.\n4. Once you've entered your email address, you will receive an email with instructions on how to reset your password. Please check your spam or junk folder as well, as sometimes emails can get filtered there.\n5. Follow the instructions provided in the email to create a new password for your account.\n\nIf you encounter any difficulties during this process or if you have any further questions, please don't hesitate to let me know. I'm here to assist you every step of the way.",
  "prompt_tokens": 70,
  "generated_tokens": 198,
  "latency_ms": 5233.696,
  "device": null,
  "self_test": "PASS"
}
real 5.35
user 0.06
sys 0.03
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:12:48 IST
```

### Final HTTP request

```console
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:12:54 IST
$ /usr/bin/time -p curl --fail-with-body http://localhost:11434/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"ghl-support","messages":[{"role":"user","content":"I forgot my password and cannot sign in. What should I do?"}],"temperature":0,"max_tokens":256,"stream":false}'
{"id":"chatcmpl-840","object":"chat.completion","created":1788698577,"model":"ghl-support","system_fingerprint":"fp_ollama","choices":[{"index":0,"message":{"role":"assistant","content":"I'm sorry to hear that you're having trouble signing in due to a forgotten password. Don't worry, I'm here to help you resolve this issue. To reset your password, please follow these steps:\n\n1. Visit our website and navigate to the login page.\n2. Look for the \"Forgot Password\" or \"Reset Password\" option and click on it.\n3. You will be prompted to provide your registered email address associated with your account. Make sure to enter the correct email address.\n4. Once you've entered your email address, you will receive an email with instructions on how to reset your password. Please check your spam or junk folder as well, as sometimes emails can get filtered there.\n5. Follow the instructions provided in the email to create a new password for your account.\n\nIf you encounter any difficulties during this process or if you have any further questions, please don't hesitate to let me know. I'm here to assist you every step of the way."},"finish_reason":"stop"}],"usage":{"prompt_tokens":70,"completion_tokens":198,"total_tokens":268}}
real 3.19
user 0.00
sys 0.00
$ date '+%Y-%m-%d %H:%M:%S IST'
2026-09-06 18:12:57 IST
```

The final request returned HTTP success with a nonempty `choices[0].message.content`, useful
password-recovery guidance, no account-access claim, and no request for a password or payment-card
credential.
