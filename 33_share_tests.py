# -*- coding: utf-8 -*-
"""
33_share_tests.py — Formal tests for the scale-free exposure share and for episodic variation
(FRL letter, long sample 2015-2026)

Script 32 measures Bitcoin's exposure to gold-specific shocks in each 74-day window by
    gamma          the loading on the gold-specific shock, and
    share = gamma / gamma*,  gamma* = sd(BTC)/sd(GLD) in the same window,
the share being comparable across Bitcoin's very different volatility regimes. Script 32 ranks the
final window descriptively. This script adds two calibrated tests under the null of a CONSTANT loading:

  T1  Is the final (summer-2026) window unusually high? Statistic: the share of earlier windows whose
      share (or gamma) is at least the final window's. Calibrated p-value: the probability of an
      equally extreme rank under the null.
  T2  Is the exposure episodic? Statistic: the standard deviation, across non-overlapping 74-day
      windows, of the window share (and of gamma). Calibrated p-value: the probability that a
      constant loading produces at least that much variation.

Null simulation: y* = X b0 + e*, where b0 is the full-sample regression of Bitcoin on the four
factors and the gold-specific shock (constant gamma), and e* are the full-sample residuals multiplied
by Rademacher signs drawn in blocks of 5 days (a wild block bootstrap). Each residual stays on its own
date, so Bitcoin's actual volatility path and the regressors are kept exactly; only the link between
Bitcoin and the gold shock is held constant.

Inputs  as script 32 (data/raw/*__20261001H.*). Output out/33_share_tests/report.md
Usage   python 33_share_tests.py [--reps 999]
"""
from __future__ import annotations

import argparse
import importlib.util
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s32", os.path.join(HERE, "32_long_sample.py"))
s32 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s32)
s30 = s32.s30
WIN, BLOCK, SEED = s32.WIN, 5, 20261014


def window_stats(y, Z, gld, starts):
    """gamma and share for windows [s, s+WIN). Z = [1, factors, gres]."""
    g = np.empty(len(starts))
    sh = np.empty(len(starts))
    for k, s in enumerate(starts):
        sl = slice(s, s + WIN)
        b, *_ = np.linalg.lstsq(Z[sl], y[sl], rcond=None)
        g[k] = b[-1]
        sh[k] = b[-1] / (y[sl].std(ddof=1) / gld[sl].std(ddof=1))
    return g, sh


def stats_for(y, Z, gld, n):
    starts_all = np.arange(0, n - WIN + 1)
    g, sh = window_stats(y, Z, gld, starts_all)
    fin_g, fin_s = g[-1], sh[-1]
    earlier = starts_all <= (n - 2 * WIN)            # windows ending before the final window starts
    rank_g = (g[earlier] >= fin_g).mean()
    rank_s = (sh[earlier] >= fin_s).mean()
    # non-overlapping windows counted back from the end, so the final window is one of them
    idx = np.arange(n - WIN, -1, -WIN)[::-1]
    g_no, s_no = window_stats(y, Z, gld, idx)
    return dict(fin_g=fin_g, fin_s=fin_s, rank_g=rank_g, rank_s=rank_s,
                sd_g=g_no.std(ddof=1), sd_s=s_no.std(ddof=1), n_no=len(idx), g_no=g_no, s_no=s_no, idx=idx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=999)
    ap.add_argument("--asof", default=s32.ASOF)
    ap.add_argument("--end", default=str(s32.END.date()))
    ap.add_argument("--holdout-start", default=str(s30.HOLDOUT_START.date()))
    a = ap.parse_args()
    global WIN
    s32.configure(a.asof, a.end, a.holdout_start)
    WIN = s32.WIN
    raw = os.path.join(HERE, "data", "raw")
    default = (a.asof, a.end, a.holdout_start) == ("20261001H", "2026-09-30", "2026-06-16")
    out = os.path.join(HERE, "out", "33_share_tests" + ("" if default else f"_{a.asof}_{a.holdout_start}"))
    os.makedirs(out, exist_ok=True)
    R, _ = s32.build_panel(raw)
    D = R.dropna(subset=["BTC16", "GLD"] + s32.FAC).copy()
    D["Gres"] = s32.gres_full(D)
    fac = s32.FAC + ["Gres"]
    n = len(D)
    y = D["BTC16"].values
    gld = D["GLD"].values
    Z = np.column_stack([np.ones(n), D[fac].values])
    obs = stats_for(y, Z, gld, n)

    b0, *_ = np.linalg.lstsq(Z, y, rcond=None)
    e = y - Z @ b0
    rng = np.random.default_rng(SEED)
    nb = int(np.ceil(n / BLOCK))
    sims = []
    for r in range(a.reps):
        signs = np.repeat(rng.choice([-1.0, 1.0], nb), BLOCK)[:n]
        sims.append(stats_for(Z @ b0 + e * signs, Z, gld, n))
    S = pd.DataFrame([{k: v for k, v in s.items() if k in ("rank_g", "rank_s", "sd_g", "sd_s")} for s in sims])

    def p_low(col, val):   # rank statistics: small = extreme
        return (np.sum(S[col] <= val) + 1) / (len(S) + 1)

    def p_high(col, val):  # dispersion statistics: large = extreme
        return (np.sum(S[col] >= val) + 1) / (len(S) + 1)

    L = []
    L.append("# Script 33 — Calibrated tests for the exposure share and for episodic variation")
    L.append("")
    L.append(f"Sample {D.index.min().date()} – {D.index.max().date()} ({n} days); windows of {WIN} days; "
             f"{a.reps} null replications (constant loading, wild block bootstrap, blocks of {BLOCK} days, seed {SEED}).")
    L.append("")
    L.append(f"## T1. Is the final window (from {s30.HOLDOUT_START.date()}) unusually high?")
    L.append("")
    L.append(s30.md([
        ["share = gamma / gamma*", f"{obs['fin_s']:.3f}", f"{obs['rank_s']:.3f}", f"{p_low('rank_s', obs['rank_s']):.3f}"],
        ["gamma", f"{obs['fin_g']:+.3f}", f"{obs['rank_g']:.3f}", f"{p_low('rank_g', obs['rank_g']):.3f}"]],
        ["Statistic", "Final window", "Share of earlier windows ≥ final", "Calibrated p (one-sided)"]))
    L.append("")
    L.append("## T2. Is the exposure episodic?")
    L.append("")
    L.append(s30.md([
        ["share", f"{obs['sd_s']:.3f}", f"{np.median(S['sd_s']):.3f}", f"{np.quantile(S['sd_s'], 0.95):.3f}", f"{p_high('sd_s', obs['sd_s']):.3f}"],
        ["gamma", f"{obs['sd_g']:.3f}", f"{np.median(S['sd_g']):.3f}", f"{np.quantile(S['sd_g'], 0.95):.3f}", f"{p_high('sd_g', obs['sd_g']):.3f}"]],
        ["Statistic", f"s.d. across {obs['n_no']} non-overlapping windows", "Null median", "Null 95th pct", "Calibrated p"]))
    L.append("")
    L.append(f"Non-overlapping windows (counted back from {D.index.max().date()}):")
    L.append("")
    ends = D.index[obs["idx"] + WIN - 1]
    starts = D.index[obs["idx"]]
    top = np.argsort(-obs["s_no"])[:8]
    L.append(s30.md([[f"{starts[i].date()} – {ends[i].date()}", f"{obs['g_no'][i]:+.3f}", f"{obs['s_no'][i]:.3f}"] for i in top],
                    ["Window", "gamma", "share"]))
    L.append("The eight highest-share non-overlapping windows.")
    pd.DataFrame({"start": starts, "end": ends, "gamma": obs["g_no"], "share": obs["s_no"]}).to_csv(
        os.path.join(out, "nonoverlapping_windows.csv"), index=False)
    txt = "\n".join(L) + "\n"
    open(os.path.join(out, "report.md"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
