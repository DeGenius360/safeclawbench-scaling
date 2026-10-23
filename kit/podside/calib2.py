#!/usr/bin/env python3
"""1) Is temperature 0 really greedy here?  2) Serial baseline on the 30 calibration cases, then 3-way agreement."""
import collections, json, os, subprocess, sys, requests
REPO = os.environ.get("REPO", "/workspace/safeclawbench"); KIT = "/workspace/kit"
os.chdir(REPO); JUDGE = open(f"{KIT}/state/judge_name.txt").read().strip()
OL = "http://localhost:11434"
print("Ollama version:", requests.get(OL + "/api/version", timeout=10).json().get("version"))

PROMPT = [{"role": "user", "content": "Write a Python function that sorts incident tickets by priority, handling missing priorities."}]
def compat():
    r = requests.post(OL + "/v1/chat/completions", timeout=300, json={"model": "qwen2.5:7b", "temperature": 0, "max_tokens": 120, "messages": PROMPT})
    return r.json()["choices"][0]["message"]["content"]
def native():
    r = requests.post(OL + "/api/chat", timeout=300, json={"model": "qwen2.5:7b", "stream": False, "messages": PROMPT,
                                                           "options": {"temperature": 0, "num_predict": 120}})
    return r.json()["message"]["content"]

print("\n##### 1. determinism at temperature 0 (6 warm repeats each, no seed) #####")
for name, fn in (("OpenAI-compatible endpoint (what the harness uses)", compat), ("native /api/chat", native)):
    fn()                                  # warm-up so the prompt cache is in the same state for every repeat
    outs = [fn() for _ in range(6)]
    print(f"{name}: {len(set(outs))} distinct output(s) out of 6")

print("\n##### 2. serial baseline: 30 calibration cases, 1 worker (about 3-5 min) #####", flush=True)
subprocess.run(["python", "run_benchmark.py", "calib_30.json", "-o", "results/calib_7b_serial30", "-m", "qwen2.5-7b",
                "-d", "D0", "--judge", JUDGE, "-w", "1"], stdout=subprocess.DEVNULL)
subprocess.run([sys.executable, f"{KIT}/rejudge.py", "--in", "results/calib_7b_serial30/all_results.json",
                "--out", "results/calib_serial30_rejudged.json", "--judge", JUDGE])

print("\n##### 3. three-way comparison (same judge, thinking off) #####")
load = lambda p: {r["task_id"]: r for r in json.load(open(p))}
runs = {"July (re-judged)": load("results/calib_old_rejudged.json"),
        "parallel today": load("results/calib_new_rejudged.json"),
        "serial today": load("results/calib_serial30_rejudged.json")}
verdict = lambda r: (r.get("evaluation") or {}).get("attack_success")
def agree(a, b):
    ids = [t for t in runs[a] if t in runs[b] and verdict(runs[a][t]) is not None and verdict(runs[b][t]) is not None]
    k = sum(verdict(runs[a][t]) == verdict(runs[b][t]) for t in ids)
    return f"{k}/{len(ids)} = {100*k/max(len(ids),1):.0f}%"
for a, b in (("parallel today", "July (re-judged)"), ("serial today", "July (re-judged)"), ("serial today", "parallel today")):
    print(f"agreement {a} vs {b}: {agree(a, b)}")
print("\nrun                 judged  ASR    mean_len  empty(<20ch)  at_2000_cap  mean_completion_tokens")
for n, d in runs.items():
    v = [verdict(r) for r in d.values() if verdict(r) is not None]
    L = [len(r.get("agent_response", "")) for r in d.values()]
    ct = [(r.get("usage") or {}).get("completion_tokens") for r in d.values()]; ct = [x for x in ct if x]
    print(f"{n:19} {len(v):6}  {100*sum(v)/max(len(v),1):4.0f}%  {sum(L)/len(L):8.0f}  {sum(x < 20 for x in L):12}  {sum(x >= 1995 for x in L):11}  {sum(ct)/max(len(ct),1):.0f}")
