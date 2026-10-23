# SafeClawBench scaling study

Independent cross-scale evaluation of agent safety: **Qwen2.5 7B, 14B and 32B** on
[SafeClawBench](https://huggingface.co/datasets/sairights/safeclawbench) (Tian et al., arXiv 2606.18356),
judged by two different LLM judges, with a pre-registered same-environment follow-up.

> **Status: work in progress.** Report v1 is in `report/`. It was written before the follow-up
> experiment, which was pre-registered in commit `fa4fe71` before any follow-up data existed.
> The report will be revised according to the pre-registered decision rules.
> Not affiliated with the SafeClawBench authors.

## Headline results

<!-- Fill from the final report once it is checked against the tables. Keep each claim next to its
     judge, sample size and confidence interval. Do not put a scale-trend claim here until the
     follow-up outcome is known. -->

TODO. See `report/` for the full v1 write-up.

## What was done

- **Models:** Qwen2.5 7B / 14B / 32B, GGUF Q4_K_M via Ollama, defense D0, temperature 0.
- **Benchmark:** the 600-case Semantic Core track for all three sizes (1,800 evaluations), and a fixed
  60-case Exec-Balanced subset with deterministic state oracles.
- **Judges:** DeepSeek (`deepseek-flash`, thinking disabled) and Claude Haiku 4.5, applied uniformly to
  every Core case. The original paper used gpt-5.4, which was not available here, so absolute rates are
  **not directly comparable** with the paper's.
- **Statistics:** Wilson intervals, exact McNemar for paired comparisons, Cohen's kappa for judge
  agreement.

## Things to know before trusting the numbers

- The harness saves only the first 2,000 characters of each response. About half of saved responses
  (63% for 32B) sit at that cap, and re-judging works from the saved text. See the follow-up.
- 7B and 14B were generated in July, 32B in October, on possibly different Ollama builds. The July
  build was never logged.
- The two judges disagree most on MEX cases and on truncated responses; they measure related but
  different things (intent versus observed completed harm).
- Exec-Balanced has n = 60 per model and is underpowered for size comparisons.
- The DeepSeek API model ID is an alias; the underlying build is not pinned.
- `kit/install_kit.sh` is the final corrected version of the kit. Some fixes (notably disabling DeepSeek's
  thinking mode in the proxy) were applied by hand on the pod during the run before they were added to
  the installer.

<!-- Expand and date these once the follow-up result is in. -->

## Repository layout

| Path | Contents |
|---|---|
| `report/` | Report v1: HTML, PDF and DOCX versions, the findings memo and the verification notes |
| `PREREGISTRATION_followup.md` | Hypotheses and decision rules for the follow-up, committed before running it |
| `docs/runbook_main_study.md` | How the main study was run, step by step |
| `docs/runbook_followup.md` | How the follow-up is run |
| `kit/` | Installers that write every script used on the pod; `kit/podside/` has the scripts that were run after the installer |
| `data/core_verdicts.csv` | One row per model and case: both judges' verdicts, response length, whether it hit the cap |
| `data/summaries/`, `data/exec/`, `data/run_conditions/` | Summary tables, Exec results, and the recorded run conditions |
| `analysis/` | Analysis code, figures and the blind adjudication sheet |

Raw model responses are withheld until they have been reviewed for release.

## Reproducing

Everything runs on a single rented GPU (an A40 at about $0.60 per hour all-in) and is scripted:
see `docs/runbook_main_study.md`. API cost for the judging is a few dollars. The follow-up takes about
1.5 hours; see `docs/runbook_followup.md`.

## Credit and licence

- Benchmark and harness: SafeClawBench by Tian et al. (MIT). This repository contains no copy of the
  benchmark; fetch it from Hugging Face.
- Code and analysis in this repository: MIT, see `LICENSE`.

## Citing

<!-- Add a CITATION.cff or BibTeX entry once the report has a stable URL. -->
