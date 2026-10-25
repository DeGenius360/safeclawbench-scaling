# Verification — every published number vs source

Two layers: the v1 main-study numbers embedded in the report/paper, and the v2 follow-up numbers embedded in the report, paper and `FOLLOWUP_RESULTS.md`. 'Claimed' = value as published; 'Source' = recomputed by `analysis/analysis.py` / `analysis/analysis_followup.py` from the per-case data.

**Result: 38 numeric checks, 38 pass, 0 fail. Case-ID SHA-256 matches the run log. Pre-registered outcomes: H1 supported, H3 inconclusive_underpowered, H4 material.**

The follow-up's shipped `summary.md` was independently recomputed from `followup_per_case.json`; all overlapping numbers agree.

| Check | Claimed | Source | Result |
|---|---|---|---|
| v1 ASR DeepSeek 7b | 68.5 | 68.5 | PASS |
| v1 ASR DeepSeek 14b | 74.0 | 74.0 | PASS |
| v1 ASR DeepSeek 32b | 85.5 | 85.5 | PASS |
| v1 ASR Haiku 7b | 55.5 | 55.5 | PASS |
| v1 ASR Haiku 14b | 58.5 | 58.5 | PASS |
| v1 ASR Haiku 32b | 65.0 | 65.0 | PASS |
| v1 trend OR DS | 1.7 | 1.699 | PASS |
| v1 trend OR HK | 1.3 | 1.296 | PASS |
| v1 exec harm 32b | 48.3 | 48.333 | PASS |
| v1 corepass DS 32b | 95.0 | 95.0 | PASS |
| FU report ASR ds_cap 7b | 73.3 | 73.333 | PASS |
| FU report ASR ds_cap 14b | 74.2 | 74.167 | PASS |
| FU report ASR ds_cap 32b | 76.7 | 76.667 | PASS |
| FU report ASR ds_full 7b | 70.0 | 70.0 | PASS |
| FU report ASR ds_full 14b | 74.2 | 74.167 | PASS |
| FU report ASR ds_full 32b | 79.2 | 79.167 | PASS |
| FU report ASR hk_cap 7b | 58.3 | 58.333 | PASS |
| FU report ASR hk_cap 14b | 55.0 | 55.0 | PASS |
| FU report ASR hk_cap 32b | 55.8 | 55.833 | PASS |
| FU report ASR hk_full 7b | 57.5 | 57.5 | PASS |
| FU report ASR hk_full 14b | 58.3 | 58.333 | PASS |
| FU report ASR hk_full 32b | 65.0 | 65.0 | PASS |
| FU H1 agree cap | 73.0 | 72.973 | PASS |
| FU H1 agree full | 81.1 | 81.081 | PASS |
| FU H1 delta | 8.1 | 8.108 | PASS |
| FU H3 Haiku delta | 7.5 | 7.5 | PASS |
| FU H3 Haiku p | 0.136 | 0.136 | PASS |
| FU H3 DeepSeek delta | 9.2 | 9.167 | PASS |
| FU H3 DeepSeek p | 0.043 | 0.043 | PASS |
| FU H4 agree 7b | 75.8 | 75.833 | PASS |
| FU H4 shift 7b | 5.8 | 5.833 | PASS |
| FU H4 agree 14b | 77.5 | 77.5 | PASS |
| FU H4 shift 14b | -2.5 | -2.5 | PASS |
| FU H4 agree 32b | 87.5 | 87.5 | PASS |
| FU H4 shift 32b | -0.8 | -0.833 | PASS |
| FU TableC 32b Haiku cap | 50.7 | 50.667 | PASS |
| FU TableC 32b Haiku full | 65.3 | 65.333 | PASS |
| FU TableC 32b Haiku delta | 14.7 | 14.667 | PASS |

---

## Post-hoc interpretive review (v1.1, 25 Oct)

A second reviewer flagged two *interpretive* sentences (not numbers, not the H1–H4 outcomes). Both were
checked against the data; **no number, figure value, or pre-registered outcome changed** — only wording.
Checks are recorded in `FOLLOWUP_RESULTS.md` → "Post-hoc checks" and are labelled exploratory.

| Concern | Checks run | Key numbers | Verdict | Wording change |
|---|---|---|---|---|
| 1 · "environment compresses / version drift" | text-identity (main vs regen, first 2000 chars); paired agreement test across sizes; per-size ASR-shift CIs; paired-bootstrap decomposition both judges; 7B same-build calibration | identical: 0/120 (7B), 0/120 (14B), 9/120 (32B); 32B-vs-7B agreement p=0.029; 7B shift +5.8 (95% CI −2.9…+14.6); env step DeepSeek −10.8 [−21.7,−0.8], Haiku −6.7 [−17.5,+5.0]; same-build ≈93% vs cross-build ≈70% | **qualify** | drift stated as "consistent with", not proven; decomposition given with intervals (env step significant for DeepSeek only); added "single-run n=120 estimates are noisy" |
| 2 · "harmful action completes after the cut" | Haiku flip counts + full-verdict HEC; token-offset heuristic; flip-by-flip reading; direction/size asymmetry | no→yes 16 (HEC-full ActionHarm 9 / SemanticOnly 7), yes→no 2; ~89% of cited tokens pre-2000; DeepSeek net −1 vs Haiku net +14 | **consistent with (corrected)** | reworded to "the response finishes its committed action after the cut"; note nothing executes in Core; note minority re-interpretation / late-caveat flips |

Both the headline (38-check) table above and these post-hoc numbers were recomputed from the per-case data
by the analysis scripts; `analysis_followup.py` still reports H1 supported, H3 inconclusive, H4 material, and
the case-ID SHA-256 still matches.
