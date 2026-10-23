# kit/

Everything needed to regenerate the data in `../data/`, scripted so nothing is typed by hand on the pod.

| File | What it is |
|---|---|
| `install_kit.sh` | Writes every pod-side script into `/workspace/kit/`: the environment file, the routing proxy (Qwen to Ollama, judge calls to DeepSeek or Anthropic), the repo patches, the setup, calibration, main-run and finalise scripts. This is the final corrected version. |
| `install_v2.sh` | Writes the scripts for the pre-registered follow-up (`../PREREGISTRATION_followup.md`): the subset builder, the response-cap patch, the two-judge pass and the analysis. |
| `podside/` | Scripts that were run on the pod after the installer: `diag.py` (judge-failure spy), `calib2.py` (determinism and serial-versus-parallel check), `haiku_validate.py` and `haiku_full.py` (the Haiku re-judge). |

The runbooks in `../docs/` say in which order to run them and what each step costs.

## One lesson worth carrying over

DeepSeek V4.1 thinks by default. With the benchmark judge's 1,024-token limit the reasoning used the whole
budget and the visible answer came back empty, which looked like a failed judgement on about 30% of cases
and was biased towards long responses. The fix is to disable thinking for grading (the proxy adds
`thinking: {"type": "disabled"}`). Any empty or unparseable verdict should be treated as a re-run, never as
a negative result.

## Not here

API keys (`keys.env` is created on the pod by `01_setup.sh` and is never committed), tunnel configs, and
logs that could contain keys.
