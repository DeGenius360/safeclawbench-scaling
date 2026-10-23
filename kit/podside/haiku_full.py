#!/usr/bin/env python3
"""Extend the Haiku validation to (up to) all 600 cases per model, reusing verdicts already paid for."""
import collections, json, math, os, random, subprocess, sys, requests
REPO = os.environ.get("REPO", "/workspace/safeclawbench"); KIT = "/workspace/kit"
os.chdir(REPO)
PER_TYPE = int(os.environ.get("HAIKU_PER_TYPE", 100)); HAIKU = "claude-haiku-4.5"
MODELS = ["qwen2.5-7b", "qwen2.5-14b", "qwen2.5-32b"]
ver = lambda e: (e or {}).get("attack_success")

if not os.environ.get("ANTHROPIC_API_KEY"): sys.exit("FAIL no ANTHROPIC_API_KEY (source /workspace/kit/env.sh first)")
r = requests.post("http://localhost:8000/v1/messages", timeout=60, json={"model": "claude-haiku-4-5", "max_tokens": 10,
                  "messages": [{"role": "user", "content": "Reply with: ok"}]})
if r.status_code != 200: sys.exit(f"FAIL Haiku probe HTTP {r.status_code}: {r.text[:300]}")

uni = {m: json.load(open(f"results/final/{m}_uniform.json")) for m in MODELS}
def prev(m):
    p = f"results/final/haiku_{m}_full.json"
    if not os.path.exists(p): p = f"results/final/haiku_{m}.json"
    return json.load(open(p)) if os.path.exists(p) else []
have = {m: {r["task_id"] for r in prev(m) if ver(r.get("evaluation")) is not None} for m in MODELS}

types = sorted({r["attack_type"] for r in uni[MODELS[0]]}); rng = random.Random(12); target = []
for t in types:
    pool = sorted(r["task_id"] for r in uni[MODELS[0]] if r["attack_type"] == t)
    keep = [i for i in pool if i in have[MODELS[0]]]
    rest = [i for i in pool if i not in have[MODELS[0]]]; rng.shuffle(rest)
    target += keep + rest[:max(0, PER_TYPE - len(keep))]
new = {m: [i for i in target if i not in have[m]] for m in MODELS}
n_new = sum(len(v) for v in new.values())
print(f"target {len(target)} cases per model; {n_new} new Haiku calls (about ${n_new*0.0018:.2f})", flush=True)

for m in MODELS:
    merged = {r["task_id"]: r for r in prev(m)}
    if new[m]:
        json.dump(new[m], open(f"{KIT}/state/haiku_new_{m}.json", "w"))
        subprocess.run([sys.executable, f"{KIT}/rejudge.py", "--in", f"results/final/{m}_uniform.json", "--ids", f"{KIT}/state/haiku_new_{m}.json",
                        "--out", f"results/final/haiku_{m}_part.json", "--judge", HAIKU, "--threads", "8"], check=True)
        for r in json.load(open(f"results/final/haiku_{m}_part.json")): merged[r["task_id"]] = r
    json.dump(list(merged.values()), open(f"results/final/haiku_{m}_full.json", "w"), indent=1)

def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),) * 2
    p = k/n; d = 1 + z*z/n; c = p + z*z/(2*n); a = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)); return (c-a)/d, (c+a)/d
def kappa(pairs):
    n = len(pairs); po = sum(a == b for a, b in pairs)/n; pa = sum(a for a, _ in pairs)/n; pb = sum(b for _, b in pairs)/n
    pe = pa*pb + (1-pa)*(1-pb); return (po-po*0-pe)/(1-pe) if pe < 1 else float("nan")
def mcnemar(x, y):                       # x, y: {task_id: bool}; exact two-sided p
    ids = [t for t in x if t in y]; b = sum(x[t] and not y[t] for t in ids); c = sum(y[t] and not x[t] for t in ids); n = b + c
    p = 1.0 if n == 0 else min(1.0, 2*sum(math.comb(n, k) for k in range(min(b, c)+1))/2**n)
    return len(ids), b, c, p
pct = lambda x: f"{100*x:.0f}%"
lines = []
def out(s=""): print(s); lines.append(s)

rows = {m: {r["task_id"]: r for r in json.load(open(f"results/final/haiku_{m}_full.json"))} for m in MODELS}
ds = {m: {t: ver(r["evaluation_prev"]) for t, r in rows[m].items() if ver(r.get("evaluation_prev")) is not None and ver(r.get("evaluation")) is not None} for m in MODELS}
hk = {m: {t: ver(r["evaluation"]) for t, r in rows[m].items() if t in ds[m] and ver(r.get("evaluation")) is not None} for m in MODELS}

out("## 1. DeepSeek vs Claude Haiku")
out("| Model | Cases | Agreement | Kappa | ASR DeepSeek [95% CI] | ASR Haiku [95% CI] | DS yes / Haiku no | DS no / Haiku yes |")
out("|---|---|---|---|---|---|---|---|")
allp = []; trunc_dis = []; trunc_all = []
for m in MODELS:
    ids = sorted(hk[m]); pairs = [(ds[m][t], hk[m][t]) for t in ids]; allp += pairs
    kd, kh = sum(a for a, _ in pairs), sum(b for _, b in pairs); n = len(pairs)
    ld, hd = wilson(kd, n); lh, hh = wilson(kh, n)
    out(f"| {m} | {n} | {pct(sum(a==b for a,b in pairs)/n)} | {kappa(pairs):.2f} | {pct(kd/n)} [{pct(ld)}-{pct(hd)}] | {pct(kh/n)} [{pct(lh)}-{pct(hh)}] | "
        f"{sum(a and not b for a,b in pairs)} | {sum(b and not a for a,b in pairs)} |")
    for t in ids:
        L = len(rows[m][t].get("agent_response", "")); trunc_all.append(L >= 1995)
        if ds[m][t] and not hk[m][t]: trunc_dis.append(L >= 1995)
out(f"\nPooled agreement {pct(sum(a==b for a,b in allp)/len(allp))} over {len(allp)} pairs, kappa {kappa(allp):.2f}.")
out(f"Truncation check: {pct(sum(trunc_dis)/max(len(trunc_dis),1))} of the DeepSeek-yes/Haiku-no cases ({len(trunc_dis)}) sit at the ~2000-char cap, vs {pct(sum(trunc_all)/len(trunc_all))} of all cases.")

out("\n## 2. Paired model comparison on the same cases (exact McNemar; ASR difference = second minus first)")
out("| Judge | Pair | Cases | ASR first | ASR second | Difference | p |")
out("|---|---|---|---|---|---|---|")
for jname, d in (("DeepSeek", ds), ("Haiku", hk)):
    for a, b in (("qwen2.5-7b", "qwen2.5-14b"), ("qwen2.5-14b", "qwen2.5-32b"), ("qwen2.5-7b", "qwen2.5-32b")):
        n, x, y, p = mcnemar({t: bool(v) for t, v in d[a].items()}, {t: bool(v) for t, v in d[b].items()})
        ids = [t for t in d[a] if t in d[b]]
        pa, pb = sum(d[a][t] for t in ids)/n, sum(d[b][t] for t in ids)/n
        out(f"| {jname} | {a[8:]} vs {b[8:]} | {n} | {pct(pa)} | {pct(pb)} | {100*(pb-pa):+.0f} pts | {p:.3f} |")

out("\n## 3. ASR by attack type (DeepSeek | Haiku), 7b / 14b / 32b")
out("| Type | DeepSeek | Haiku | Judge agreement |")
out("|---|---|---|---|")
tp = {m: {t: rows[m][t]["attack_type"] for t in hk[m]} for m in MODELS}
for t in types:
    cells = {}
    for jn, d in (("ds", ds), ("hk", hk)):
        cells[jn] = " / ".join(pct(sum(d[m][i] for i in d[m] if tp[m].get(i) == t) / max(1, sum(1 for i in d[m] if tp[m].get(i) == t))) for m in MODELS)
    pr = [(ds[m][i], hk[m][i]) for m in MODELS for i in hk[m] if tp[m][i] == t]
    out(f"| {t} | {cells['ds']} | {cells['hk']} | {pct(sum(a==b for a,b in pr)/len(pr))} (n={len(pr)}) |")
open("results/final/haiku_validation_full.md", "w").write("\n".join(lines))
print("\nsaved -> results/final/haiku_validation_full.md")
