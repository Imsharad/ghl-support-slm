# Colab Session: ghl-v2

## Session Created: 2026-09-07 17:59:28
- Endpoint: `gpu-t4-s-kkb-usw4a2-27ab1iekflivv`

### Execution (2026-09-07 18:00:13)
```python
import subprocess, os, time
def sh(c):
    print("$", c, flush=True); t=time.time()
    subprocess.run(c, shell=True, check=True); print(f"  ok {time.time()-t:.0f}s", flush=True)
sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
if not os.path.isdir("/content/ghl-support-slm"):
    sh("git clone --branch v2 --depth 1 -q https://github.com/Imsharad/ghl-support-slm.git /content/ghl-support-slm")
os.chdir("/content/ghl-support-slm")
sh("git rev-parse HEAD")
sh("pip install -q 'transformers==5.16.1' 'peft==0.20.0' 'trl==1.12.0' 'bitsandbytes==0.50.2' 'accelerate>=0.34' 'datasets==5.0.1' 'sentence-transformers>=3.0' 'scikit-learn>=1.5' 'pyyaml>=6.0' 'matplotlib>=3.9'")
sh("python -c \"import torch,transformers,peft,bitsandbytes;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'tf',transformers.__version__,'peft',peft.__version__,'bnb',bitsandbytes.__version__)\"")
sh("python data/fetch.py")
print("SETUP DONE", time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
$ nvidia-smi --query-gpu=name,memory.total --format=csv
```

**Output**:
```
  ok 0s
```

**Output**:
```
$ git clone --branch v2 --depth 1 -q https://github.com/Imsharad/ghl-support-slm.git /content/ghl-support-slm
```

**Output**:
```
  ok 1s
```

**Output**:
```
$ git rev-parse HEAD
```

**Output**:
```
  ok 0s
```

**Output**:
```
$ pip install -q 'transformers==5.16.1' 'peft==0.20.0' 'trl==1.12.0' 'bitsandbytes==0.50.2' 'accelerate>=0.34' 'datasets==5.0.1' 'sentence-transformers>=3.0' 'scikit-learn>=1.5' 'pyyaml>=6.0' 'matplotlib>=3.9'
```

**Output**:
```
  ok 11s
```

**Output**:
```
$ python -c "import torch,transformers,peft,bitsandbytes;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'tf',transformers.__version__,'peft',peft.__version__,'bnb',bitsandbytes.__version__)"
```

**Output**:
```
  ok 27s
```

**Output**:
```
$ python data/fetch.py
```

**Output**:
```
  ok 3s
```

**Output**:
```
SETUP DONE 18:00:13 UTC
```

### Execution (2026-09-07 18:01:13)
```python
import subprocess, os
os.chdir("/content/ghl-support-slm")
for c in ["nvidia-smi --query-gpu=name,memory.total --format=csv,noheader", "git rev-parse --short HEAD",
          "python -c \"import torch,transformers,peft,bitsandbytes,trl,datasets;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'tf',transformers.__version__,'peft',peft.__version__,'bnb',bitsandbytes.__version__,'trl',trl.__version__,'datasets',datasets.__version__)\"",
          "ls -la data/raw | tail -3", "nproc; free -g | head -2; df -h /content | tail -1"]:
    r = subprocess.run(c, shell=True, capture_output=True, text=True)
    print("$", c, "\n", (r.stdout + r.stderr).strip()[:600], flush=True)

```

**Output**:
```
$ nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 
 Tesla T4, 15360 MiB
```

**Output**:
```
$ git rev-parse --short HEAD 
 f5ae72e
```

**Output**:
```
$ python -c "import torch,transformers,peft,bitsandbytes,trl,datasets;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'tf',transformers.__version__,'peft',peft.__version__,'bnb',bitsandbytes.__version__,'trl',trl.__version__,'datasets',datasets.__version__)" 
 torch 2.11.0+cu128 cuda True tf 5.16.1 peft 0.20.0 bnb 0.50.2 trl 1.12.0 datasets 5.0.1
```

**Output**:
```
$ ls -la data/raw | tail -3 
 drwxr-xr-x 5 root root     4096 Sep  7 18:00 ..
-rw-r--r-- 1 root root 19202474 Sep  7 18:00 bitext.csv
-rw-r--r-- 1 root root       77 Sep  7 18:00 bitext.csv.sha256
```

**Output**:
```
$ nproc; free -g | head -2; df -h /content | tail -1 
 2
               total        used        free      shared  buff/cache   available
Mem:              12           0           5           0           6          11
overlay         113G   48G   65G  43% /
```

### Execution (2026-09-07 18:01:51)
```python
import subprocess, os, time
os.chdir("/content/ghl-support-slm")
def sh(c, n=1200):
    print("$", c, flush=True); t=time.time()
    r = subprocess.run(c, shell=True, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    print("\n".join(out[-n:]), flush=True); print(f"  rc={r.returncode} {time.time()-t:.0f}s", flush=True)
    if r.returncode: raise SystemExit(r.returncode)
sh("python data/prepare.py --placeholder-mode substitute --out data/v2", 12)
sh("python data/prepare.py --audit-only --out data/v2 --strict", 6)
sh("python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push", 25)
sh("python tools/check_run.py train/runs/smoke-v2-t4 --max-memory-gb 12", 15)
print("PRESMOKE DONE", time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
$ python data/prepare.py --placeholder-mode substitute --out data/v2
```

**Output**:
```
        pretrained_model_name_or_path,
    ...<9 lines>...
        _commit_hash=commit_hash,
    )
  File "/usr/local/lib/python3.13/dist-packages/transformers/utils/hub.py", line 294, in cached_file
    file = cached_files(path_or_repo_id=path_or_repo_id, filenames=[filename], **kwargs)
  File "/usr/local/lib/python3.13/dist-packages/transformers/utils/hub.py", line 521, in cached_files
    raise OSError(
    ...<3 lines>...
    ) from e
OSError: We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.
Check your internet connection or see how to run the library in offline mode at 'https://huggingface.co/docs/transformers/installation#offline-mode'.
```

**Output**:
```
  rc=1 16s
```

**Output**:
```
/usr/local/lib/python3.13/dist-packages/IPython/core/interactiveshell.py:3561: UserWarning: To exit: use 'exit', 'quit', or Ctrl-D.
  warn("To exit: use 'exit', 'quit', or Ctrl-D.", stacklevel=1)
```

### Execution (2026-09-07 18:02:26)
```python
import subprocess
for c in ["curl -sS -o /dev/null -w '%{http_code} %{time_total}s\\n' https://huggingface.co/api/models/sentence-transformers/all-MiniLM-L6-v2",
          "curl -sS -o /dev/null -w '%{http_code}\\n' https://github.com", "env | grep -i -E 'hf_|proxy' | sed 's/=.*/=<set>/'",
          "python -c \"import huggingface_hub as h; print(h.__version__); print(h.whoami() if False else 'skip')\"", "cat /etc/resolv.conf | head -3"]:
    r = subprocess.run(c, shell=True, capture_output=True, text=True); print("$", c, "\n", (r.stdout + r.stderr).strip()[:400], flush=True)

```

**Output**:
```
$ curl -sS -o /dev/null -w '%{http_code} %{time_total}s\n' https://huggingface.co/api/models/sentence-transformers/all-MiniLM-L6-v2 
 200 0.165304s
```

**Output**:
```
$ curl -sS -o /dev/null -w '%{http_code}\n' https://github.com 
 200
```

**Output**:
```
$ env | grep -i -E 'hf_|proxy' | sed 's/=.*/=<set>/' 
 COLAB_LANGUAGE_SERVER_PROXY=<set>
COLAB_KERNEL_MANAGER_PROXY_HOST=<set>
MODEL_PROXY_HOST=<set>
COLAB_KERNEL_MANAGER_PROXY_PORT=<set>
```

**Output**:
```
$ python -c "import huggingface_hub as h; print(h.__version__); print(h.whoami() if False else 'skip')" 
 1.28.0
skip
```

**Output**:
```
$ cat /etc/resolv.conf | head -3 
 # Generated by Docker Engine.
# This file can be edited; Docker Engine will not make further changes once it
# has been modified.
```

### Execution (2026-09-07 18:02:40)
```python
import subprocess
for c in ["curl -sS -m 20 -o /dev/null -w '%{http_code} %{time_total}s' https://huggingface.co/api/models/sentence-transformers/all-MiniLM-L6-v2 2>&1",
          "curl -sS -m 20 -o /dev/null -w '%{http_code}' https://cdn-lfs.huggingface.co 2>&1",
          "getent hosts huggingface.co 2>&1", "curl -sS -m 20 -o /dev/null -w '%{http_code}' https://pypi.org 2>&1"]:
    r = subprocess.run(c, shell=True, capture_output=True, text=True); print("$", c[:70], "->", (r.stdout + r.stderr).strip()[:300], flush=True)

```

**Output**:
```
$ curl -sS -m 20 -o /dev/null -w '%{http_code} %{time_total}s' https://h -> 200 0.171764s
```

**Output**:
```
$ curl -sS -m 20 -o /dev/null -w '%{http_code}' https://cdn-lfs.huggingf -> curl: (6) Could not resolve host: cdn-lfs.huggingface.co
000
```

**Output**:
```
$ getent hosts huggingface.co 2>&1 -> 2600:9000:24ba:d400:17:b174:6d00:93a1 huggingface.co
2600:9000:24ba:1e00:17:b174:6d00:93a1 huggingface.co
2600:9000:24ba:4a00:17:b174:6d00:93a1 huggingface.co
2600:9000:24ba:a600:17:b174:6d00:93a1 huggingface.co
2600:9000:24ba:4c00:17:b174:6d00:93a1 huggingface.co
2600:9000:24ba:bc00:17:b174:6d00:93
```

**Output**:
```
$ curl -sS -m 20 -o /dev/null -w '%{http_code}' https://pypi.org 2>&1 -> 200
```

### Execution (2026-09-07 18:03:09)
```python
import subprocess, os, time
os.chdir("/content/ghl-support-slm")
def sh(c, n=1200):
    print("$", c, flush=True); t=time.time()
    r = subprocess.run(c, shell=True, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    print("\n".join(out[-n:]), flush=True); print(f"  rc={r.returncode} {time.time()-t:.0f}s", flush=True)
    if r.returncode: raise SystemExit(r.returncode)
sh("python data/prepare.py --placeholder-mode substitute --out data/v2", 12)
sh("python data/prepare.py --audit-only --out data/v2 --strict", 6)
sh("python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push", 25)
sh("python tools/check_run.py train/runs/smoke-v2-t4 --max-memory-gb 12", 15)
print("PRESMOKE DONE", time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
$ python data/prepare.py --placeholder-mode substitute --out data/v2
```

**Output**:
```
        pretrained_model_name_or_path,
    ...<9 lines>...
        _commit_hash=commit_hash,
    )
  File "/usr/local/lib/python3.13/dist-packages/transformers/utils/hub.py", line 294, in cached_file
    file = cached_files(path_or_repo_id=path_or_repo_id, filenames=[filename], **kwargs)
  File "/usr/local/lib/python3.13/dist-packages/transformers/utils/hub.py", line 521, in cached_files
    raise OSError(
    ...<3 lines>...
    ) from e
OSError: We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.
Check your internet connection or see how to run the library in offline mode at 'https://huggingface.co/docs/transformers/installation#offline-mode'.
```

**Output**:
```
  rc=1 17s
```

### Execution (2026-09-07 18:03:49)
```python
import subprocess
code = r'''
import traceback, os
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"]="1"
from huggingface_hub import hf_hub_download
try:
    p = hf_hub_download("sentence-transformers/all-MiniLM-L6-v2", "config.json"); print("ok", p)
except Exception as e:
    traceback.print_exc()
    c = e.__cause__ or e.__context__
    while c: print("CAUSE:", type(c).__name__, str(c)[:300]); c = c.__cause__ or c.__context__
'''
r = subprocess.run(["python", "-c", code], capture_output=True, text=True); print((r.stdout + r.stderr)[-2500:], flush=True)

```

**Output**:
```
ok /root/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/config.json
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.

```

### Execution (2026-09-07 18:04:24)
```python
import subprocess, os
os.chdir("/content/ghl-support-slm")
r = subprocess.run("HF_HUB_VERBOSITY=debug python data/prepare.py --placeholder-mode substitute --out data/v2", shell=True, capture_output=True, text=True)
lines = (r.stdout + r.stderr).splitlines()
keep = [l for l in lines if any(k in l for k in ("Error","error","Traceback","File \"/content","huggingface.co","429","401","403","revision","Request","Max retries","Connection"))]
print("\n".join(keep[:45]), flush=True); print("rc", r.returncode, "lines", len(lines), flush=True)

```

**Output**:
```
Traceback (most recent call last):
    _raise_on_head_call_error(head_call_error, force_download, local_files_only)
  File "/usr/local/lib/python3.13/dist-packages/huggingface_hub/file_download.py", line 1896, in _raise_on_head_call_error
    raise LocalEntryNotFoundError(
huggingface_hub.errors.LocalEntryNotFoundError: Cannot find the requested files in the disk cache and outgoing traffic has been disabled. To enable hf.co look-ups and downloads online, set 'local_files_only' to False.
Traceback (most recent call last):
    raise OSError(
OSError: We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.
Check your internet connection or see how to run the library in offline mode at 'https://huggingface.co/docs/transformers/installation#offline-mode'.
Traceback (most recent call last):
    _raise_on_head_call_error(head_call_error, force_download, local_files_only)
  File "/usr/local/lib/python3.13/dist-packages/huggingface_hub/file_download.py", line 1896, in _raise_on_head_call_error
    raise LocalEntryNotFoundError(
huggingface_hub.errors.LocalEntryNotFoundError: Cannot find the requested files in the disk cache and outgoing traffic has been disabled. To enable hf.co look-ups and downloads online, set 'local_files_only' to False.
Traceback (most recent call last):
  File "/content/ghl-support-slm/data/prepare.py", line 1297, in <module>
  File "/content/ghl-support-slm/data/prepare.py", line 1286, in main
  File "/content/ghl-support-slm/data/prepare.py", line 985, in prepare
  File "/content/ghl-support-slm/data/prepare.py", line 874, in get_collator
  File "/content/ghl-support-slm/train/render.py", line 42, in get_tokenizer
        revision=revision,
    raise OSError(
OSError: We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.
Check your internet connection or see how to run the library in offline mode at 'https://huggingface.co/docs/transformers/installation#offline-mode'.
```

**Output**:
```
rc 1 lines 141
```

### Execution (2026-09-07 18:05:15)
```python
import subprocess, os, json, time
os.chdir("/content/ghl-support-slm")
v = json.load(open("configs/versions.json"))
print(json.dumps({k: v[k] for k in v if isinstance(v[k], dict)}, indent=0)[:600], flush=True)
code = r'''
import json, os, time
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"]="1"
from huggingface_hub import snapshot_download
v = json.load(open("configs/versions.json"))
for key, entry in v.items():
    if isinstance(entry, dict) and "repo_id" in entry and "revision" in entry:
        t=time.time(); p = snapshot_download(entry["repo_id"], revision=entry["revision"]); print(key, entry["repo_id"], "->", p, f"{time.time()-t:.0f}s", flush=True)
'''
r = subprocess.run(["python", "-c", code], capture_output=True, text=True); print((r.stdout + r.stderr)[-1500:], flush=True)
print("PREDL DONE rc", r.returncode, time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
{
"base_model": {
"repo_id": "Qwen/Qwen2.5-1.5B-Instruct",
"revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
"license": "Apache-2.0"
},
"dataset": {
"repo_id": "bitext/Bitext-customer-support-llm-chatbot-training-dataset",
"revision": "430d1a89bd93bd1fa23c16f29dd53e73f0087443",
"license": "CDLA-Sharing-1.0"
},
"llama_cpp_converter": {
"repo": "https://github.com/ggml-org/llama.cpp",
"commit": "6a1a922d269908a29cbd4b49c27e6a8e7fd10fae"
}
}
```

**Output**:
```
o_type)
             ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.13/dist-packages/huggingface_hub/hf_api.py", line 4100, in list_repo_tree
    for path_info in paginate(path=tree_url, headers=headers, params={"recursive": recursive, "expand": expand}):
                     ~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.13/dist-packages/huggingface_hub/utils/_pagination.py", line 37, in paginate
    hf_raise_for_status(r)
    ~~~~~~~~~~~~~~~~~~~^^^
  File "/usr/local/lib/python3.13/dist-packages/huggingface_hub/utils/_http.py", line 885, in hf_raise_for_status
    raise _format(RepositoryNotFoundError, message, response, repo_type=repo_type, repo_id=repo_id) from e
huggingface_hub.errors.RepositoryNotFoundError: 401 Client Error. (Request ID: Root=1-6a9efcdb-4b7f1ad00255716d6d11c464;45509f06-d224-4b69-a700-7e8de8d6a490)

Repository Not Found for url: https://huggingface.co/api/models/bitext/Bitext-customer-support-llm-chatbot-training-dataset/tree/430d1a89bd93bd1fa23c16f29dd53e73f0087443?recursive=true&expand=false.
Please make sure you specified the correct `repo_id` and `repo_type`.
If you are trying to access a private or gated repo, make sure you are authenticated and your token has the required permissions.
For more details, see https://huggingface.co/docs/huggingface_hub/authentication
Invalid username or password.

```

**Output**:
```
PREDL DONE rc 1 18:05:15 UTC
```

### Execution (2026-09-07 18:07:13)
```python
import subprocess, os, time
os.chdir("/content/ghl-support-slm")
def sh(c, n=1200):
    print("$", c, flush=True); t=time.time()
    r = subprocess.run(c, shell=True, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    print("\n".join(out[-n:]), flush=True); print(f"  rc={r.returncode} {time.time()-t:.0f}s", flush=True)
    if r.returncode: raise SystemExit(r.returncode)
sh("python data/prepare.py --placeholder-mode substitute --out data/v2", 12)
sh("python data/prepare.py --audit-only --out data/v2 --strict", 6)
sh("python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push", 25)
sh("python tools/check_run.py train/runs/smoke-v2-t4 --max-memory-gb 12", 15)
print("PRESMOKE DONE", time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
$ python data/prepare.py --placeholder-mode substitute --out data/v2
```

**Output**:
```
Batches:  66%|██████▌   | 69/105 [00:04<00:01, 22.15it/s]
Batches:  69%|██████▊   | 72/105 [00:04<00:01, 23.33it/s]
Batches:  71%|███████▏  | 75/105 [00:04<00:01, 23.78it/s]
Batches:  74%|███████▍  | 78/105 [00:04<00:01, 24.38it/s]
Batches:  77%|███████▋  | 81/105 [00:04<00:00, 25.23it/s]
Batches:  80%|████████  | 84/105 [00:04<00:00, 26.36it/s]
Batches:  83%|████████▎ | 87/105 [00:04<00:00, 26.55it/s]
Batches:  87%|████████▋ | 91/105 [00:05<00:00, 27.91it/s]
Batches:  90%|█████████ | 95/105 [00:05<00:00, 28.64it/s]
Batches:  94%|█████████▍| 99/105 [00:05<00:00, 30.00it/s]
Batches:  98%|█████████▊| 103/105 [00:05<00:00, 31.90it/s]
Batches: 100%|██████████| 105/105 [00:05<00:00, 18.96it/s]
```

**Output**:
```
  rc=0 64s
```

**Output**:
```
$ python data/prepare.py --audit-only --out data/v2 --strict
```

**Output**:
```
audit-only ok train=20926 val=2753 test=3085
strict: hashes and intersections match
```

**Output**:
```
  rc=0 1s
```

**Output**:
```
$ python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push
```

**Output**:
```
Loading weights:  58%|█████▊    | 195/338 [00:03<00:03, 41.16it/s]
Loading weights:  59%|█████▉    | 201/338 [00:03<00:03, 36.10it/s]
Loading weights:  61%|██████    | 207/338 [00:04<00:03, 38.42it/s]
Loading weights:  63%|██████▎   | 212/338 [00:04<00:03, 34.60it/s]
Loading weights:  65%|██████▍   | 219/338 [00:04<00:03, 38.62it/s]
Loading weights:  66%|██████▋   | 224/338 [00:04<00:03, 33.87it/s]
Loading weights:  68%|██████▊   | 231/338 [00:04<00:02, 37.20it/s]
Loading weights:  70%|██████▉   | 236/338 [00:04<00:03, 32.01it/s]
Loading weights:  72%|███████▏  | 243/338 [00:05<00:02, 35.55it/s]
Loading weights:  73%|███████▎  | 247/338 [00:05<00:03, 29.72it/s]
Loading weights:  75%|███████▌  | 255/338 [00:05<00:02, 35.53it/s]
Loading weights:  77%|███████▋  | 259/338 [00:05<00:02, 29.67it/s]
Loading weights:  79%|███████▉  | 267/338 [00:05<00:02, 35.46it/s]
Loading weights:  80%|████████  | 271/338 [00:06<00:02, 29.50it/s]
Loading weights:  83%|████████▎ | 279/338 [00:06<00:01, 35.33it/s]
Loading weights:  84%|████████▎ | 283/338 [00:06<00:01, 29.51it/s]
Loading weights:  86%|████████▌ | 291/338 [00:06<00:01, 35.41it/s]
Loading weights:  87%|████████▋ | 295/338 [00:06<00:01, 29.53it/s]
Loading weights:  90%|████████▉ | 303/338 [00:06<00:00, 35.31it/s]
Loading weights:  91%|█████████ | 307/338 [00:07<00:01, 29.40it/s]
Loading weights:  93%|█████████▎| 315/338 [00:07<00:00, 35.34it/s]
Loading weights:  94%|█████████▍| 319/338 [00:07<00:00, 29.46it/s]
Loading weights:  97%|█████████▋| 327/338 [00:07<00:00, 34.71it/s]
Loading weights:  98%|█████████▊| 331/338 [00:07<00:00, 29.36it/s]
Loading weights: 100%|██████████| 338/338 [00:07<00:00, 42.55it/s]
```

**Output**:
```
  rc=0 50s
```

**Output**:
```
$ python tools/check_run.py train/runs/smoke-v2-t4 --max-memory-gb 12
```

**Output**:
```
FAIL: run directory not found: /content/ghl-support-slm/train/runs/smoke-v2-t4
```

**Output**:
```
  rc=1 0s
```

**Output**:
```
/usr/local/lib/python3.13/dist-packages/IPython/core/interactiveshell.py:3561: UserWarning: To exit: use 'exit', 'quit', or Ctrl-D.
  warn("To exit: use 'exit', 'quit', or Ctrl-D.", stacklevel=1)
```

### Execution (2026-09-07 18:10:21)
```python
import subprocess, os, glob
os.chdir("/content/ghl-support-slm")
def sh(c):
    r = subprocess.run(c, shell=True, capture_output=True, text=True); print("$", c, "\n", (r.stdout + r.stderr).strip()[-1200:], "\n rc", r.returncode, flush=True)
sh("ls train/runs; ls train/runs/*/ | head -30")
d = sorted(glob.glob("train/runs/smoke*"))
for x in d: sh(f"python tools/check_run.py {x} --max-memory-gb 12")
sh("python -c \"import json,glob; [print(f, {k: json.load(open(f)).get(k) for k in ('run_name','device','wall_s','peak_memory_gb','final_step','git_sha','n_train')}) for f in glob.glob('train/runs/smoke*/config.json')]\"")

```

**Output**:
```
$ ls train/runs; ls train/runs/*/ | head -30 
 local-t4
v2-t4
train/runs/local-t4/:
config.json
curves.png
loss.csv

train/runs/v2-t4/:
checkpoint-10
checkpoint-20
config.json
loss.csv
smoke.json 
 rc 0
```

**Output**:
```
$ python -c "import json,glob; [print(f, {k: json.load(open(f)).get(k) for k in ('run_name','device','wall_s','peak_memory_gb','final_step','git_sha','n_train')}) for f in glob.glob('train/runs/smoke*/config.json')]" 
  
 rc 0
```

### Execution (2026-09-07 18:10:50)
```python
import subprocess, os, shutil
os.chdir("/content/ghl-support-slm")
def sh(c):
    r = subprocess.run(c, shell=True, capture_output=True, text=True); print("$", c, "\n", (r.stdout + r.stderr).strip()[-1500:], "\n rc", r.returncode, flush=True)
sh("python tools/check_run.py train/runs/v2-t4 --max-memory-gb 12")
sh("cat train/runs/v2-t4/smoke.json; python -c \"import json; d=json.load(open('train/runs/v2-t4/config.json')); print({k: d.get(k) for k in ('run_name','device','wall_s','peak_memory_gb','final_step','git_sha','n_train','max_steps','smoke')})\"")
shutil.rmtree("train/runs/v2-t4"); print("removed smoke dir train/runs/v2-t4 so the full run starts clean", flush=True)
sh("ls train/runs")

```

**Output**:
```
$ python tools/check_run.py train/runs/v2-t4 --max-memory-gb 12 
 pport-slm/train/runs/v2-t4
loss.csv: 6 logged steps, 6 with a validation loss
peak memory: 3.12 GB (limit 12.0 GB)
git sha: f5ae72edc1e08db85ae7f0f4b6867e604d9f1a96
smoke resume: matched at steps [15, 20], max_abs_diff 0.00177
reloading checkpoint-20 on cuda

Loading weights:   0%|          | 0/338 [00:00<?, ?it/s]
Loading weights:   0%|          | 1/338 [00:00<05:22,  1.04it/s]
Loading weights:  19%|█▉        | 64/338 [00:01<00:03, 82.36it/s]
Loading weights:  30%|██▉       | 101/338 [00:01<00:02, 99.27it/s]
Loading weights:  38%|███▊      | 127/338 [00:01<00:01, 116.21it/s]
Loading weights:  44%|████▍     | 150/338 [00:01<00:01, 126.20it/s]
Loading weights:  51%|█████     | 172/338 [00:01<00:01, 140.93it/s]
Loading weights:  58%|█████▊    | 195/338 [00:01<00:00, 149.94it/s]
Loading weights:  64%|██████▎   | 215/338 [00:01<00:00, 151.55it/s]
Loading weights:  69%|██████▉   | 234/338 [00:02<00:00, 146.38it/s]
Loading weights:  75%|███████▌  | 255/338 [00:02<00:00, 160.11it/s]
Loading weights:  81%|████████  | 273/338 [00:02<00:00, 161.14it/s]
Loading weights:  86%|████████▌ | 291/338 [00:02<00:00, 165.57it/s]
Loading weights:  91%|█████████▏| 309/338 [00:02<00:00, 159.53it/s]
Loading weights:  97%|█████████▋| 327/338 [00:02<00:00, 163.64it/s]
Loading weights: 100%|██████████| 338/338 [00:02<00:00, 124.84it/s]

FAIL: 1 problem(s)
  - adapter reload or generation failed: Found an incompatible version of torchao. Found version 0.10.0, but only versions above 0.16.0 are supported 
 rc 1
```

**Output**:
```
$ cat train/runs/v2-t4/smoke.json; python -c "import json; d=json.load(open('train/runs/v2-t4/config.json')); print({k: d.get(k) for k in ('run_name','device','wall_s','peak_memory_gb','final_step','git_sha','n_train','max_steps','smoke')})" 
 {
  "run_dir": "/content/ghl-support-slm/train/runs/v2-t4",
  "device": "cuda",
  "resume_from": 10,
  "steps": 20,
  "tolerance": 0.05,
  "compared_steps": [
    15,
    20
  ],
  "phase1_train_loss": {
    "15": 1.50847,
    "20": 1.30801
  },
  "resumed_train_loss": {
    "15": 1.51024,
    "20": 1.30875
  },
  "max_abs_diff": 0.00177,
  "ok": true,
  "checked_at": "2026-09-07 23:37:11 IST"
}
{'run_name': 'v2-t4', 'device': 'cuda', 'wall_s': 8.1, 'peak_memory_gb': 3.12, 'final_step': 20, 'git_sha': 'f5ae72edc1e08db85ae7f0f4b6867e604d9f1a96', 'n_train': None, 'max_steps': None, 'smoke': None} 
 rc 0
```

**Output**:
```
removed smoke dir train/runs/v2-t4 so the full run starts clean
```

**Output**:
```
$ ls train/runs 
 local-t4 
 rc 0
```

## Session Created: 2026-09-07 19:27:08
- Endpoint: `gpu-t4-s-kkb-ass1b0-27nyc8ajuvgrk`

### Execution (2026-09-07 19:28:12)
```python
import subprocess, os, time
def sh(c):
    print("$", c, flush=True); t=time.time()
    subprocess.run(c, shell=True, check=True); print(f"  ok {time.time()-t:.0f}s", flush=True)
sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
if not os.path.isdir("/content/ghl-support-slm"):
    sh("git clone --branch v2 --depth 1 -q https://github.com/Imsharad/ghl-support-slm.git /content/ghl-support-slm")
os.chdir("/content/ghl-support-slm")
sh("git rev-parse HEAD")
sh("pip install -q 'transformers==5.16.1' 'peft==0.20.0' 'trl==1.12.0' 'bitsandbytes==0.50.2' 'accelerate>=0.34' 'datasets==5.0.1' 'sentence-transformers>=3.0' 'scikit-learn>=1.5' 'pyyaml>=6.0' 'matplotlib>=3.9'")
sh("python -c \"import torch,transformers,peft,bitsandbytes;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'tf',transformers.__version__,'peft',peft.__version__,'bnb',bitsandbytes.__version__)\"")
sh("python data/fetch.py")
print("SETUP DONE", time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
$ nvidia-smi --query-gpu=name,memory.total --format=csv
```

**Output**:
```
  ok 0s
```

**Output**:
```
$ git clone --branch v2 --depth 1 -q https://github.com/Imsharad/ghl-support-slm.git /content/ghl-support-slm
```

**Output**:
```
  ok 1s
```

**Output**:
```
$ git rev-parse HEAD
```

**Output**:
```
  ok 0s
```

**Output**:
```
$ pip install -q 'transformers==5.16.1' 'peft==0.20.0' 'trl==1.12.0' 'bitsandbytes==0.50.2' 'accelerate>=0.34' 'datasets==5.0.1' 'sentence-transformers>=3.0' 'scikit-learn>=1.5' 'pyyaml>=6.0' 'matplotlib>=3.9'
```

**Output**:
```
  ok 12s
```

**Output**:
```
$ python -c "import torch,transformers,peft,bitsandbytes;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'tf',transformers.__version__,'peft',peft.__version__,'bnb',bitsandbytes.__version__)"
```

**Output**:
```
  ok 29s
```

**Output**:
```
$ python data/fetch.py
```

**Output**:
```
  ok 3s
```

**Output**:
```
SETUP DONE 19:28:12 UTC
```

### Execution (2026-09-07 19:28:46)
```python
import subprocess, os, json, time
os.chdir("/content/ghl-support-slm")
v = json.load(open("configs/versions.json"))
print(json.dumps({k: v[k] for k in v if isinstance(v[k], dict)}, indent=0)[:600], flush=True)
code = r'''
import json, os, time
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"]="1"
from huggingface_hub import snapshot_download
v = json.load(open("configs/versions.json"))
for key, entry in v.items():
    if isinstance(entry, dict) and "repo_id" in entry and "revision" in entry:
        t=time.time()
        try: p = snapshot_download(entry["repo_id"], revision=entry["revision"]); print(key, entry["repo_id"], "->", p, f"{time.time()-t:.0f}s", flush=True)
        except Exception as exc: print(key, entry["repo_id"], "skipped:", str(exc)[:80], flush=True)
'''
r = subprocess.run(["python", "-c", code], capture_output=True, text=True); print((r.stdout + r.stderr)[-1500:], flush=True)
print("PREDL DONE rc", r.returncode, time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
{
"base_model": {
"repo_id": "Qwen/Qwen2.5-1.5B-Instruct",
"revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
"license": "Apache-2.0"
},
"dataset": {
"repo_id": "bitext/Bitext-customer-support-llm-chatbot-training-dataset",
"revision": "430d1a89bd93bd1fa23c16f29dd53e73f0087443",
"license": "CDLA-Sharing-1.0"
},
"llama_cpp_converter": {
"repo": "https://github.com/ggml-org/llama.cpp",
"commit": "6a1a922d269908a29cbd4b49c27e6a8e7fd10fae"
}
}
```

**Output**:
```
base_model Qwen/Qwen2.5-1.5B-Instruct -> /root/.cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/989aa7980e4cf806f80c7fef2b1adb7bc71aa306 26s
dataset bitext/Bitext-customer-support-llm-chatbot-training-dataset skipped: 401 Client Error. (Request ID: Root=1-6a9f106e-0f2f64453ff8313a75d49188;d6e8b4fc
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.

```

**Output**:
```
PREDL DONE rc 0 19:28:46 UTC
```

### Execution (2026-09-07 19:28:58)
```python
import subprocess, os, time, shutil, json
os.chdir("/content/ghl-support-slm")
def sh(c, n=12):
    t=time.time(); r = subprocess.run(c, shell=True, capture_output=True, text=True)
    out = [l for l in (r.stdout + r.stderr).splitlines() if "it/s]" not in l and "s/it]" not in l]
    print("$", c, "\n" + "\n".join(out[-n:]), f"\n  rc={r.returncode} {time.time()-t:.0f}s", flush=True); return r.returncode
sh("nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader", 2)
sh("git fetch -q --depth 1 origin v2 && git reset -q --hard FETCH_HEAD && git log --oneline -1", 2)
shutil.rmtree("train/runs/v2-t4", ignore_errors=True)
rc = sh("python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push", 14)
sh("cat train/runs/v2-t4/smoke.json", 20)
sh("python tools/check_run.py train/runs/v2-t4 --max-memory-gb 12", 20)
sh("python -c \"import json; d=json.load(open('train/runs/v2-t4/config.json')); print({k: d.get(k) for k in ('run_name','device','wall_s','peak_memory_gb','final_step','git_sha')})\"", 3)
shutil.rmtree("train/runs/v2-t4", ignore_errors=True); print("smoke dir removed; SMOKE2 DONE rc", rc, time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
$ nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 
Tesla T4, 0 MiB, 15360 MiB 
  rc=0 0s
```

**Output**:
```
$ git fetch -q --depth 1 origin v2 && git reset -q --hard FETCH_HEAD && git log --oneline -1 
47789ec V2-A1: decision 13, the closer remedy stops after two rounds 
  rc=0 1s
```

**Output**:
```
$ python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push 
[2026-09-08 00:58:56 IST] config configs/train-t4.yaml device cuda run dir /content/ghl-support-slm/train/runs/v2-t4
[2026-09-08 00:58:56 IST] smoke phase 1: training from scratch
data file not found: /content/ghl-support-slm/data/processed/v2/train.jsonl
Regenerate the split with: uv run python data/prepare.py 
  rc=1 9s
```

**Output**:
```
$ cat train/runs/v2-t4/smoke.json 
cat: train/runs/v2-t4/smoke.json: No such file or directory 
  rc=1 0s
```

**Output**:
```
$ python tools/check_run.py train/runs/v2-t4 --max-memory-gb 12 
FAIL: run directory not found: /content/ghl-support-slm/train/runs/v2-t4 
  rc=1 0s
```

**Output**:
```
$ python -c "import json; d=json.load(open('train/runs/v2-t4/config.json')); print({k: d.get(k) for k in ('run_name','device','wall_s','peak_memory_gb','final_step','git_sha')})" 
    import json; d=json.load(open('train/runs/v2-t4/config.json')); print({k: d.get(k) for k in ('run_name','device','wall_s','peak_memory_gb','final_step','git_sha')})
                             ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: 'train/runs/v2-t4/config.json' 
  rc=1 0s
```

**Output**:
```
smoke dir removed; SMOKE2 DONE rc 1 19:28:58 UTC
```

### Execution (2026-09-07 19:31:45)
```python
import subprocess, os, time
os.chdir("/content/ghl-support-slm")
def sh(c, n=1200):
    print("$", c, flush=True); t=time.time()
    r = subprocess.run(c, shell=True, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    print("\n".join(out[-n:]), flush=True); print(f"  rc={r.returncode} {time.time()-t:.0f}s", flush=True)
    if r.returncode: raise SystemExit(r.returncode)
sh("python data/prepare.py --placeholder-mode substitute --out data/v2", 12)
sh("python data/prepare.py --audit-only --out data/v2 --strict", 6)
sh("python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push", 25)
sh("cat train/runs/v2-t4/smoke.json", 20)
sh("python tools/check_run.py train/runs/v2-t4 --max-memory-gb 12", 20)
import shutil; shutil.rmtree("train/runs/v2-t4", ignore_errors=True); print("smoke dir removed")
print("PRESMOKE DONE", time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
$ python data/prepare.py --placeholder-mode substitute --out data/v2
```

**Output**:
```
Batches:  69%|██████▊   | 72/105 [00:05<00:01, 21.55it/s]
Batches:  71%|███████▏  | 75/105 [00:05<00:01, 22.34it/s]
Batches:  74%|███████▍  | 78/105 [00:05<00:01, 23.17it/s]
Batches:  77%|███████▋  | 81/105 [00:05<00:01, 23.82it/s]
Batches:  80%|████████  | 84/105 [00:05<00:00, 25.04it/s]
Batches:  83%|████████▎ | 87/105 [00:05<00:00, 25.39it/s]
Batches:  86%|████████▌ | 90/105 [00:05<00:00, 26.47it/s]
Batches:  89%|████████▊ | 93/105 [00:06<00:00, 27.33it/s]
Batches:  92%|█████████▏| 97/105 [00:06<00:00, 28.33it/s]
Batches:  95%|█████████▌| 100/105 [00:06<00:00, 28.60it/s]
Batches:  99%|█████████▉| 104/105 [00:06<00:00, 30.54it/s]
Batches: 100%|██████████| 105/105 [00:06<00:00, 16.29it/s]
```

**Output**:
```
  rc=0 75s
```

**Output**:
```
$ python data/prepare.py --audit-only --out data/v2 --strict
```

**Output**:
```
audit-only ok train=20926 val=2753 test=3085
strict: hashes and intersections match
```

**Output**:
```
  rc=0 2s
```

**Output**:
```
$ python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push
```

**Output**:
```
Loading weights:  57%|█████▋    | 191/338 [00:03<00:02, 53.45it/s]
Loading weights:  59%|█████▊    | 198/338 [00:03<00:03, 42.02it/s]
Loading weights:  61%|██████    | 207/338 [00:03<00:02, 44.94it/s]
Loading weights:  63%|██████▎   | 213/338 [00:03<00:03, 39.09it/s]
Loading weights:  65%|██████▍   | 219/338 [00:03<00:02, 40.34it/s]
Loading weights:  66%|██████▋   | 224/338 [00:04<00:03, 34.32it/s]
Loading weights:  68%|██████▊   | 231/338 [00:04<00:02, 37.42it/s]
Loading weights:  70%|██████▉   | 236/338 [00:04<00:03, 32.32it/s]
Loading weights:  72%|███████▏  | 243/338 [00:04<00:02, 35.90it/s]
Loading weights:  73%|███████▎  | 247/338 [00:04<00:03, 29.85it/s]
Loading weights:  75%|███████▌  | 255/338 [00:05<00:02, 35.61it/s]
Loading weights:  77%|███████▋  | 259/338 [00:05<00:02, 29.58it/s]
Loading weights:  79%|███████▉  | 267/338 [00:05<00:01, 35.70it/s]
Loading weights:  80%|████████  | 271/338 [00:05<00:02, 30.51it/s]
Loading weights:  83%|████████▎ | 279/338 [00:05<00:01, 36.78it/s]
Loading weights:  84%|████████▍ | 284/338 [00:06<00:01, 32.15it/s]
Loading weights:  86%|████████▌ | 291/338 [00:06<00:01, 36.19it/s]
Loading weights:  87%|████████▋ | 295/338 [00:06<00:01, 29.77it/s]
Loading weights:  90%|████████▉ | 303/338 [00:06<00:00, 35.94it/s]
Loading weights:  91%|█████████ | 307/338 [00:06<00:01, 29.73it/s]
Loading weights:  93%|█████████▎| 315/338 [00:06<00:00, 35.61it/s]
Loading weights:  94%|█████████▍| 319/338 [00:07<00:00, 29.53it/s]
Loading weights:  97%|█████████▋| 327/338 [00:07<00:00, 35.51it/s]
Loading weights:  98%|█████████▊| 331/338 [00:07<00:00, 29.97it/s]
Loading weights: 100%|██████████| 338/338 [00:07<00:00, 44.91it/s]
```

**Output**:
```
  rc=0 55s
```

**Output**:
```
$ cat train/runs/v2-t4/smoke.json
```

**Output**:
```
  "device": "cuda",
  "resume_from": 10,
  "steps": 20,
  "tolerance": 0.05,
  "compared_steps": [
    15,
    20
  ],
  "phase1_train_loss": {
    "15": 1.50847,
    "20": 1.30801
  },
  "resumed_train_loss": {
    "15": 1.51024,
    "20": 1.30875
  },
  "max_abs_diff": 0.00177,
  "ok": true,
  "checked_at": "2026-09-08 01:01:28 IST"
}
```

**Output**:
```
  rc=0 0s
```

**Output**:
```
$ python tools/check_run.py train/runs/v2-t4 --max-memory-gb 12
```

**Output**:
```

Loading weights:   0%|          | 0/338 [00:00<?, ?it/s]
Loading weights:   0%|          | 1/338 [00:00<03:28,  1.62it/s]
Loading weights:  19%|█▉        | 65/338 [00:00<00:02, 119.51it/s]
Loading weights:  30%|██▉       | 100/338 [00:00<00:01, 134.95it/s]
Loading weights:  38%|███▊      | 127/338 [00:01<00:01, 145.10it/s]
Loading weights:  44%|████▍     | 150/338 [00:01<00:01, 147.82it/s]
Loading weights:  51%|█████     | 171/338 [00:01<00:01, 158.02it/s]
Loading weights:  57%|█████▋    | 191/338 [00:01<00:00, 157.49it/s]
Loading weights:  62%|██████▏   | 210/338 [00:01<00:00, 149.22it/s]
Loading weights:  68%|██████▊   | 231/338 [00:01<00:00, 160.67it/s]
Loading weights:  74%|███████▎  | 249/338 [00:01<00:00, 159.82it/s]
Loading weights:  79%|███████▉  | 267/338 [00:01<00:00, 159.20it/s]
Loading weights:  84%|████████▍ | 284/338 [00:02<00:00, 153.72it/s]
Loading weights:  90%|████████▉ | 303/338 [00:02<00:00, 156.17it/s]
Loading weights:  94%|█████████▍| 319/338 [00:02<00:00, 144.87it/s]
Loading weights: 100%|██████████| 338/338 [00:02<00:00, 140.67it/s]

FAIL: 1 problem(s)
  - adapter reload or generation failed: Found an incompatible version of torchao. Found version 0.10.0, but only versions above 0.16.0 are supported
```

**Output**:
```
  rc=1 14s
```

**Output**:
```
/usr/local/lib/python3.13/dist-packages/IPython/core/interactiveshell.py:3561: UserWarning: To exit: use 'exit', 'quit', or Ctrl-D.
  warn("To exit: use 'exit', 'quit', or Ctrl-D.", stacklevel=1)
```

### Execution (2026-09-07 19:33:47)
```python
import subprocess, os, time, shutil
os.chdir("/content/ghl-support-slm")
def sh(c, n=12):
    t=time.time(); r = subprocess.run(c, shell=True, capture_output=True, text=True)
    out = [l for l in (r.stdout + r.stderr).splitlines() if "it/s]" not in l and "s/it]" not in l and "Warning" not in l]
    print("$", c, "\n" + "\n".join(out[-n:]), f"\n  rc={r.returncode} {time.time()-t:.0f}s", flush=True); return r.returncode
sh("pip install -q 'torchao>=0.16' 2>&1 | tail -2; python -c \"import torchao, torch, transformers; print('torchao', torchao.__version__, 'torch', torch.__version__, 'tf', transformers.__version__)\"", 4)
shutil.rmtree("train/runs/v2-t4", ignore_errors=True)
sh("python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push", 3)
sh("python -c \"import json; d=json.load(open('train/runs/v2-t4/smoke.json')); print({k: d[k] for k in ('device','max_abs_diff','ok')})\"", 2)
rc = sh("python tools/check_run.py train/runs/v2-t4 --max-memory-gb 12", 12)
shutil.rmtree("train/runs/v2-t4", ignore_errors=True); print("smoke dir removed; FIXAO DONE check_run rc", rc, flush=True)

```

**Output**:
```
$ pip install -q 'torchao>=0.16' 2>&1 | tail -2; python -c "import torchao, torch, transformers; print('torchao', torchao.__version__, 'torch', torch.__version__, 'tf', transformers.__version__)" 
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.4/3.4 MB 104.3 MB/s eta 0:00:00
torchao 0.18.0 torch 2.11.0+cu128 tf 5.16.1
Failed to load /usr/local/lib/python3.13/dist-packages/torchao/_C_cutlass_90a.abi3.so: Could not load this library: /usr/local/lib/python3.13/dist-packages/torchao/_C_cutlass_90a.abi3.so
Failed to load /usr/local/lib/python3.13/dist-packages/torchao/_C_mxfp8.cpython-310-x86_64-linux-gnu.so: Could not load this library: /usr/local/lib/python3.13/dist-packages/torchao/_C_mxfp8.cpython-310-x86_64-linux-gnu.so 
  rc=0 12s
```

**Output**:
```
$ python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push 

[transformers] `use_cache=True` is incompatible with gradient checkpointing. Setting `use_cache=False`.
 
  rc=0 51s
```

**Output**:
```
$ python -c "import json; d=json.load(open('train/runs/v2-t4/smoke.json')); print({k: d[k] for k in ('device','max_abs_diff','ok')})" 
{'device': 'cuda', 'max_abs_diff': 0.00177, 'ok': True} 
  rc=0 0s
```

**Output**:
```
$ python tools/check_run.py train/runs/v2-t4 --max-memory-gb 12 
git sha: 47789ec37810257b497d7f94322569e3933c2084
smoke resume: matched at steps [15, 20], max_abs_diff 0.00177
reloading checkpoint-20 on cuda
sample answer:
If you've forgotten your password and can't access your account, there are several steps you can take to regain control of your account:

1. **Contact Customer Support**: Reach out to the customer service team of the platform where you're having trouble logging in. They will be able to assist you with resetting your password.

PASS: run directory is complete and the adapter reloads
Failed to load /usr/local/lib/python3.13/dist-packages/torchao/_C_cutlass_90a.abi3.so: Could not load this library: /usr/local/lib/python3.13/dist-packages/torchao/_C_cutlass_90a.abi3.so
Failed to load /usr/local/lib/python3.13/dist-packages/torchao/_C_mxfp8.cpython-310-x86_64-linux-gnu.so: Could not load this library: /usr/local/lib/python3.13/dist-packages/torchao/_C_mxfp8.cpython-310-x86_64-linux-gnu.so
 
  rc=0 23s
```

**Output**:
```
smoke dir removed; FIXAO DONE check_run rc 0
```

### Execution (2026-09-07 19:33:47)
```python
print("alive")

```

**Output**:
```
alive
```

### Execution (2026-09-07 19:57:24)
```python
import subprocess, os, json, time
os.chdir("/content/ghl-support-slm")
subprocess.run("git fetch -q origin v2 && git checkout -q --detach origin/v2 && git log --oneline -1", shell=True)
nb = json.load(open("notebooks/train_colab.ipynb"))
keep = []
for c in nb["cells"]:
    src = c["source"] if isinstance(c["source"], str) else "".join(c["source"])
    if c["cell_type"] == "code" and "run_name v2-t4 --no-push\")" in src and "--smoke" not in src: break  # stop before the full train cell
    if "--admissions data/v2/admissions.jsonl" in src: src = src.replace(" --admissions data/v2/admissions.jsonl", "").replace("data/v2/admissions.jsonl ", "")
    c["source"] = src; keep.append(c)
nb["cells"] = keep; json.dump(nb, open("/content/dry.ipynb", "w"))
print("dry cells", len(keep), flush=True)
t = time.time()
r = subprocess.run("jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=1200 --ExecutePreprocessor.allow_errors=True /content/dry.ipynb --output /content/dry_out.ipynb", shell=True, capture_output=True, text=True)
print("nbconvert rc", r.returncode, f"{time.time()-t:.0f}s", (r.stderr or "")[-600:], flush=True)
out = json.load(open("/content/dry_out.ipynb"))
for i, c in enumerate(out["cells"]):
    if c["cell_type"] != "code": continue
    errs = [o for o in c.get("outputs", []) if o.get("output_type") == "error"]
    texts = "".join("".join(o.get("text", "")) for o in c.get("outputs", []) if o.get("output_type") == "stream")
    print(f"--- cell {i} {'ERROR' if errs else 'ok'}: {texts.strip()[-500:]}", flush=True)
    for e in errs: print("   ", e.get("ename"), str(e.get("evalue"))[:200], flush=True)

```

**Output**:
```
dry cells 24
```

### Execution (2026-09-07 19:57:47)
```python
import subprocess, os, json
os.chdir("/content/ghl-support-slm")
subprocess.run("pkill -f 'jupyter-nbconvert' ; git fetch -q origin v2 && git checkout -q --detach origin/v2 && git log --oneline -1", shell=True)
nb = json.load(open("notebooks/train_colab.ipynb")); keep = []
for c in nb["cells"]:
    src = c["source"] if isinstance(c["source"], str) else "".join(c["source"])
    if c["cell_type"] == "code" and "run_name v2-t4 --no-push\")" in src and "--smoke" not in src: break
    c["source"] = src; keep.append(c)
nb["cells"] = keep; json.dump(nb, open("/content/dry.ipynb", "w")); print("dry cells", len(keep), flush=True)
cmd = "cd /content/ghl-support-slm && jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=1200 --ExecutePreprocessor.allow_errors=True --debug /content/dry.ipynb --output /content/dry_out.ipynb > /content/nbdry.log 2>&1"
p = subprocess.Popen(cmd, shell=True, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("nbconvert pid", p.pid, flush=True)

```

**Output**:
```
dry cells 24
```

**Output**:
```
nbconvert pid 9144
```

### Execution (2026-09-07 19:58:49)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT NOT RUNNING; ls -la /content/*.ipynb /content/*.log 2>/dev/null | awk '{print $5, $9}'; grep -E 'Executing cell|msg_type|error|Error|Traceback' /content/nbdry.log | tail -8; tail -c 600 /content/nbdry.log", shell=True, capture_output=True, text=True).stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
11235 /content/dry.ipynb
17267 /content/nbdry.log
[NbConvertApp] msg_type: execute_input
[NbConvertApp] msg_type: stream
[NbConvertApp] msg_type: status
[NbConvertApp] Executing cell:
shutil.rmtree("train/runs/v2-t4", ignore_errors=True)
[NbConvertApp] msg_type: status
[NbConvertApp] msg_type: execute_input
[NbConvertApp] content: {'code': 'shutil.rmtree("train/runs/v2-t4", ignore_errors=True)\nrun("python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push", tail=4)\ns = json.load(open("train/runs/v2-t4/smoke.json")); print({k: s[k] for k in ("device", "steps", "resume_from", "max_abs_diff", "ok")})\nrun("python tools/check_run.py train/runs/v2-t4 --max-memory-gb 12")\nshutil.rmtree("train/runs/v2-t4")', 'execution_count': 7}
tApp] msg_type: status
[NbConvertApp] content: {'execution_state': 'busy'}
[NbConvertApp] msg_type: execute_input
[NbConvertApp] content: {'code': 'shutil.rmtree("train/runs/v2-t4", ignore_errors=True)\nrun("python train/train.py --config configs/train-t4.yaml --smoke --data-dir data/processed/v2 --run-name v2-t4 --no-push", tail=4)\ns = json.load(open("train/runs/v2-t4/smoke.json")); print({k: s[k] for k in ("device", "steps", "resume_from", "max_abs_diff", "ok")})\nrun("python tools/check_run.py train/runs/v2-t4 --max-memory-gb 12")\nshutil.rmtree("train/runs/v2-t4")', 'execution_count': 7}

```

### Execution (2026-09-07 20:00:41)
```python
import subprocess, json, os
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; tail -c 300 /content/nbdry.log", shell=True, capture_output=True, text=True).stdout, flush=True)
if os.path.exists("/content/dry_out.ipynb"):
    out = json.load(open("/content/dry_out.ipynb"))
    for i, c in enumerate(out["cells"]):
        if c["cell_type"] != "code": continue
        errs = [o for o in c.get("outputs", []) if o.get("output_type") == "error"]
        texts = "".join("".join(o.get("text", "")) for o in c.get("outputs", []) if o.get("output_type") == "stream")
        print(f"--- cell {i} {'ERROR' if errs else 'ok'}: {texts.strip()[-420:]}", flush=True)
        for e in errs: print("   ", e.get("ename"), str(e.get("evalue"))[:200], flush=True)

```

**Output**:
```
NBCONVERT RUNNING
")
[NbConvertApp] msg_type: status
[NbConvertApp] content: {'execution_state': 'busy'}
[NbConvertApp] msg_type: execute_input
[NbConvertApp] content: {'code': 'run("python train/train.py --config configs/train-t4.yaml --data-dir data/processed/v2 --run-name v2-t4 --no-push")', 'execution_count': 8}

```

### Execution (2026-09-07 20:01:08)
```python
import subprocess, os, time, re
os.chdir("/content/ghl-support-slm")
subprocess.run("pkill -f jupyter-nbconvert; pkill -f 'train/train.py'; sleep 2", shell=True)
log = open("/content/nbdry.log").read()
errs = re.findall(r"'output_type': 'error'.{0,300}", log)
cells = re.findall(r"Executing cell:\n(.{0,80})", log)
print("dry cells reached:", len(cells), "| error outputs:", len(errs), flush=True)
for e in errs[:5]: print("  ", e[:250], flush=True)
print("smoke ok line:", re.findall(r"'max_abs_diff'[^}]*", log)[:1], "| check_run:", re.findall(r"check_run[^\n]{0,120}rc=\d", log)[-1:] if re.findall(r"rc=\d", log) else "", flush=True)
subprocess.run("rm -rf train/runs/v2-t4 artifacts/merged; git fetch -q origin v2 && git checkout -q --detach origin/v2 && git log --oneline -1 && test -s data/v2/admissions.jsonl && wc -l data/v2/admissions.jsonl", shell=True)
cmd = ("cd /content/ghl-support-slm && jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=-1 "
       "--ExecutePreprocessor.allow_errors=True notebooks/train_colab.ipynb --output /content/v2_colab_run.ipynb > /content/nbrun.log 2>&1")
p = subprocess.Popen(cmd, shell=True, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("REAL RUN nbconvert pid", p.pid, time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
dry cells reached: 8 | error outputs: 0
```

**Output**:
```
smoke ok line: ["'max_abs_diff': 0.00177, 'ok': True"] | check_run: []
```

**Output**:
```
REAL RUN nbconvert pid 10083 20:01:08 UTC
```

### Execution (2026-09-07 20:02:23)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0

4525 MiB

```

### Execution (2026-09-07 20:02:54)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-10 config.json loss.csv 
5,0.0781,8.945702546981969e-05,1.59063,1.49799,6.6,2.66
10,0.1562,5.4128967273616625e-05,1.34656,1.41828,14.0,2.66
15,0.2344,1.6135921418712956e-05,1.50847,1.38185,21.7,2.66
6315 MiB

```

### Execution (2026-09-07 20:05:38)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
config.json 
6603 MiB

```

### Execution (2026-09-07 20:08:05)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
config.json loss.csv 
step,epoch,lr,train_loss,val_loss,elapsed_s,peak_memory_gb
25,0.05,9.989514131188559e-05,1.08797,1.07148,401.0,2.83
3303 MiB

```

### Execution (2026-09-07 20:08:44)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
config.json loss.csv 
step,epoch,lr,train_loss,val_loss,elapsed_s,peak_memory_gb
25,0.05,9.989514131188559e-05,1.08797,1.07148,401.0,2.83
3305 MiB

```

### Execution (2026-09-07 20:13:46)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
config.json loss.csv 
step,epoch,lr,train_loss,val_loss,elapsed_s,peak_memory_gb
25,0.05,9.989514131188559e-05,1.08797,1.07148,401.0,2.83
25,0.05,9.989514131188559e-05,1.08797,1.07148,309.2,2.83
3839 MiB

```

### Execution (2026-09-07 20:18:47)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
config.json loss.csv 
25,0.05,9.989514131188559e-05,1.08797,1.07148,401.0,2.83
25,0.05,9.989514131188559e-05,1.08797,1.07148,309.2,2.83
50,0.1,9.872052623234632e-05,0.97963,0.87492,573.6,2.85
4391 MiB

```

### Execution (2026-09-07 20:19:08)
```python
import subprocess
print(subprocess.run("ps -eo pid,ppid,lstart,etimes,cmd | grep -E 'train/train.py|nbconvert' | grep -v grep | cut -c1-200; echo ---; cat /content/ghl-support-slm/train/runs/v2-t4/loss.csv; echo ---; ls -la --time-style=+%H:%M:%S /content/ghl-support-slm/train/runs/v2-t4/; nvidia-smi --query-compute-apps=pid,used_memory --format=csv", shell=True, capture_output=True, text=True).stdout, flush=True)

```

**Output**:
```
  10083    9039 Mon Sep  7 20:01:08 2026    1080 /bin/sh -c cd /content/ghl-support-slm && jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.allow_errors
  10084   10083 Mon Sep  7 20:01:08 2026    1080 /usr/bin/python3 /usr/local/bin/jupyter-nbconvert --to notebook --execute --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.allow_errors=True note
  10977   10122 Mon Sep  7 20:04:20 2026     888 /bin/sh -c python train/train.py --config configs/train-t4.yaml --data-dir data/processed/v2 --run-name v2-t4 --no-push
  10978   10977 Mon Sep  7 20:04:20 2026     888 python3 train/train.py --config configs/train-t4.yaml --data-dir data/processed/v2 --run-name v2-t4 --no-push
---
step,epoch,lr,train_loss,val_loss,elapsed_s,peak_memory_gb
25,0.05,9.989514131188559e-05,1.08797,1.07148,401.0,2.83
25,0.05,9.989514131188559e-05,1.08797,1.07148,309.2,2.83
50,0.1,9.872052623234632e-05,0.97963,0.87492,573.6,2.85
75,0.15,9.627106148213522e-05,0.85932,0.8321,837.8,2.88
---
total 16
drwxr-xr-x 2 root root 4096 20:06:43 .
drwxr-xr-x 4 root root 4096 20:05:08 ..
-rw-r--r-- 1 root root 2490 20:05:08 config.json
-rw-r--r-- 1 root root  290 20:19:06 loss.csv
pid, used_gpu_memory [MiB]
10978, 4388 MiB

```

### Execution (2026-09-07 20:19:40)
```python
p="/content/ghl-support-slm/train/runs/v2-t4/loss.csv"
lines=open(p).read().splitlines(); stale=[l for l in lines if l.startswith("25,") and l.split(",")[5]=="401.0"]
keep=[l for l in lines if l not in stale]; open(p,"w").write("\n".join(keep)+"\n")
print("removed", stale, "| remaining rows", len(keep)-1, flush=True); print(open(p).read(), flush=True)

```

**Output**:
```
removed ['25,0.05,9.989514131188559e-05,1.08797,1.07148,401.0,2.83'] | remaining rows 3
```

**Output**:
```
step,epoch,lr,train_loss,val_loss,elapsed_s,peak_memory_gb
25,0.05,9.989514131188559e-05,1.08797,1.07148,309.2,2.83
50,0.1,9.872052623234632e-05,0.97963,0.87492,573.6,2.85
75,0.15,9.627106148213522e-05,0.85932,0.8321,837.8,2.88

```

### Execution (2026-09-07 20:23:49)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 config.json loss.csv 
50,0.1,9.872052623234632e-05,0.97963,0.87492,573.6,2.85
75,0.15,9.627106148213522e-05,0.85932,0.8321,837.8,2.88
100,0.2,9.261084118279847e-05,0.92473,0.7866,1103.9,2.88
4393 MiB

```

### Execution (2026-09-07 20:29:54)
```python
import subprocess
print(subprocess.run("ps -eo pid,ppid,lstart,etimes,cmd | grep -E 'train/train.py|nbconvert' | grep -v grep | cut -c1-200; echo ---; cat /content/ghl-support-slm/train/runs/v2-t4/loss.csv; echo ---; ls -la --time-style=+%H:%M:%S /content/ghl-support-slm/train/runs/v2-t4/; nvidia-smi --query-compute-apps=pid,used_memory --format=csv", shell=True, capture_output=True, text=True).stdout, flush=True)

```

**Output**:
```
  10083    9039 Mon Sep  7 20:01:08 2026    1725 /bin/sh -c cd /content/ghl-support-slm && jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.allow_errors
  10084   10083 Mon Sep  7 20:01:08 2026    1725 /usr/bin/python3 /usr/local/bin/jupyter-nbconvert --to notebook --execute --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.allow_errors=True note
  10977   10122 Mon Sep  7 20:04:20 2026    1533 /bin/sh -c python train/train.py --config configs/train-t4.yaml --data-dir data/processed/v2 --run-name v2-t4 --no-push
  10978   10977 Mon Sep  7 20:04:20 2026    1533 python3 train/train.py --config configs/train-t4.yaml --data-dir data/processed/v2 --run-name v2-t4 --no-push
---
step,epoch,lr,train_loss,val_loss,elapsed_s,peak_memory_gb
25,0.05,9.989514131188559e-05,1.08797,1.07148,309.2,2.83
50,0.1,9.872052623234632e-05,0.97963,0.87492,573.6,2.85
75,0.15,9.627106148213522e-05,0.85932,0.8321,837.8,2.88
100,0.2,9.261084118279847e-05,0.92473,0.7866,1103.9,2.88
125,0.25,8.783564079088477e-05,0.75378,0.75808,1370.3,2.88
---
total 20
drwxr-xr-x 3 root root 4096 20:23:32 .
drwxr-xr-x 4 root root 4096 20:05:08 ..
drwxr-xr-x 2 root root 4096 20:23:35 checkpoint-100
-rw-r--r-- 1 root root 2490 20:05:08 config.json
-rw-r--r-- 1 root root  346 20:27:58 loss.csv
pid, used_gpu_memory [MiB]
10978, 4390 MiB

```

### Execution (2026-09-07 20:30:24)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 config.json loss.csv 
75,0.15,9.627106148213522e-05,0.85932,0.8321,837.8,2.88
100,0.2,9.261084118279847e-05,0.92473,0.7866,1103.9,2.88
125,0.25,8.783564079088477e-05,0.75378,0.75808,1370.3,2.88
4977 MiB

```

### Execution (2026-09-07 20:35:25)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 config.json loss.csv 
100,0.2,9.261084118279847e-05,0.92473,0.7866,1103.9,2.88
125,0.25,8.783564079088477e-05,0.75378,0.75808,1370.3,2.88
150,0.3,8.2070410981557e-05,0.76716,0.7442,1635.3,2.94
4977 MiB

```

## Session Created: 2026-09-07 20:42:10
- Endpoint: `gpu-t4-s-kkb-ass1c1-3iwzx34ppp799`

### Execution (2026-09-07 20:43:29)
```python
import subprocess, os, time
def sh(c):
    print("$", c, flush=True); t=time.time()
    subprocess.run(c, shell=True, check=True); print(f"  ok {time.time()-t:.0f}s", flush=True)
sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
if not os.path.isdir("/content/ghl-support-slm"):
    sh("git clone --branch v2 --depth 1 -q https://github.com/Imsharad/ghl-support-slm.git /content/ghl-support-slm")
os.chdir("/content/ghl-support-slm")
sh("git rev-parse HEAD")
sh("pip install -q 'transformers==5.16.1' 'peft==0.20.0' 'trl==1.12.0' 'bitsandbytes==0.50.2' 'accelerate>=0.34' 'datasets==5.0.1' 'sentence-transformers>=3.0' 'scikit-learn>=1.5' 'pyyaml>=6.0' 'matplotlib>=3.9'")
sh("python -c \"import torch,transformers,peft,bitsandbytes;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'tf',transformers.__version__,'peft',peft.__version__,'bnb',bitsandbytes.__version__)\"")
sh("python data/fetch.py")
print("SETUP DONE", time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
$ nvidia-smi --query-gpu=name,memory.total --format=csv
```

**Output**:
```
  ok 0s
```

**Output**:
```
$ git clone --branch v2 --depth 1 -q https://github.com/Imsharad/ghl-support-slm.git /content/ghl-support-slm
```

**Output**:
```
  ok 1s
```

**Output**:
```
$ git rev-parse HEAD
```

**Output**:
```
  ok 0s
```

**Output**:
```
$ pip install -q 'transformers==5.16.1' 'peft==0.20.0' 'trl==1.12.0' 'bitsandbytes==0.50.2' 'accelerate>=0.34' 'datasets==5.0.1' 'sentence-transformers>=3.0' 'scikit-learn>=1.5' 'pyyaml>=6.0' 'matplotlib>=3.9'
```

**Output**:
```
  ok 12s
```

**Output**:
```
$ python -c "import torch,transformers,peft,bitsandbytes;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'tf',transformers.__version__,'peft',peft.__version__,'bnb',bitsandbytes.__version__)"
```

**Output**:
```
  ok 26s
```

**Output**:
```
$ python data/fetch.py
```

**Output**:
```
  ok 3s
```

**Output**:
```
SETUP DONE 20:43:29 UTC
```

### Execution (2026-09-07 20:43:29)
```python
print("alive")

```

**Output**:
```
alive
```

### Execution (2026-09-07 20:44:00)
```python
import subprocess, os, json, time
os.chdir("/content/ghl-support-slm")
v = json.load(open("configs/versions.json"))
print(json.dumps({k: v[k] for k in v if isinstance(v[k], dict)}, indent=0)[:600], flush=True)
code = r'''
import json, os, time
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"]="1"
from huggingface_hub import snapshot_download
v = json.load(open("configs/versions.json"))
for key, entry in v.items():
    if isinstance(entry, dict) and "repo_id" in entry and "revision" in entry:
        t=time.time()
        try: p = snapshot_download(entry["repo_id"], revision=entry["revision"]); print(key, entry["repo_id"], "->", p, f"{time.time()-t:.0f}s", flush=True)
        except Exception as exc: print(key, entry["repo_id"], "skipped:", str(exc)[:80], flush=True)
'''
r = subprocess.run(["python", "-c", code], capture_output=True, text=True); print((r.stdout + r.stderr)[-1500:], flush=True)
print("PREDL DONE rc", r.returncode, time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
{
"base_model": {
"repo_id": "Qwen/Qwen2.5-1.5B-Instruct",
"revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
"license": "Apache-2.0"
},
"dataset": {
"repo_id": "bitext/Bitext-customer-support-llm-chatbot-training-dataset",
"revision": "430d1a89bd93bd1fa23c16f29dd53e73f0087443",
"license": "CDLA-Sharing-1.0"
},
"llama_cpp_converter": {
"repo": "https://github.com/ggml-org/llama.cpp",
"commit": "6a1a922d269908a29cbd4b49c27e6a8e7fd10fae"
}
}
```

**Output**:
```
base_model Qwen/Qwen2.5-1.5B-Instruct -> /root/.cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/989aa7980e4cf806f80c7fef2b1adb7bc71aa306 29s
dataset bitext/Bitext-customer-support-llm-chatbot-training-dataset skipped: 401 Client Error. (Request ID: Root=1-6a9f2210-11948a1d6c3c9ac3130ddb3b;045fdae2
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.

```

**Output**:
```
PREDL DONE rc 0 20:44:00 UTC
```

### Execution (2026-09-07 20:44:23)
```python
import subprocess, os, time, re
os.chdir("/content/ghl-support-slm")
subprocess.run("pkill -f jupyter-nbconvert; pkill -f 'train/train.py'; sleep 2", shell=True)
log = open("/content/nbdry.log").read()
errs = re.findall(r"'output_type': 'error'.{0,300}", log)
cells = re.findall(r"Executing cell:\n(.{0,80})", log)
print("dry cells reached:", len(cells), "| error outputs:", len(errs), flush=True)
for e in errs[:5]: print("  ", e[:250], flush=True)
print("smoke ok line:", re.findall(r"'max_abs_diff'[^}]*", log)[:1], "| check_run:", re.findall(r"check_run[^\n]{0,120}rc=\d", log)[-1:] if re.findall(r"rc=\d", log) else "", flush=True)
subprocess.run("rm -rf train/runs/v2-t4 artifacts/merged; git fetch -q origin v2 && git checkout -q --detach origin/v2 && git log --oneline -1 && test -s data/v2/admissions.jsonl && wc -l data/v2/admissions.jsonl", shell=True)
cmd = ("cd /content/ghl-support-slm && jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=-1 "
       "--ExecutePreprocessor.allow_errors=True notebooks/train_colab.ipynb --output /content/v2_colab_run.ipynb > /content/nbrun.log 2>&1")
p = subprocess.Popen(cmd, shell=True, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("REAL RUN nbconvert pid", p.pid, time.strftime("%H:%M:%S UTC"), flush=True)

```

### Execution (2026-09-07 20:44:42)
```python
import subprocess, os, time
os.chdir("/content/ghl-support-slm")
subprocess.run("pkill -f jupyter-nbconvert; pkill -f 'train/train.py'; sleep 1; rm -rf train/runs/v2-t4 artifacts/merged; git fetch -q origin v2 && git checkout -q --detach origin/v2 && git log --oneline -1 && wc -l data/v2/admissions.jsonl", shell=True)
cmd = ("cd /content/ghl-support-slm && jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=-1 "
       "--ExecutePreprocessor.allow_errors=True notebooks/train_colab.ipynb --output /content/v2_colab_run.ipynb > /content/nbrun.log 2>&1")
p = subprocess.Popen(cmd, shell=True, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("NOTEBOOK RUN nbconvert pid", p.pid, time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
NOTEBOOK RUN nbconvert pid 2483 20:44:42 UTC
```

### Execution (2026-09-07 20:45:34)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0

0 MiB

```

### Execution (2026-09-07 20:46:00)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0

3 MiB

```

### Execution (2026-09-07 20:51:02)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
config.json 
3639 MiB

```

### Execution (2026-09-07 20:56:04)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
config.json loss.csv 
step,epoch,lr,train_loss,val_loss,elapsed_s,peak_memory_gb
25,0.05,9.989514131188559e-05,1.19414,1.04785,242.1,2.93
50,0.1,9.872052623234632e-05,1.09392,0.89198,483.2,2.93
3639 MiB

```

### Execution (2026-09-07 21:01:06)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
config.json loss.csv 
25,0.05,9.989514131188559e-05,1.19414,1.04785,242.1,2.93
50,0.1,9.872052623234632e-05,1.09392,0.89198,483.2,2.93
75,0.15,9.627106148213522e-05,0.79207,0.84139,723.6,2.93
3639 MiB

```

### Execution (2026-09-07 21:06:08)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 config.json loss.csv 
50,0.1,9.872052623234632e-05,1.09392,0.89198,483.2,2.93
75,0.15,9.627106148213522e-05,0.79207,0.84139,723.6,2.93
100,0.2,9.261084118279847e-05,0.89039,0.80091,965.4,2.93
3639 MiB

```

### Execution (2026-09-07 21:11:09)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 config.json loss.csv 
75,0.15,9.627106148213522e-05,0.79207,0.84139,723.6,2.93
100,0.2,9.261084118279847e-05,0.89039,0.80091,965.4,2.93
125,0.25,8.783564079088477e-05,0.96537,0.78967,1208.8,2.93
3639 MiB

```

### Execution (2026-09-07 21:11:56)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
TARRED checkpoint-100
```

**Output**:
```
have: ['checkpoint-100']
```

*File Operation*: `download` on `/content/checkpoint-100.tgz`

### Execution (2026-09-07 21:16:11)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 config.json loss.csv 
125,0.25,8.783564079088477e-05,0.96537,0.78967,1208.8,2.93
150,0.3,8.2070410981557e-05,0.88277,0.7689,1448.9,2.93
175,0.35,7.546600811643816e-05,0.63258,0.75215,1698.5,2.93
3639 MiB

```

### Execution (2026-09-07 21:16:22)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100']
```

### Execution (2026-09-07 21:20:44)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
TARRED checkpoint-200
```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200']
```

*File Operation*: `download` on `/content/checkpoint-200.tgz`

### Execution (2026-09-07 21:21:13)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 config.json loss.csv 
150,0.3,8.2070410981557e-05,0.88277,0.7689,1448.9,2.93
175,0.35,7.546600811643816e-05,0.63258,0.75215,1698.5,2.93
200,0.4,6.819524684817438e-05,0.70124,0.73183,1939.3,2.94
4223 MiB

```

### Execution (2026-09-07 21:25:10)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200']
```

### Execution (2026-09-07 21:26:19)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 config.json loss.csv 
175,0.35,7.546600811643816e-05,0.63258,0.75215,1698.5,2.93
200,0.4,6.819524684817438e-05,0.70124,0.73183,1939.3,2.94
225,0.45,6.044837815156377e-05,0.68569,0.72224,2189.2,2.94
4223 MiB

```

### Execution (2026-09-07 21:29:33)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
TARRED checkpoint-250
```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250']
```

*File Operation*: `download` on `/content/checkpoint-250.tgz`

### Execution (2026-09-07 21:31:20)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 config.json loss.csv 
200,0.4,6.819524684817438e-05,0.70124,0.73183,1939.3,2.94
225,0.45,6.044837815156377e-05,0.68569,0.72224,2189.2,2.94
250,0.5,5.242811110572242e-05,0.7325,0.71812,2428.1,2.94
4223 MiB

```

### Execution (2026-09-07 21:33:58)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250']
```

### Execution (2026-09-07 21:36:22)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 config.json loss.csv 
250,0.5,5.242811110572242e-05,0.7325,0.71812,2428.1,2.94
275,0.55,4.434430869023579e-05,0.68229,0.71308,2677.0,2.94
300,0.6,3.640849638818286e-05,0.69991,0.70715,2916.8,2.94
4223 MiB

```

### Execution (2026-09-07 21:38:54)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
TARRED checkpoint-300
```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300']
```

*File Operation*: `download` on `/content/checkpoint-300.tgz`

### Execution (2026-09-07 21:41:24)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 config.json loss.csv 
275,0.55,4.434430869023579e-05,0.68229,0.71308,2677.0,2.94
300,0.6,3.640849638818286e-05,0.69991,0.70715,2916.8,2.94
325,0.65,2.882832728712551e-05,0.75521,0.69384,3165.7,2.94
4223 MiB

```

### Execution (2026-09-07 21:43:40)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300']
```

### Execution (2026-09-07 21:46:59)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 config.json loss.csv 
300,0.6,3.640849638818286e-05,0.69991,0.70715,2916.8,2.94
325,0.65,2.882832728712551e-05,0.75521,0.69384,3165.7,2.94
350,0.7,2.180214850745467e-05,0.72351,0.69468,3404.6,2.94
4223 MiB

```

### Execution (2026-09-07 21:47:54)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300']
```

### Execution (2026-09-07 21:50:22)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 config.json loss.csv 
325,0.65,2.882832728712551e-05,0.75521,0.69384,3165.7,2.94
350,0.7,2.180214850745467e-05,0.72351,0.69468,3404.6,2.94
375,0.75,1.5513811136094787e-05,0.67599,0.69068,3641.9,2.94
4811 MiB

```

### Execution (2026-09-07 21:52:15)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
TARRED checkpoint-400
```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400']
```

### Execution (2026-09-07 21:52:15)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 checkpoint-400 config.json loss.csv 
350,0.7,2.180214850745467e-05,0.72351,0.69468,3404.6,2.94
375,0.75,1.5513811136094787e-05,0.67599,0.69068,3641.9,2.94
400,0.8,1.012785947186397e-05,0.67541,0.6871,3877.0,2.94
4811 MiB

```

*File Operation*: `download` on `/content/checkpoint-400.tgz`

### Execution (2026-09-07 21:56:42)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400']
```

### Execution (2026-09-07 21:57:17)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 checkpoint-400 config.json loss.csv 
375,0.75,1.5513811136094787e-05,0.67599,0.69068,3641.9,2.94
400,0.8,1.012785947186397e-05,0.67541,0.6871,3877.0,2.94
425,0.85,5.785225463498828e-06,0.66718,0.68617,4121.3,2.94
4811 MiB

```

### Execution (2026-09-07 22:00:44)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400']
```

### Execution (2026-09-07 22:02:19)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 checkpoint-400 config.json loss.csv 
400,0.8,1.012785947186397e-05,0.67541,0.6871,3877.0,2.94
425,0.85,5.785225463498828e-06,0.66718,0.68617,4121.3,2.94
450,0.9,2.5995410021864787e-06,0.88971,0.6855,4360.1,2.94
4811 MiB

```

### Execution (2026-09-07 22:04:46)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400']
```

### Execution (2026-09-07 22:08:00)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 checkpoint-400 checkpoint-500 config.json curves.png loss.csv 
450,0.9,2.5995410021864787e-06,0.88971,0.6855,4360.1,2.94
475,0.95,6.54164563305465e-07,0.78234,0.68506,4596.8,2.94
500,1.0,0.0,0.65239,0.68509,4831.5,2.94
3 MiB

```

### Execution (2026-09-07 22:13:02)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 checkpoint-400 checkpoint-500 config.json curves.png loss.csv 
450,0.9,2.5995410021864787e-06,0.88971,0.6855,4360.1,2.94
475,0.95,6.54164563305465e-07,0.78234,0.68506,4596.8,2.94
500,1.0,0.0,0.65239,0.68509,4831.5,2.94
0 MiB

```

### Execution (2026-09-07 22:13:17)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 checkpoint-400 checkpoint-500 config.json curves.png loss.csv 
450,0.9,2.5995410021864787e-06,0.88971,0.6855,4360.1,2.94
475,0.95,6.54164563305465e-07,0.78234,0.68506,4596.8,2.94
500,1.0,0.0,0.65239,0.68509,4831.5,2.94
0 MiB

```

### Execution (2026-09-07 22:18:02)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
TARRED checkpoint-500
```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

### Execution (2026-09-07 22:18:04)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 checkpoint-400 checkpoint-500 config.json curves.png loss.csv 
450,0.9,2.5995410021864787e-06,0.88971,0.6855,4360.1,2.94
475,0.95,6.54164563305465e-07,0.78234,0.68506,4596.8,2.94
500,1.0,0.0,0.65239,0.68509,4831.5,2.94
0 MiB

```

*File Operation*: `download` on `/content/checkpoint-500.tgz`

### Execution (2026-09-07 22:22:26)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

### Execution (2026-09-07 22:23:06)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 checkpoint-400 checkpoint-500 config.json curves.png loss.csv 
450,0.9,2.5995410021864787e-06,0.88971,0.6855,4360.1,2.94
475,0.95,6.54164563305465e-07,0.78234,0.68506,4596.8,2.94
500,1.0,0.0,0.65239,0.68509,4831.5,2.94
0 MiB

```

### Execution (2026-09-07 22:26:27)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

### Execution (2026-09-07 22:28:08)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 checkpoint-400 checkpoint-500 config.json curves.png loss.csv 
450,0.9,2.5995410021864787e-06,0.88971,0.6855,4360.1,2.94
475,0.95,6.54164563305465e-07,0.78234,0.68506,4596.8,2.94
500,1.0,0.0,0.65239,0.68509,4831.5,2.94
0 MiB

```

### Execution (2026-09-07 22:28:55)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; ls train/runs/v2-t4 | grep -E 'dev-|zip|curves' | tr '\\n' ' '; echo; ls -la /content/*.zip /content/v2_colab_run.ipynb 2>/dev/null | awk '{print $5,$9}'; ps -eo etimes,cmd | grep -E 'eval/run.py|merge.py' | grep -v grep | cut -c1-90", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
curves.png 
139487 /content/v2_colab_run.ipynb
1225378342 /content/v2-t4.zip

```

*File Operation*: `download` on `/content/v2_colab_run.ipynb`

### Execution (2026-09-07 22:30:17)
```python
import subprocess, os, time, shutil, glob
os.chdir("/content/ghl-support-slm"); os.environ["PYTHONPATH"] = "/content/ghl-support-slm"; os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
subprocess.run("pkill -f jupyter-nbconvert", shell=True)
cmd = ("cd /content/ghl-support-slm && export PYTHONPATH=/content/ghl-support-slm && ( for d in $(ls -d train/runs/v2-t4/checkpoint-* | sort -t- -k2 -n); do s=${d##*-}; out=train/runs/v2-t4/dev-checkpoint-$s-raw.jsonl; "
       "rm -rf artifacts/merged; python tools/merge.py --adapter $d --output artifacts/merged 2>&1 | tail -1; "
       "python eval/run.py --model tuned --backend transformers --split dev --device cuda --output $out --check-complete 2>&1 | grep -vE 'it/s|Could not load|Failed to load' | tail -2; done; rm -rf artifacts/merged; echo DEVANS2 DONE ) > /content/devans2.log 2>&1")
p = subprocess.Popen(cmd, shell=True, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("devans2 pid", p.pid, time.strftime("%H:%M:%S UTC"), flush=True)

```

**Output**:
```
devans2 pid 28816 22:30:17 UTC
```

### Execution (2026-09-07 22:30:39)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

*File Operation*: `download` on `/content/v2-t4.zip`

### Execution (2026-09-07 22:33:11)
```python
import subprocess
print(subprocess.run("pgrep -f jupyter-nbconvert >/dev/null && echo NBCONVERT RUNNING || echo NBCONVERT DONE; pgrep -f 'train/train.py' >/dev/null && echo TRAIN RUNNING || echo train not running; grep -c 'Executing cell' /content/nbrun.log; grep -E 'output_type.: .error' /content/nbrun.log | wc -l; ls train/runs/v2-t4 2>/dev/null | tr '\\n' ' '; echo; tail -n 3 train/runs/v2-t4/loss.csv 2>/dev/null; grep -oE '\\[20[^]]*\\] [^\\\\]{0,100}' /content/nbrun.log | tail -3; nvidia-smi --query-gpu=memory.used --format=csv,noheader", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
NBCONVERT RUNNING
TRAIN RUNNING
0
0
checkpoint-100 checkpoint-200 checkpoint-250 checkpoint-300 checkpoint-400 checkpoint-500 config.json curves.png dev-checkpoint-100-raw.jsonl loss.csv 
450,0.9,2.5995410021864787e-06,0.88971,0.6855,4360.1,2.94
475,0.95,6.54164563305465e-07,0.78234,0.68506,4596.8,2.94
500,1.0,0.0,0.65239,0.68509,4831.5,2.94
3293 MiB

```

### Execution (2026-09-07 22:33:27)
```python
import subprocess
print(subprocess.run("tail -n 8 /content/devans2.log; ls -la train/runs/v2-t4 | grep dev- | awk '{print $5, $9}'; pgrep -f 'eval/run.py|merge.py' >/dev/null && echo STILL RUNNING || echo NOT RUNNING", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
prompt=/content/ghl-support-slm/artifacts/merged/prompt.txt
7965 dev-checkpoint-100-raw.jsonl
STILL RUNNING

```

### Execution (2026-09-07 22:33:52)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
22 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
0

```

### Execution (2026-09-07 22:34:48)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

### Execution (2026-09-07 22:34:54)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
40 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
0

```

### Execution (2026-09-07 22:35:26)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
49 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
0

```

### Execution (2026-09-07 22:35:58)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
0

```

*File Operation*: `download` on `/content/ghl-support-slm/train/runs/v2-t4/dev-checkpoint-100-raw.jsonl`

### Execution (2026-09-07 22:38:49)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

### Execution (2026-09-07 22:39:30)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
31 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
0

```

### Execution (2026-09-07 22:40:31)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
47 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
0

```

### Execution (2026-09-07 22:41:32)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
0

```

*File Operation*: `download` on `/content/ghl-support-slm/train/runs/v2-t4/dev-checkpoint-200-raw.jsonl`

### Execution (2026-09-07 22:42:35)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
1 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
0

```

### Execution (2026-09-07 22:43:33)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

### Execution (2026-09-07 22:43:36)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
21 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
0

```

### Execution (2026-09-07 22:44:38)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
35 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
0

```

### Execution (2026-09-07 22:47:52)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

### Execution (2026-09-07 22:48:19)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
10 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
0

```

*File Operation*: `download` on `/content/ghl-support-slm/train/runs/v2-t4/dev-checkpoint-250-raw.jsonl`

### Execution (2026-09-07 22:49:21)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
27 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
0

```

### Execution (2026-09-07 22:50:42)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
52 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
0

```

### Execution (2026-09-07 22:51:44)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
0

```

*File Operation*: `download` on `/content/ghl-support-slm/train/runs/v2-t4/dev-checkpoint-300-raw.jsonl`

### Execution (2026-09-07 22:52:14)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

### Execution (2026-09-07 22:52:46)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
0

```

### Execution (2026-09-07 22:53:47)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
10 train/runs/v2-t4/dev-checkpoint-400-raw.jsonl
0

```

### Execution (2026-09-07 22:55:02)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
32 train/runs/v2-t4/dev-checkpoint-400-raw.jsonl
0

```

### Execution (2026-09-07 22:56:03)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
47 train/runs/v2-t4/dev-checkpoint-400-raw.jsonl
0

```

### Execution (2026-09-07 22:56:47)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

### Execution (2026-09-07 22:57:05)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-400-raw.jsonl
0

```

*File Operation*: `download` on `/content/ghl-support-slm/train/runs/v2-t4/dev-checkpoint-400-raw.jsonl`

### Execution (2026-09-07 22:58:07)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-400-raw.jsonl
2 train/runs/v2-t4/dev-checkpoint-500-raw.jsonl
0

```

### Execution (2026-09-07 22:59:31)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-400-raw.jsonl
27 train/runs/v2-t4/dev-checkpoint-500-raw.jsonl
0

```

### Execution (2026-09-07 23:00:33)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-400-raw.jsonl
41 train/runs/v2-t4/dev-checkpoint-500-raw.jsonl
0

```

### Execution (2026-09-07 23:00:49)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

### Execution (2026-09-07 23:01:44)
```python
import subprocess
print(subprocess.run("for f in train/runs/v2-t4/dev-checkpoint-*-raw.jsonl; do echo $(wc -l < $f) $f; done; grep -c 'DEVANS2 DONE' /content/devans2.log", shell=True, capture_output=True, text=True, cwd="/content/ghl-support-slm").stdout, flush=True)

```

**Output**:
```
54 train/runs/v2-t4/dev-checkpoint-100-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-200-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-250-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-300-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-400-raw.jsonl
54 train/runs/v2-t4/dev-checkpoint-500-raw.jsonl
1

```

*File Operation*: `download` on `/content/ghl-support-slm/train/runs/v2-t4/dev-checkpoint-500-raw.jsonl`

### Execution (2026-09-07 23:04:51)
```python
import subprocess, os, sys, glob
os.chdir("/content/ghl-support-slm/train/runs/v2-t4")
done = set(open("/content/tarred.txt").read().split()) if os.path.exists("/content/tarred.txt") else set()
for d in sorted(glob.glob("checkpoint-*")):
    if d in done or not os.path.exists(f"{d}/adapter_config.json"): continue
    subprocess.run(f"tar czf /content/{d}.tgz {d} loss.csv config.json && sha256sum /content/{d}.tgz", shell=True)
    open("/content/tarred.txt", "a").write(d + "\n"); print("TARRED", d, flush=True)
print("have:", sorted(glob.glob("checkpoint-*")), flush=True)

```

**Output**:
```
have: ['checkpoint-100', 'checkpoint-200', 'checkpoint-250', 'checkpoint-300', 'checkpoint-400', 'checkpoint-500']
```

*File Operation*: `download` on `/content/devans2.log`

