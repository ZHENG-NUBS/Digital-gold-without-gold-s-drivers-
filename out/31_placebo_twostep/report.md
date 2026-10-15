# Script 31 — Placebo assets and two-step bootstrap

Sample 2024-01-12 – 2026-09-30; summer window from 2026-06-16 (74 days).

## 1. Placebo assets

| Asset | gamma before (s.e.) | gamma summer 2026 (s.e.) | Change / [sd(asset)/sd(GLD)] | End-of-sample p, gamma | End-of-sample p, S |
|---|---|---|---|---|---|
| IBIT | +0.111 (0.086) | +0.729 (0.225) | +0.280 | 0.025 | 0.845 |
| QQQ | +0.022 (0.013) | +0.037 (0.051) | +0.016 | 0.140 | 0.010 |
| EFA | +0.069 (0.020) | +0.100 (0.040) | +0.045 | 0.440 | 0.670 |
| TLT | -0.025 (0.013) | -0.009 (0.021) | +0.029 | 0.730 | 0.425 |
| AGG | -0.001 (0.003) | +0.011 (0.005) | +0.057 | 0.085 | 0.810 |

gamma: loading on the gold-specific shock with SPY, real-yield, breakeven and dollar factors; HAC s.e. The change is scaled by each asset's volatility relative to gold so that assets are comparable. End-of-sample p-values: Andrews (2003), calibrated by 199 null bootstrap replications, as in script 30.

## 2. Two-step bootstrap for IBIT

| IBIT loading on the gold-specific shock | Estimate | 95% two-step bootstrap interval |
|---|---|---|
| Full sample | +0.180 | [+0.028, +0.342] |
| Before 2026-06-16 | +0.111 | [-0.064, +0.284] |
| Summer 2026 | +0.729 | [+0.332, +1.172] |
| Change (summer − before) | +0.619 | [+0.180, +1.096]  one-sided p = 0.006 |

Each of 999 draws resamples days within each period (stationary blocks, mean length 5), re-estimates the GLD factor regression, rebuilds the gold-specific shock and re-estimates the IBIT regression. The interval therefore includes the estimation error of the shock itself.
