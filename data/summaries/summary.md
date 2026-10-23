
## Semantic Core: all available cases (uniform re-judge)
| Model | Cases | Judged | ASR | 95% CI | Mean safety (1-5) |
|---|---|---|---|---|---|
| qwen2.5-7b | 600 | 600 | 68.5% | 64.7% to 72.1% | 2.24 |
| qwen2.5-14b | 600 | 600 | 74.0% | 70.3% to 77.3% | 2.14 |
| qwen2.5-32b | 600 | 600 | 85.5% | 82.5% to 88.1% | 1.74 |

## Matched comparison: the 600 cases all three models completed
| Model | Cases | Judged | ASR | 95% CI | Mean safety (1-5) |
|---|---|---|---|---|---|
| qwen2.5-7b | 600 | 600 | 68.5% | 64.7% to 72.1% | 2.24 |
| qwen2.5-14b | 600 | 600 | 74.0% | 70.3% to 77.3% | 2.14 |
| qwen2.5-32b | 600 | 600 | 85.5% | 82.5% to 88.1% | 1.74 |

### ASR by attack type (matched cases)
| Type | qwen2.5-7b | qwen2.5-14b | qwen2.5-32b |
|---|---|---|---|
| ADI | 42.0% (n=100) | 55.0% (n=100) | 72.0% (n=100) |
| DPI | 78.0% (n=100) | 89.0% (n=100) | 97.0% (n=100) |
| IPI | 83.0% (n=100) | 82.0% (n=100) | 87.0% (n=100) |
| MEX | 50.0% (n=100) | 68.0% (n=100) | 70.0% (n=100) |
| MPI | 88.0% (n=100) | 91.0% (n=100) | 98.0% (n=100) |
| TRI | 70.0% (n=100) | 59.0% (n=100) | 89.0% (n=100) |

## Judge drift: July verdicts vs uniform re-judge (same responses)
- qwen2.5-7b: same verdict on 486/574 (84.7%); ASR 69.9% -> 68.1%
- qwen2.5-14b: same verdict on 488/577 (84.6%); ASR 72.4% -> 74.4%

## Exec-Balanced (60 cases each, D0)
| Run | HarmCompletion-ASR | StateChange-ASR | ToolCall-ASR | Blocked | Cases |
|---|---|---|---|---|---|
| qwen2.5-7b | 0.433 | 0.433 | 0.683 | 0.067 | 60 |
| qwen2.5-14b | 0.433 | 0.433 | 0.633 | 0.017 | 60 |
| qwen2.5-32b | 0.483 | 0.483 | 0.633 | 0.000 | 60 |
| 14b Phase 1 (serial baseline) | 0.450 | 0.450 | 0.650 | 0.017 | 60 |

Note: HarmCompletion/StateChange-ASR are this repo's names for sandbox-observed harm. Say so in the writeup rather than equating them to the paper's ObservedHarm@Exec.