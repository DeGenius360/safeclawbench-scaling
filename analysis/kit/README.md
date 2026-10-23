# kit/

This folder is for the generation and judging scripts and the SafeClawBench repo patches
used to produce the data in `../data/`.

**Add your own scripts here before publishing**, after a secrets scan:

- `router_proxy.py` and the Ollama/judge driver scripts
- the repo patches applied to SafeClawBench (as `.patch` files, so the diff is auditable)
- `state/` with `conditions.txt`, `judge_builds.txt`, `calibration.txt`

Do **not** commit: `keys.env`, cloudflared tunnel configs with tokens, or any log containing
API keys. See `../PUBLISHING_CHECKLIST.md`. The DeepSeek thinking-mode fix (disable thinking for
grading; treat any empty/parse-error verdict as a re-run, never as a negative) should be documented
here — it's the practical lesson from this run.
