# Follow-up study: pre-registration

**Commit this file to the GitHub repo before you run `v2_all.sh`, and keep the commit hash.** The point is that the predictions and decision rules below exist in writing, with a timestamp, before any follow-up data does.

Edit anything you disagree with *before* committing. These are my proposed predictions; after the commit they are yours.

## What this is, and what it is not

This registers the **follow-up** only. The main study's results (1,800 Core cases, both judges) had already been seen when this was written, and the follow-up was designed in response to them. So this is a pre-registered *test of explanations that came from looking at the data*, not a clean confirmatory study. The write-up should say so in one sentence.

## Why the follow-up exists

Three open threats to validity from the main study:

1. **Truncation.** The harness saves only the first 2,000 characters of each response, and re-judging works from that text. About 46–48% (7B, 14B) and 63% (32B) of saved responses sit at the cap. If the DeepSeek-vs-Haiku disagreement and the scale trend partly come from what each judge does with cut-off text, judging full-length responses should change them.
2. **Environment.** 7B and 14B were generated in July, 32B in October. The July Ollama version was never logged, so a size effect could partly be a build effect.
3. **Underpowered cross-checks.** The environment check so far rests on 30 cases of one model.

## Design

- **Cases:** 120, stratified: 20 per attack family (ADI, DPI, IPI, MEX, MPI, TRI), drawn with `random.Random(2026)` from `benchmark_v5_600.json` by `v2_make_subset.py`. The SHA-256 of the sorted ID list is printed by the script and goes in the write-up. The same 120 cases go to all three sizes.
- **Generation:** Qwen2.5 7B, 14B, 32B (Q4_K_M, Ollama), defense D0, temperature 0, one fresh pod, one Ollama build, `OLLAMA_NUM_PARALLEL=4`, context 8192. **Full response saved** (`SCB_SAVE_CAP=20000`, so nothing is cut at save time).
- **Judging:** every response judged by DeepSeek (`deepseek-flash`, thinking disabled) and Claude Haiku 4.5. Responses over 2,000 characters are judged twice: on the first 2,000 characters (reproducing the main study's view) and on the full text. Shorter responses are judged once.
- **Unit of analysis:** the case. Paired comparisons use exact McNemar; intervals are Wilson; agreement is Cohen's kappa.

## Power, stated up front

With 120 paired cases, a 7B-vs-32B difference needs to be roughly **10–12 percentage points or more** to reach p < 0.05 (exact figure depends on how many cases are discordant). Smaller real effects will come out "not significant", and that will mean *underpowered*, not *absent*. The write-up must report the interval, not only the p-value.

## Hypotheses, predictions and decision rules

**H1: Truncation explains part of the judge disagreement.**
- *Prediction:* among responses over 2,000 characters, DeepSeek-vs-Haiku agreement is **higher on the full text than on the first 2,000 characters** (pooled over sizes, by at least 5 points), and kappa rises.
- *Supported* if pooled agreement on long responses rises by ≥ 5 points. *Not supported* if it rises by less than 2 points or falls. In between: reported as weak/inconclusive.
- *If not supported:* the disagreement is about judge semantics (intent vs observed harm), not about truncation, and the "truncation artefact" wording in the main write-up must be dropped.

**H2: Truncation moves ASR, not just agreement.**
- *Prediction:* on long responses, ASR under at least one judge changes between the cut and the full text.
- *Decision:* paired McNemar on the flips for each judge, reported separately. The direction is not pre-specified, because the two judges could plausibly move in opposite directions. Which judge moves, and which way, is itself the finding.

**H3: The scale trend survives same-environment, full-length judging.** *(Primary hypothesis.)*
- *Primary outcome:* paired ASR difference, 7B vs 32B, **Haiku, full text**, on the 120 cases.
- *Prediction:* positive (32B has the higher ASR).
- *Replicated* if the primary difference is positive with p < 0.05, **and** the DeepSeek full-text difference has the same sign.
- *Not replicated* if the primary difference is negative or under 3 points under either judge.
- *Anything else:* inconclusive, underpowered. Only the primary outcome is a confirmatory test. All other size comparisons in the output are exploratory and labelled so.

**H4: The July-vs-October environment confound is small.**
- *Measure:* for each size, per-case agreement between the main study's saved verdict (Haiku) and today's verdict on the first 2,000 characters, plus the ASR shift.
- *Small* if agreement is ≥ 80% and the ASR shift is ≤ 5 points for 7B and 14B. *Material* if either size falls outside that. Because 32B was generated in October and 7B/14B in July, a gap that appears only for 7B/14B points to version drift; a similar gap for all three points to ordinary run-to-run variation. Compare `results/v2/conditions.txt` with the Ollama version in the main study's `kit/state/conditions.txt` before interpreting.

## What would change the main write-up

| Outcome | Consequence for the headline claim |
|---|---|
| H3 replicated, H4 small | Scale-trend claim stands, with the follow-up as a same-environment confirmation. |
| H3 not replicated, H4 small | Scale trend downgraded to "not robust to full-length judging"; report both. |
| H4 material | The 7B/14B vs 32B comparison in the main study carries an environment caveat; lead with the same-environment numbers. |
| H1 not supported | Remove the truncation-artefact explanation of judge disagreement. |

## Deviations

Any change to the above after the first run (a different subset, a dropped judge, a rule changed because of what the data showed) goes in a "Deviations" section of the write-up with the reason. Re-running the same script after an interruption is not a deviation; the script is resumable by design.

## Disclosed limitations

n = 120 per size; one run per condition; Q4_K_M quantisation; the DeepSeek API model ID is an alias and the underlying build is not pinned; no OpenAI-judge (gpt-5.4) comparison available; Exec-Balanced is not part of this follow-up.
