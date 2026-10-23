#!/usr/bin/env python3
"""A: why does the judge return nothing for ~30% of cases?  B: does a SERIAL 7B re-run reproduce July's text?"""
import collections, json, os, random, subprocess, sys, time
REPO = os.environ.get("REPO", "/workspace/safeclawbench")
os.chdir(REPO); sys.path.insert(0, REPO)
import evaluator.judge as J
judge = open("/workspace/kit/state/judge_name.txt").read().strip()
bench = {c["task_id"]: c for c in json.load(open("benchmark_v5_600.json"))}
ok = lambda ev: ev is not None and ev.get("attack_success") is not None

print("##### A. judge failures #####")
rows = json.load(open("results/calib_new_rejudged.json"))
bad = [r for r in rows if not ok(r.get("evaluation"))]
print(f"{len(bad)}/{len(rows)} unjudged. By type: {dict(collections.Counter(r['attack_type'] for r in bad))}")
print("response lengths of the unjudged cases:", sorted(len(r.get('agent_response', '')) for r in bad))

orig = J.call_with_retry
def spy(*a, **k):
    t = time.time(); res = orig(*a, **k)
    print(f"   [{time.time()-t:.1f}s] RAW: {repr(res)[:600]}")
    return res

def run(r):
    try:
        return J.evaluate_response(sample=bench[r["task_id"]], agent_response=r.get("agent_response", ""), judge_model=judge)
    except Exception as e:
        print("   EXCEPTION:", repr(e)[:300]); return None

print("\n-- A1. four failing cases, one at a time, raw judge output shown --")
J.call_with_retry = spy
for r in bad[:4]:
    print(r["task_id"], r["attack_type"]); ev = run(r); print("   ->", "NONE (failed)" if not ok(ev) else "judged OK this time")
J.call_with_retry = orig

print("\n-- A2. ten random cases, one at a time --")
random.seed(3)
sample = random.sample(rows, min(10, len(rows)))
fails = sum(0 if ok(run(r)) else 1 for r in sample)
print(f"serial judge failures: {fails}/{len(sample)}")

print("\n##### B. does a SERIAL re-run reproduce July's text? (6 cases, 7B) #####")
calib = json.load(open("calib_30.json")); seen, six = set(), []
for c in calib:
    t = c.get("attack_type") or str(c["task_id"]).split("_")[0]
    if t not in seen: seen.add(t); six.append(c)
json.dump(six, open("calib_6.json", "w"))
subprocess.run(["python", "run_benchmark.py", "calib_6.json", "-o", "results/calib_7b_serial", "-m", "qwen2.5-7b",
                "-d", "D0", "--judge", judge, "-w", "1"], stdout=subprocess.DEVNULL)
load = lambda p: {r["task_id"]: r.get("agent_response", "") for r in json.load(open(p))}
july = load("results/phase2_core_qwen2.5-7b/all_results.json")
par = load("results/calib_7b_parallel/all_results.json")
ser = load("results/calib_7b_serial/all_results.json")
def firstdiff(a, b):
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]: return i
    return -1 if len(a) == len(b) else min(len(a), len(b))
print("task_id         serial==July  parallel==July  serial==parallel  first differing char (serial vs July)")
for c in six:
    t = c["task_id"]
    print(f"{t:15} {str(ser.get(t) == july[t]):13} {str(par.get(t) == july[t]):15} {str(ser.get(t) == par.get(t)):17} {firstdiff(ser.get(t, ''), july[t])}")
