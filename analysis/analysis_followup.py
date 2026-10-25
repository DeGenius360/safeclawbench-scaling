#!/usr/bin/env python3
"""
SafeClawBench follow-up (pre-registered): same-environment, full-length re-judging.
Recomputes every table from followup_per_case.json / the main-study verdicts, applies the
pre-registration decision rules mechanically, and regenerates the follow-up figures.

Usage:
    python3 analysis/analysis_followup.py --data ./data --out ./out

Reads (verdicts and lengths only — no response text anywhere):
    {data}/followup_per_case.json      per-model list of {tid,type,n,long,ds_cap,ds_full,hk_cap,hk_full}
    {data}/per_case_verdicts.csv       main-study v1 verdicts (for the H4 environment check)
Dependencies: numpy, scipy, matplotlib.
"""
import json, os, math, argparse, csv, hashlib
import numpy as np
from scipy import stats

MODELS = ["qwen2.5-7b", "qwen2.5-14b", "qwen2.5-32b"]
SH = {"qwen2.5-7b": "7b", "qwen2.5-14b": "14b", "qwen2.5-32b": "32b"}
FAMS = ["ADI", "DPI", "IPI", "MEX", "MPI", "TRI"]
EXPECTED_SHA = "4230f25b837fa46dc87d5d7679e6a70b596d79fbcdf842315403671f164e9f75"

def load(p):
    with open(p) as f: return json.load(f)

def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),) * 3
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)

def mcnemar(a, b):
    a = np.array(a, bool); b = np.array(b, bool)
    yn = int((a & ~b).sum()); ny = int((~a & b).sum()); nd = yn + ny
    p = 1.0 if nd == 0 else stats.binomtest(min(yn, ny), nd, 0.5).pvalue
    return (b.mean() - a.mean()) * 100, yn, ny, p

def kappa(a, b):
    a = np.array(a, bool); b = np.array(b, bool); po = (a == b).mean()
    pa, pb = a.mean(), b.mean(); pe = pa * pb + (1 - pa) * (1 - pb)
    return po, ((po - pe) / (1 - pe) if pe < 1 else float("nan"))

def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--data", default=os.path.join(here, "data"))
    ap.add_argument("--out", default=os.path.join(here, "out"))
    a = ap.parse_args()
    pc = load(os.path.join(a.data, "followup_per_case.json"))
    ids = sorted(r["tid"] for r in pc[MODELS[0]])
    R = {}

    # ---- sanity ----
    sha = hashlib.sha256(("\n".join(ids)).encode()).hexdigest()
    R["sanity"] = {"sha256_sorted_ids": sha, "sha256_matches": sha == EXPECTED_SHA, "ids_same_across_sizes":
                   all(sorted(r["tid"] for r in pc[m]) == ids for m in MODELS)}
    for m in MODELS:
        rows = pc[m]
        fam = {f: sum(r["type"] == f for r in rows) for f in FAMS}
        R["sanity"][SH[m]] = dict(n=len(rows), families=fam,
            missing=sum(any(r.get(k) is None for k in ["ds_cap","ds_full","hk_cap","hk_full"]) for r in rows),
            max_len=max(r["n"] for r in rows), n_long=sum(r["long"] for r in rows),
            short_cap_ne_full=sum((not r["long"]) and (r["ds_cap"]!=r["ds_full"] or r["hk_cap"]!=r["hk_full"]) for r in rows),
            long_defn_ok=all(r["long"] == (r["n"] > 2000) for r in rows))

    VIEWS = [("ds_cap","DeepSeek cap"),("hk_cap","Haiku cap"),("ds_full","DeepSeek full"),("hk_full","Haiku full")]
    # ---- Table A: ASR per size x view ----
    R["A_asr"] = {}
    for m in MODELS:
        for key, lab in VIEWS:
            k = sum(r[key] for r in pc[m]); p, lo, hi = wilson(k, 120)
            R["A_asr"][f"{SH[m]}|{key}"] = dict(asr=p, lo=lo, hi=hi, k=k, n=120)
    # ---- Table B: paired size comparisons per view ----
    R["B_paired"] = {}
    for key, lab in VIEWS:
        for x, y in [("qwen2.5-7b","qwen2.5-14b"),("qwen2.5-14b","qwen2.5-32b"),("qwen2.5-7b","qwen2.5-32b")]:
            dx = {r["tid"]: r[key] for r in pc[x]}; dy = {r["tid"]: r[key] for r in pc[y]}
            d, yn, ny, p = mcnemar([dx[t] for t in ids], [dy[t] for t in ids])
            R["B_paired"][f"{key}|{SH[x]}->{SH[y]}"] = dict(delta=d, up=ny, down=yn, p=p)
    # ---- Table C: cut vs full on long, per judge ----
    R["C_cutfull"] = {}
    for m in MODELS:
        rows = [r for r in pc[m] if r["long"]]
        for j, cap, full in [("DeepSeek","ds_cap","ds_full"),("Haiku","hk_cap","hk_full")]:
            d, yn, ny, p = mcnemar([r[cap] for r in rows], [r[full] for r in rows])
            R["C_cutfull"][f"{SH[m]}|{j}"] = dict(n=len(rows),
                cap=float(np.mean([r[cap] for r in rows])), full=float(np.mean([r[full] for r in rows])),
                delta=d, cap_to_full_yesno=yn, cap_to_full_noyes=ny, p=p)
    # ---- Table D: DS vs HK agreement cap/full ----
    R["D_agree"] = {}
    for m in MODELS + ["POOLED"]:
        rows = [r for mm in MODELS for r in pc[mm]] if m == "POOLED" else pc[m]
        agc, kc = kappa([r["ds_cap"] for r in rows], [r["hk_cap"] for r in rows])
        agf, kf = kappa([r["ds_full"] for r in rows], [r["hk_full"] for r in rows])
        R["D_agree"]["POOLED" if m == "POOLED" else SH[m]] = dict(cap_agree=agc, cap_kappa=kc, full_agree=agf, full_kappa=kf)
    # ---- H1: agreement on long responses, cap vs full (pooled) ----
    longrows = [r for m in MODELS for r in pc[m] if r["long"]]
    agc, kc = kappa([r["ds_cap"] for r in longrows], [r["hk_cap"] for r in longrows])
    agf, kf = kappa([r["ds_full"] for r in longrows], [r["hk_full"] for r in longrows])
    R["H1"] = dict(n_long=len(longrows), agree_cap=agc, agree_full=agf, delta=(agf-agc)*100,
                   kappa_cap=kc, kappa_full=kf,
                   outcome=("supported" if (agf-agc)*100 >= 5 else "not_supported" if (agf-agc)*100 < 2 else "weak"))
    # ---- H3 primary + exploratory ----
    def full_pair(key):
        d7 = {r["tid"]: r[key] for r in pc["qwen2.5-7b"]}; d32 = {r["tid"]: r[key] for r in pc["qwen2.5-32b"]}
        return mcnemar([d7[t] for t in ids], [d32[t] for t in ids])
    dh, ynh, nyh, ph = full_pair("hk_full")
    dd, ynd, nyd, pd = full_pair("ds_full")
    replicated = (ph < 0.05) and ((dh > 0) == (dd > 0)) and dd > 0 and dh > 0
    not_rep = (dh < 0 or dh < 3) or (dd < 0 or dd < 3)
    R["H3"] = dict(primary_haiku_delta=dh, primary_haiku_p=ph, deepseek_delta=dd, deepseek_p=pd,
                   outcome=("replicated" if replicated else "not_replicated" if not_rep else "inconclusive_underpowered"))
    # ---- H4 environment check: main Haiku (cap) vs v2 hk_cap ----
    mainhk = {}
    with open(os.path.join(a.data, "per_case_verdicts.csv")) as f:
        for row in csv.DictReader(f):
            mainhk[(row["model"], row["task_id"])] = (row["haiku_success"] == "1")
    R["H4"] = {}
    for m in MODELS:
        pairs = [(mainhk[(SH[m], r["tid"])], r["hk_cap"]) for r in pc[m] if (SH[m], r["tid"]) in mainhk]
        agree = np.mean([x == y for x, y in pairs]) * 100
        shift = (np.mean([y for x, y in pairs]) - np.mean([x for x, y in pairs])) * 100
        R["H4"][SH[m]] = dict(n=len(pairs), agree=agree, main_asr=float(np.mean([x for x,y in pairs])*100),
                              v2_asr=float(np.mean([y for x,y in pairs])*100), shift=shift)
    R["H4"]["outcome"] = ("material" if (R["H4"]["7b"]["agree"] < 80 or abs(R["H4"]["7b"]["shift"]) > 5
                           or R["H4"]["14b"]["agree"] < 80 or abs(R["H4"]["14b"]["shift"]) > 5) else "small")

    os.makedirs(a.out, exist_ok=True)
    json.dump(R, open(os.path.join(a.out, "results_followup.json"), "w"), indent=2)
    _print(R); _figures(R, pc, os.path.join(a.out, "figures"))
    print(f"\nWrote {os.path.join(a.out,'results_followup.json')} and follow-up figures.")

def _print(R):
    pc_ = lambda x: f"{x*100:.1f}%"
    print("== SANITY =="); s = R["sanity"]
    print(f"  sha256 match: {s['sha256_matches']}  ids_same_across_sizes: {s['ids_same_across_sizes']}")
    for m in ["7b","14b","32b"]:
        d = s[m]; print(f"  {m}: n={d['n']} fam={d['families']} missing={d['missing']} max_len={d['max_len']} long={d['n_long']} short_cap!=full={d['short_cap_ne_full']}")
    print("\n== TABLE A: ASR per size x view ==")
    for m in ["7b","14b","32b"]:
        print("  "+m+": "+"  ".join(f"{k.split('|')[1]}={pc_(R['A_asr'][f'{m}|{k.split(chr(124))[1]}']['asr'])}" for k in [f"{m}|ds_cap",f"{m}|hk_cap",f"{m}|ds_full",f"{m}|hk_full"]))
    print("\n== H1 (truncation drives disagreement) ==")
    h=R["H1"]; print(f"  long n={h['n_long']} agree cap={pc_(h['agree_cap'])} -> full={pc_(h['agree_full'])} Δ={h['delta']:+.1f}pts kappa {h['kappa_cap']:.2f}->{h['kappa_full']:.2f}  => {h['outcome'].upper()}")
    print("\n== TABLE C (cut vs full on long, per judge) ==")
    for k,v in R["C_cutfull"].items():
        print(f"  {k}: n={v['n']} cap={pc_(v['cap'])}->full={pc_(v['full'])} Δ={v['delta']:+.1f} flips(y->n {v['cap_to_full_yesno']}/n->y {v['cap_to_full_noyes']}) p={v['p']:.3f}")
    print("\n== H3 (scale trend, same-env full-text) ==")
    h=R["H3"]; print(f"  PRIMARY Haiku full 7B->32B Δ={h['primary_haiku_delta']:+.1f} p={h['primary_haiku_p']:.3f} | DeepSeek Δ={h['deepseek_delta']:+.1f} p={h['deepseek_p']:.3f}  => {h['outcome'].upper()}")
    print("\n== H4 (environment) ==")
    for m in ["7b","14b","32b"]:
        d=R["H4"][m]; print(f"  {m}: agree={d['agree']:.1f}% main={d['main_asr']:.1f}% -> v2={d['v2_asr']:.1f}% shift={d['shift']:+.1f}")
    print(f"  => {R['H4']['outcome'].upper()}")

def _figures(R, pc, outdir):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    DS, HK, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
    themes = dict(light=dict(bg="#FFFFFF", fg="#14171B", grid="#D8DEE4", muted="#5A616A"),
                  dark=dict(bg="#161A1E", fg="#ECEEF1", grid="#333A42", muted="#9AA2AC"))
    os.makedirs(outdir, exist_ok=True)
    SL = ["7b","14b","32b"]; SLAB=["7B","14B","32B"]; xp=np.arange(3)
    def style(t):
        plt.rcParams.update({"figure.facecolor":t["bg"],"axes.facecolor":t["bg"],"savefig.facecolor":t["bg"],
            "text.color":t["fg"],"axes.labelcolor":t["fg"],"axes.edgecolor":t["muted"],"xtick.color":t["fg"],
            "ytick.color":t["fg"],"grid.color":t["grid"],"font.size":11,"axes.grid":True,"grid.alpha":.5,
            "axes.spines.top":False,"axes.spines.right":False})
    for theme in ("light","dark"):
        t=themes[theme]; style(t)
        # Fig FU1: cut vs full ASR, per judge, per size (4 bars/size: DS cap, DS full, HK cap, HK full)
        fig,ax=plt.subplots(figsize=(8,4.6))
        groups=[("ds_cap",DS,"DeepSeek cap",.35),("ds_full",DS,"DeepSeek full",1.0),
                ("hk_cap",HK,"Haiku cap",.35),("hk_full",HK,"Haiku full",1.0)]
        w=0.19
        for i,(key,col,lab,al) in enumerate(groups):
            vals=[R["A_asr"][f"{m}|{key}"]["asr"]*100 for m in SL]
            xs=xp+(i-1.5)*w
            ax.bar(xs,vals,w,color=col,alpha=al,edgecolor=t["bg"],linewidth=.6,
                   hatch=("//" if "cap" in key else None),label=lab)
            for x,v in zip(xs,vals): ax.text(x,v+1,f"{v:.0f}",ha="center",fontsize=8,fontfamily="monospace",color=t["fg"])
        ax.set_xticks(xp);ax.set_xticklabels(SLAB);ax.set_ylabel("ASR (%)");ax.set_ylim(0,100)
        ax.set_title("Follow-up ASR: first 2,000 chars (hatched) vs full text")
        ax.legend(frameon=False,fontsize=8,ncol=2)
        fig.tight_layout();fig.savefig(f"{outdir}/figFU1_cut_vs_full_asr_{theme}.png",dpi=200,bbox_inches="tight");plt.close(fig)
        # Fig FU2: DS-HK agreement cap vs full, per size + pooled
        fig,ax=plt.subplots(figsize=(7.2,4.4))
        labs=["7b","14b","32b","POOLED"];xp2=np.arange(4)
        capv=[R["D_agree"][l]["cap_agree"]*100 for l in labs]; fullv=[R["D_agree"][l]["full_agree"]*100 for l in labs]
        ax.bar(xp2-0.2,capv,0.38,color=t["muted"],hatch="//",label="first 2,000 chars",edgecolor=t["bg"])
        ax.bar(xp2+0.2,fullv,0.38,color=AQUA,label="full text",edgecolor=t["bg"])
        for x,v in zip(xp2-0.2,capv): ax.text(x,v+1,f"{v:.0f}",ha="center",fontsize=8.5,fontfamily="monospace",color=t["fg"])
        for x,v in zip(xp2+0.2,fullv): ax.text(x,v+1,f"{v:.0f}",ha="center",fontsize=8.5,fontfamily="monospace",color=t["fg"])
        ax.set_xticks(xp2);ax.set_xticklabels(["7B","14B","32B","Pooled"]);ax.set_ylabel("DeepSeek–Haiku agreement (%)")
        ax.set_ylim(0,100);ax.set_title("Judge agreement rises on full text");ax.legend(frameon=False,fontsize=9)
        fig.tight_layout();fig.savefig(f"{outdir}/figFU2_agreement_cut_vs_full_{theme}.png",dpi=200,bbox_inches="tight");plt.close(fig)
        # Fig FU3: environment check — agreement + shift
        fig,ax=plt.subplots(figsize=(7.2,4.4))
        GOOD,BAD="#1a7f37","#c23b3a"
        agree=[R["H4"][m]["agree"] for m in SL]
        ax.bar(xp,agree,0.5,color=[GOOD if a>=80 else BAD for a in agree],edgecolor=t["bg"])
        ax.axhline(80,ls="--",color=t["muted"],lw=1);ax.text(0.0,82,"80% 'small' threshold",fontsize=8,color=t["muted"],ha="left")
        for x,m in zip(xp,SL):
            ax.text(x,R["H4"][m]["agree"]+1.5,f"{R['H4'][m]['agree']:.0f}%",ha="center",fontsize=10,fontfamily="monospace",color=t["fg"])
            ax.text(x,6,f"shift {R['H4'][m]['shift']:+.1f}",ha="center",fontsize=8.5,fontfamily="monospace",color="#FFFFFF")
        builds={"7b":"July build","14b":"July build","32b":"Oct build"}
        ax.set_xticks(xp);ax.set_xticklabels([f"{SLAB[i]}\n({builds[SL[i]]})" for i in range(3)])
        ax.set_ylabel("Agreement: main study vs same-env (%)");ax.set_ylim(0,100)
        ax.set_title("Environment check: July-built 7B/14B drift below the 'small' threshold")
        fig.tight_layout();fig.savefig(f"{outdir}/figFU3_environment_{theme}.png",dpi=200,bbox_inches="tight");plt.close(fig)

if __name__ == "__main__":
    main()
