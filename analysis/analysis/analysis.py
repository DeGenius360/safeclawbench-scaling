#!/usr/bin/env python3
"""
SafeClawBench cross-scale study (Qwen2.5 7B/14B/32B, defence D0) — reproducible analysis.

Regenerates every table (printed + results.json) and every figure (light + dark PNG)
from the phase2_final_v3 data bundle. Dependencies: numpy, scipy, matplotlib only
(statsmodels deliberately avoided; the trend model is implemented here as a
population-averaged / GEE logistic with independence working correlation and
cluster-robust (CR1) SEs by case).

Usage:
    python3 analysis.py --data /path/to/phase2_final_v3_extracted --out ./out

Expects under --data:
    results/final/qwen2.5-{7b,14b,32b}_uniform.json      (DeepSeek in `evaluation`, July/inline in `evaluation_prev`)
    results/final/haiku_qwen2.5-{7b,14b,32b}_full.json    (Haiku in `evaluation`, DeepSeek copy in `evaluation_prev`)
    benchmark_v5_600.json
    results/phase2_exec_qwen2.5-{7b,14b,32b}/results_qwen2.5-{m}_D0.json
    results/calib_7b_serial30/results_qwen2.5-7b_D0.json
    results/calib_7b_parallel/results_qwen2.5-7b_D0.json
"""
import json, os, math, argparse
import numpy as np
from scipy import stats

MODELS = ["7b", "14b", "32b"]
SIZE_ORD = {"7b": 0, "14b": 1, "32b": 2}
FAMILIES = ["ADI", "DPI", "IPI", "MEX", "MPI", "TRI"]
TRUNC_CAP = 2000
BOOT_B = 5000
BOOT_SEED = 12345

# ----------------------------------------------------------------------------- loaders
def load(p):
    with open(p) as f:
        return json.load(f)

def build_frame(data):
    rows = []
    bench = {r["task_id"]: r for r in load(os.path.join(data, "benchmark_v5_600.json"))}
    for m in MODELS:
        uni = {r["task_id"]: r for r in load(os.path.join(data, f"results/final/qwen2.5-{m}_uniform.json"))}
        hai = {r["task_id"]: r for r in load(os.path.join(data, f"results/final/haiku_qwen2.5-{m}_full.json"))}
        for tid in sorted(set(uni) | set(hai)):
            u, h = uni.get(tid), hai.get(tid)
            resp = (u or h).get("agent_response") or ""
            ds = u["evaluation"] if u else None
            hk = h["evaluation"] if h else None
            b = bench.get(tid, {})
            rows.append(dict(
                model=m, task_id=tid, family=tid.split("_")[0],
                harm_type=(u or h).get("harm_type"),
                resp_len=len(resp), truncated=len(resp) >= TRUNC_CAP,
                ds_success=bool(ds["attack_success"]) if ds else None,
                hk_success=bool(hk["attack_success"]) if hk else None,
                ds_prev_success=bool(h["evaluation_prev"]["attack_success"]) if h else None,  # DeepSeek copy in haiku file
                ds_hec=ds.get("harm_evidence_category") if ds else None,
                hk_hec=hk.get("harm_evidence_category") if hk else None,
                ds_defbeh=ds.get("defense_behavior") if ds else None,
                hk_defbeh=hk.get("defense_behavior") if hk else None,
                ds_expl=ds.get("explanation") if ds else None,
                hk_expl=hk.get("explanation") if hk else None,
                user_prompt=b.get("user_prompt"), success_pred=b.get("success_predicate"),
                safe_beh=b.get("safe_behavior"), resp=resp,
            ))
    return rows

# ----------------------------------------------------------------------------- stats
def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),) * 3
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)

def cluster_bootstrap_ci(x, B=BOOT_B, seed=BOOT_SEED):
    rng = np.random.default_rng(seed); x = np.asarray(x, float); n = len(x)
    means = x[rng.integers(0, n, size=(B, n))].mean(1)
    return float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))

def mcnemar_exact(b, c):
    nd = b + c
    if nd == 0: return 0, 1.0
    return (b - c), stats.binomtest(min(b, c), nd, 0.5, alternative="two-sided").pvalue

def holm(pvals):
    items = sorted(pvals.items(), key=lambda kv: kv[1]); m = len(items); adj = {}; run = 0.0
    for i, (lab, p) in enumerate(items):
        run = max(run, (m - i) * p); adj[lab] = min(1.0, run)
    return adj

def cohen_kappa(a, b):
    a = np.asarray(a, bool); b = np.asarray(b, bool)
    po = (a == b).mean(); pa, pb = a.mean(), b.mean()
    pe = pa * pb + (1 - pa) * (1 - pb)
    return po, ((po - pe) / (1 - pe) if pe < 1 else float("nan"))

def _irls_logit(X, y, maxit=100, tol=1e-10):
    n, k = X.shape; beta = np.zeros(k)
    for _ in range(maxit):
        mu = 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))
        W = np.clip(mu * (1 - mu), 1e-9, None)
        H = (X.T * W) @ X; g = X.T @ (y - mu)
        try: step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError: step = np.linalg.pinv(H) @ g
        beta += step
        if np.max(np.abs(step)) < tol: break
    return beta

def gee_logit_cluster(X, y, clusters):
    """Population-averaged logistic (independence working corr) + CR1 sandwich SE clustered by case."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    beta = _irls_logit(X, y)
    mu = 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))
    W = np.clip(mu * (1 - mu), 1e-9, None)
    bread = np.linalg.pinv((X.T * W) @ X)
    u = X * ((y - mu)[:, None])
    meat = np.zeros((X.shape[1],) * 2)
    uniq = np.unique(clusters)
    for cci in uniq:
        s = u[clusters == cci].sum(0); meat += np.outer(s, s)
    G, n, k = len(uniq), len(y), X.shape[1]
    corr = (G / (G - 1)) * ((n - 1) / (n - k)) if G > 1 else 1.0
    cov = bread @ meat @ bread * corr
    se = np.sqrt(np.diag(cov)); z = beta / se
    return beta, se, z, 2 * stats.norm.sf(np.abs(z))

# ----------------------------------------------------------------------------- analyses
def sub(rows, m, trunc=None):
    return [r for r in rows if r["model"] == m and (trunc is None or r["truncated"] == trunc)]

def analyse(rows, data):
    R = {}
    # integrity
    R["integrity"] = {}
    for m in MODELS:
        rm = sub(rows, m)
        R["integrity"][m] = dict(
            n=len(rm), unique_ids=len({r["task_id"] for r in rm}),
            ds_null=sum(r["ds_success"] is None for r in rm),
            hk_null=sum(r["hk_success"] is None for r in rm),
            truncated=sum(r["truncated"] for r in rm),
            deepseek_consistency=sum(r["ds_success"] == r["ds_prev_success"] for r in rm),
        )
    # ASR
    R["asr"] = {}
    for judge, key in [("DeepSeek", "ds_success"), ("Haiku", "hk_success")]:
        for m in MODELS:
            x = np.array([r[key] for r in sub(rows, m)], float)
            p, wlo, whi = wilson(int(x.sum()), len(x)); _, blo, bhi = cluster_bootstrap_ci(x)
            R["asr"][f"{judge}|{m}"] = dict(k=int(x.sum()), n=len(x), asr=p,
                                            wilson=[wlo, whi], boot=[blo, bhi])
    # paired McNemar overall
    R["mcnemar"] = {}
    for judge, key in [("DeepSeek", "ds_success"), ("Haiku", "hk_success")]:
        idx = {m: {r["task_id"]: r[key] for r in sub(rows, m)} for m in MODELS}
        ids = sorted(idx["7b"]); res = {}
        for a, b in [("7b", "14b"), ("14b", "32b"), ("7b", "32b")]:
            ya = np.array([idx[a][i] for i in ids], bool); yb = np.array([idx[b][i] for i in ids], bool)
            b01 = int((~ya & yb).sum()); b10 = int((ya & ~yb).sum())
            _, p = mcnemar_exact(b10, b01)
            res[f"{a}->{b}"] = dict(delta_pts=(yb.mean() - ya.mean()) * 100, up=b01, down=b10, p=p)
        for k, v in zip(res, holm({k: v["p"] for k, v in res.items()}).values()):
            res[k]["p_holm"] = list(holm({k: v["p"] for k, v in res.items()}).values())[list(res).index(k)]
        adj = holm({k: v["p"] for k, v in res.items()})
        for k in res: res[k]["p_holm"] = adj[k]
        R["mcnemar"][judge] = res
    # per-family ASR + 7b->32b paired (Holm across families)
    R["family_asr"] = {}; R["family_mcnemar"] = {}
    for f in FAMILIES:
        for judge, key in [("DeepSeek", "ds_success"), ("Haiku", "hk_success")]:
            R["family_asr"][f"{f}|{judge}"] = [float(np.mean([r[key] for r in rows if r["family"] == f and r["model"] == m])) for m in MODELS]
    for judge, key in [("DeepSeek", "ds_success"), ("Haiku", "hk_success")]:
        idx = {m: {r["task_id"]: r[key] for r in rows if r["model"] == m} for m in MODELS}
        ps = {}; info = {}
        for f in FAMILIES:
            ids = sorted([r["task_id"] for r in rows if r["model"] == "7b" and r["family"] == f])
            ya = np.array([idx["7b"][i] for i in ids], bool); yb = np.array([idx["32b"][i] for i in ids], bool)
            b01 = int((~ya & yb).sum()); b10 = int((ya & ~yb).sum())
            _, p = mcnemar_exact(b10, b01); ps[f] = p
            info[f] = dict(delta_pts=(yb.mean() - ya.mean()) * 100, up=b01, down=b10, p=p)
        adj = holm(ps)
        for f in FAMILIES: info[f]["p_holm"] = adj[f]
        R["family_mcnemar"][judge] = info
    # agreement/kappa
    R["agreement"] = {}
    for m in MODELS:
        rm = sub(rows, m); po, kp = cohen_kappa([r["ds_success"] for r in rm], [r["hk_success"] for r in rm])
        R["agreement"][m] = dict(agreement=po, kappa=kp)
    R["agreement_family"] = {}
    for f in FAMILIES:
        rf = [r for r in rows if r["family"] == f]; po, kp = cohen_kappa([r["ds_success"] for r in rf], [r["hk_success"] for r in rf])
        R["agreement_family"][f] = dict(agreement=po, kappa=kp,
                                        ds=float(np.mean([r["ds_success"] for r in rf])),
                                        hk=float(np.mean([r["hk_success"] for r in rf])))
    # GEE trend
    R["trend"] = {}
    fam_levels = FAMILIES[1:]
    for judge, key in [("DeepSeek", "ds_success"), ("Haiku", "hk_success")]:
        X = []; y = []; cl = []
        for r in rows:
            X.append([1.0, SIZE_ORD[r["model"]]] + [1.0 if r["family"] == f else 0.0 for f in fam_levels])
            y.append(float(r[key])); cl.append(hash(r["task_id"]))
        beta, se, z, p = gee_logit_cluster(np.array(X), np.array(y), np.array(cl))
        R["trend"][judge] = dict(beta_size=float(beta[1]), se_size=float(se[1]), p_size=float(p[1]),
                                 OR=float(np.exp(beta[1])),
                                 OR_ci=[float(np.exp(beta[1] - 1.96 * se[1])), float(np.exp(beta[1] + 1.96 * se[1]))])
    # disagreement forensics
    disc = [r for r in rows if r["ds_success"] and not r["hk_success"]]
    rev = [r for r in rows if not r["ds_success"] and r["hk_success"]]
    R["disagreement"] = dict(
        ds_yes_hk_no=len(disc), ds_no_hk_yes=len(rev),
        by_family={f: sum(r["ds_success"] != r["hk_success"] for r in rows if r["family"] == f) for f in FAMILIES},
        trunc_rate_disagree=float(np.mean([r["truncated"] for r in rows if r["ds_success"] != r["hk_success"]])),
        trunc_rate_agree=float(np.mean([r["truncated"] for r in rows if r["ds_success"] == r["hk_success"]])),
        ds_hec_in_disc={k: int(sum(r["ds_hec"] == k for r in disc)) for k in set(r["ds_hec"] for r in disc)},
        hk_defbeh_in_disc={k: int(sum(r["hk_defbeh"] == k for r in disc)) for k in set(r["hk_defbeh"] for r in disc)},
    )
    # truncation-stratified ASR + trend
    R["truncation"] = {}
    for trunc in [False, True]:
        for m in MODELS:
            rm = sub(rows, m, trunc)
            R["truncation"][f"{'trunc' if trunc else 'full'}|{m}"] = dict(
                n=len(rm), ds=float(np.mean([r["ds_success"] for r in rm])),
                hk=float(np.mean([r["hk_success"] for r in rm])),
                agree=float(np.mean([r["ds_success"] == r["hk_success"] for r in rm])))
    R["trend_by_trunc"] = {}
    for trunc in [False, True]:
        idx = {m: {r["task_id"]: r for r in sub(rows, m)} for m in MODELS}
        for judge, key in [("DeepSeek", "ds_success"), ("Haiku", "hk_success")]:
            ids = [t for t in idx["7b"] if idx["7b"][t]["truncated"] == trunc and idx["32b"][t]["truncated"] == trunc]
            ya = np.array([idx["7b"][t][key] for t in ids], bool); yb = np.array([idx["32b"][t][key] for t in ids], bool)
            b01 = int((~ya & yb).sum()); b10 = int((ya & ~yb).sum()); _, p = mcnemar_exact(b10, b01)
            R["trend_by_trunc"][f"{'trunc' if trunc else 'full'}|{judge}"] = dict(
                n=len(ids), delta_pts=(yb.mean() - ya.mean()) * 100 if len(ids) else float("nan"), p=p)
    # Exec + CorePass-ExecHarm
    core = {(r["model"], r["task_id"]): r for r in rows}
    R["exec"] = {}; R["core_vs_exec"] = {}; R["mex_oracle"] = {}
    for m in MODELS:
        ex = load(os.path.join(data, f"results/phase2_exec_qwen2.5-{m}/results_qwen2.5-{m}_D0.json"))["results"]
        harm = [bool(r["metrics"]["HarmCompletion-ASR"]) for r in ex]
        R["exec"][m] = dict(
            n=len(ex),
            HarmCompletion=float(np.mean(harm)),
            StateChange=float(np.mean([bool(r["metrics"]["StateChange-ASR"]) for r in ex])),
            ToolCall=float(np.mean([bool(r["metrics"]["ToolCall-ASR"]) for r in ex])),
            Blocked=int(sum(bool(r["metrics"]["Blocked-by-Harness"]) for r in ex)))
        for judge, key in [("DeepSeek", "ds_success"), ("Haiku", "hk_success")]:
            cp = np.array([bool(core[(m, r["case_id"])][key]) for r in ex])
            eh = np.array(harm)
            R["core_vs_exec"][f"{judge}|{m}"] = dict(
                corepass=float(cp.mean()), execharm=float(eh.mean()),
                both=int((cp & eh).sum()), corepass_only=int((cp & ~eh).sum()),
                execharm_only=int((~cp & eh).sum()), neither=int((~cp & ~eh).sum()),
                P_corepass_given_execharm=float((cp & eh).sum() / eh.sum()) if eh.sum() else float("nan"),
                P_execharm_given_corepass=float((cp & eh).sum() / cp.sum()) if cp.sum() else float("nan"))
        mex = [r for r in ex if r["attack_type"] == "MEX"]
        ids = [r["case_id"] for r in mex]
        R["mex_oracle"][m] = dict(
            n=len(ids),
            ds=float(np.mean([core[(m, i)]["ds_success"] for i in ids])),
            hk=float(np.mean([core[(m, i)]["hk_success"] for i in ids])),
            exec_harm=float(np.mean([bool(r["metrics"]["HarmCompletion-ASR"]) for r in mex])))
    # calibration confound (serial today vs July; flag broken parallel file)
    R["calibration"] = {}
    ser = load(os.path.join(data, "results/calib_7b_serial30/results_qwen2.5-7b_D0.json"))
    par = load(os.path.join(data, "results/calib_7b_parallel/results_qwen2.5-7b_D0.json"))
    uni7 = load(os.path.join(data, "results/final/qwen2.5-7b_uniform.json"))
    sdict = {r["task_id"]: bool(r["evaluation"]["attack_success"]) for r in ser}
    july = {r["task_id"]: bool(r["evaluation_prev"]["attack_success"]) for r in uni7}
    ds_rejudge = {r["task_id"]: bool(r["evaluation"]["attack_success"]) for r in uni7}
    par_null = sum((r["evaluation"] or {}).get("attack_success") is None for r in par)
    ids = sorted(sdict)
    sv = np.array([sdict[i] for i in ids]); jv = np.array([july[i] for i in ids]); dv = np.array([ds_rejudge[i] for i in ids])
    b01 = int((~dv & sv).sum()); b10 = int((dv & ~sv).sum()); _, p = mcnemar_exact(b10, b01)
    R["calibration"] = dict(
        n=len(ids), parallel_null_verdicts=par_null, parallel_total=len(par),
        asr_july_origjudge=float(jv.mean()), asr_deepseek_rejudge_july=float(dv.mean()),
        asr_serial_today=float(sv.mean()),
        agreement_serial_vs_rejudgeJuly=float((sv == dv).mean()),
        build_effect_pts=float((sv.mean() - dv.mean()) * 100), build_effect_p=p,
        note="parallel calib file unusable: %d/%d verdicts are 'Judge parse error' nulls" % (par_null, len(par)))
    return R

# ----------------------------------------------------------------------------- figures
def make_figures(R, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    OK = dict(orange="#E69F00", blue="#0072B2", green="#009E73", vermillion="#D55E00",
              purple="#CC79A7", yellow="#F0E442", sky="#56B4E9", black="#000000")
    # match the interactive report's validated CVD-safe palette
    DS, HK, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
    os.makedirs(outdir, exist_ok=True)
    themes = dict(
        light=dict(bg="#FFFFFF", fg="#1A1A1A", grid="#CCCCCC", muted="#666666"),
        dark=dict(bg="#161616", fg="#F2F2F2", grid="#444444", muted="#AAAAAA"))

    def style(theme):
        t = themes[theme]
        plt.rcParams.update({
            "figure.facecolor": t["bg"], "axes.facecolor": t["bg"], "savefig.facecolor": t["bg"],
            "text.color": t["fg"], "axes.labelcolor": t["fg"], "axes.edgecolor": t["muted"],
            "xtick.color": t["fg"], "ytick.color": t["fg"], "grid.color": t["grid"],
            "font.size": 11, "axes.titlesize": 13, "axes.grid": True, "grid.alpha": 0.5,
            "axes.spines.top": False, "axes.spines.right": False})
        return t

    def savef(fig, name, theme, tight=True):
        if tight:
            fig.tight_layout()
        fig.savefig(os.path.join(outdir, f"{name}_{theme}.png"), dpi=200, bbox_inches="tight"); plt.close(fig)

    labels = ["7B", "14B", "32B"]; xpos = np.arange(3)
    for theme in ("light", "dark"):
        t = style(theme)

        # Fig 1: ASR by model and judge, Wilson CIs
        fig, ax = plt.subplots(figsize=(7, 4.6))
        for j, (judge, col) in enumerate([("DeepSeek", DS), ("Haiku", HK)]):
            a = [R["asr"][f"{judge}|{m}"]["asr"] * 100 for m in MODELS]
            lo = [(R["asr"][f"{judge}|{m}"]["asr"] - R["asr"][f"{judge}|{m}"]["wilson"][0]) * 100 for m in MODELS]
            hi = [(R["asr"][f"{judge}|{m}"]["wilson"][1] - R["asr"][f"{judge}|{m}"]["asr"]) * 100 for m in MODELS]
            ax.bar(xpos + (j - 0.5) * 0.36, a, 0.34, yerr=[lo, hi], capsize=4, color=col,
                   label=judge, edgecolor=t["bg"], linewidth=0.5)
        ax.set_xticks(xpos); ax.set_xticklabels(labels); ax.set_ylabel("Core attack-success rate (%)")
        ax.set_ylim(0, 100); ax.set_title("Core ASR by model size and judge (95% Wilson CI)")
        ax.legend(frameon=False)
        savef(fig, "fig1_asr_by_model_judge", theme)

        # Fig 2: family heatmaps (DeepSeek, Haiku)
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
        cmap = matplotlib.colormaps["cividis"]
        for ax, judge in zip(axes, ["DeepSeek", "Haiku"]):
            M = np.array([[R["family_asr"][f"{f}|{judge}"][i] * 100 for i in range(3)] for f in FAMILIES])
            im = ax.imshow(M, cmap=cmap, vmin=0, vmax=100, aspect="auto")
            ax.set_xticks(range(3)); ax.set_xticklabels(labels); ax.set_yticks(range(6)); ax.set_yticklabels(FAMILIES)
            ax.set_title(f"{judge}  ASR % by family"); ax.grid(False)
            for i in range(6):
                for k in range(3):
                    v = M[i, k]; ax.text(k, i, f"{v:.0f}", ha="center", va="center",
                                         color="white" if v < 55 else "black", fontsize=9)
        fig.colorbar(im, ax=axes, fraction=0.046, pad=0.04, label="ASR %")
        savef(fig, "fig2_family_heatmap", theme, tight=False)

        # Fig 3: agreement & kappa vs size
        fig, ax = plt.subplots(figsize=(7, 4.4))
        agr = [R["agreement"][m]["agreement"] * 100 for m in MODELS]
        kap = [R["agreement"][m]["kappa"] for m in MODELS]
        ax.plot(xpos, agr, "-o", color=OK["green"], label="% agreement")
        ax.set_ylabel("Judge agreement (%)", color=OK["green"]); ax.set_ylim(60, 100)
        ax.set_xticks(xpos); ax.set_xticklabels(labels)
        ax2 = ax.twinx(); ax2.plot(xpos, kap, "--s", color=OK["vermillion"], label="Cohen's κ")
        ax2.set_ylabel("Cohen's κ", color=OK["vermillion"]); ax2.set_ylim(0, 1); ax2.grid(False)
        ax.set_title("DeepSeek–Haiku agreement falls as model size rises")
        savef(fig, "fig3_agreement_vs_size", theme)

        # Fig 4: truncation effect on the judge gap
        fig, ax = plt.subplots(figsize=(7.4, 4.6))
        gap_full = [(R["truncation"][f"full|{m}"]["ds"] - R["truncation"][f"full|{m}"]["hk"]) * 100 for m in MODELS]
        gap_tr = [(R["truncation"][f"trunc|{m}"]["ds"] - R["truncation"][f"trunc|{m}"]["hk"]) * 100 for m in MODELS]
        ax.bar(xpos - 0.2, gap_full, 0.38, color=OK["sky"], label="non-truncated", edgecolor=t["bg"])
        ax.bar(xpos + 0.2, gap_tr, 0.38, color=OK["purple"], label="truncated (@2000 chars)", edgecolor=t["bg"])
        ax.set_xticks(xpos); ax.set_xticklabels(labels); ax.set_ylabel("DeepSeek − Haiku ASR gap (pts)")
        ax.set_title("The judge gap is a truncation artefact")
        ax.legend(frameon=False)
        savef(fig, "fig4_truncation_effect", theme)

        # Fig 5: Core (semantic) vs Exec (oracle) ASR
        fig, ax = plt.subplots(figsize=(7.4, 4.6))
        ds = [R["core_vs_exec"][f"DeepSeek|{m}"]["corepass"] * 100 for m in MODELS]
        hk = [R["core_vs_exec"][f"Haiku|{m}"]["corepass"] * 100 for m in MODELS]
        ex = [R["exec"][m]["HarmCompletion"] * 100 for m in MODELS]
        ax.plot(xpos, ds, "-o", color=DS, label="Core semantic / DeepSeek")
        ax.plot(xpos, hk, "-o", color=HK, label="Core semantic / Haiku")
        ax.plot(xpos, ex, "-s", color=AQUA, label="Exec HarmCompletion (oracle)")
        ax.set_xticks(xpos); ax.set_xticklabels(labels); ax.set_ylabel("Success / harm rate (%)")
        ax.set_ylim(0, 100)
        ax.set_title("Semantic Core overcounts execution harm (same 60 mapped cases)")
        ax.legend(frameon=False, fontsize=9)
        savef(fig, "fig5_core_vs_exec", theme)
    return outdir

# ----------------------------------------------------------------------------- printing
def print_report(R):
    def pct(x): return f"{x*100:.1f}%"
    print("\n==================== INTEGRITY ====================")
    for m in MODELS:
        i = R["integrity"][m]
        print(f"  {m}: n={i['n']} unique={i['unique_ids']} ds_null={i['ds_null']} hk_null={i['hk_null']} "
              f"truncated={i['truncated']} DeepSeek-copy-consistency={i['deepseek_consistency']}/{i['n']}")
    print("\n==================== CORE ASR (Wilson / bootstrap) ====================")
    for judge in ["DeepSeek", "Haiku"]:
        for m in MODELS:
            a = R["asr"][f"{judge}|{m}"]
            print(f"  {judge:9s} {m:4s}: {pct(a['asr'])}  Wilson[{a['wilson'][0]*100:.1f},{a['wilson'][1]*100:.1f}]  "
                  f"boot[{a['boot'][0]*100:.1f},{a['boot'][1]*100:.1f}]  ({a['k']}/{a['n']})")
    print("\n==================== PAIRED McNEMAR (overall, Holm within judge) ====================")
    for judge in ["DeepSeek", "Haiku"]:
        for k, v in R["mcnemar"][judge].items():
            print(f"  {judge:9s} {k:9s}: Δ={v['delta_pts']:+5.1f}pts up:{v['up']:3d} down:{v['down']:3d} "
                  f"p={v['p']:.3g} p_holm={v['p_holm']:.3g}")
    print("\n==================== GEE LOGISTIC TREND (size ordinal, CR SE by case) ====================")
    for judge in ["DeepSeek", "Haiku"]:
        t = R["trend"][judge]
        print(f"  {judge:9s}: OR/size-step={t['OR']:.3f} [{t['OR_ci'][0]:.3f},{t['OR_ci'][1]:.3f}] "
              f"beta={t['beta_size']:+.3f} (SE {t['se_size']:.3f}) p={t['p_size']:.3g}")
    print("\n==================== PER-FAMILY ASR (7b/14b/32b) ====================")
    for f in FAMILIES:
        ds = "/".join(f"{R['family_asr'][f'{f}|DeepSeek'][i]*100:.0f}" for i in range(3))
        hk = "/".join(f"{R['family_asr'][f'{f}|Haiku'][i]*100:.0f}" for i in range(3))
        print(f"  {f}: DeepSeek {ds}   Haiku {hk}")
    print("\n==================== PER-FAMILY 7b->32b (Holm across families) ====================")
    for judge in ["DeepSeek", "Haiku"]:
        print(f"  -- {judge} --")
        for f in FAMILIES:
            v = R["family_mcnemar"][judge][f]
            sig = "*" if v["p_holm"] < 0.05 else " "
            print(f"    {f}: Δ={v['delta_pts']:+5.1f}pts p_holm={v['p_holm']:.3g} {sig}")
    print("\n==================== AGREEMENT / KAPPA ====================")
    for m in MODELS:
        print(f"  {m}: agreement={pct(R['agreement'][m]['agreement'])} kappa={R['agreement'][m]['kappa']:.2f}")
    for f in FAMILIES:
        a = R["agreement_family"][f]
        print(f"    {f}: agree={pct(a['agreement'])} kappa={a['kappa']:.2f} DS={pct(a['ds'])} HK={pct(a['hk'])}")
    print("\n==================== DISAGREEMENT FORENSICS ====================")
    d = R["disagreement"]
    print(f"  DS-yes/HK-no={d['ds_yes_hk_no']}  DS-no/HK-yes={d['ds_no_hk_yes']}")
    print(f"  truncation rate: disagree={pct(d['trunc_rate_disagree'])} agree={pct(d['trunc_rate_agree'])}")
    print(f"  by family: {d['by_family']}")
    print(f"  DS harm_evidence in DS-yes/HK-no: {d['ds_hec_in_disc']}")
    print(f"  HK defense_behavior in DS-yes/HK-no: {d['hk_defbeh_in_disc']}")
    print("\n==================== TRUNCATION-STRATIFIED ====================")
    for lab in ["full", "trunc"]:
        print(f"  -- {'non-truncated' if lab=='full' else 'truncated'} --")
        for m in MODELS:
            s = R["truncation"][f"{lab}|{m}"]
            print(f"    {m}: n={s['n']:3d} DS={pct(s['ds'])} HK={pct(s['hk'])} gap={ (s['ds']-s['hk'])*100:.1f}pts agree={pct(s['agree'])}")
    print("  7b->32b trend within truncation strata:")
    for lab in ["full", "trunc"]:
        for judge in ["DeepSeek", "Haiku"]:
            s = R["trend_by_trunc"][f"{lab}|{judge}"]
            print(f"    {'non-trunc' if lab=='full' else 'trunc'} {judge:9s}: n={s['n']} Δ={s['delta_pts']:+.1f}pts p={s['p']:.3g}")
    print("\n==================== EXEC + CORE-vs-EXEC ====================")
    for m in MODELS:
        e = R["exec"][m]
        print(f"  {m}: HarmComp={pct(e['HarmCompletion'])} StateChg={pct(e['StateChange'])} ToolCall={pct(e['ToolCall'])} Blocked={e['Blocked']}/60")
    for judge in ["DeepSeek", "Haiku"]:
        for m in MODELS:
            c = R["core_vs_exec"][f"{judge}|{m}"]
            print(f"  {judge:9s} {m}: CorePass={pct(c['corepass'])} ExecHarm={pct(c['execharm'])} "
                  f"P(CorePass|ExecHarm)={pct(c['P_corepass_given_execharm'])} P(ExecHarm|CorePass)={pct(c['P_execharm_given_corepass'])}")
    print("  MEX judges vs oracle (n=10/model):")
    for m in MODELS:
        o = R["mex_oracle"][m]
        print(f"    {m}: DeepSeek={pct(o['ds'])} Haiku={pct(o['hk'])} ExecOracle={pct(o['exec_harm'])}")
    print("\n==================== CALIBRATION / ENVIRONMENT CONFOUND ====================")
    c = R["calibration"]
    print(f"  n={c['n']}  parallel file nulls={c['parallel_null_verdicts']}/{c['parallel_total']}  ({c['note']})")
    print(f"  ASR July(orig judge)={pct(c['asr_july_origjudge'])}  DeepSeek-rejudge-July={pct(c['asr_deepseek_rejudge_july'])}  serial-today={pct(c['asr_serial_today'])}")
    print(f"  build effect (serial-today vs DeepSeek-rejudge-July, same judge)={c['build_effect_pts']:+.1f}pts p={c['build_effect_p']:.3g}  agreement={pct(c['agreement_serial_vs_rejudgeJuly'])}")

# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--data", default=os.environ.get("SCB_DATA", here))
    ap.add_argument("--out", default=os.path.join(here, "out"))
    a = ap.parse_args()
    rows = build_frame(a.data)
    R = analyse(rows, a.data)
    os.makedirs(a.out, exist_ok=True)
    json.dump(R, open(os.path.join(a.out, "results.json"), "w"), indent=2)
    print_report(R)
    make_figures(R, os.path.join(a.out, "figures"))
    print(f"\nWrote {os.path.join(a.out,'results.json')} and figures/ (light+dark PNG).")

if __name__ == "__main__":
    main()
