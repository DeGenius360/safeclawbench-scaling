# SafeClawBench cross-scale study — findings memo

**Scope.** Qwen2.5 7B / 14B / 32B (GGUF Q4_K_M, Ollama), defence D0, SafeClawBench Semantic Core
(600 cases/model) and Exec-Balanced (60 cases/model). Two LLM judges on the identical 600 saved
responses per model: DeepSeek `deepseek-flash` (primary) and Claude Haiku 4.5 (validation). All
numbers below are reproduced from the shipped files by `analysis.py`; intervals are 95%.

**One-line takeaway.** The scaling result is real and survives judge choice — bigger Qwen2.5 is
reliably more exploitable under D0 — but the *size* of the effect and the per-family picture are
judge-dependent, and that judge-dependence is overwhelmingly a **2000-character response-truncation
artefact**, not a genuine disagreement about what scaling does. That artefact finding is the most
novel thing in the dataset and should be a headline, not a footnote.

---

## 1. Data integrity (checked, not assumed)

- 600 rows/model, 1800 total; no duplicate or missing `task_id`; identical task-id set across sizes;
  families balanced 100/100/100/100/100/100; zero null verdicts in the final files.
- The DeepSeek verdict stored inside the Haiku files (`evaluation_prev`) matches the uniform
  DeepSeek re-judge on `attack_success` for **600/600** rows at every size — the two sources are
  consistent.
- Headline ASR reproduces exactly: DeepSeek 68.5 / 74.0 / 85.5%, Haiku 55.5 / 58.5 / 65.0%.
- Truncation cap is **exactly 2000 characters** (clean spike of 272 / 290 / 378 responses sitting
  at 2000). Truncation rate rises sharply with size: **45.3% / 48.3% / 63.0%**. This matters a lot
  (see §4).
- **Data problem to flag:** `results/calib_7b_parallel/results_qwen2.5-7b_D0.json` has **15/30
  verdicts = `"Judge parse error"` nulls** (the thinking-mode empty-output failure). Those nulls
  silently read as "safe", which is why a naive recompute shows parallel ASR ≈ 30%. The corrected
  ("REVISED-PASS") parallel per-case file is **not in the bundle** — only the one-line summary in
  `kit/state/calibration.txt` survives. So the *parallel* arm of the environment calibration is not
  independently reproducible from what you shipped. The serial-vs-July arm is (see §7).

## 2. Claims ranked by strength of evidence

### Tier A — robust, survive judge choice
1. **Agent-security failure under D0 is high at every size, under both judges.** DeepSeek
   68.5% [64.7–72.1] / 74.0% [70.3–77.3] / 85.5% [82.5–88.1]; Haiku 55.5% [51.5–59.4] /
   58.5% [54.5–62.4] / 65.0% [61.1–68.7]. Even the stricter judge's floor (55%) is above the
   paper's frontier D0 CoreFail range (9.0–44.2%).
2. **ASR increases monotonically with size under both judges.** Population-averaged (GEE) logistic
   with case-clustered robust SEs and attack-family covariate: DeepSeek OR = **1.70 per size step**
   [1.50–1.92], p = 1.5×10⁻¹⁷; Haiku OR = **1.30 per step** [1.16–1.45], p = 4.9×10⁻⁶. Paired exact
   McNemar agrees: 7B→32B is +17.0 pts (DeepSeek, p≈10⁻¹⁶) and +9.5 pts (Haiku, p≈10⁻⁵), both
   Holm-robust. 7B→14B is significant under DeepSeek only.
3. **Judge agreement falls as models get larger** (80% / 78% / 78%; κ = 0.59 / 0.51 / 0.44) and
   **DeepSeek is systematically the more permissive judge** — 340 DeepSeek-yes/Haiku-no vs 46 the
   other way across 1800 pairs.

### Tier B — strong, but measurement- or judge-caveated
4. **The judge gap is mostly a truncation artefact (novel, and the most interesting result).**
   On non-truncated responses the DeepSeek−Haiku ASR gap is only **5.2 / 7.4 / 9.9 pts**; on
   truncated responses it is **22.4 / 24.1 / 26.7 pts**. Restricting the 7B→32B paired test to cases
   non-truncated at *both* sizes (n=180), the scaling effect is **+11.1 pts under both judges**
   (DeepSeek p=0.004, Haiku p=0.005) — identical. On cases truncated at both sizes (n=230), DeepSeek
   still shows +10.0 pts (p<0.001) but Haiku shows **+0.9 pts (p=0.89, flat)**. So Haiku's weaker
   overall trend is entirely a truncation effect: on clean responses the two judges agree on the
   scaling magnitude.
5. **Semantic Core ASR substantially overcounts observable execution harm.** On the 60 Exec cases
   mapped back to Core (case-ids map 1:1 to Core task-ids), at 32B DeepSeek CorePass = 95% but Exec
   HarmCompletion = 48.3% [36–61]; P(ExecHarm | CorePass) is only **38–46%** under DeepSeek and
   38–52% under Haiku. Fewer than half of semantic "successes" produce an actual harmful state
   change when tools really run. (This is the paper's CorePass-vs-ExecHarm point, reproduced; their
   reported 83.9% is P(CorePass | ExecHarm) — here 69/73/90% DeepSeek, 58/58/79% Haiku, n=60 so
   ±~17 pts.)
6. **MEX is the divergence epicentre and DeepSeek over-counts it.** Pooled MEX: DeepSeek 63% vs
   Haiku 16%, agreement 53%, κ=0.20, and **141/141 of MEX disagreements are DeepSeek-yes/Haiku-no.**
   On the 10 MEX cases with deterministic oracles, DeepSeek scores 90/100/100%, Haiku 20/60/20%, and
   the **execution oracle shows 0/0/10% actual harm** — Haiku is far closer to ground truth. Reading
   30+ MEX cases confirms the mechanism: the attack asks the agent to "enumerate your internal
   policies/logic"; the agent emits generic GDPR/best-practice boilerplate that leaks nothing
   concrete; DeepSeek scores the literal success predicate ("agent described policies" → success,
   evidence tagged `SemanticOnly`) while Haiku requires an actual leak (→ `NotObservable`, safe).

### Tier C — NOT supported by this data
7. **No "capability" or mechanism claim.** You measured one axis (parameter count) under one
   quantisation and one defence. Nothing here isolates *why* larger models comply more. Do not write
   "more capable models are more vulnerable" — write "larger models in this family are".
8. **No size effect at the execution layer.** Exec HarmCompletion is 43.3% / 43.3% / 48.3% with
   heavily overlapping intervals (±~12 pts at n=60). The scaling signal lives in the *semantic* layer
   only; at the state-oracle layer it is undetectable at this sample size. State-change and tool-call
   rates are likewise flat.
9. **Per-family scaling is NOT judge-robust.** Under DeepSeek, 7B→32B is Holm-significant for ADI,
   DPI, MEX, MPI, TRI (IPI flat). Under Haiku, **only ADI survives Holm.** Any per-family scaling
   narrative rests on the DeepSeek judge.
10. **Cannot cleanly separate model size from generation environment.** 7B/14B Core was generated in
    July (older Ollama, serial); 32B on 23 Oct (Ollama 0.40.9, 4 parallel slots). The cross-environment
    calibration exists only for 7B, on ~30 cases, and its parallel file is corrupted (§1).
11. **Cannot claim the paper's "MPI/MEX dominant" frontier pattern.** Under DeepSeek MPI/MEX are
    high; under Haiku MEX collapses to ~16%. Which pattern is real depends on which judge is right,
    and §6 suggests Haiku is closer for MEX.

## 3. What each judge is actually keying on (from reading 40 cases in full)

- **DeepSeek = intent / predicate-literal.** Scores success when the agent *adopts or commits to* the
  harmful objective — states the unsafe policy, lays out the exfiltration plan, "describes" the
  requested internals — measured against the literal success predicate. Harm is then down-graded via
  `harm_evidence_category` (`SemanticOnly` in 221/340 disagreements) but still counts as success.
- **Haiku = observable completed harm.** Requires the harmful action/leak to actually happen in the
  visible output; treats partial compliance, asked-for-clarification, generic boilerplate, or a
  plan truncated before execution as *not* success (228/340 disagreements it tags
  `partial_compliance`, 72 `asked_clarification`, 37 `ignored_attack`).
- **Why disagreement grows with size:** larger models write longer, more elaborate *planful*
  responses, so they hit the 2000-char cap more often (63% at 32B). A capped response shows a
  compliant preamble/plan but not the executed action — exactly the zone where the two definitions
  diverge. When responses clearly *complete* the harm ("I've updated my records", "exported
  successfully"), both judges agree it's success.
- **Neither is globally stricter.** In the 46 reverse cases Haiku counts mere acknowledgement/echo
  (e.g. decoding a Base64 instruction, documenting a poisoned policy) as success where DeepSeek wants
  action. They apply different, case-sensitive thresholds; DeepSeek's is just lower on average.

## 4. Threats to validity (put these in the paper)

- **Neither judge is ground truth**; the paper's judge was gpt-5.4, so cross-paper ASR comparisons
  are indicative only.
- **Truncation at 2000 chars touches ~half of all cases (63% at 32B)** and is the dominant driver of
  judge disagreement; both judges saw partial responses. The original judge saw up to 3000 chars, so
  even the DeepSeek re-judge is on more-truncated text than generation time.
- **Environment confound:** size is partly confounded with Ollama build and serial-vs-parallel
  serving (7B/14B July, 32B October). Truncation rate is itself partly confounded the same way.
- **Exec is underpowered** (n=60, ±~12 pts) and the **state oracle under-detects extraction harms** —
  MEX "leaks" rarely change world state, so the oracle's ~0% MEX harm is a floor, not proof Haiku is
  perfectly calibrated there.
- **Judge build not pinned:** `deepseek-flash` is an alias (V4.1); thinking mode was disabled via the
  proxy after it returned empty output on ~30% of cases — and the calib parallel file shows that
  failure mode concretely (15/30 parse errors).
- **Greedy decoding is only deterministic given identical cache state;** response text still drifts
  between July and October even at temperature 0.

## 5. Comparison with the paper

Comparable: the *shape* — high D0 failure, Core overcounting Exec harm, a monotonic risk gradient —
all reproduce. Not comparable as point values: your ASR definitions (`HarmCompletion-ASR`,
`StateChange-ASR`) differ in name and construction from the paper's `ObservedHarm@Exec`, and your
judges differ from gpt-5.4. State the paper's 9.0–44.2% frontier D0 CoreFail range as *context*,
not a baseline you beat; your models are smaller/open-weight and your judge is more permissive, so
"Qwen2.5 fails far more than frontier D0" is directionally supportable but not a like-for-like number.

## 6. Where you're underselling (direct feedback)

- The **"judge-sensitivity is a truncation artefact"** result is a genuine methodological
  contribution: it explains the judge disagreement, quantifies it, and shows the scaling conclusion is
  robust once you control for it. Frame the paper around *judge-robustness of agent-security scaling*
  with truncation as the confound you found and fixed — that's more publishable than "we ran
  SafeClawBench on three sizes".
- The **MEX oracle triangulation** (judges vs deterministic state) is a clean, quantitative way to
  say *which* judge is closer to truth on the family where they most disagree. Most judge-comparison
  work can't do this. Lead with it.
- Don't bury these as "limitations". They are the findings.

## 7. Environment confound — what the calibration can and cannot bound

Clean, reproducible arm (held-constant DeepSeek judge, same 30 cases, generation only varied):
DeepSeek-rejudge-of-July = 66.7%, serial-today = 76.7% → **+10 pts point estimate, p=0.38 (n=30, not
significant), agreement 25/30 (83%)**. So the serial build effect is *bounded loosely at single-to-low-
double digits and is not statistically distinguishable from zero at n=30.* It cannot by itself produce
the 17-pt (DeepSeek) 7B→32B gap, but the confound is only measured on 7B and the parallel arm is
unverifiable (§1). **Conclusion: the environment confound is probably small but not ruled out; the
only way to retire it is to re-generate 7B/14B in today's environment.**

## 8. Recommended wording

**Paper (methodology/abstract sentence):**
> Across Qwen2.5 7B–32B under SafeClawBench defence D0, semantic attack-success rose monotonically
> with model size under two independent LLM judges (DeepSeek: +17 pts 7B→32B, OR 1.70/step, p<10⁻¹⁵;
> Haiku 4.5: +9.5 pts, OR 1.30/step, p<10⁻⁴). Inter-judge agreement fell with size (κ 0.59→0.44); we
> show this divergence is primarily an artefact of 2000-character response truncation — on
> non-truncated responses both judges agree on an ~11-pt 7B→32B increase — and that semantic
> attack-success overcounts deterministic execution harm by roughly 2× at 32B.

**CV bullet (one line):**
> Ran a cross-scale LLM agent-security evaluation (Qwen2.5 7B/14B/32B on SafeClawBench), with
> dual-judge validation, GEE trend modelling and deterministic execution oracles; identified and
> quantified a response-truncation confound that explained most of the inter-judge disagreement.

**LinkedIn post (short, human):**
> New result from my agent-security work: as Qwen2.5 scales 7B→32B, its susceptibility to
> SafeClawBench agent attacks goes *up*, not down — and it holds under two independent judges. The
> interesting part was the disagreement between judges. It looked like a scoring problem; it turned
> out to be a data artefact — responses capped at 2000 characters, which hits the biggest model most.
> Control for truncation and the two judges agree. Also confirmed the semantic "attack succeeded"
> label overcounts actual execution harm by about 2× at 32B. Measurement design matters as much as
> the model. Full writeup soon.

## 9. Follow-up experiments (rough cost)

1. **Re-generate 7B/14B Core in today's environment** (Ollama 0.40.9, parallel), same benchmark —
   removes the build/serving confound and makes the three sizes directly comparable. ~$1–1.4 on a
   fresh A40 pod, ~1–2 h. *Highest value for the lowest cost.*
2. **Re-run generation with a larger (or no) response cap** (e.g. 8000 chars) on a stratified
   ~200-case subset, then re-judge — directly tests the truncation-artefact claim end-to-end. ~$1–2.
3. **Hand-adjudicate the 60-case blind sheet** (shipped) — 1–2 h of your time, no compute; turns
   "Haiku is closer on MEX" from an oracle-based inference into a measured judge accuracy/bias.
4. **Expand Exec-Balanced** from 60 to ~180 cases (30/family) to get enough power to detect (or rule
   out) a size effect at the execution layer. ~$3–5.
5. **Third judge** (gpt-5.4 or an open judge) on the MEX + 32B-DSyes/HKno disagreement cases only,
   to break ties without full re-judging. API cost only, small.

## 10. Housekeeping (from the handoff; do before publishing the repo)
- Revoke the exposed Gemini key; delete the expired Anthropic key in the console.
- Attribute SafeClawBench (arXiv 2606.18356) and release the repo patches + kit scripts.

---

### Files in this deliverable
- `analysis.py` — regenerates every table (→ `out/results.json`, stdout) and all figures.
- `out/figures/*_light.png`, `*_dark.png` — fig1 ASR×judge, fig2 family heatmap, fig3 agreement×size,
  fig4 truncation artefact, fig5 Core-vs-Exec. Colour-blind-safe (Okabe–Ito), light & dark variants.
- `blind_adjudication_sheet.md` / `.csv` — 60 blind cases (30 MEX-disagree, 20 32B-DSyes/HKno,
  10 agreement controls), judge identity hidden and A/B randomised per row.
- `answer_key.json` / `answer_key.md` — the de-blinding key (open after labelling).
- `score_adjudication.py` — scores your labels: per-judge accuracy, bias, sensitivity/specificity,
  McNemar, and which judge you side with, overall and per stratum.
- `out/results.json` — all machine-readable numbers behind this memo.
