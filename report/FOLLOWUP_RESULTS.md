# Follow-up results: pre-registered same-environment, full-length replication

**Design.** 120 cases (20 per family), drawn with `random.Random(2026)` from the 600-case Core, sent
to all three Qwen2.5 sizes generated on one pod / one Ollama build (0.40.11), defence D0, temperature 0,
responses saved uncapped. Every response judged by DeepSeek and Haiku twice when over 2,000 characters:
on the first 2,000 characters (the main study's view, "cap") and on the full text ("full"). Pre-registration
committed before any follow-up data existed (`PREREGISTRATION_followup.md`, commit `fa4fe71`).

All numbers below are recomputed from `data/followup_per_case.json` / the main-study verdicts by
`analysis/analysis_followup.py`. Where `summary.md` from the run overlaps, the two agree.

This is a pre-registered test of explanations that came from looking at the main-study data; it is not a
clean confirmatory study of a novel question. Only the H3 primary outcome is confirmatory; everything else
is exploratory and labelled so.

## Sanity checks (all pass)

- 120 cases per size; 20 per family; **0 missing verdicts**.
- The same 120 cases went to all three sizes.
- SHA-256 of the sorted case-ID list = `4230f25b…4e9f75`, **matches** the value printed in the run log
  (computed over the newline-joined sorted IDs).
- Uncapped save worked: maximum saved length is 5,240 / 4,796 / 4,607 characters (7B/14B/32B), all > 2,000.
- Long responses (> 2,000 chars): 60 / 50 / 75 per size. Short responses have `cap == full` for both
  judges in every case (0 exceptions), as expected by construction.
- Conditions recorded: Ollama 0.40.11, NVIDIA A40, 25 Oct 2026. Main study: 0.40.9 (32B, 23 Oct); the
  July 7B/14B build was never logged.

## Pre-registration outcome table

| # | Hypothesis | Rule as written | Observed (n=120/size) | Outcome |
|---|---|---|---|---|
| **H1** | Truncation explains part of the judge disagreement | Supported if, on long responses pooled, DeepSeek–Haiku agreement rises ≥ 5 pts on full text vs cap; not supported if < 2 pts or falls | Agreement **73.0% → 81.1% (+8.1 pts)**; κ 0.45 → 0.58 (long n=185) | **SUPPORTED** |
| **H2** | Truncation moves ASR, not just agreement | McNemar on cap→full flips, each judge, on long responses; direction not pre-specified | **Haiku rises** (32B +14.7 pts, p=0.001; 14B +8.0, p=0.125; 7B −1.7, p=1.0); **DeepSeek stable** (7B −6.7 p=0.125; 14B 0.0; 32B +4.0 p=0.375) | **Observed — Haiku moves up, DeepSeek flat** |
| **H3** *(primary, confirmatory)* | Scale trend survives same-environment, full-length judging | Replicated if primary (Haiku, full, 7B vs 32B, paired) p < 0.05 **and** DeepSeek full-text same sign; not replicated if either judge < 3 pts or negative | Haiku **+7.5 pts, p=0.136**; DeepSeek **+9.2 pts, p=0.043** (same, positive sign) | **INCONCLUSIVE (underpowered)** |
| **H4** | July-vs-October environment confound is small | Small if per-size agreement (main Haiku vs same-env, cap) ≥ 80% **and** ASR shift ≤ 5 pts, for 7B and 14B | 7B **75.8%, +5.8 pts**; 14B **77.5%, −2.5 pts**; 32B 87.5%, −0.8 pts | **MATERIAL** |

### Notes on the two loosely-worded rules
- **H2 "changes":** taken literally as "a non-zero ASR change under at least one judge on long responses."
  That is clearly met (Haiku). The more demanding reading ("a *significant* change") is also met — Haiku at
  32B, p=0.001. Both readings give the same outcome.
- **H3 "not replicated" clause ("negative or under 3 points under either judge"):** taken literally as
  *either* judge's full-text 7B→32B difference being negative *or* below 3 points. Haiku (+7.5) and DeepSeek
  (+9.2) are both positive and ≥ 3, so "not replicated" is **not** triggered. But "replicated" requires the
  primary test to reach p < 0.05, which it does not (p=0.136). The result therefore lands in the
  pre-registered third category: **inconclusive, underpowered** — exactly the case the power note anticipated
  for a true effect below ~10–12 points. The alternative reading of the clause (magnitude only) gives the
  same outcome.

## Deviations

None affecting the pre-registered tests. The SHA-256 was confirmed to be computed over the newline-joined
sorted ID list (the run log did not state the join format); this changes no result. `analysis_followup.py`
is new (the pre-registration anticipated either extending `analysis.py` or adding a new script).

After the first draft, a second reviewer flagged two *interpretive* sentences (not numbers, not the H1–H4
outcomes). I ran the checks below; they are **post hoc and exploratory, outside the pre-registration**, and
they changed only wording. The H1–H4 outcome table and every number are unchanged.

## Post-hoc checks (exploratory; outside the pre-registration)

**On the environment claim (Concern 1).** All post hoc.
- *Text identity.* Comparing the first 2,000 characters of each regenerated response with the main-study
  saved text: byte-identical for **0/120 (7B), 0/120 (14B), 9/120 (32B)**. At temperature 0, generation is
  non-deterministic run-to-run at every size; the smallest effect is 32B being marginally more reproducible.
  This means the July-vs-October disagreement cannot be read as "7B/14B text changed and 32B did not" — all of
  it changed.
- *Is 32B really more reproducible?* Paired (per case) McNemar on the agree/disagree indicator: 32B vs 7B
  p=0.029, 32B vs 14B p=0.023, 7B vs 14B p=0.875. So 32B does agree significantly more, but 7B and 14B are
  indistinguishable. A model-size effect on determinism is confounded with build here and cannot be separated.
- *Per-size ASR shift significance.* Main→same-env Haiku(cap) shift: 7B +5.8 (SE 4.5, 95% CI −2.9…+14.6),
  14B −2.5 (CI −11.0…+6.0), 32B −0.8 (CI −7.2…+5.5). **No individual shift is significant** — the reviewer's
  back-of-envelope (≈1.3 SE for 7B) is confirmed.
- *Decomposition intervals (paired case bootstrap, both judges).* Environment step (same-env cap − main cap
  gap): DeepSeek −10.8 [−21.7, −0.8] (excludes 0); Haiku −6.7 [−17.5, +5.0] (includes 0). Truncation step
  (same-env full − same-env cap gap): DeepSeek +5.8 [+0.8, +11.7]; Haiku +10.0 [+4.2, +16.7] (both exclude 0).
  The four-step chain is therefore not exact; the environment step is significant for DeepSeek only. The
  reverse-order decomposition ("judge view first, environment second") is not computable because the main
  study has no full-text verdicts — full text exists only for the regenerated responses.
- *Same-build baseline.* From the main-study 7B calibration: serial-vs-parallel **same-build** agreement ≈93%
  (recoverable on 15/30 cases — the stored parallel file has 15 null parse-error verdicts, so the corrected
  parallel per-case file is not reproducible from the bundle; the state file records 28/30), serial-vs-July
  **cross-build** ≈70% (30 cases). Same-build noise is lower than cross-build, which is consistent with some
  drift, but it is n=30 on one model.

**On the truncation mechanism (Concern 2).** All post hoc; no response text is reproduced here.
- *Haiku cap→full flips on long responses:* 16 no→yes (7B 1, 14B 4, 32B 11), 2 yes→no (both 7B); DeepSeek is
  near-balanced (5 no→yes, 6 yes→no, net −1) against Haiku's net +14.
- *harm_evidence_category of the full verdict on the 16 no→yes flips:* ActionHarm 9, SemanticOnly 7 — and on
  the pooled long set the distribution shifts from NotObservable toward both SemanticOnly (+11) and ActionHarm
  (+6). Reading the cases, the ActionHarm flips are ones where the agent *finishes writing* the action (gpg +
  mutt email, an upload loop, an smtplib block, a downgrade command) after the 2,000-character cut; **nothing
  is executed** (Core does not run tools).
- *Offset check:* among Haiku's full-verdict explanations on no→yes flips, ~89% of located distinctive tokens
  are already present in the first 2,000 characters; only 8/16 cite any post-2000-only token and 0/16 rest
  mainly on post-2000 material. (Crude — key entities like the target email/URL are named early — so weighted
  below the case reading.)
- *Direction:* the 2 yes→no flips are a late "would you like me to proceed?" clarification and a tail that
  reveals the data was hypothetical — i.e. the reviewer's alternative mechanism does occur.
- *Reading:* consistent with "the response finishes its committed action after the cut", with the corrections
  that nothing executes and that a minority of flips are re-interpretation or late-caveat driven. "Harm
  completes late" overstates it; "more context changes how the stricter grader reads a long response" is safe.

## What this changes in the main (v1) write-up

Applying the pre-registration's consequence table:

- **H1 supported → the truncation-artefact explanation stays, and is strengthened.** v1's truncation
  analysis was *observational* (it compared long vs short responses, which confounds truncation with response
  type). The follow-up judges the **same responses** both ways, removing that confound, and confirms the
  effect: lifting the cap raises DeepSeek–Haiku agreement by 8 points on long responses, driven by **Haiku's**
  ASR rising 14.7 points on long 32B responses (p=0.001) while DeepSeek barely moves. On the *mechanism*, a
  post-hoc reading of the flipped cases (see "Post-hoc checks") is **consistent with, but does not prove**, the
  v1 story: in most no→yes flips the agent finishes writing the committed action after the 2,000-character cut
  (an exfiltration or destructive script, or an explicit offer to act on real data), so the completed response
  reads as compliance where the cut fragment did not. Two corrections to the v1 wording: nothing is actually
  *executed* in the Core track (that is the Exec track), so what completes after the cut is the committed
  plan/code, not observed harm; and a minority of flips go the other way — the tail adds a late clarification
  or reveals the output was hypothetical — so "more context changes how the stricter grader reads a long
  response" is the safe description, not "harm completes late."
- **H4 material → the main study's 7B/14B-vs-32B comparison carries an environment caveat, and the
  same-environment numbers should lead.** This outcome follows the pre-registered rule and is unchanged.
  The *causal reading* is weaker than v1 stated, and the post-hoc checks qualify it: regeneration flipped about
  a quarter of 7B/14B verdicts, 32B agrees significantly more than the smaller models on a paired test
  (p≈0.02–0.03), and the 7B calibration (same-build ≈93% vs July-vs-October ≈70%) points toward build drift —
  but one re-run cannot separate drift from ordinary run-to-run non-determinism. At temperature 0, **almost
  every response changed between runs at every size** (byte-identical on the first 2,000 chars for 0/120 of 7B,
  0/120 of 14B, and only 9/120 of 32B), each individual size's ASR shift is within sampling noise (7B +5.8 pts,
  95% CI −2.9 to +14.6), and a model-size effect on determinism could produce the same pattern. So the honest
  statement is: regeneration changes verdicts materially (confounding the cross-build comparison), the
  direction of the 32B-vs-smaller agreement gap is consistent with drift, but how much is drift versus noise is
  not identified from one run.
- **H3 inconclusive → the scale claim is revised down in strength, not in direction.** In the same
  environment on full text, 32B is still more attackable than 7B under both judges (+9.2 DeepSeek, p=0.043;
  +7.5 Haiku, p=0.136), but the one confirmatory test is underpowered at n=120. The main study's headline
  **+17 points (DeepSeek) is larger than the same-environment, full-length estimate (~+9 points).** A step
  decomposition (DeepSeek, 7B→32B) is +17.0 on the full 600 → +14.2 on these 120 cases with the original
  responses → +3.3 once 7B/14B are regenerated on the same build → +9.2 once the full text is judged. These
  steps carry wide, paired-bootstrap intervals and should not be read as exact: the **environment step is
  −10.8 pts (95% CI −21.7 to −0.8) under DeepSeek but −6.7 (95% CI −17.5 to +5.0, not distinguishable from
  zero) under Haiku**, while the **truncation step is positive and excludes zero under both** (DeepSeek +5.8
  [+0.8, +11.7]; Haiku +10.0 [+4.2, +16.7]). So "the environment compresses the gap" holds for DeepSeek only
  and marginally; the robust part is that full-text judging widens it, and that the same-environment estimate
  is smaller than the cross-environment +17.

**Net:** bigger still scored as riskier under both judges, and the truncation finding holds and is cleaner
than before — but the magnitude of the scale effect is smaller than v1 implied, the confirmatory replication
is underpowered, and a further honest result emerges from the post-hoc checks: **at n=120, with roughly a
quarter of verdicts flipping between runs, single-run estimates of the size effect are noisy.** All of this is
model-layer; no infrastructure-layer claim is made.

## Plain-language reading

I re-ran a slice of the study the right way: same hardware and software build for all three model sizes, and
I kept the full model responses instead of cutting them at 2,000 characters. Two things came out of it.
First, the disagreement between my two graders really was mostly about truncation — when they both read the
whole response, they agree much more. Looking at exactly which cases flip, the fuller response usually shows
the model finishing the thing it was asked to do (writing out the complete script, or offering to run it on
real data), which the stricter grader reads as going along with the attack; a few cases flip the other way
when the end of the response adds a caveat or shows the data was only hypothetical. Second, the "bigger models
are easier to attack" result still points the same way, but it is weaker and less certain than my first
write-up implied. On one build, judging full responses, the gap is about half the size and no longer
statistically clean at this sample size. Some of the original gap may be down to the 7B and 14B models having
been generated on an older software build in July, but I can only show that indirectly: at temperature zero
the model's output changed between runs for essentially every case at every size, so a single re-run cannot
cleanly separate a build difference from ordinary randomness. The honest summary is that single-run estimates
at this sample size are noisy. So I am keeping the direction of the finding and the truncation story, and I am
dialling back how
strongly I state the size effect.

## Costs (from the run logs)

RunPod ≈ $0.53. Judging: 1,090 calls (545 Haiku ≈ $1.36 estimated; DeepSeek a few tens of pence). The Haiku
budget guard ($1.50) was not tripped.

## Limitations

n = 120 per size; one run per condition; Q4_K_M quantisation; `deepseek-flash` is an alias and the build is
not pinned; no gpt-5.4 (OpenAI) third judge; Exec-Balanced is not part of this follow-up.
