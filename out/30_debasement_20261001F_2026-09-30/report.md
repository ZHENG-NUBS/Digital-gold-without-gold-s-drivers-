# Script 30 — Does Bitcoin respond to gold's drivers?

Sample: 2024-01-12 – 2026-09-30, 681 U.S. trading days. Price snapshot __20261001F, macro snapshot __20260921D. Seed 20261014.

## 0. Data checks

| Series | N | s.d. (% or bp) |
|---|---|---|
| IBIT | 681 | 3.094 |
| GLD | 681 | 1.400 |
| SPY | 681 | 0.983 |
| TLT | 681 | 0.773 |
| BTC16 | 681 | 3.066 |
| USD | 681 | 0.411 |
| dRY | 681 | 4.165 |
| dBE | 681 | 2.270 |

   CHECK [PASS] 0a. Δnominal ≈ Δreal + Δbreakeven (max abs gap < 2 bp; trivially 0 when T10YIE is computed from the other two) max 0.00 bp
   CHECK [PASS] 0b. TLT loads negatively on real yields and breakevens (sanity) -1.41, -1.49 % per 10 bp
   CHECK [PASS] 0c. IBIT vs Bitcoin at 16:00 ET daily correlation > 0.98 0.9997

## A. Factor regressions (daily)

| Asset | S&P 500 (per 1%) | Real yield (per +10 bp) | Breakeven infl. (per +10 bp) | Dollar, UUP (per 1%) | R² | N |
|---|---|---|---|---|---|---|
| GLD | +0.217*** (+3.54) | -0.158 (-1.23) | +0.223 (+0.98) | -1.394*** (-7.34) | 0.208 | 681 |
| IBIT | +1.256*** (+6.33) | +0.459 (+1.53) | +0.794 (+1.21) | -0.936*** (-2.66) | 0.179 | 681 |
| BTC16 | +1.241*** (+6.25) | +0.465 (+1.56) | +0.792 (+1.22) | -0.933*** (-2.66) | 0.179 | 681 |
| TLT | +0.072** (+2.38) | -1.411*** (-42.91) | -1.487*** (-24.80) | +0.152*** (+3.47) | 0.852 | 681 |

Coefficients are % return per unit of the factor shown; HAC t-statistics in parentheses; *, **, *** = 10%, 5%, 1%.

Standardized loadings (beta x sd(factor) / sd(asset)), 95% stationary-bootstrap intervals (B = 2000, mean block 5 days):

| Factor | GLD | IBIT | IBIT − GLD | p (diff) | IBIT same sign as GLD, CI excludes 0 |
|---|---|---|---|---|---|
| S&P 500 (per 1%) | +0.152 [+0.050, +0.255] | +0.399 [+0.331, +0.473] | +0.247 [+0.138, +0.366] | 0.000 | yes |
| Real yield (per +10 bp) | -0.047 [-0.132, +0.024] | +0.062 [-0.016, +0.131] | +0.109 [+0.009, +0.216] | 0.033 | no |
| Breakeven infl. (per +10 bp) | +0.036 [-0.039, +0.108] | +0.058 [-0.029, +0.145] | +0.022 [-0.083, +0.135] | 0.681 | no |
| Dollar, UUP (per 1%) | -0.409 [-0.501, -0.299] | -0.124 [-0.208, -0.037] | +0.285 [+0.158, +0.412] | 0.000 | yes |


### A2. Adding the gold-specific shock (H4)

| Asset | S&P 500 (per 1%) | Real yield (per +10 bp) | Breakeven infl. (per +10 bp) | Dollar, UUP (per 1%) | Gold-specific shock (per 1%) | R² | N |
|---|---|---|---|---|---|---|---|
| IBIT | +1.256*** (+6.27) | +0.459 (+1.53) | +0.794 (+1.22) | -0.936*** (-2.69) | +0.180** (+2.23) | 0.185 | 681 |
| BTC16 | +1.241*** (+6.19) | +0.465 (+1.56) | +0.792 (+1.22) | -0.933*** (-2.70) | +0.179** (+2.24) | 0.184 | 681 |

Coefficients are % return per unit of the factor shown; HAC t-statistics in parentheses; *, **, *** = 10%, 5%, 1%.


Benchmark test for H4: loading on the gold-specific shock (per 1% shock = per 1% return) against a 'digital gold' benchmark beta* = sd(asset)/sd(GLD), the loading that gives the asset the same standardized exposure to gold's own shock as GLD itself; HAC standard errors.

| Asset | Loading | 95% CI | Benchmark beta* | p (beta = beta*) | p (beta = beta*/2) | Min. detectable effect |
|---|---|---|---|---|---|---|
| IBIT | +0.180 | [+0.022, +0.338] | 2.21 | 9.7e-140 | 1.9e-30 | 0.23 |
| BTC16 | +0.179 | [+0.022, +0.336] | 2.19 | 5.9e-139 | 3e-30 | 0.22 |

## B. Gold-conditioned co-movement

| Statistic | Estimate | 95% CI | Null (independence) | p |
|---|---|---|---|---|
| corr(IBIT, GLD) | 0.175 | [0.081, 0.264] | 0.00 | 0.000 |
| partial corr(IBIT, GLD | SPY) | 0.110 | [0.024, 0.190] | 0.00 | 0.013 |
| corr(IBIT, gold-specific shock) | 0.072 | [-0.015, 0.154] | 0.00 | 0.103 |
| P(IBIT top 10% | GLD top 10%) | 0.174 | [0.100, 0.275] | 0.10 | 0.059 |
| P(IBIT bottom 10% | GLD bottom 10%) | 0.174 | [0.101, 0.275] | 0.10 | 0.034 |
| P(IBIT top 10% | GLD top 10%), SPY removed from both | 0.159 | [0.086, 0.261] | 0.10 | 0.107 |
| P(IBIT bottom 10% | GLD bottom 10%), SPY removed from both | 0.130 | [0.058, 0.229] | 0.10 | 0.340 |
| IBIT mean return on debasement days − other days (%) | 0.629 | [-0.142, 1.373] | 0.00 | 0.116 |
| GLD mean return on debasement days − other days (%) | 2.326 | [1.888, 2.758] | 0.00 | 0.000 |

Bootstrap: stationary, mean block 10 days, B = 2000. 'Debasement days' are the top decile of the gold-specific shock (GLD return orthogonal to SPY, real-yield, breakeven and dollar factors), 68 of 681 days.

## C. Stability over time

| Period | Asset | S&P 500 (per 1%) | Real yield (per +10 bp) | Breakeven infl. (per +10 bp) | Dollar, UUP (per 1%) | R² | N |
|---|---|---|---|---|---|---|---|
| 2024 | GLD | +0.218*** | -0.303** | +0.434* | -0.910*** | 0.23 | 244 |
| 2024 | IBIT | +1.668*** | +0.473 | +0.897 | -0.987 | 0.15 | 244 |
| 2025 | GLD | +0.085 | +0.140 | -0.029 | -1.151*** | 0.18 | 250 |
| 2025 | IBIT | +0.977*** | +0.652* | -0.138 | -0.616 | 0.21 | 250 |
| 2026 | GLD | +0.472** | -0.356 | +0.177 | -2.155*** | 0.30 | 187 |
| 2026 | IBIT | +1.820*** | +0.656 | +2.342** | -0.830 | 0.28 | 187 |

Figure: out/30_debasement_20261001F_2026-09-30/fig_rolling_loadings.png (120-day rolling standardized loadings).

## E. Is the gold-specific loading stable?

Andrews (1993) sup-Wald test for a single break in the IBIT loading on the gold-specific shock (HAC Wald statistics; asymptotic p-values simulated):

| Trimming | Break dates searched | sup-Wald | p-value | Most likely break | Loading before | Loading after | Days after break |
|---|---|---|---|---|---|---|---|
| 15% | 2024-06-10 – 2026-05-05 | 6.22 | 0.147 | 2026-04-13 | +0.091 | +0.595 | 119 |
| 10% | 2024-04-22 – 2026-06-24 | 8.68 | 0.059 | 2026-06-11 | +0.103 | +0.727 | 77 |

A break in the last part of the sample, beyond the searched range, cannot be located by this test; the rolling estimate below covers the end of the sample.

End-of-sample test (Andrews 2003): the last 74 days (from 2026-06-16, the data added after the first-pass analysis) against all 534 other 74-day windows of the earlier sample; p-values calibrated by 199 null bootstrap replications.

| Statistic | Last window | Median of earlier windows | Raw p | Calibrated p |
|---|---|---|---|---|
| S (all coefficients and residual variance) | 350.89 | 696.62 | 0.837 | 0.845 |
| Loading on the gold-specific shock (one-sided: higher) | +0.715 | +0.150 | 0.009 | 0.025 |

S is scaled by 10⁴.

Rolling 120-day loading on the gold-specific shock: last window (to 2026-09-30) +0.683 (95% band +0.284 to +1.082); 'digital gold' benchmark in that window 1.57. Share of windows whose band excludes 0: 12%.
Figure: out/30_debasement_20261001F_2026-09-30/fig_rolling_gres.png

## D. Robustness

### D1. Two-day non-overlapping returns

| Asset | S&P 500 (per 1%) | Real yield (per +10 bp) | Breakeven infl. (per +10 bp) | Dollar, UUP (per 1%) | R² | N |
|---|---|---|---|---|---|---|
| GLD | +0.250*** (+2.87) | -0.171 (-0.84) | +0.490 (+1.61) | -1.307*** (-4.62) | 0.201 | 341 |
| IBIT | +1.246*** (+5.49) | +0.037 (+0.10) | +0.896 (+1.17) | -0.615 (-1.15) | 0.195 | 341 |

Coefficients are % return per unit of the factor shown; HAC t-statistics in parentheses; *, **, *** = 10%, 5%, 1%.

Standardized loadings (beta x sd(factor) / sd(asset)), 95% stationary-bootstrap intervals (B = 2000, mean block 5 days):

| Factor | GLD | IBIT | IBIT − GLD | p (diff) | IBIT same sign as GLD, CI excludes 0 |
|---|---|---|---|---|---|
| S&P 500 (per 1%) | +0.178 [+0.052, +0.299] | +0.410 [+0.329, +0.504] | +0.232 [+0.097, +0.389] | 0.002 | yes |
| Real yield (per +10 bp) | -0.054 [-0.189, +0.064] | +0.005 [-0.089, +0.109] | +0.060 [-0.099, +0.234] | 0.439 | no |
| Breakeven infl. (per +10 bp) | +0.083 [-0.019, +0.182] | +0.071 [-0.033, +0.175] | -0.013 [-0.151, +0.124] | 0.907 | no |
| Dollar, UUP (per 1%) | -0.370 [-0.502, -0.206] | -0.081 [-0.200, +0.059] | +0.290 [+0.099, +0.482] | 0.003 | no |


### D2. Weekly (Wednesday-to-Wednesday) returns

| Asset | S&P 500 (per 1%) | Real yield (per +10 bp) | Breakeven infl. (per +10 bp) | Dollar, UUP (per 1%) | R² | N |
|---|---|---|---|---|---|---|
| GLD | +0.134 (+0.97) | -0.593*** (-3.36) | +0.913* (+1.71) | -1.755*** (-4.67) | 0.328 | 142 |
| IBIT | +1.415*** (+5.38) | +0.108 (+0.19) | +1.989** (+2.06) | -0.854 (-1.31) | 0.208 | 142 |

Coefficients are % return per unit of the factor shown; HAC t-statistics in parentheses; *, **, *** = 10%, 5%, 1%.

Standardized loadings (beta x sd(factor) / sd(asset)), 95% stationary-bootstrap intervals (B = 2000, mean block 5 days):

| Factor | GLD | IBIT | IBIT − GLD | p (diff) | IBIT same sign as GLD, CI excludes 0 |
|---|---|---|---|---|---|
| S&P 500 (per 1%) | +0.083 [-0.104, +0.254] | +0.405 [+0.269, +0.557] | +0.322 [+0.092, +0.565] | 0.006 | yes |
| Real yield (per +10 bp) | -0.171 [-0.289, -0.084] | +0.014 [-0.136, +0.172] | +0.185 [+0.024, +0.365] | 0.022 | no |
| Breakeven infl. (per +10 bp) | +0.138 [-0.031, +0.286] | +0.140 [-0.004, +0.292] | +0.001 [-0.215, +0.244] | 0.970 | no |
| Dollar, UUP (per 1%) | -0.502 [-0.667, -0.272] | -0.113 [-0.309, +0.103] | +0.389 [+0.134, +0.625] | 0.004 | no |


### D4. Market-based inflation proxy: TIP − IEF return instead of Δbreakeven

| Asset | S&P 500 (per 1%) | Real yield (per +10 bp) | TIP − IEF return (per 1%) | Dollar, UUP (per 1%) | R² | N |
|---|---|---|---|---|---|---|
| GLD | +0.214*** (+3.50) | -0.205 (-1.51) | +0.353 (+1.13) | -1.391*** (-7.35) | 0.208 | 681 |
| IBIT | +1.234*** (+5.95) | +0.215 (+0.67) | +1.671** (+2.08) | -0.966*** (-2.88) | 0.184 | 681 |

Coefficients are % return per unit of the factor shown; HAC t-statistics in parentheses; *, **, *** = 10%, 5%, 1%.


## Checks

- [PASS] 0a. Δnominal ≈ Δreal + Δbreakeven (max abs gap < 2 bp; trivially 0 when T10YIE is computed from the other two) max 0.00 bp
- [PASS] 0b. TLT loads negatively on real yields and breakevens (sanity) -1.41, -1.49 % per 10 bp
- [PASS] 0c. IBIT vs Bitcoin at 16:00 ET daily correlation > 0.98 0.9997
