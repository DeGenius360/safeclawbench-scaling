#!/bin/bash
# SafeClawBench follow-up v2: same-environment, uncapped-response replication on a stratified 120-case subset.
# Run AFTER install_kit.sh and 01_setup.sh. Writes five scripts into /workspace/kit/. Safe to re-run.
mkdir -p /workspace/kit/state /workspace/kit/logs
cd /workspace/kit

# ---------------------------------------------------------------- v2_patch.py
cat > v2_patch.py << 'EOF_P'
#!/usr/bin/env python3
"""Idempotent. Makes the two response caps env-controlled; defaults are unchanged.
SCB_SAVE_CAP : characters of the response saved to results (default 2000)
SCB_JUDGE_CAP: characters of the response shown to the judge (default 3000)"""
import os, sys
from pathlib import Path
R = Path(os.environ.get("REPO", "/workspace/safeclawbench"))

def patch(rel, cap, env, label):
    p = R / rel; s = p.read_text()
    if env in s:
        print(f"OK {label}: already applied"); return
    old = f"agent_response[:{cap}]"
    n = s.count(old)
    if n == 0:
        print(f"FAIL {label}: '{old}' not found in {rel}. Lines mentioning {cap}:")
        os.system(f'grep -n "{cap}" "{p}"'); sys.exit(1)
    new = f'agent_response[:int(__import__("os").environ.get("{env}", {cap}))]'
    p.write_text(s.replace(old, new))
    print(f"OK {label}: applied ({n} occurrence(s))")

patch("run_benchmark.py", 2000, "SCB_SAVE_CAP", "saved-response cap")
patch("evaluator/judge.py", 3000, "SCB_JUDGE_CAP", "judge-input cap")
for rel in ("run_benchmark.py", "evaluator/judge.py"):
    if os.system(f'python3 -m py_compile "{R / rel}"') != 0:
        print(f"FAIL {rel} no longer compiles after patching"); sys.exit(1)
print("OK both files compile")
EOF_P

# ---------------------------------------------------------------- v2_make_subset.py
cat > v2_make_subset.py << 'EOF_S'
#!/usr/bin/env python3
"""Deterministic stratified subset: 20 cases per attack family, fixed seed.
Usage: python3 v2_make_subset.py <benchmark_v5_600.json> <out_dir>   (works locally too: standard library only)"""
import hashlib, json, os, random, sys
from collections import Counter, defaultdict
bench = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
SEED, PER_TYPE = 2026, 20
atype = lambda c: c.get("attack_type") or str(c["task_id"]).split("_")[0]
by = defaultdict(list)
for c in bench: by[atype(c)].append(c)
rng = random.Random(SEED); chosen = []
for t in sorted(by):
    pool = sorted(by[t], key=lambda c: c["task_id"])
    chosen += rng.sample(pool, min(PER_TYPE, len(pool)))
ids = [c["task_id"] for c in chosen]
json.dump(chosen, open(os.path.join(out, "v2_subset.json"), "w"))
json.dump(ids, open(os.path.join(out, "v2_subset_ids.json"), "w"), indent=0)
print(f"{len(chosen)} cases", dict(Counter(atype(c) for c in chosen)))
print("seed", SEED, "| sha256 of the sorted id list:", hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest())
EOF_S

# ---------------------------------------------------------------- v2_judge.py
cat > v2_judge.py << 'EOF_J'
#!/usr/bin/env python3
"""Judge every regenerated response with both judges on the FULL text and, if it is longer than 2000 chars,
also on its first 2000 chars. Resumable (judge_cache.json) and guarded by a Haiku budget."""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
REPO = os.environ.get("REPO", "/workspace/safeclawbench"); KIT = "/workspace/kit"
os.chdir(REPO); sys.path.insert(0, REPO)
os.environ["SCB_JUDGE_CAP"] = "20000"          # the judge must see the whole response
import evaluator.judge as J
MODELS = ["qwen2.5-7b", "qwen2.5-14b", "qwen2.5-32b"]; CAP = 2000; HK = "claude-haiku-4.5"
DS = open(f"{KIT}/state/judge_name.txt").read().strip()
BUDGET = float(os.environ.get("HAIKU_BUDGET", "1.5")); PER_CALL = 0.0025       # rough $ per Haiku call on full-length text
os.makedirs("results/v2", exist_ok=True); cache_p = "results/v2/judge_cache.json"
cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
bench = {c["task_id"]: c for c in json.load(open("benchmark_v5_600.json"))}

jobs = []
for m in MODELS:
    for r in json.load(open(f"results/v2_gen_{m}/all_results.json")):
        text = r.get("agent_response", "")
        for judge in (DS, HK):
            for cond, t in (("full", text), ("cap", text[:CAP])):
                if cond == "cap" and len(text) <= CAP: continue
                key = f"{m}|{r['task_id']}|{judge}|{cond}"
                if (cache.get(key) or {}).get("attack_success") is None: jobs.append((key, r["task_id"], judge, t))
hk_calls = sum(1 for j in jobs if j[2] == HK)
print(f"{len(jobs)} judge calls to make ({hk_calls} Haiku, about ${hk_calls*PER_CALL:.2f}; budget guard ${BUDGET:.2f})", flush=True)
if hk_calls * PER_CALL > BUDGET:
    sys.exit(f"STOP: estimated Haiku cost exceeds the guard. Raise it with HAIKU_BUDGET=<dollars> if you accept that.")

KEEP = ("attack_success", "safety_score", "harm_type_actual", "defense_behavior", "harm_evidence_category", "explanation")
def run(job):
    key, tid, judge, t = job; ev = None
    for _ in range(2):
        try: ev = J.evaluate_response(sample=bench[tid], agent_response=t, judge_model=judge)
        except Exception as e: print("  error", key, repr(e)[:120], flush=True); ev = None
        if ev is not None and ev.get("attack_success") is not None: break
    return key, ({k: ev.get(k) for k in KEEP} if ev else {"attack_success": None})

with ThreadPoolExecutor(max_workers=8) as ex:
    for i, (key, ev) in enumerate(ex.map(run, jobs), 1):
        cache[key] = ev
        if i % 50 == 0: json.dump(cache, open(cache_p, "w")); print(f"  {i}/{len(jobs)}", flush=True)
json.dump(cache, open(cache_p, "w"))
bad = sum(1 for v in cache.values() if v.get("attack_success") is None)
print(f"OK judging finished; {bad} verdicts missing (re-run this script to retry them)")
EOF_J

# ---------------------------------------------------------------- v2_analyze.py
cat > v2_analyze.py << 'EOF_A'
#!/usr/bin/env python3
import json, math, os
REPO = os.environ.get("REPO", "/workspace/safeclawbench"); KIT = "/workspace/kit"; os.chdir(REPO)
MODELS = ["qwen2.5-7b", "qwen2.5-14b", "qwen2.5-32b"]; CAP = 2000; HK = "claude-haiku-4.5"
DS = open(f"{KIT}/state/judge_name.txt").read().strip()
cache = json.load(open("results/v2/judge_cache.json"))
lines = []
def out(s=""): print(s); lines.append(s)
pct = lambda x: "n/a" if x != x else f"{100*x:.0f}%"
def wilson(k, n, z=1.96):
    if n == 0: return float("nan"), float("nan")
    p = k/n; d = 1 + z*z/n; c = p + z*z/(2*n); a = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)); return (c-a)/d, (c+a)/d
def kappa(pairs):
    if not pairs: return float("nan")
    n = len(pairs); po = sum(a == b for a, b in pairs)/n; pa = sum(a for a, _ in pairs)/n; pb = sum(b for _, b in pairs)/n
    pe = pa*pb + (1-pa)*(1-pb); return (po - pe)/(1 - pe) if pe < 1 else float("nan")
def mcnemar(x, y):
    ids = [t for t in x if t in y and x[t] is not None and y[t] is not None]
    b = sum(bool(x[t]) and not y[t] for t in ids); c = sum(bool(y[t]) and not x[t] for t in ids); n = b + c
    p = 1.0 if n == 0 else min(1.0, 2*sum(math.comb(n, k) for k in range(min(b, c)+1))/2**n)
    return len(ids), b, c, p
def v(m, tid, judge, cond, long):
    c = "cap" if (cond == "cap" and long) else "full"
    return (cache.get(f"{m}|{tid}|{judge}|{c}") or {}).get("attack_success")

rows = {}
for m in MODELS:
    rows[m] = []
    for r in json.load(open(f"results/v2_gen_{m}/all_results.json")):
        text = r.get("agent_response", ""); long = len(text) > CAP; tid = r["task_id"]
        rows[m].append(dict(tid=tid, type=r.get("attack_type") or str(tid).split("_")[0], n=len(text), long=long,
                            ds_full=v(m, tid, DS, "full", long), ds_cap=v(m, tid, DS, "cap", long),
                            hk_full=v(m, tid, HK, "full", long), hk_cap=v(m, tid, HK, "cap", long)))
COLS = [("ds_cap", "DeepSeek, first 2000 chars"), ("hk_cap", "Haiku, first 2000 chars"),
        ("ds_full", "DeepSeek, full text"), ("hk_full", "Haiku, full text")]
asr = lambda rs, k: [r[k] for r in rs if r[k] is not None]

out("## A. Same-environment ASR on the 120-case subset (all three sizes generated today, same build, same settings)")
out("| Model | Cases | Responses > 2000 chars | " + " | ".join(c[1] for c in COLS) + " |")
out("|---|---|---|" + "---|"*len(COLS))
for m in MODELS:
    rs = rows[m]; cells = []
    for k, _ in COLS:
        a = asr(rs, k); lo, hi = wilson(sum(a), len(a)); cells.append(f"{pct(sum(a)/max(len(a),1))} [{pct(lo)}-{pct(hi)}] (n={len(a)})")
    out(f"| {m} | {len(rs)} | {pct(sum(r['long'] for r in rs)/len(rs))} | " + " | ".join(cells) + " |")

out("\n## B. Paired size comparisons on the same cases (exact McNemar; difference = second minus first)")
out("| Verdict column | Pair | Cases | ASR first | ASR second | Difference | p |")
out("|---|---|---|---|---|---|---|")
for k, label in COLS:
    for a, b in (("qwen2.5-7b", "qwen2.5-14b"), ("qwen2.5-14b", "qwen2.5-32b"), ("qwen2.5-7b", "qwen2.5-32b")):
        x = {r["tid"]: r[k] for r in rows[a]}; y = {r["tid"]: r[k] for r in rows[b]}
        n, b1, c1, p = mcnemar(x, y); ids = [t for t in x if t in y and x[t] is not None and y[t] is not None]
        pa = sum(bool(x[t]) for t in ids)/max(n, 1); pb = sum(bool(y[t]) for t in ids)/max(n, 1)
        out(f"| {label} | {a[8:]} vs {b[8:]} | {n} | {pct(pa)} | {pct(pb)} | {100*(pb-pa):+.0f} pts | {p:.3f} |")

out("\n## C. The truncation test: same response, judged on the first 2000 chars vs the full text (responses longer than 2000 chars only)")
out("| Model | Long responses | DeepSeek ASR cap -> full | DS flips (yes->no / no->yes), p | Haiku ASR cap -> full | Haiku flips (yes->no / no->yes), p | DS minus Haiku gap: cap -> full |")
out("|---|---|---|---|---|---|---|")
def trunc_row(label, rs):
    L = [r for r in rs if r["long"] and None not in (r["ds_cap"], r["ds_full"], r["hk_cap"], r["hk_full"])]
    if not L: out(f"| {label} | 0 | | | | | |"); return
    n = len(L); f = lambda k: sum(bool(r[k]) for r in L)/n
    def flips(k1, k2):
        x = {i: L[i][k1] for i in range(n)}; y = {i: L[i][k2] for i in range(n)}; _, b, c, p = mcnemar(x, y); return b, c, p
    d = flips("ds_cap", "ds_full"); h = flips("hk_cap", "hk_full")
    out(f"| {label} | {n} | {pct(f('ds_cap'))} -> {pct(f('ds_full'))} | {d[0]} / {d[1]}, p={d[2]:.3f} | {pct(f('hk_cap'))} -> {pct(f('hk_full'))} | {h[0]} / {h[1]}, p={h[2]:.3f} | "
        f"{100*(f('ds_cap')-f('hk_cap')):+.0f} -> {100*(f('ds_full')-f('hk_full')):+.0f} pts |")
for m in MODELS: trunc_row(m, rows[m])
trunc_row("all three pooled", [r for m in MODELS for r in rows[m]])

out("\n## D. Judge agreement (all cases): first 2000 chars vs full text")
out("| Model | Agreement cap | Kappa cap | Agreement full | Kappa full |")
out("|---|---|---|---|---|")
for m in MODELS + ["pooled"]:
    rs = [r for mm in MODELS for r in rows[mm]] if m == "pooled" else rows[m]
    def ag(a, b):
        pr = [(r[a], r[b]) for r in rs if r[a] is not None and r[b] is not None]
        return (sum(x == y for x, y in pr)/len(pr) if pr else float("nan")), kappa(pr)
    c1, c2 = ag("ds_cap", "hk_cap"), ag("ds_full", "hk_full")
    out(f"| {m} | {pct(c1[0])} | {c1[1]:.2f} | {pct(c2[0])} | {c2[1]:.2f} |")

out("\n## E. Environment check: the same 120 cases as generated earlier (7B/14B in July, 32B in October) vs today, same 2000-char judge view")
out("| Model | Judge | ASR earlier | ASR today | Agreement per case | Share of responses at/over the cap: earlier -> today |")
out("|---|---|---|---|---|---|")
for m in MODELS:
    ids = {r["tid"] for r in rows[m]}
    old_ds = {r["task_id"]: r for r in json.load(open(f"results/final/{m}_uniform.json")) if r["task_id"] in ids}
    old_hk = {r["task_id"]: r for r in json.load(open(f"results/final/haiku_{m}_full.json")) if r["task_id"] in ids} if os.path.exists(f"results/final/haiku_{m}_full.json") else {}
    cap_old = sum(len(r.get("agent_response", "")) >= 1995 for r in old_ds.values())/max(len(old_ds), 1)
    cap_new = sum(r["long"] for r in rows[m])/len(rows[m])
    for label, old, k in (("DeepSeek", old_ds, "ds_cap"), ("Haiku", old_hk, "hk_cap")):
        pr = [((old[r["tid"]].get("evaluation") or {}).get("attack_success"), r[k]) for r in rows[m] if r["tid"] in old]
        pr = [(a, b) for a, b in pr if a is not None and b is not None]
        if not pr: continue
        out(f"| {m} | {label} | {pct(sum(a for a, _ in pr)/len(pr))} | {pct(sum(b for _, b in pr)/len(pr))} | {pct(sum(a == b for a, b in pr)/len(pr))} (n={len(pr)}) | {pct(cap_old)} -> {pct(cap_new)} |")

open("results/v2/summary.md", "w").write("\n".join(lines))
json.dump({m: rows[m] for m in MODELS}, open("results/v2/per_case.json", "w"), indent=1)
print("\nsaved -> results/v2/summary.md and results/v2/per_case.json")
EOF_A

# ---------------------------------------------------------------- v2_all.sh
cat > v2_all.sh << 'EOF_ALL'
#!/bin/bash
# One command for the whole follow-up. Resumable: re-run it after any interruption.
source /workspace/kit/env.sh
cd $REPO || { echo "FAIL run 01_setup.sh first"; exit 1; }
KIT=/workspace/kit; MODELS="qwen2.5-7b qwen2.5-14b qwen2.5-32b"
[ -f $KIT/state/judge_name.txt ] || { echo "FAIL run 01_setup.sh first (judge not probed)"; exit 1; }
pgrep -f router_proxy.py >/dev/null || { echo "FAIL proxy is down: run 01_setup.sh"; exit 1; }

mkdir -p results/v2
{ echo "date: $(date -u)"; echo "ollama: $(ollama --version 2>&1 | tail -1)"; echo "gpu: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1 | head -1)"
  echo "OLLAMA_NUM_PARALLEL=$OLLAMA_NUM_PARALLEL OLLAMA_CONTEXT_LENGTH=$OLLAMA_CONTEXT_LENGTH"; } > results/v2/conditions.txt
cat results/v2/conditions.txt
echo "== 1/6 restore earlier results (results/final only) =="
shopt -s nullglob
for z in /workspace/phase2_final_v3_*.zip; do unzip -n -q "$z" 'results/final/*' -d $REPO && echo "restored from $z"; done
[ -f results/final/qwen2.5-7b_uniform.json ] || { echo "FAIL results/final/*_uniform.json missing: upload phase2_final_v3_*.zip to /workspace"; exit 1; }

echo "== 2/6 patches =="
python3 $KIT/apply_patches.py || exit 1
python3 $KIT/v2_patch.py || exit 1

echo "== 3/6 subset =="
python3 $KIT/v2_make_subset.py benchmark_v5_600.json chunks || exit 1

echo "== 4/6 generation: full-length responses saved =="
export SCB_SAVE_CAP=20000 SCB_JUDGE_CAP=20000
JUDGE=$(cat $KIT/state/judge_name.txt); peak_warning
for M in $MODELS; do
  OUT=results/v2_gen_$M
  if python3 $KIT/chunk_done.py $OUT chunks/v2_subset.json; then echo "SKIP $M (already generated)"; continue; fi
  echo "=== $M — $(date) ==="
  python run_benchmark.py chunks/v2_subset.json -o $OUT -m $M -d D0 --judge $JUDGE -w 4 || echo "!!! $M failed"
done
for M in $MODELS; do python3 $KIT/chunk_done.py results/v2_gen_$M chunks/v2_subset.json || { echo "FAIL generation incomplete for $M: re-run this script"; exit 1; }; done

echo "== 5/6 judging (both judges, full text and first 2000 chars) =="
python3 $KIT/v2_judge.py || exit 1

echo "== 6/6 analysis =="
python3 $KIT/v2_analyze.py
echo; echo "DONE. Zip results/v2 and results/v2_gen_* and download them, then Terminate the pod."
EOF_ALL

echo; echo "== syntax check =="
for f in /workspace/kit/v2_*.sh; do bash -n "$f" && echo "ok  $f" || echo "SYNTAX ERROR  $f"; done
for f in /workspace/kit/v2_*.py; do python3 -m py_compile "$f" && echo "ok  $f" || echo "SYNTAX ERROR  $f"; done
