# SafeClawBench · Qwen2.5 scaling study

> **Status: report v1.** Written before the same-environment follow-up, which was pre-registered in commit `fa4fe71` (see [`PREREGISTRATION_followup.md`](PREREGISTRATION_followup.md)). Two claims below are exactly what that follow-up tests, and this page will be updated according to its decision rules. Independent work; not affiliated with the SafeClawBench authors.

**Does making an open-weight model bigger make it a safer or riskier agent?**

I ran the 600-scenario [SafeClawBench](https://arxiv.org/abs/2606.18356) Semantic Core and the
60-scenario Exec-Balanced track against Qwen2.5 **7B / 14B / 32B** (GGUF Q4_K_M, Ollama, defence
**D0** — no added guardrails), scored every Core response with **two independent LLM judges**
(DeepSeek and Claude Haiku 4.5), and cross-checked against the benchmark's deterministic sandbox
oracles. Short version:

- **Bigger scored as riskier, not safer, under both judges.** Semantic attack-success rose from 7B→32B by **+17 points**
  (DeepSeek) / **+9.5 points** (Haiku); the trend is monotonic and significant under both judges
  (GEE odds ratio per size step 1.70 and 1.30, both p < 10⁻⁴).
- **The two judges disagreed a lot, and the gap sits almost entirely in truncated responses.** On responses not cut
  off at the 2,000-character cap the judges land within 5–10 points and agree on an ~11-point
  7B→32B rise; the big gap (22–27 points) only appears on truncated responses, which hit 32B hardest
  (63% truncated vs 45% at 7B). Whether truncation actually causes the gap is what the pre-registered follow-up tests.
- **"Attack succeeded" is a definition, not a fact.** Semantic "the model complied" roughly doubles
  the sandbox "harm actually happened" rate (95% vs 48% at 32B).
- **One family (MEX) drives the disagreement**, and the sandbox (≈0% real harm there) points toward
  the stricter judge for that family.
- **No size effect at the execution layer** (43/43/48%, n=60, wide intervals) — the scaling signal
  lives in semantic grading only.

**📊 [Read the interactive report](report/index.html)** (also publishable via GitHub Pages).

This distinguishes **model-layer** findings (the model's own susceptibility under D0) from
**infrastructure-layer** concerns (sandboxing, approval gates) throughout — only the former is
measured here.

---

## Key findings in one figure each

### 1 · Scaling up raised attack-success, under both judges
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/fig1_asr_by_model_judge_dark.png">
  <img alt="Grouped bar chart of Core attack-success rate by model size for both judges with 95% confidence intervals. DeepSeek rises 68.5 to 74.0 to 85.5 percent across 7B, 14B, 32B; Haiku rises 55.5 to 58.5 to 65.0 percent. Both trends go up with size." src="figures/fig1_asr_by_model_judge_light.png" width="640">
</picture>

### 2 · The judge gap sits almost entirely in truncated responses
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/fig4_truncation_effect_dark.png">
  <img alt="Bar chart of the DeepSeek minus Haiku attack-success gap, split by whether the response was truncated. On non-truncated responses the gap is 5 to 10 points; on truncated responses it is 22 to 27 points, across all three model sizes." src="figures/fig4_truncation_effect_light.png" width="640">
</picture>

### 3 · Semantic grading overcounts execution harm
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/fig5_core_vs_exec_dark.png">
  <img alt="Line chart on the 60 mapped scenarios. Two semantic-judge lines (DeepSeek, Haiku) rise with size and sit well above a flat green execution-harm line at about 43 to 48 percent. At 32B DeepSeek reaches 95 percent against 48 percent observed harm." src="figures/fig5_core_vs_exec_light.png" width="640">
</picture>

### 4 · Where the attacks land (MEX is the outlier)
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/fig2_family_heatmap_dark.png">
  <img alt="Two heatmaps of attack-success by family and size, one per judge. Most families are high under both judges, but the MEX row drops from 50 to 70 percent under DeepSeek to 12 to 18 percent under Haiku." src="figures/fig2_family_heatmap_light.png" width="720">
</picture>

### 5 · Judge agreement falls as models get larger
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/fig3_agreement_vs_size_dark.png">
  <img alt="Line chart showing judge percentage agreement falling slightly and Cohen's kappa falling from 0.59 at 7B to 0.44 at 32B as model size increases." src="figures/fig3_agreement_vs_size_light.png" width="640">
</picture>

See [`data/summary_tables.md`](data/summary_tables.md) for every number with intervals.

---

## Reproduce

```bash
pip install numpy scipy matplotlib
python3 analysis/analysis.py --data ./data --out ./out
# regenerates out/results.json, all tables (stdout), and figures/ (light + dark PNG)
```

The analysis reads the released per-case verdicts; it needs no GPU. To regenerate the *responses*
you need the benchmark (not redistributed here — see below) and an Ollama host with the three Qwen2.5
sizes.

The monotonic-trend test is a population-averaged (GEE) logistic with cluster-robust (CR1) standard
errors by scenario, implemented directly in `analysis.py` (no `statsmodels` dependency).

### Costs

| Step | Hardware | Rough cost |
|---|---|---|
| Generate 600 Core + 60 Exec per size | A40, ~$0.59/h on-demand | a few $ total |
| Pre-registered follow-up: 120 cases × 3 sizes in one environment, full-length responses (`docs/runbook_followup.md`) | A40 + Haiku/DeepSeek API | about $0.9 GPU + $1–1.4 Haiku, ~1.5 h |
| Re-grade from saved responses | API only | judge API cost |
| Run `analysis.py` | any laptop | free |

---

## What's in here

```
README.md                    this page
PREREGISTRATION_followup.md  hypotheses and decision rules for the follow-up, committed before running it
report/                      the interactive report (index.html), the paper (PDF, DOCX), the findings memo, verification notes
analysis/                    analysis.py (all tables + figures) and score_adjudication.py
data/                        aggregated tables + per-scenario verdicts & metrics (NO raw model responses)
figures/                     static PNG exports (light + dark) used in this README
kit/                         installers that write every pod-side script, plus the scripts run after them
docs/                        runbooks: how the main study and the follow-up are run
CITATION.cff                 how to cite
```

**What is deliberately *not* here:** raw model responses, the attack prompts, and
`benchmark_v5_600.json`. The benchmark is © its authors — get it from the
[Hugging Face dataset](https://huggingface.co/datasets/sairights/safeclawbench) under its own licence
terms. Only aggregated results and per-scenario *verdicts/metrics* are released.

## How much to trust it

Full caveats are in the [report](report/index.html). In brief: neither judge is ground truth; the
2,000-char truncation touches ~half of responses; 7B/14B were generated in July and 32B in October,
so a serving-environment difference is confounded with size (bounded at ~+10 points, not
statistically distinguishable from zero, measured only on 7B); one sample per scenario; Exec is n=60.

## Licence & attribution

My analysis code, figures and report are released under the **MIT Licence** (see [`LICENSE`](LICENSE)).

This work **extends SafeClawBench** — Tian et al., 2026, [arXiv:2606.18356](https://arxiv.org/abs/2606.18356),
MIT-licensed. The benchmark design, attack taxonomy and Exec oracles are theirs. If you use this
repo, please cite both it ([`CITATION.cff`](CITATION.cff)) and the original paper.
