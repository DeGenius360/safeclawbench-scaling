# Verification pass — every report number vs source

**90 checks, 90 pass, 0 fail.** Claimed = value embedded in report/index.html; Source = recomputed from per-case data / results.json.

| Check | Claimed | Source | Result |
|---|---|---|---|
| ASR DeepSeek 7b | 68.5 | 68.5 | PASS |
| ASR DeepSeek 14b | 74.0 | 74.0 | PASS |
| ASR DeepSeek 32b | 85.5 | 85.5 | PASS |
| ASR Haiku 7b | 55.5 | 55.5 | PASS |
| ASR Haiku 14b | 58.5 | 58.5 | PASS |
| ASR Haiku 32b | 65.0 | 65.0 | PASS |
| ASR DS CI-lo 7b | 64.7 | 64.675 | PASS |
| ASR DS CI-hi 7b | 72.1 | 72.089 | PASS |
| ASR DS CI-lo 14b | 70.3 | 70.345 | PASS |
| ASR DS CI-hi 14b | 77.3 | 77.349 | PASS |
| ASR DS CI-lo 32b | 82.5 | 82.457 | PASS |
| ASR DS CI-hi 32b | 88.1 | 88.092 | PASS |
| fam ADI DS 7b | 42 | 42.0 | PASS |
| fam ADI HK 7b | 34 | 34.0 | PASS |
| fam ADI DS 14b | 55 | 55.0 | PASS |
| fam ADI HK 14b | 46 | 46.0 | PASS |
| fam ADI DS 32b | 72 | 72.0 | PASS |
| fam ADI HK 32b | 52 | 52.0 | PASS |
| fam DPI DS 7b | 78 | 78.0 | PASS |
| fam DPI HK 7b | 81 | 81.0 | PASS |
| fam DPI DS 14b | 89 | 89.0 | PASS |
| fam DPI HK 14b | 85 | 85.0 | PASS |
| fam DPI DS 32b | 97 | 97.0 | PASS |
| fam DPI HK 32b | 91 | 91.0 | PASS |
| fam IPI DS 7b | 83 | 83.0 | PASS |
| fam IPI HK 7b | 67 | 67.0 | PASS |
| fam IPI DS 14b | 82 | 82.0 | PASS |
| fam IPI HK 14b | 74 | 74.0 | PASS |
| fam IPI DS 32b | 87 | 87.0 | PASS |
| fam IPI HK 32b | 77 | 77.0 | PASS |
| fam MEX DS 7b | 50 | 50.0 | PASS |
| fam MEX HK 7b | 12 | 12.0 | PASS |
| fam MEX DS 14b | 68 | 68.0 | PASS |
| fam MEX HK 14b | 18 | 18.0 | PASS |
| fam MEX DS 32b | 70 | 70.0 | PASS |
| fam MEX HK 32b | 17 | 17.0 | PASS |
| fam MPI DS 7b | 88 | 88.0 | PASS |
| fam MPI HK 7b | 77 | 77.0 | PASS |
| fam MPI DS 14b | 91 | 91.0 | PASS |
| fam MPI HK 14b | 76 | 76.0 | PASS |
| fam MPI DS 32b | 98 | 98.0 | PASS |
| fam MPI HK 32b | 82 | 82.0 | PASS |
| fam TRI DS 7b | 70 | 70.0 | PASS |
| fam TRI HK 7b | 62 | 62.0 | PASS |
| fam TRI DS 14b | 59 | 59.0 | PASS |
| fam TRI HK 14b | 52 | 52.0 | PASS |
| fam TRI DS 32b | 89 | 89.0 | PASS |
| fam TRI HK 32b | 71 | 71.0 | PASS |
| CM 7b both-success | 313 | 313 | PASS |
| CM 7b DSyes/HKno | 98 | 98 | PASS |
| CM 7b DSno/HKyes | 20 | 20 | PASS |
| CM 7b both-safe | 169 | 169 | PASS |
| CM 14b both-success | 330 | 330 | PASS |
| CM 14b DSyes/HKno | 114 | 114 | PASS |
| CM 14b DSno/HKyes | 21 | 21 | PASS |
| CM 14b both-safe | 135 | 135 | PASS |
| CM 32b both-success | 385 | 385 | PASS |
| CM 32b DSyes/HKno | 128 | 128 | PASS |
| CM 32b DSno/HKyes | 5 | 5 | PASS |
| CM 32b both-safe | 82 | 82 | PASS |
| agree 7b | 80.3 | 80.333 | PASS |
| kappa 7b | 0.59 | 0.59 | PASS |
| agree 14b | 77.5 | 77.5 | PASS |
| kappa 14b | 0.51 | 0.51 | PASS |
| agree 32b | 77.8 | 77.833 | PASS |
| kappa 32b | 0.44 | 0.437 | PASS |
| gap full 7b | 5.2 | 5.183 | PASS |
| gap full 14b | 7.4 | 7.419 | PASS |
| gap full 32b | 9.9 | 9.91 | PASS |
| gap trunc 7b | 22.4 | 22.426 | PASS |
| gap trunc 14b | 24.1 | 24.138 | PASS |
| gap trunc 32b | 26.7 | 26.72 | PASS |
| trunc% 7b | 45.3 | 45.333 | PASS |
| trunc% 14b | 48.3 | 48.333 | PASS |
| trunc% 32b | 63.0 | 63.0 | PASS |
| CorePass DS 7b | 78.3 | 78.333 | PASS |
| CorePass HK 7b | 55.0 | 55.0 | PASS |
| Exec harm 7b | 43.3 | 43.333 | PASS |
| CorePass DS 14b | 81.7 | 81.667 | PASS |
| CorePass HK 14b | 66.7 | 66.667 | PASS |
| Exec harm 14b | 43.3 | 43.333 | PASS |
| CorePass DS 32b | 95.0 | 95.0 | PASS |
| CorePass HK 32b | 73.3 | 73.333 | PASS |
| Exec harm 32b | 48.3 | 48.333 | PASS |
| trend OR DS | 1.7 | 1.699 | PASS |
| trend OR HK | 1.3 | 1.296 | PASS |
| delta DS 7->32 | 17.0 | 17.0 | PASS |
| delta HK 7->32 | 9.5 | 9.5 | PASS |
| nontrunc trend HK | 11.1 | 11.111 | PASS |
| trunc trend HK | 0.9 | 0.87 | PASS |
