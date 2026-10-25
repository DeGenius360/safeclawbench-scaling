#!/usr/bin/env python3
"""
Recompute the main-study HEADLINE tables from the PUBLIC per-case CSVs — no response text needed.

    python3 analysis/recompute_headline.py --data ./data

This reproduces the numbers that appear in the report and paper (Core ASR, paired size tests, the GEE
trend, per-family ASR, judge agreement, truncation-stratified ASR, Exec metrics, Core-vs-Exec and the
MEX oracle) from `data/per_case_verdicts.csv` + `data/exec_per_case.csv`, and cross-checks them against
the shipped `data/results.json`. It deliberately does NOT need the raw responses.

(The companion `analysis.py` regenerates everything — including the harm-evidence breakdowns and the
environment calibration — from the full generation bundle, which contains model responses and is not
redistributed. `analysis_followup.py` covers the pre-registered follow-up.)

Dependencies: numpy, scipy.
"""
import csv, json, os, math, argparse
import numpy as np
from scipy import stats

MODELS = ["7b", "14b", "32b"]
SIZE_ORD = {"7b": 0, "14b": 1, "32b": 2}
FAMILIES = ["ADI", "DPI", "IPI", "MEX", "MPI", "TRI"]

def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),) * 3
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)

def mcnemar(a, b):
    a = np.array(a, bool); b = np.array(b, bool)
    yn = int((a & ~b).sum()); ny = int((~a & b).sum()); nd = yn + ny
    return (b.mean() - a.mean()) * 100, (1.0 if nd == 0 else stats.binomtest(min(yn, ny), nd, 0.5).pvalue)

def holm(pvals):
    items = sorted(pvals.items(), key=lambda kv: kv[1]); m = len(items); adj = {}; run = 0.0
    for i, (lab, p) in enumerate(items):
        run = max(run, (m - i) * p); adj[lab] = min(1.0, run)
    return adj

def kappa(a, b):
    a = np.array(a, bool); b = np.array(b, bool); po = (a == b).mean()
    pa, pb = a.mean(), b.mean(); pe = pa * pb + (1 - pa) * (1 - pb)
    return po, ((po - pe) / (1 - pe) if pe < 1 else float("nan"))

def _irls(X, y, it=100, tol=1e-10):
    b = np.zeros(X.shape[1])
    for _ in range(it):
        mu = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30))); W = np.clip(mu * (1 - mu), 1e-9, None)
        step = np.linalg.pinv((X.T * W) @ X) @ (X.T @ (y - mu)); b += step
        if np.max(np.abs(step)) < tol: break
    return b

def gee(X, y, cl):
    X = np.asarray(X, float); y = np.asarray(y, float); b = _irls(X, y)
    mu = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30))); W = np.clip(mu * (1 - mu), 1e-9, None)
    bread = np.linalg.pinv((X.T * W) @ X); u = X * ((y - mu)[:, None]); meat = np.zeros((X.shape[1],) * 2)
    for c in np.unique(cl):
        s = u[cl == c].sum(0); meat += np.outer(s, s)
    G, n, k = len(np.unique(cl)), len(y), X.shape[1]
    cov = bread @ meat @ bread * (G / (G - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(cov)); return b, se

def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--data", default=os.path.join(here, "data"))
    a = ap.parse_args()
    rows = []
    with open(os.path.join(a.data, "per_case_verdicts.csv")) as f:
        for r in csv.DictReader(f):
            rows.append(dict(model=r["model"], tid=r["task_id"], fam=r["family"],
                             rlen=int(r["resp_len"]), trunc=r["truncated"] == "1",
                             ds=r["deepseek_success"] == "1", hk=r["haiku_success"] == "1"))
    ex = {}
    with open(os.path.join(a.data, "exec_per_case.csv")) as f:
        for r in csv.DictReader(f):
            ex.setdefault(r["model"], []).append(dict(cid=r["case_id"], fam=r["family"],
                harm=r["harm_completion"] == "1", tool=r["tool_call"] == "1", blk=r["blocked_by_harness"] == "1"))
    def sub(m, t=None): return [r for r in rows if r["model"] == m and (t is None or r["trunc"] == t)]

    print("CORE ASR (Wilson 95%)")
    for j, key in [("DeepSeek", "ds"), ("Haiku", "hk")]:
        for m in MODELS:
            x = [r[key] for r in sub(m)]; p, lo, hi = wilson(sum(x), len(x))
            print(f"  {j:9s} {m:3s}: {p*100:.1f}% [{lo*100:.1f}-{hi*100:.1f}] (n={len(x)})")
    print("\nPAIRED McNEMAR 7b->32b")
    for j, key in [("DeepSeek", "ds"), ("Haiku", "hk")]:
        idx = {m: {r["tid"]: r[key] for r in sub(m)} for m in MODELS}
        ids = sorted(idx["7b"])
        d, p = mcnemar([idx["7b"][i] for i in ids], [idx["32b"][i] for i in ids])
        print(f"  {j:9s}: Δ={d:+.1f}pts p={p:.3g}")
    print("\nGEE TREND (size ordinal, CR SE by case)")
    fam_lv = FAMILIES[1:]
    for j, key in [("DeepSeek", "ds"), ("Haiku", "hk")]:
        X = [[1.0, SIZE_ORD[r["model"]]] + [1.0 if r["fam"] == f else 0.0 for f in fam_lv] for r in rows]
        y = [r[key] for r in rows]; cl = [hash(r["tid"]) for r in rows]
        b, se = gee(np.array(X), np.array(y), np.array(cl))
        print(f"  {j:9s}: OR/step={math.exp(b[1]):.2f} [{math.exp(b[1]-1.96*se[1]):.2f}-{math.exp(b[1]+1.96*se[1]):.2f}] p={2*stats.norm.sf(abs(b[1]/se[1])):.2g}")
    print("\nAGREEMENT / KAPPA")
    for m in MODELS:
        po, kp = kappa([r["ds"] for r in sub(m)], [r["hk"] for r in sub(m)])
        print(f"  {m}: agree={po*100:.1f}% kappa={kp:.2f}")
    print("\nTRUNCATION-STRATIFIED ASR (gap = DS-HK)")
    for t, lab in [(False, "complete"), (True, "truncated")]:
        line = f"  {lab:9s}: "
        for m in MODELS:
            rm = sub(m, t); ds = np.mean([r["ds"] for r in rm]); hk = np.mean([r["hk"] for r in rm])
            line += f"{m} gap={ (ds-hk)*100:.1f} "
        print(line)
    print("\nEXEC + CORE-vs-EXEC + MEX oracle")
    core = {(r["model"], r["tid"]): r for r in rows}
    for m in MODELS:
        e = ex[m]; harm = np.mean([r["harm"] for r in e])
        cp_ds = np.mean([core[(m, r["cid"])]["ds"] for r in e]); cp_hk = np.mean([core[(m, r["cid"])]["hk"] for r in e])
        mex = [r for r in e if r["fam"] == "MEX"]
        print(f"  {m}: ExecHarm={harm*100:.1f}% CorePassDS={cp_ds*100:.0f}% CorePassHK={cp_hk*100:.0f}% | "
              f"MEX oracle={np.mean([r['harm'] for r in mex])*100:.0f}% "
              f"(DS={np.mean([core[(m,r['cid'])]['ds'] for r in mex])*100:.0f}% HK={np.mean([core[(m,r['cid'])]['hk'] for r in mex])*100:.0f}%)")

    # cross-check vs shipped results.json
    rj = os.path.join(a.data, "results.json")
    if os.path.exists(rj):
        R = json.load(open(rj)); bad = 0
        for m in MODELS:
            for j, key in [("DeepSeek", "ds"), ("Haiku", "hk")]:
                got = np.mean([r[key] for r in sub(m)]) * 100; exp = R["asr"][f"{j}|{m}"]["asr"] * 100
                if abs(got - exp) > 0.1: bad += 1; print(f"  MISMATCH {j} {m}: {got:.1f} vs {exp:.1f}")
        print(f"\nCross-check vs results.json: {'all headline ASR match' if bad == 0 else str(bad)+' mismatches'}")

if __name__ == "__main__":
    main()
