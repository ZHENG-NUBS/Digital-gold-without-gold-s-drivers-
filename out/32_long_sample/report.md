# Script 32 — Long sample: is summer 2026 unusual in Bitcoin's history?

Sample 2015-01-05 – 2026-09-30, 2952 U.S. trading days with all series. Bitcoin at 16:00 ET (13:00 on early-close days) from Coinbase hourly bars; Bitstamp fills 137 days.

## 0. Checks

| Series | N | s.d. (% or bp) |
|---|---|---|
| BTC16 | 2952 | 4.081 |
| GLD | 2952 | 1.025 |
| SPY | 2952 | 1.105 |
| USD | 2952 | 0.454 |
| dRY | 2952 | 4.789 |
| dBE | 2952 | 3.004 |

Over the ETF period the panel has 681 days (script 30: 681).

## L1. Factor loadings by era

| Era | Asset | S&P 500 (per 1%) | Real yield (per +10 bp) | Breakeven infl. (per +10 bp) | Dollar, UUP (per 1%) | gamma (s.e.) | R² | N |
|---|---|---|---|---|---|---|---|---|
| 2015-2019 | GLD | -0.022 | -0.763*** | -0.519*** | -0.658*** | — | 0.34 | 1257 |
| 2015-2019 | BTC16 | +0.071 | +0.017 | +0.266 | +0.011 | +0.224 (0.221) | 0.00 | 1257 |
| 2020-2023 | GLD | +0.033 | -0.511*** | +0.047 | -0.675*** | — | 0.31 | 1006 |
| 2020-2023 | BTC16 | +0.944*** | +0.021 | +0.223 | -0.947** | +0.281* (0.156) | 0.14 | 1006 |
| Jan 2024 - 15 Jun 2026 | GLD | +0.196*** | -0.131 | +0.238 | -1.311*** | — | 0.19 | 615 |
| Jan 2024 - 15 Jun 2026 | BTC16 | +1.234*** | +0.431 | +0.803 | -0.764** | +0.115 (0.086) | 0.18 | 615 |
| 16 Jun - 30 Sep 2026 | GLD | +0.312 | -0.003 | -0.467 | -2.643*** | — | 0.39 | 74 |
| 16 Jun - 30 Sep 2026 | BTC16 | +0.683* | -0.184 | +0.608 | -0.882 | +0.705*** (0.221) | 0.33 | 74 |

Daily returns; HAC (5 lags). gamma = loading of Bitcoin on the gold-specific shock (GLD residual on the four factors, full-sample regression); per 1% shock.

Weekly (Wednesday-to-Wednesday) returns:

| Era | Asset | S&P 500 (per 1%) | Real yield (per +10 bp) | Breakeven infl. (per +10 bp) | Dollar, UUP (per 1%) | R² | N |
|---|---|---|---|---|---|---|---|
| 2015-2019 | GLD | +0.043 | -1.037*** | -0.524*** | -0.721*** | 0.43 | 260 |
| 2015-2019 | BTC16 | +0.421 | +0.028 | +1.311 | +0.591 | 0.01 | 260 |
| 2020-2023 | GLD | -0.098* | -0.505*** | +0.338* | -0.994*** | 0.43 | 209 |
| 2020-2023 | BTC16 | +0.921*** | -0.457 | +2.265*** | -1.206* | 0.26 | 209 |
| Jan 2024 - 15 Jun 2026 | GLD | +0.050 | -0.628*** | +1.022 | -1.803*** | 0.33 | 128 |
| Jan 2024 - 15 Jun 2026 | BTC16 | +1.533*** | +0.343 | +1.590 | -0.859 | 0.22 | 128 |
| Full sample | GLD | -0.022 | -0.693*** | +0.020 | -0.914*** | 0.33 | 613 |
| Full sample | BTC16 | +0.982*** | -0.556* | +1.658*** | -0.217 | 0.10 | 613 |

## L2. Rolling 120-day gamma since 2015

Last window (to 2026-09-30): gamma +0.666 (95% band +0.273 to +1.059); benchmark 1.55; share of a gold-like exposure 43%. It exceeds 77.6% of all earlier 120-day windows in gamma and 99.9% in share. Highest earlier 120-day gamma: +2.771 (window ending 2019-07-03).
Figure: out/32_long_sample/fig_long_gamma.png

## L3. The final 74-day window against every earlier 74-day window since 2015

| Statistic | Final window | Median earlier | 95th pct earlier | Max earlier | Share of earlier windows ≥ final |
|---|---|---|---|---|---|
| gamma | +0.705 | +0.091 | +1.878 | +3.331 | 0.252 |
| gamma / gamma* | 0.45 | 0.03 | 0.36 | 0.54 | 0.010 |

2805 earlier windows (overlapping), ending before the final window starts. The share in the last column is a descriptive rank, not a p-value: overlapping windows are dependent (see L4).

| Window (approx.) | gamma | gamma / gamma* |
|---|---|---|
| 2019-03-21 – 2019-07-02 | +3.331 | 0.36 |
| 2019-08-29 – 2019-12-10 | +2.710 | 0.53 |
| 2017-03-21 – 2017-06-30 | +2.291 | 0.27 |
| 2020-04-24 – 2020-08-05 | +1.754 | 0.45 |
| 2023-01-23 – 2023-05-04 | +1.631 | 0.42 |
| 2019-12-18 – 2020-03-30 | +1.423 | 0.38 |
| 2015-01-12 – 2015-04-23 | +1.319 | 0.26 |
| 2016-04-14 – 2016-07-26 | +1.282 | 0.36 |

Largest earlier episodes: the highest-gamma windows, at least about 74 trading days apart.

## L4. End-of-sample instability test on the long sample

End-of-sample test (Andrews 2003): the last 74 days (from 2026-06-16, the summer-2026 window) against all 2805 other 74-day windows of the earlier sample; p-values calibrated by 199 null bootstrap replications.

| Statistic | Last window | Median of earlier windows | Raw p | Calibrated p |
|---|---|---|---|---|
| S (all coefficients and residual variance) | 318.62 | 934.09 | 0.949 | 0.915 |
| Loading on the gold-specific shock (one-sided: higher) | +0.729 | +0.070 | 0.251 | 0.135 |

S is scaled by 10⁴.

Here the comparison windows run back to 2015. The S statistic is not informative over this sample, because Bitcoin's volatility, and with it the residual variance, has fallen several-fold since 2015; use the gamma row.

## L5. Gold-specific shock re-estimated year by year

| Era | gamma | s.e. | N |
|---|---|---|---|
| 2015-2019 | +0.145 | 0.230 | 1257 |
| 2020-2023 | +0.366** | 0.165 | 1006 |
| Jan 2024 - 15 Jun 2026 | +0.076 | 0.090 | 615 |
| 16 Jun - 30 Sep 2026 | +0.705*** | 0.221 | 74 |

The GLD factor regression is re-estimated within each calendar year, so the gold-specific shock allows gold's own factor loadings to drift over the 12 years.

