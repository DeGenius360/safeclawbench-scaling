## DeepSeek vs Claude Haiku (same 120 cases per model)
| Model | Judged pairs | Agreement | Kappa | ASR DeepSeek | ASR Haiku | DS yes / Haiku no | DS no / Haiku yes |
|---|---|---|---|---|---|---|---|
| qwen2.5-7b | 120/120 | 81% | 0.58 | 72% | 60% | 19 | 4 |
| qwen2.5-14b | 120/120 | 75% | 0.46 | 75% | 57% | 26 | 4 |
| qwen2.5-32b | 120/120 | 75% | 0.36 | 89% | 64% | 30 | 0 |

Pooled: 277/360 = 76.9% agreement (95% CI 72-81%), kappa 0.48

Agreement by attack type (pooled): ADI 83%, DPI 92%, IPI 77%, MEX 45%, MPI 88%, TRI 77%

If the Haiku ASR column keeps the same ordering as the DeepSeek column, the scale trend does not depend on the judge.