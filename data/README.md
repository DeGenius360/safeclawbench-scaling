# data/

Aggregated results and per-scenario verdicts. **No raw model responses or attack prompts.**

- `results.json` — all machine-readable numbers behind the report (ASR, intervals, trend model,
  per-family, agreement, truncation strata, exec, calibration).
- `summary_tables.md` — the same numbers as human-readable tables.
- `per_case_verdicts.csv` — one row per (model, scenario) for the 600-case Core track:
  `task_id, model, family, harm_type, resp_len, truncated, deepseek_success, haiku_success,
  deepseek_harm_evidence, haiku_harm_evidence, deepseek_defense_behavior, haiku_defense_behavior`.
  `*_success` is 1/0. `resp_len` is the saved (truncated-at-2000) character count.
- `exec_per_case.csv` — one row per (model, scenario) for the 60-case Exec track:
  `case_id, model, family, harm_completion, state_change, tool_call, blocked_by_harness` (all 1/0).

## Follow-up (v2) files
- `results_followup.json` — machine-readable follow-up tables and hypothesis outcomes.
- `followup_per_case.json` — per model, one row per case: `tid, type, n (length), long, ds_cap, ds_full,
  hk_cap, hk_full` (verdict booleans; `cap` = first 2,000 chars, `full` = full text).
- `followup_per_case_verdicts.csv` — the same, flattened (`model, task_id, family, resp_len, long,
  ds_cap, ds_full, hk_cap, hk_full`).
- `followup_conditions.txt` — Ollama build and GPU for the follow-up run.
