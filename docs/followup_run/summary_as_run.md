## A. Same-environment ASR on the 120-case subset (all three sizes generated today, same build, same settings)
| Model | Cases | Responses > 2000 chars | DeepSeek, first 2000 chars | Haiku, first 2000 chars | DeepSeek, full text | Haiku, full text |
|---|---|---|---|---|---|---|
| qwen2.5-7b | 120 | 50% | 73% [65%-80%] (n=120) | 58% [49%-67%] (n=120) | 70% [61%-77%] (n=120) | 57% [49%-66%] (n=120) |
| qwen2.5-14b | 120 | 42% | 74% [66%-81%] (n=120) | 55% [46%-64%] (n=120) | 74% [66%-81%] (n=120) | 58% [49%-67%] (n=120) |
| qwen2.5-32b | 120 | 62% | 77% [68%-83%] (n=120) | 56% [47%-64%] (n=120) | 79% [71%-85%] (n=120) | 65% [56%-73%] (n=120) |

## B. Paired size comparisons on the same cases (exact McNemar; difference = second minus first)
| Verdict column | Pair | Cases | ASR first | ASR second | Difference | p |
|---|---|---|---|---|---|---|
| DeepSeek, first 2000 chars | 7b vs 14b | 120 | 73% | 74% | +1 pts | 1.000 |
| DeepSeek, first 2000 chars | 14b vs 32b | 120 | 74% | 77% | +3 pts | 0.678 |
| DeepSeek, first 2000 chars | 7b vs 32b | 120 | 73% | 77% | +3 pts | 0.557 |
| Haiku, first 2000 chars | 7b vs 14b | 120 | 58% | 55% | -3 pts | 0.618 |
| Haiku, first 2000 chars | 14b vs 32b | 120 | 55% | 56% | +1 pts | 1.000 |
| Haiku, first 2000 chars | 7b vs 32b | 120 | 58% | 56% | -3 pts | 0.728 |
| DeepSeek, full text | 7b vs 14b | 120 | 70% | 74% | +4 pts | 0.424 |
| DeepSeek, full text | 14b vs 32b | 120 | 74% | 79% | +5 pts | 0.263 |
| DeepSeek, full text | 7b vs 32b | 120 | 70% | 79% | +9 pts | 0.043 |
| Haiku, full text | 7b vs 14b | 120 | 57% | 58% | +1 pts | 1.000 |
| Haiku, full text | 14b vs 32b | 120 | 58% | 65% | +7 pts | 0.200 |
| Haiku, full text | 7b vs 32b | 120 | 57% | 65% | +8 pts | 0.136 |

## C. The truncation test: same response, judged on the first 2000 chars vs the full text (responses longer than 2000 chars only)
| Model | Long responses | DeepSeek ASR cap -> full | DS flips (yes->no / no->yes), p | Haiku ASR cap -> full | Haiku flips (yes->no / no->yes), p | DS minus Haiku gap: cap -> full |
|---|---|---|---|---|---|---|
| qwen2.5-7b | 60 | 77% -> 70% | 4 / 0, p=0.125 | 53% -> 52% | 2 / 1, p=1.000 | +23 -> +18 pts |
| qwen2.5-14b | 50 | 82% -> 82% | 1 / 1, p=1.000 | 48% -> 56% | 0 / 4, p=0.125 | +34 -> +26 pts |
| qwen2.5-32b | 75 | 76% -> 80% | 1 / 4, p=0.375 | 51% -> 65% | 0 / 11, p=0.001 | +25 -> +15 pts |
| all three pooled | 185 | 78% -> 77% | 6 / 5, p=1.000 | 51% -> 58% | 2 / 16, p=0.001 | +27 -> +19 pts |

## D. Judge agreement (all cases): first 2000 chars vs full text
| Model | Agreement cap | Kappa cap | Agreement full | Kappa full |
|---|---|---|---|---|
| qwen2.5-7b | 78% | 0.53 | 81% | 0.59 |
| qwen2.5-14b | 76% | 0.49 | 79% | 0.55 |
| qwen2.5-32b | 79% | 0.56 | 86% | 0.66 |
| pooled | 78% | 0.53 | 82% | 0.60 |

## E. Environment check: the same 120 cases as generated earlier (7B/14B in July, 32B in October) vs today, same 2000-char judge view
| Model | Judge | ASR earlier | ASR today | Agreement per case | Share of responses at/over the cap: earlier -> today |
|---|---|---|---|---|---|
| qwen2.5-7b | DeepSeek | 68% | 73% | 78% (n=120) | 48% -> 50% |
| qwen2.5-7b | Haiku | 52% | 58% | 76% (n=120) | 48% -> 50% |
| qwen2.5-14b | DeepSeek | 75% | 74% | 79% (n=120) | 47% -> 42% |
| qwen2.5-14b | Haiku | 57% | 55% | 78% (n=120) | 47% -> 42% |
| qwen2.5-32b | DeepSeek | 82% | 77% | 92% (n=120) | 65% -> 62% |
| qwen2.5-32b | Haiku | 57% | 56% | 88% (n=120) | 65% -> 62% |