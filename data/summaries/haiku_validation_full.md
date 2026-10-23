## 1. DeepSeek vs Claude Haiku
| Model | Cases | Agreement | Kappa | ASR DeepSeek [95% CI] | ASR Haiku [95% CI] | DS yes / Haiku no | DS no / Haiku yes |
|---|---|---|---|---|---|---|---|
| qwen2.5-7b | 600 | 80% | 0.59 | 68% [65%-72%] | 56% [52%-59%] | 98 | 20 |
| qwen2.5-14b | 600 | 78% | 0.51 | 74% [70%-77%] | 58% [55%-62%] | 114 | 21 |
| qwen2.5-32b | 600 | 78% | 0.44 | 86% [82%-88%] | 65% [61%-69%] | 128 | 5 |

Pooled agreement 79% over 1800 pairs, kappa 0.52.
Truncation check: 70% of the DeepSeek-yes/Haiku-no cases (340) sit at the ~2000-char cap, vs 52% of all cases.

## 2. Paired model comparison on the same cases (exact McNemar; ASR difference = second minus first)
| Judge | Pair | Cases | ASR first | ASR second | Difference | p |
|---|---|---|---|---|---|---|
| DeepSeek | 7b vs 14b | 600 | 68% | 74% | +5 pts | 0.009 |
| DeepSeek | 14b vs 32b | 600 | 74% | 86% | +12 pts | 0.000 |
| DeepSeek | 7b vs 32b | 600 | 68% | 86% | +17 pts | 0.000 |
| Haiku | 7b vs 14b | 600 | 56% | 58% | +3 pts | 0.187 |
| Haiku | 14b vs 32b | 600 | 58% | 65% | +7 pts | 0.001 |
| Haiku | 7b vs 32b | 600 | 56% | 65% | +9 pts | 0.000 |

## 3. ASR by attack type (DeepSeek | Haiku), 7b / 14b / 32b
| Type | DeepSeek | Haiku | Judge agreement |
|---|---|---|---|
| ADI | 42% / 55% / 72% | 34% / 46% / 52% | 81% (n=300) |
| DPI | 78% / 89% / 97% | 81% / 85% / 91% | 90% (n=300) |
| IPI | 83% / 82% / 87% | 67% / 74% / 77% | 85% (n=300) |
| MEX | 50% / 68% / 70% | 12% / 18% / 17% | 53% (n=300) |
| MPI | 88% / 91% / 98% | 77% / 76% / 82% | 83% (n=300) |
| TRI | 70% / 59% / 89% | 62% / 52% / 71% | 79% (n=300) |