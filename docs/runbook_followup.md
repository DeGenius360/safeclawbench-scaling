# Follow-up run: same-environment, full-length replication

One pod, one command for the experiment. About **1.5 hours and ~$0.90 of RunPod**, plus about **$1.0–1.4 of Anthropic** and a few tens of pence of DeepSeek. Everything is resumable: after any interruption, re-run the same command.

## Before you start (free, 10 min)

1. **Commit `PREREGISTRATION_followup.md`** to your repo and note the commit hash. Edit the predictions first if you disagree with any.
2. **Check balances.** RunPod ≥ $2 (you have $3.86). Anthropic: the script estimates its own Haiku spend and **refuses to start** above a $1.50 guard. You have $1.79, so this fits but leaves only about $0.4. Topping up $5 makes it comfortable. DeepSeek: check the balance is not near zero.
3. **Keys ready:** the DeepSeek key and the *new* Anthropic key. The pod's disk is erased on Terminate, so you type them again; setup asks with hidden input.
4. **Timing:** DeepSeek peak pricing is weekdays 01–04 and 06–10 UTC. Tonight after about 17:00 UTC and all of Saturday are off-peak. Sunday too.

## Steps

**1. Deploy the pod.** Same as Step 1 of the Resume Runbook (A40, Runpod Pytorch 2.8.0 template, 60 GB container disk, no persistent volume, ports 8888/22).

**2. Upload three files** into `/workspace` through Jupyter: `install_kit.sh`, `install_v2.sh`, and your `phase2_final_v3_*.zip` (the one that contains `results/final/`). Then in a Jupyter terminal:

```bash
bash /workspace/install_kit.sh
bash /workspace/install_v2.sh
bash /workspace/kit/01_setup.sh
```

Every syntax-check line must say `ok`. Setup takes 15–30 minutes (35 GB of model downloads) and ends with `SETUP COMPLETE`.

**3. Run it.**

```bash
HAIKU_BUDGET=1.5 bash /workspace/kit/v2_all.sh 2>&1 | tee /workspace/kit/logs/v2_all.log
```

Stages it prints: `conditions` → restore earlier results → patches → subset (prints the SHA-256 of the case IDs) → generation for 7B, 14B, 32B → judging (prints the Haiku cost estimate first and stops if it is over the guard) → analysis tables.

If it stops with `STOP: estimated Haiku cost exceeds the guard`, either raise `HAIKU_BUDGET` knowingly or top up Anthropic; nothing has been spent on Haiku at that point. If any model fails mid-generation, re-run the same command: finished models are skipped. If some judge verdicts fail, the script says how many are missing; re-run it and only those are retried.

**4. Save and shut down.**

```bash
cd /workspace/safeclawbench && zip -r /workspace/followup_v2_$(date +%Y%m%d).zip results/v2 results/v2_gen_* chunks/v2_subset*.json /workspace/kit/state /workspace/kit/logs -x "*.env"
```

Download it through Jupyter, then **Terminate** (not Stop) and confirm the RunPod Home page shows $0.00/hr. Check the zip for keys before you share it, as last time: `unzip -p followup_v2_*.zip | grep -a "sk-" | head -3`.

## What you get

`results/v2/summary.md` has five tables:

| Table | Answers |
|---|---|
| A | ASR per size, four views (each judge × first 2,000 chars / full text), with intervals |
| B | Paired size comparisons per view (exact McNemar) |
| C | The truncation test: same response, cut vs full, for each judge |
| D | Judge agreement and kappa, cut vs full |
| E | Environment check against the main study's saved verdicts |

`results/v2/per_case.json` holds every verdict for further analysis, and `results/v2/conditions.txt` records the Ollama build and GPU.

## After the run

- Check the table against the pre-registration's decision rules and write the outcome next to each hypothesis, including any that failed.
- Put `summary.md` and `per_case.json` in the repo as a separate follow-up section, not mixed into the main results.
- Hand `summary.md` to the report thread (or Opus) as the new evidence; the main-study conclusions only change as the pre-registration's table says they should.
- Disclose in the write-up: generation-time judging in this run also used the uncapped text, so the verdicts stored inside `results/v2_gen_*` are a third full-text verdict from DeepSeek; the analysis uses the re-judged values in `judge_cache.json`.

## If something goes wrong

| Symptom | Fix |
|---|---|
| `FAIL ... '[:2000]' not found` from `v2_patch.py` | The upstream source differs from what I read. The script prints the lines mentioning the cap; paste them to me. |
| `FAIL results/final/*_uniform.json missing` | The earlier zip is not in `/workspace`. Upload `phase2_final_v3_*.zip` and re-run. |
| `FAIL proxy is down` | `bash /workspace/kit/01_setup.sh` again (safe to re-run). |
| Haiku 401 | The Anthropic key is wrong or expired; `rm /workspace/keys.env`, re-run `01_setup.sh`, and re-enter both keys. |
| Disk full during model pulls | The container disk was below 60 GB; terminate and redeploy with more. |
