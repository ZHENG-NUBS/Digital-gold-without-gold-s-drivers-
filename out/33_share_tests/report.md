# Script 33 — Calibrated tests for the exposure share and for episodic variation

Sample 2015-01-05 – 2026-09-30 (2952 days); windows of 74 days; 999 null replications (constant loading, wild block bootstrap, blocks of 5 days, seed 20261014).

## T1. Is the final window (summer 2026) unusually high?

| Statistic | Final window | Share of earlier windows ≥ final | Calibrated p (one-sided) |
|---|---|---|---|
| share = gamma / gamma* | 0.454 | 0.010 | 0.074 |
| gamma | +0.705 | 0.252 | 0.039 |


## T2. Is the exposure episodic?

| Statistic | s.d. across 39 non-overlapping windows | Null median | Null 95th pct | Calibrated p |
|---|---|---|---|---|
| share | 0.185 | 0.170 | 0.201 | 0.205 |
| gamma | 0.941 | 0.913 | 1.251 | 0.438 |


Non-overlapping windows (counted back from 30 Sep 2026):

| Window | gamma | share |
|---|---|---|
| 2026-06-16 – 2026-09-30 | +0.705 | 0.454 |
| 2019-02-05 – 2019-05-21 | +3.123 | 0.400 |
| 2020-07-24 – 2020-11-05 | +0.888 | 0.366 |
| 2019-12-20 – 2020-04-07 | +1.241 | 0.353 |
| 2019-05-22 – 2019-09-05 | +2.062 | 0.315 |
| 2019-09-06 – 2019-12-19 | +1.622 | 0.289 |
| 2023-03-17 – 2023-07-03 | +0.869 | 0.255 |
| 2020-04-08 – 2020-07-23 | +0.763 | 0.214 |

The eight highest-share non-overlapping windows.
