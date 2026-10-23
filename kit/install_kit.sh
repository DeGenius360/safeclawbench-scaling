#!/bin/bash
# SafeClawBench resume kit installer. Writes every script into /workspace/kit/.
# Safe to re-run: it overwrites the kit scripts but never touches keys.env, state/ or results.
mkdir -p /workspace/kit/state /workspace/kit/logs
cd /workspace/kit

# ---------------------------------------------------------------- env.sh
cat > env.sh << 'EOF_ENV'
#!/bin/bash
# Sourced by every script in the kit.
[ -f /workspace/keys.env ] && source /workspace/keys.env
export KIT=/workspace/kit
export REPO=/workspace/safeclawbench
export SAFECLAWBENCH_API_BASE=http://localhost:8000
export SAFECLAWBENCH_API_KEY=anything
export OLLAMA_MODELS=/workspace/ollama-models
export OLLAMA_NUM_PARALLEL=4
export OLLAMA_CONTEXT_LENGTH=8192
mkdir -p "$KIT/state" "$KIT/logs"

peak_warning() {
  local dow h
  dow=$(date -u +%u); h=$((10#$(date -u +%H)))
  if [ "$dow" -le 5 ] && { { [ "$h" -ge 1 ] && [ "$h" -lt 4 ]; } || { [ "$h" -ge 6 ] && [ "$h" -lt 10 ]; }; }; then
    echo "WARNING: DeepSeek peak-price window right now (weekdays 01-04 and 06-10 UTC): judge calls cost about 2x."
  fi
}
EOF_ENV

# ---------------------------------------------------------------- router_proxy.py
cat > router_proxy.py << 'EOF_PROXY'
#!/usr/bin/env python3
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import requests

OLLAMA = "http://localhost:11434"
ANTHROPIC = "https://api.anthropic.com"
DEEPSEEK = "https://api.deepseek.com"
AKEY = os.environ.get("ANTHROPIC_API_KEY", "")
DKEY = os.environ.get("DEEPSEEK_API_KEY", "")

class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    request_queue_size = 64

class H(BaseHTTPRequestHandler):
    def _reply(self, code, body, ctype="application/json"):
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n))
            model = payload.get("model", "")
            if self.path == "/v1/messages":
                url = ANTHROPIC + "/v1/messages"
                hdr = {"Content-Type": "application/json", "x-api-key": AKEY, "anthropic-version": "2023-06-01"}
            elif model.startswith("qwen2.5"):
                url = OLLAMA + self.path
                hdr = {"Content-Type": "application/json"}
            elif model.startswith("deepseek"):
                url = DEEPSEEK + self.path
                payload.setdefault("thinking", {"type": "disabled"})  # V4.1 thinks by default and burns max_tokens
                hdr = {"Content-Type": "application/json", "Authorization": "Bearer " + DKEY}
            else:
                return self._reply(404, b'{"error":"unknown model"}')
            r = requests.post(url, headers=hdr, json=payload, timeout=300)
            self._reply(r.status_code, r.content)
        except Exception as e:
            self._reply(502, json.dumps({"error": str(e)}).encode())

    def log_message(self, fmt, *a):
        print("[proxy]", fmt % a, flush=True)

if __name__ == "__main__":
    print("proxy on 127.0.0.1:8000", flush=True)
    Server(("127.0.0.1", 8000), H).serve_forever()
EOF_PROXY

# ---------------------------------------------------------------- apply_patches.py
cat > apply_patches.py << 'EOF_PATCH'
#!/usr/bin/env python3
"""Idempotent. Applies every code fix found during the July runs."""
import os, sys
from pathlib import Path
R = Path(os.environ.get("REPO", "/workspace/safeclawbench"))

def read(rel): return (R / rel).read_text()
def write(rel, s): (R / rel).write_text(s)

entries = {
    "qwen2.5-7b": '("qwen2.5:7b", "openai")',
    "qwen2.5-14b": '("qwen2.5:14b", "openai")',
    "qwen2.5-32b": '("qwen2.5:32b", "openai")',
    "claude-haiku-4.5": '("claude-haiku-4-5", "anthropic")',
    "deepseek-v4-flash": '("deepseek-v4-flash", "openai")',
    "deepseek-flash": '("deepseek-flash", "openai")',
}
s = read("agents/api_wrapper.py")
if "MODELS = {\n" not in s:
    print("FAIL MODELS dict not found in agents/api_wrapper.py (repo changed?)"); sys.exit(1)
added = []
for k, v in entries.items():
    if f'"{k}"' not in s:
        s = s.replace("MODELS = {\n", f'MODELS = {{\n    "{k}": {v},\n', 1)
        added.append(k)
write("agents/api_wrapper.py", s)
print("OK MODELS:", ("added " + ", ".join(added)) if added else "already complete")

def patch(rel, old, new, marker, label):
    s = read(rel)
    if marker in s:
        print(f"OK {label}: already applied"); return
    if old not in s:
        print(f"FAIL {label}: expected code not found in {rel} (repo changed?)"); sys.exit(1)
    write(rel, s.replace(old, new, 1))
    print(f"OK {label}: applied")

patch("agents/api_wrapper.py",
'''def call_openai(model_id: str, messages: List[Dict], temperature: float = 0,
                max_tokens: int = 2048, timeout: int = 60) -> Dict:
    """Call OpenAI-compatible API."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = requests.post(f"{API_BASE}/v1/chat/completions",
                         headers=headers, json=payload, timeout=timeout)''',
'''def call_openai(model_id: str, messages: List[Dict], temperature: float = 0,
                max_tokens: int = 2048, timeout: int = 60, response_format: dict = None) -> Dict:
    """Call OpenAI-compatible API."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format
    resp = requests.post(f"{API_BASE}/v1/chat/completions",
                         headers=headers, json=payload, timeout=timeout)''',
"response_format: dict = None", "call_openai JSON-mode support")

patch("agents/api_wrapper.py",
'def call_anthropic(model_id: str, messages: List[Dict], temperature: float = 0,\n                   max_tokens: int = 2048, timeout: int = 60) -> Dict:',
'def call_anthropic(model_id: str, messages: List[Dict], temperature: float = 0,\n                   max_tokens: int = 2048, timeout: int = 60, **_ignored) -> Dict:',
"**_ignored", "call_anthropic ignores extra kwargs")

patch("evaluator/judge.py",
'''result = call_with_retry(judge_model, [
        {"role": "user", "content": prompt}
    ], max_retries=2, temperature=0, max_tokens=1024, timeout=60)''',
'''result = call_with_retry(judge_model, [
        {"role": "user", "content": prompt}
    ], max_retries=2, temperature=0, max_tokens=1024, timeout=60,
       response_format={"type": "json_object"})''',
'response_format={"type": "json_object"}', "judge JSON mode")

patch("run_benchmark.py",
'''    response = call_with_retry(model_name, messages, max_retries=2,
                               temperature=0, timeout=90)''',
'''    response = call_with_retry(model_name, messages, max_retries=2,
                               temperature=0, timeout=240)''',
"timeout=240", "target-model timeout 240s")
EOF_PATCH

# ---------------------------------------------------------------- probe_judge.py
cat > probe_judge.py << 'EOF_PROBE'
#!/usr/bin/env python3
"""Finds a working DeepSeek judge model ID and records which build the API reports."""
import sys, time, requests
from pathlib import Path
st = Path("/workspace/kit/state"); st.mkdir(parents=True, exist_ok=True)
for name in ("deepseek-flash", "deepseek-v4-flash"):
    try:
        r = requests.post("http://localhost:8000/v1/chat/completions", timeout=60, json={
            "model": name, "temperature": 0, "max_tokens": 5,
            "messages": [{"role": "user", "content": "Reply with the single word: ok"}]})
    except Exception as e:
        print(f"{name}: request error {e}"); continue
    if r.status_code == 200:
        returned = r.json().get("model", "?")
        print(f"OK judge '{name}' works. API reports model build: {returned}")
        (st / "judge_name.txt").write_text(name)
        with open(st / "judge_builds.txt", "a") as f:
            f.write(f"{time.strftime('%FT%TZ', time.gmtime())}\t{name}\t{returned}\n")
        sys.exit(0)
    print(f"{name}: HTTP {r.status_code} {r.text[:200]}")
print("FAIL no working DeepSeek model ID. Check the key, your credit, and DeepSeek's docs for current model names.")
sys.exit(1)
EOF_PROBE

# ---------------------------------------------------------------- prep.py
cat > prep.py << 'EOF_PREP'
#!/usr/bin/env python3
"""Checks restored results, builds stratified 100-case chunks and a 30-case calibration set."""
import json, math, os, random
from pathlib import Path
from collections import defaultdict, Counter
R = Path(os.environ.get("REPO", "/workspace/safeclawbench")); ST = Path("/workspace/kit/state")
ST.mkdir(parents=True, exist_ok=True)
bench = json.load(open(R / "benchmark_v5_600.json"))
atype = lambda c: c.get("attack_type") or str(c["task_id"]).split("_")[0]
print(f"benchmark: {len(bench)} cases", dict(Counter(atype(c) for c in bench)))

print("\n== restored results ==")
for m in ("qwen2.5-7b", "qwen2.5-14b"):
    p = R / f"results/phase2_core_{m}/all_results.json"
    if not p.exists():
        print(f"MISSING {p}  -> upload your phase2_partial zip to /workspace and re-run (or this model needs a full re-run)")
        continue
    rows = json.load(open(p))
    bad = sum(1 for r in rows if (r.get("evaluation") or {}).get("attack_success") is None)
    lens = [len(r.get("agent_response", "")) for r in rows]
    mx = max(lens) if lens else 0
    at_cap = sum(1 for x in lens if x >= mx - 5)
    print(f"OK {m}: {len(rows)} cases, {bad} unjudged. Longest stored response {mx} chars ({at_cap} responses sit at that cap)")
print("(If the cap is about 2000, saved text is truncated: that is why every model gets re-judged from saved text the same way.)")
p1 = R / "results/phase1_exec/summary.json"
print("OK 14B Exec pilot (Phase 1) present" if p1.exists() else "note: phase1_exec summary not found (only needed as a calibration reference)")

groups = defaultdict(list)
for c in bench: groups[atype(c)].append(c)
rng = random.Random(42)
for g in groups.values(): rng.shuffle(g)
order = []
while any(groups.values()):
    for t in sorted(groups):
        if groups[t]: order.append(groups[t].pop())
(R / "chunks").mkdir(exist_ok=True)
print("\n== stratified chunks (any prefix of chunks is balanced) ==")
for i in range(math.ceil(len(order) / 100)):
    ch = order[i * 100:(i + 1) * 100]
    json.dump(ch, open(R / f"chunks/strat_{i}.json", "w"))
    print(f"chunk {i}: {len(ch)} cases", dict(Counter(atype(c) for c in ch)))

p7 = R / "results/phase2_core_qwen2.5-7b/all_results.json"
if p7.exists():
    done = {r["task_id"] for r in json.load(open(p7)) if r.get("status") == "ok"}
    by = defaultdict(list)
    for c in bench:
        if c["task_id"] in done: by[atype(c)].append(c)
    rng = random.Random(7); calib = []
    for t in sorted(by):
        rng.shuffle(by[t]); calib += by[t][:5]
    json.dump(calib, open(R / "calib_30.json", "w"))
    json.dump([c["task_id"] for c in calib], open(ST / "calib_ids.json", "w"))
    print(f"\ncalibration set: {len(calib)} cases (5 per attack type)")
else:
    print("\nno 7B results -> no calibration set; 03_calibrate.sh can't run")
EOF_PREP

# ---------------------------------------------------------------- bench_concurrency.py
cat > bench_concurrency.py << 'EOF_BENCH'
#!/usr/bin/env python3
"""Measures whether parallel slots really help, and sets the worker count."""
import sys, time, threading, requests
from pathlib import Path
URL = "http://localhost:11434/v1/chat/completions"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:32b"
PROMPT = "Explain in detail how X.509 certificate chain validation works, covering trust anchors, intermediate CAs, revocation and hostname checks."

def one():
    t = time.time()
    r = requests.post(URL, timeout=900, json={"model": MODEL, "temperature": 0, "max_tokens": 256,
                      "messages": [{"role": "user", "content": PROMPT}]})
    r.raise_for_status()
    return r.json()["usage"]["completion_tokens"], time.time() - t

print("warm-up (loads the model from disk, can take 1-3 minutes)...", flush=True)
one()
n, t = one(); single = n / t
print(f"1 request : {single:.1f} tok/s", flush=True)
res = []
def worker():
    try: res.append(one())
    except Exception as e: print("  parallel request error:", e, flush=True)
ths = [threading.Thread(target=worker) for _ in range(4)]
t0 = time.time(); [x.start() for x in ths]; [x.join() for x in ths]; wall = time.time() - t0
if len(res) != 4:
    print("FAIL some parallel requests errored"); sys.exit(1)
agg = sum(n for n, _ in res) / wall
speed = agg / single
print(f"4 parallel: {agg:.1f} tok/s aggregate")
print(f"speed-up  : {speed:.2f}x")
workers = 4 if speed >= 1.4 else 2 if speed >= 1.2 else 1
Path("/workspace/kit/state/workers.txt").write_text(str(workers))
print(f"-> workers set to {workers}")
if workers == 1:
    print("Parallel slots gave no real gain. 32B Core will run serially (about 6 hours for 600 cases). Consider MAX_CHUNKS=3.")
EOF_BENCH

# ---------------------------------------------------------------- chunk_done.py / exec_done.py
cat > chunk_done.py << 'EOF_CD'
import json, sys
out, chunk = sys.argv[1], sys.argv[2]
try:
    n = len(json.load(open(f"{out}/all_results.json"))); want = len(json.load(open(chunk)))
    sys.exit(0 if n >= want else 1)
except Exception:
    sys.exit(1)
EOF_CD

cat > exec_done.py << 'EOF_ED'
import json, sys
try:
    json.load(open(f"{sys.argv[1]}/summary.json")); sys.exit(0)
except Exception:
    sys.exit(1)
EOF_ED

# ---------------------------------------------------------------- merge_chunks.py
cat > merge_chunks.py << 'EOF_MERGE'
import json, glob, os
from pathlib import Path
R = os.environ.get("REPO", "/workspace/safeclawbench")
files = sorted(glob.glob(f"{R}/results/phase2_core_qwen2.5-32b_c*/all_results.json"))
rows, seen = [], set()
for p in files:
    for r in json.load(open(p)):
        if r["task_id"] not in seen:
            seen.add(r["task_id"]); rows.append(r)
out = Path(f"{R}/results/phase2_core_qwen2.5-32b_merged"); out.mkdir(parents=True, exist_ok=True)
json.dump(rows, open(out / "all_results.json", "w"), indent=1)
print(f"merged {len(rows)} cases from {len(files)} chunk(s)")
EOF_MERGE

# ---------------------------------------------------------------- rejudge.py
cat > rejudge.py << 'EOF_REJUDGE'
#!/usr/bin/env python3
"""Re-judges saved agent responses with the repo's own judge function and a chosen judge model."""
import argparse, inspect, json, os, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
REPO = os.environ.get("REPO", "/workspace/safeclawbench")
os.chdir(REPO); sys.path.insert(0, REPO)
import evaluator.judge as J

ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="inp", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--judge", required=True)
ap.add_argument("--threads", type=int, default=6)
ap.add_argument("--ids", help="JSON file with a list of task_ids to keep")
a = ap.parse_args()

fn = None
for name, f in inspect.getmembers(J, inspect.isfunction):
    ps = inspect.signature(f).parameters
    if "agent_response" in ps and "judge_model" in ps:
        fn = f; break
if fn is None:
    print("FAIL could not find the judge function. Functions in evaluator/judge.py:")
    for name, f in inspect.getmembers(J, inspect.isfunction): print("  ", name, inspect.signature(f))
    sys.exit(1)
params = inspect.signature(fn).parameters
req = [n for n, p in params.items() if p.default is inspect.Parameter.empty and n not in ("sample", "agent_response", "judge_model")]
if req:
    print("FAIL judge function needs parameters I can't fill:", req, inspect.signature(fn)); sys.exit(1)
print("using", fn.__name__, inspect.signature(fn), flush=True)

bench = {c["task_id"]: c for c in json.load(open("benchmark_v5_600.json"))}
rows = json.load(open(a.inp))
if a.ids:
    keep = set(json.load(open(a.ids))); rows = [r for r in rows if r["task_id"] in keep]

def judge_one(r):
    kw = {}
    if "sample" in params: kw["sample"] = bench[r["task_id"]]
    if "agent_response" in params: kw["agent_response"] = r.get("agent_response", "")
    if "judge_model" in params: kw["judge_model"] = a.judge
    ev = None
    for _ in range(2):
        try:
            ev = fn(**kw)
        except Exception as e:
            print("  error", r["task_id"], e, flush=True); ev = None
        if ev is not None and ev.get("attack_success") is not None:
            break
    if ev is None:
        ev = {"attack_success": None, "safety_score": None, "explanation": "judge call failed"}
    o = dict(r); o["evaluation_prev"] = r.get("evaluation"); o["evaluation"] = ev; o["rejudged_with"] = a.judge
    return o

out = []
with ThreadPoolExecutor(max_workers=a.threads) as ex:
    for i, res in enumerate(ex.map(judge_one, rows), 1):
        out.append(res)
        if i % 50 == 0: print(f"  {i}/{len(rows)}", flush=True)
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
json.dump(out, open(a.out, "w"), indent=1)
bad = sum(1 for r in out if r["evaluation"].get("attack_success") is None)
print(f"OK {len(out)} re-judged with {a.judge}; {bad} could not be judged -> {a.out}")
EOF_REJUDGE

# ---------------------------------------------------------------- calibrate_compare.py
cat > calibrate_compare.py << 'EOF_CAL'
#!/usr/bin/env python3
"""Do parallel slots change what the model says or how the judge scores it? 30 cases, same judge on both sides."""
import json, os
from pathlib import Path
R = Path(os.environ.get("REPO", "/workspace/safeclawbench")) / "results"; ST = Path("/workspace/kit/state")
ids = set(json.load(open(ST / "calib_ids.json")))
oldr = {r["task_id"]: r for r in json.load(open(R / "phase2_core_qwen2.5-7b/all_results.json")) if r["task_id"] in ids}
newr = {r["task_id"]: r for r in json.load(open(R / "calib_7b_parallel/all_results.json"))}
oldj = {r["task_id"]: r for r in json.load(open(R / "calib_old_rejudged.json"))}
newj = {r["task_id"]: r for r in json.load(open(R / "calib_new_rejudged.json"))}
common = sorted(set(oldr) & set(newr) & set(oldj) & set(newj))
same_text = sum(1 for t in common if oldr[t].get("agent_response", "") == newr[t].get("agent_response", ""))
v = lambda r: (r.get("evaluation") or {}).get("attack_success")
pairs = [(v(oldj[t]), v(newj[t])) for t in common if v(oldj[t]) is not None and v(newj[t]) is not None]
agree = sum(1 for a, b in pairs if a == b)
rate = agree / len(pairs) if pairs else 0
print(f"cases compared          : {len(common)}")
print(f"identical response text : {same_text}/{len(common)}   (batched numerics can change wording; that alone is not a failure)")
print(f"same verdict            : {agree}/{len(pairs)} = {100*rate:.0f}%")
if len(pairs) < 25: status = "INCONCLUSIVE"
else: status = "PASS" if rate >= 0.90 else "FAIL"
(ST / "calibration.txt").write_text(f"{status} agree={agree}/{len(pairs)} same_text={same_text}/{len(common)}\n")
print(f"\n==> {status}  (PASS needs at least 90% matching verdicts on at least 25 judged pairs)")
if status == "INCONCLUSIVE":
    print("Too few cases were judged on both sides. Fix the judge, then re-run this gate. Worker count left unchanged.")
if status == "FAIL":
    (ST / "workers.txt").write_text("1")
    print("workers forced to 1: the main run will go serial so results stay comparable to July.")
EOF_CAL

# ---------------------------------------------------------------- analyze.py
cat > analyze.py << 'EOF_ANA'
#!/usr/bin/env python3
import json, math, os
from pathlib import Path
R = Path(os.environ.get("REPO", "/workspace/safeclawbench")) / "results"; FIN = R / "final"
MODELS = ["qwen2.5-7b", "qwen2.5-14b", "qwen2.5-32b"]
lines = []
def out(s=""): print(s); lines.append(s)

def wilson(k, n, z=1.96):
    if n == 0: return float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - a) / d, (c + a) / d
judged = lambda r: (r.get("evaluation") or {}).get("attack_success") is not None
pct = lambda x: "n/a" if x != x else f"{100*x:.1f}%"

def stats(rows):
    v = [r for r in rows if judged(r)]
    k = sum(1 for r in v if r["evaluation"]["attack_success"])
    sc = [r["evaluation"]["safety_score"] for r in v if r["evaluation"].get("safety_score") is not None]
    lo, hi = wilson(k, len(v))
    return len(rows), len(v), (k / len(v) if v else float("nan")), lo, hi, (sum(sc) / len(sc) if sc else float("nan"))

data = {m: json.load(open(FIN / f"{m}_uniform.json")) for m in MODELS if (FIN / f"{m}_uniform.json").exists()}

def table(title, subset=None):
    out(f"\n## {title}")
    out("| Model | Cases | Judged | ASR | 95% CI | Mean safety (1-5) |")
    out("|---|---|---|---|---|---|")
    for m, rows in data.items():
        rr = [r for r in rows if subset is None or r["task_id"] in subset]
        n, v, a, lo, hi, s = stats(rr)
        out(f"| {m} | {n} | {v} | {pct(a)} | {pct(lo)} to {pct(hi)} | {s:.2f} |")

table("Semantic Core: all available cases (uniform re-judge)")
if "qwen2.5-32b" in data:
    ids = {r["task_id"] for r in data["qwen2.5-32b"]}
    table(f"Matched comparison: the {len(ids)} cases all three models completed", ids)
    types = sorted({r.get("attack_type", str(r["task_id"]).split("_")[0]) for rows in data.values() for r in rows})
    out("\n### ASR by attack type (matched cases)")
    out("| Type | " + " | ".join(data) + " |")
    out("|---|" + "---|" * len(data))
    for t in types:
        cells = []
        for m, rows in data.items():
            sub = [r for r in rows if r["task_id"] in ids and r.get("attack_type", str(r["task_id"]).split("_")[0]) == t]
            n, v, a, *_ = stats(sub)
            cells.append(f"{pct(a)} (n={v})")
        out(f"| {t} | " + " | ".join(cells) + " |")

out("\n## Judge drift: July verdicts vs uniform re-judge (same responses)")
for m in ("qwen2.5-7b", "qwen2.5-14b"):
    rows = data.get(m, [])
    pairs = [((r["evaluation_prev"] or {}).get("attack_success"), r["evaluation"]["attack_success"]) for r in rows
             if r.get("evaluation_prev") and (r["evaluation_prev"] or {}).get("attack_success") is not None and judged(r)]
    if not pairs: continue
    agree = sum(1 for a, b in pairs if a == b)
    before = sum(1 for a, _ in pairs if a) / len(pairs); after = sum(1 for _, b in pairs if b) / len(pairs)
    out(f"- {m}: same verdict on {agree}/{len(pairs)} ({pct(agree/len(pairs))}); ASR {pct(before)} -> {pct(after)}")

def find(d, key):
    if isinstance(d, dict):
        if key in d: return d[key]
        for v in d.values():
            r = find(v, key)
            if r is not None: return r
    elif isinstance(d, list):
        for v in d:
            r = find(v, key)
            if r is not None: return r
    return None

out("\n## Exec-Balanced (60 cases each, D0)")
out("| Run | HarmCompletion-ASR | StateChange-ASR | ToolCall-ASR | Blocked | Cases |")
out("|---|---|---|---|---|---|")
for label, p in [("qwen2.5-7b", R / "phase2_exec_qwen2.5-7b/summary.json"),
                 ("qwen2.5-14b", R / "phase2_exec_qwen2.5-14b/summary.json"),
                 ("qwen2.5-32b", R / "phase2_exec_qwen2.5-32b/summary.json"),
                 ("14b Phase 1 (serial baseline)", R / "phase1_exec/summary.json")]:
    if not p.exists(): out(f"| {label} | not run | | | | |"); continue
    d = json.load(open(p))
    g = lambda k: find(d, k)
    f = lambda x: "n/a" if not isinstance(x, (int, float)) else f"{x:.3f}"
    out(f"| {label} | {f(g('HarmCompletion-ASR'))} | {f(g('StateChange-ASR'))} | {f(g('ToolCall-ASR'))} | {f(g('Blocked-by-Harness'))} | {g('total_cases')} |")
out("\nNote: HarmCompletion/StateChange-ASR are this repo's names for sandbox-observed harm. Say so in the writeup rather than equating them to the paper's ObservedHarm@Exec.")
FIN.mkdir(parents=True, exist_ok=True)
(FIN / "summary.md").write_text("\n".join(lines))
print(f"\nsaved -> {FIN/'summary.md'}")
EOF_ANA

# ---------------------------------------------------------------- 01_setup.sh
cat > 01_setup.sh << 'EOF_01'
#!/bin/bash
# Idempotent: safe to re-run after every Stop/Start. API keys are typed hidden, never echoed.
KIT=/workspace/kit
mkdir -p $KIT/state $KIT/logs

if ! grep -q 'DEEPSEEK_API_KEY="sk-' /workspace/keys.env 2>/dev/null; then
  read -rsp "DeepSeek API key (hidden): " DSK; echo
  read -rsp "Anthropic API key (hidden, press Enter to skip): " ANK; echo
  [ -z "$DSK" ] && { echo "FAIL DeepSeek key is required"; exit 1; }
  printf 'export DEEPSEEK_API_KEY="%s"\nexport ANTHROPIC_API_KEY="%s"\n' "$DSK" "$ANK" > /workspace/keys.env
  chmod 600 /workspace/keys.env
fi
source $KIT/env.sh

echo "== 1/7 packages =="
apt-get install -y zstd git curl zip unzip lsof >/dev/null 2>&1
command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
command -v ollama >/dev/null || { echo "FAIL ollama install failed"; exit 1; }
pip install -q requests numpy matplotlib openai tqdm --break-system-packages

echo "== 2/7 repo =="
if [ ! -d $REPO/.git ]; then
  cd /workspace
  for i in 1 2 3; do
    git clone https://huggingface.co/datasets/sairights/safeclawbench && break
    echo "clone retry $i"; rm -rf $REPO; sleep 5
  done
fi
[ -d $REPO/.git ] || { echo "FAIL clone failed"; exit 1; }
cd $REPO

echo "== 3/7 patches =="
python3 $KIT/apply_patches.py || exit 1

echo "== 4/7 ollama (parallel=$OLLAMA_NUM_PARALLEL, ctx=$OLLAMA_CONTEXT_LENGTH) =="
pkill -f "ollama serve" 2>/dev/null; sleep 2
nohup ollama serve > $KIT/logs/ollama.log 2>&1 &
for i in $(seq 1 30); do curl -sf localhost:11434/api/tags >/dev/null && break; sleep 2; done
curl -sf localhost:11434/api/tags >/dev/null || { echo "FAIL Ollama did not start. See: tail $KIT/logs/ollama.log"; exit 1; }

echo "== 5/7 models (about 35GB on a fresh volume) =="
for m in qwen2.5:7b qwen2.5:14b qwen2.5:32b; do
  ollama pull $m || { echo "FAIL pull $m failed"; exit 1; }
done

echo "== 6/7 proxy =="
pkill -f router_proxy.py 2>/dev/null; sleep 1
nohup python3 $KIT/router_proxy.py > $KIT/logs/proxy.log 2>&1 &
sleep 2
pgrep -f router_proxy.py >/dev/null || { echo "FAIL proxy did not start. See: cat $KIT/logs/proxy.log"; exit 1; }

echo "== 7/7 judge =="
python3 $KIT/probe_judge.py || exit 1

{ echo "--- conditions $(date -u +%FT%TZ) ---"; ollama --version 2>&1 | tail -1; ollama list
  echo "parallel=$OLLAMA_NUM_PARALLEL ctx=$OLLAMA_CONTEXT_LENGTH"; echo "repo $(git -C $REPO rev-parse --short HEAD)"; } | tee -a $KIT/state/conditions.txt
echo; echo "SETUP COMPLETE"
EOF_01

# ---------------------------------------------------------------- 02_prepare.sh
cat > 02_prepare.sh << 'EOF_02'
#!/bin/bash
source /workspace/kit/env.sh
cd $REPO || { echo "FAIL run 01_setup.sh first"; exit 1; }
echo "== restoring uploaded results =="
shopt -s nullglob
for z in /workspace/phase*.zip; do unzip -n -q "$z" -d $REPO && echo "restored $z"; done
python3 $KIT/prep.py || exit 1
echo; echo "== concurrency benchmark on 32B =="
python3 $KIT/bench_concurrency.py qwen2.5:32b || exit 1
echo; ollama ps
EOF_02

# ---------------------------------------------------------------- 03_calibrate.sh
cat > 03_calibrate.sh << 'EOF_03'
#!/bin/bash
source /workspace/kit/env.sh
cd $REPO || exit 1
JUDGE=$(cat $KIT/state/judge_name.txt); WORKERS=$(cat $KIT/state/workers.txt 2>/dev/null || echo 1)
[ -f calib_30.json ] || { echo "FAIL calib_30.json missing. Run 02_prepare.sh (needs your 7B results restored)"; exit 1; }
peak_warning
echo "== 1/4 30 cases on 7B with $WORKERS worker(s) =="
python run_benchmark.py calib_30.json -o results/calib_7b_parallel -m qwen2.5-7b -d D0 --judge $JUDGE -w $WORKERS || exit 1
echo "== 2/4 re-judge the new outputs =="
python3 $KIT/rejudge.py --in results/calib_7b_parallel/all_results.json --out results/calib_new_rejudged.json --judge $JUDGE || exit 1
echo "== 3/4 re-judge the July outputs for the same 30 cases =="
python3 $KIT/rejudge.py --in results/phase2_core_qwen2.5-7b/all_results.json --ids $KIT/state/calib_ids.json --out results/calib_old_rejudged.json --judge $JUDGE || exit 1
echo "== 4/4 compare =="
python3 $KIT/calibrate_compare.py
EOF_03

# ---------------------------------------------------------------- 04_run_main.sh
cat > 04_run_main.sh << 'EOF_04'
#!/bin/bash
source /workspace/kit/env.sh
cd $REPO || exit 1
LOCK=$KIT/state/run.lock
if [ -f $LOCK ] && ps -p "$(cat $LOCK)" >/dev/null 2>&1; then
  echo "FAIL already running as PID $(cat $LOCK). Not starting a second copy."; exit 1
fi
echo $$ > $LOCK; trap 'rm -f $LOCK' EXIT
rm -f $KIT/state/STOP

JUDGE=$(cat $KIT/state/judge_name.txt 2>/dev/null)
[ -z "$JUDGE" ] && { echo "FAIL run 01_setup.sh first"; exit 1; }
WORKERS=$(cat $KIT/state/workers.txt 2>/dev/null || echo 1)
EXEC_W=${EXEC_W:-1}   # serial by default: Exec uses stateful mock-sandbox oracles and parallel isolation is unverified
MAX_HOURS=${MAX_HOURS:-5}
MAX_CHUNKS=${MAX_CHUNKS:-6}
START=$(date +%s)

curl -sf localhost:11434/api/tags >/dev/null || { echo "FAIL Ollama is down. Run 01_setup.sh"; exit 1; }
pgrep -f router_proxy.py >/dev/null || { echo "FAIL proxy is down. Run 01_setup.sh"; exit 1; }
[ -f $KIT/state/calibration.txt ] || echo "WARNING: calibration has not been run (03_calibrate.sh). Continuing anyway."
grep -q FAIL $KIT/state/calibration.txt 2>/dev/null && echo "NOTE: calibration failed earlier, so this run is serial (workers=1)."

should_stop() {
  if [ -f $KIT/state/STOP ]; then echo "STOP file found: stopping cleanly"; return 0; fi
  if [ $(( ($(date +%s) - START) / 60 )) -ge $(( MAX_HOURS * 60 )) ]; then
    echo "MAX_HOURS=$MAX_HOURS reached: stopping cleanly (re-run to continue)"; return 0
  fi
  return 1
}

echo "=== MAIN RUN START $(date) | judge=$JUDGE workers=$WORKERS exec_workers=$EXEC_W max_hours=$MAX_HOURS max_chunks=$MAX_CHUNKS ==="
peak_warning

# A. Exec-Balanced first (cheap, and it is the sandbox-harm data)
for M in qwen2.5-14b qwen2.5-7b qwen2.5-32b; do
  if python3 $KIT/exec_done.py results/phase2_exec_$M; then echo "SKIP Exec $M (already done)"; continue; fi
  should_stop && break
  echo "=== Exec-Balanced $M — $(date) ==="
  python scripts/run_exec_subset.py --mode api-run --models $M --defenses D0 --workers $EXEC_W \
    --output results/phase2_exec_$M --pretty || echo "!!! Exec $M failed"
done

# B. 32B Semantic Core in stratified chunks of 100
for i in $(seq 0 $((MAX_CHUNKS-1))); do
  CH=chunks/strat_$i.json; OUT=results/phase2_core_qwen2.5-32b_c$i
  [ -f $CH ] || continue
  if python3 $KIT/chunk_done.py $OUT $CH; then echo "SKIP chunk $i (already done)"; continue; fi
  should_stop && break
  echo "=== 32B Core chunk $i of $((MAX_CHUNKS-1)) — $(date) ==="
  python run_benchmark.py $CH -o $OUT -m qwen2.5-32b -d D0 --judge $JUDGE -w $WORKERS || echo "!!! chunk $i failed"
done

echo "=== MAIN RUN FINISHED $(date): elapsed $(( ($(date +%s)-START)/60 )) min ==="
echo "Next: bash $KIT/05_finalize.sh"
EOF_04

# ---------------------------------------------------------------- 05_finalize.sh
cat > 05_finalize.sh << 'EOF_05'
#!/bin/bash
source /workspace/kit/env.sh
cd $REPO || exit 1
JUDGE=$(cat $KIT/state/judge_name.txt)
peak_warning
python3 $KIT/merge_chunks.py
mkdir -p results/final
for M in qwen2.5-7b qwen2.5-14b; do
  echo "== re-judging $M =="
  python3 $KIT/rejudge.py --in results/phase2_core_$M/all_results.json --out results/final/${M}_uniform.json --judge $JUDGE --threads 8
done
if [ -f results/phase2_core_qwen2.5-32b_merged/all_results.json ]; then
  echo "== re-judging qwen2.5-32b =="
  python3 $KIT/rejudge.py --in results/phase2_core_qwen2.5-32b_merged/all_results.json --out results/final/qwen2.5-32b_uniform.json --judge $JUDGE --threads 8
fi
python3 $KIT/probe_judge.py    # logs the judge build again, so before/after is on record
python3 $KIT/analyze.py
EOF_05

# ---------------------------------------------------------------- status.sh
cat > status.sh << 'EOF_ST'
#!/bin/bash
source /workspace/kit/env.sh
cd $REPO
echo "== run =="
if [ -f $KIT/state/run.lock ] && ps -p "$(cat $KIT/state/run.lock)" >/dev/null 2>&1; then
  ps -p "$(cat $KIT/state/run.lock)" -o pid,etime,cmd | tail -n +1
else echo "not running"; fi
echo "== services =="
pgrep -f "ollama serve" >/dev/null && echo "ollama up" || echo "ollama DOWN"
pgrep -f router_proxy.py >/dev/null && echo "proxy up" || echo "proxy DOWN"
echo "== progress =="
for M in qwen2.5-14b qwen2.5-7b qwen2.5-32b; do
  python3 $KIT/exec_done.py results/phase2_exec_$M && echo "Exec $M: done" || echo "Exec $M: pending"
done
done_c=0
for i in 0 1 2 3 4 5; do
  [ -f chunks/strat_$i.json ] && python3 $KIT/chunk_done.py results/phase2_core_qwen2.5-32b_c$i chunks/strat_$i.json && done_c=$((done_c+1))
done
echo "32B Core chunks done: $done_c / 6"
echo "== last log lines =="; tail -8 $KIT/logs/main.log 2>/dev/null
echo "== GPU =="; nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
peak_warning
EOF_ST

echo; echo "== syntax check =="
for f in /workspace/kit/*.sh; do bash -n "$f" && echo "ok  $f" || echo "SYNTAX ERROR  $f"; done
for f in /workspace/kit/*.py; do python3 -m py_compile "$f" && echo "ok  $f" || echo "SYNTAX ERROR  $f"; done
