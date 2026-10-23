#!/usr/bin/env python3
"""Validate the DeepSeek judge against Claude Haiku on a stratified subset (same cases for every model)."""
import collections, json, math, os, random, subprocess, sys, requests
REPO = os.environ.get("REPO", "/workspace/safeclawbench"); KIT = "/workspace/kit"
os.chdir(REPO)
PER_TYPE = int(os.environ.get("PER_TYPE", 20)); HAIKU = "claude-haiku-4.5"
MODELS = ["qwen2.5-7b", "qwen2.5-14b", "qwen2.5-32b"]

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit("FAIL no ANTHROPIC_API_KEY in /workspace/keys.env (01_setup.sh's second prompt was skipped). Add it with:\n"
             "  echo 'export ANTHROPIC_API_KEY=\"sk-ant-...\"' >> /workspace/keys.env   then restart the proxy and re-run.")
r = requests.post("http://localhost:8000/v1/messages", timeout=60, json={"model": "claude-haiku-4-5", "max_tokens": 10,
                  "messages": [{"role": "user", "content": "Reply with: ok"}]})
if r.status_code != 200:
    sys.exit(f"FAIL Haiku probe HTTP {r.status_code}: {r.text[:300]}\n(401 = bad key, 400 = credit exhausted, 404 = model id)")
print("Haiku reachable via proxy.")

full = {m: json.load(open(f"results/final/{m}_uniform.json")) for m in MODELS}
types = sorted({r["attack_type"] for r in full[MODELS[0]]})
rng = random.Random(11); ids = []
for t in types:
    pool = sorted(r["task_id"] for r in full[MODELS[0]] if r["attack_type"] == t)
    ids += rng.sample(pool, min(PER_TYPE, len(pool)))
json.dump(ids, open(f"{KIT}/state/haiku_ids.json", "w"))
print(f"{len(ids)} cases x {len(MODELS)} models = {len(ids)*len(MODELS)} Haiku calls (about ${len(ids)*len(MODELS)*0.0018:.2f})", flush=True)

for m in MODELS:
    subprocess.run([sys.executable, f"{KIT}/rejudge.py", "--in", f"results/final/{m}_uniform.json", "--ids", f"{KIT}/state/haiku_ids.json",
                    "--out", f"results/final/haiku_{m}.json", "--judge", HAIKU, "--threads", "8"], check=True)

def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),) * 2
    p = k / n; d = 1 + z*z/n; c = p + z*z/(2*n); a = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)); return (c-a)/d, (c+a)/d
def kappa(pairs):
    n = len(pairs); po = sum(a == b for a, b in pairs) / n
    pa = sum(a for a, _ in pairs) / n; pb = sum(b for _, b in pairs) / n; pe = pa*pb + (1-pa)*(1-pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")
ver = lambda e: (e or {}).get("attack_success")
lines = []
def out(s=""): print(s); lines.append(s)
allpairs = []; bytype = collections.defaultdict(list)
out("## DeepSeek vs Claude Haiku (same 120 cases per model)")
out("| Model | Judged pairs | Agreement | Kappa | ASR DeepSeek | ASR Haiku | DS yes / Haiku no | DS no / Haiku yes |")
out("|---|---|---|---|---|---|---|---|")
for m in MODELS:
    rows = json.load(open(f"results/final/haiku_{m}.json"))
    pr = [(ver(r["evaluation_prev"]), ver(r["evaluation"]), r["attack_type"]) for r in rows
          if ver(r.get("evaluation_prev")) is not None and ver(r.get("evaluation")) is not None]
    p2 = [(a, b) for a, b, _ in pr]; allpairs += p2
    for a, b, t in pr: bytype[t].append((a, b))
    k = sum(a == b for a, b in p2)
    out(f"| {m} | {len(pr)}/{len(rows)} | {100*k/len(pr):.0f}% | {kappa(p2):.2f} | {100*sum(a for a,_ in p2)/len(pr):.0f}% | {100*sum(b for _,b in p2)/len(pr):.0f}% | "
        f"{sum(a and not b for a,b in p2)} | {sum(b and not a for a,b in p2)} |")
k = sum(a == b for a, b in allpairs); lo, hi = wilson(k, len(allpairs))
out(f"\nPooled: {k}/{len(allpairs)} = {100*k/len(allpairs):.1f}% agreement (95% CI {100*lo:.0f}-{100*hi:.0f}%), kappa {kappa(allpairs):.2f}")
out("\nAgreement by attack type (pooled): " + ", ".join(f"{t} {100*sum(a==b for a,b in v)/len(v):.0f}%" for t, v in sorted(bytype.items())))
out("\nIf the Haiku ASR column keeps the same ordering as the DeepSeek column, the scale trend does not depend on the judge.")
open("results/final/haiku_validation.md", "w").write("\n".join(lines))
print("\nsaved -> results/final/haiku_validation.md")
