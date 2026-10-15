# -*- coding: utf-8 -*-
"""
31_placebo_twostep.py — Two robustness checks for the summer-2026 rise in Bitcoin's loading on
gold-specific shocks (script 30, section E).

1. Placebo assets. If every risky asset began to move with gold-specific shocks in summer 2026, the
   rise is not about Bitcoin. For IBIT and for placebo ETFs (QQQ, EFA, TLT, AGG) we estimate the
   loading gamma on the gold-specific shock before and after HOLDOUT_START and run the same calibrated
   end-of-sample test as script 30. The factor set and the gold shock are those of script 30.

2. Two-step bootstrap. The gold-specific shock is a residual estimated on the same data, so plain
   standard errors for gamma ignore its estimation error. Here each stationary-block bootstrap draw
   resamples days jointly, re-estimates the GLD regression, rebuilds the shock and re-estimates the
   IBIT regression. Reported: full-sample gamma, gamma before and after HOLDOUT_START, and the change.

Inputs  data/raw/*__20261001F.csv (from 30b) plus QQQ/EFA/AGG from the __20260921S files, which since
        14 Oct 2026 run to 30 Sep 2026 (see the README note); macro series __20260921D (from 30a).
Usage   python 31_placebo_twostep.py [--boot 999]
Output  out/31_placebo_twostep/report.md
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import contextlib
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s30", os.path.join(HERE, "30_debasement_drivers.py"))
s30 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s30)

END = pd.Timestamp("2026-09-30")
PLACEBO = [("QQQ", "20260921S"), ("EFA", "20260921S"), ("TLT", "20261001F"), ("AGG", "20260921S")]
LINES = []


def w(s=""):
    LINES.append(s)
    print(s)


def gamma_ols(y, X, g):
    Z = np.column_stack([np.ones(len(y)), X, g])
    b, *_ = np.linalg.lstsq(Z, y, rcond=None)
    return b[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=999)
    ap.add_argument("--end", default=str(END.date()))
    ap.add_argument("--holdout-start", default=str(s30.HOLDOUT_START.date()))
    ap.add_argument("--asof-prices", default="20261001F")
    ap.add_argument("--asof-macro", default=s30.ASOF_D)
    a = ap.parse_args()
    s30.ASOF_S, s30.ASOF_D, s30.END = a.asof_prices, a.asof_macro, pd.Timestamp(a.end)
    s30.HOLDOUT_START = pd.Timestamp(a.holdout_start)
    raw = os.path.join(HERE, "data", "raw")
    R, _ = s30.build_panel(raw)
    for t, sfx in PLACEBO:
        if t not in R:
            s = s30.load_px(raw, t, sfx)
            if s is not None:
                R[t] = s.reindex(s.index.union(R.index)).pct_change().reindex(R.index)
    D = R.copy()
    D["Gres"] = s30.gold_residual(D, s30.FACTORS)
    fac = s30.FACTORS + ["Gres"]
    post = D.index >= s30.HOLDOUT_START
    out = os.path.join(HERE, "out", "31_placebo_twostep" + ("" if a.holdout_start == "2026-06-16" else f"_{a.holdout_start}"))
    os.makedirs(out, exist_ok=True)

    w("# Script 31 — Placebo assets and two-step bootstrap")
    w()
    w(f"Sample {D.index.min().date()} – {D.index.max().date()}; summer window from {s30.HOLDOUT_START.date()} "
      f"({int(post.sum())} days).")
    w()
    w("## 1. Placebo assets")
    w()
    rows = []
    for asset in ["IBIT"] + [t for t, _ in PLACEBO]:
        if asset not in D or D[asset].notna().sum() < 600:
            rows.append([asset, "not available", "", "", "", ""])
            continue
        sub = D[[asset] + fac].dropna().rename(columns={asset: "IBIT"})
        pre_m = s30.ols_hac(sub.loc[~(sub.index >= s30.HOLDOUT_START), "IBIT"], sub.loc[~(sub.index >= s30.HOLDOUT_START), fac])
        post_m = s30.ols_hac(sub.loc[sub.index >= s30.HOLDOUT_START, "IBIT"], sub.loc[sub.index >= s30.HOLDOUT_START, fac])
        sd_ratio = sub["IBIT"].std() / D.loc[sub.index, "GLD"].std()
        with contextlib.redirect_stdout(io.StringIO()):
            saved = list(s30.LINES)
            cS, cG = s30.end_of_sample_test(sub[["IBIT"] + fac], fac)
            s30.LINES[:] = saved
        rows.append([asset, f"{pre_m.params['Gres']:+.3f} ({pre_m.bse['Gres']:.3f})",
                     f"{post_m.params['Gres']:+.3f} ({post_m.bse['Gres']:.3f})",
                     f"{(post_m.params['Gres'] - pre_m.params['Gres']) / sd_ratio:+.3f}",
                     f"{cG:.3f}", f"{cS:.3f}"])
    w(s30.md(rows, ["Asset", "gamma before (s.e.)", "gamma summer 2026 (s.e.)",
                    "Change / [sd(asset)/sd(GLD)]", "End-of-sample p, gamma", "End-of-sample p, S"]))
    w("gamma: loading on the gold-specific shock with SPY, real-yield, breakeven and dollar factors; HAC s.e. "
      "The change is scaled by each asset's volatility relative to gold so that assets are comparable. "
      "End-of-sample p-values: Andrews (2003), calibrated by 199 null bootstrap replications, as in script 30.")
    w()

    w("## 2. Two-step bootstrap for IBIT")
    w()
    sub = D[["IBIT", "GLD"] + s30.FACTORS].dropna()
    n = len(sub)
    y, gld, X = sub["IBIT"].values, sub["GLD"].values, sub[s30.FACTORS].values
    pmask = (sub.index >= s30.HOLDOUT_START)

    def two_step(idx):
        Xb, gb, yb, pm = X[idx], gld[idx], y[idx], pmask[idx]
        Z = np.column_stack([np.ones(len(idx)), Xb])
        bg, *_ = np.linalg.lstsq(Z, gb, rcond=None)
        res = gb - Z @ bg
        full = gamma_ols(yb, Xb, res)
        pre = gamma_ols(yb[~pm], Xb[~pm], res[~pm])
        pst = gamma_ols(yb[pm], Xb[pm], res[pm]) if pm.sum() > 10 else np.nan
        return full, pre, pst

    rng = np.random.default_rng(s30.SEED)
    pt = two_step(np.arange(n))
    # Resample within the two periods separately (blocks never cross the split), so each draw keeps
    # the summer's length and the change is estimated with both periods' uncertainty.
    pre_idx, post_idx = np.where(~pmask)[0], np.where(pmask)[0]
    I1 = s30.stationary_boot(len(pre_idx), a.boot, s30.L_BOOT, rng)
    I2 = s30.stationary_boot(len(post_idx), a.boot, s30.L_BOOT, rng)
    bs = np.array([two_step(np.concatenate([pre_idx[I1[:, r]], post_idx[I2[:, r]]])) for r in range(a.boot)])
    rows = []
    for k, lab in enumerate(["Full sample", f"Before {s30.HOLDOUT_START.date()}", "Summer 2026"]):
        lo, hi = np.nanpercentile(bs[:, k], [2.5, 97.5])
        rows.append([lab, f"{pt[k]:+.3f}", f"[{lo:+.3f}, {hi:+.3f}]"])
    d = bs[:, 2] - bs[:, 1]
    lo, hi = np.nanpercentile(d, [2.5, 97.5])
    rows.append(["Change (summer − before)", f"{pt[2] - pt[1]:+.3f}", f"[{lo:+.3f}, {hi:+.3f}]  "
                 f"one-sided p = {(np.sum(d <= 0) + 1) / (np.isfinite(d).sum() + 1):.3f}"])
    w(s30.md(rows, ["IBIT loading on the gold-specific shock", "Estimate", "95% two-step bootstrap interval"]))
    w(f"Each of {a.boot} draws resamples days within each period (stationary blocks, mean length {s30.L_BOOT}), "
      "re-estimates the GLD factor regression, rebuilds the gold-specific shock and re-estimates the IBIT "
      "regression. The interval therefore includes the estimation error of the shock itself.")
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"\nWrote {out}/report.md")


if __name__ == "__main__":
    main()
