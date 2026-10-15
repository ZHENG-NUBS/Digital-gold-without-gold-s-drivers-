# -*- coding: utf-8 -*-
"""
32_long_sample.py — Is summer 2026 unusual in Bitcoin's history?

The ETF sample (Jan 2024 - Sep 2026) is short. Bitcoin itself trades back to 2015 at hourly
frequency, and every other series exists over that period, so this script repeats the analysis of
script 30 for Bitcoin priced at 16:00 ET (Coinbase hourly bars, Bitstamp as fallback) from
January 2015 to September 2026, synchronised with the ETF closes.

  L1  Factor loadings of Bitcoin and GLD by era: 2015-19, 2020-23, Jan 2024 - 15 Jun 2026, and the
      74 days from 16 Jun 2026; daily and weekly.
  L2  Rolling 120-day loading on the gold-specific shock (gamma), its 95% band, and the "share of a
      gold-like exposure" gamma / gamma*, gamma* = sd(BTC)/sd(GLD) in the same window (figure).
  L3  How unusual is the final 74-day window? Its gamma and gamma/gamma* ranked against every earlier
      74-day window since 2015, and the largest earlier episodes (non-overlapping peaks).
  L4  End-of-sample instability test (Andrews 2003) on the long sample, calibrated as in script 30.
  L5  Robustness: the gold-specific shock re-estimated year by year instead of over the full sample.

Inputs   data/raw/*__20261001H.* (from 32a_fetch_long.py). Reuses functions of 30_debasement_drivers.py.
Output   out/32_long_sample/report.md, rolling_gamma_long.csv, windows74.csv, fig_long_gamma.png
Usage    python 32_long_sample.py [--bcal 199]
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s30", os.path.join(HERE, "30_debasement_drivers.py"))
s30 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s30)

ASOF = "20261001H"
START, END = pd.Timestamp("2015-01-02"), pd.Timestamp("2026-09-30")
WIN = 74                     # length of the summer-2026 window (16 Jun - 30 Sep 2026)
ERAS = [("2015-2019", "2015-01-01", "2019-12-31"), ("2020-2023", "2020-01-01", "2023-12-31"),
        ("Jan 2024 - 15 Jun 2026", "2024-01-01", "2026-06-15"), ("16 Jun - 30 Sep 2026", "2026-06-16", "2026-09-30")]
FAC = s30.FACTORS
w, md, stars = s30.w, s30.md, s30.stars


def early_closes(y0=2014, y1=2026):
    """NYSE 13:00 closes by rule: day after Thanksgiving; 3 Jul when Mon-Thu; 24 Dec when Mon-Thu."""
    out = set()
    for y in range(y0, y1 + 1):
        nov = pd.date_range(f"{y}-11-01", f"{y}-11-30")
        thanks = [d for d in nov if d.weekday() == 3][3]
        out.add((thanks + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
        for d in (pd.Timestamp(f"{y}-07-03"), pd.Timestamp(f"{y}-12-24")):
            if d.weekday() <= 3:
                out.add(d.strftime("%Y-%m-%d"))
    return out


def load_hourly(raw, name):
    p = os.path.join(raw, f"BTCUSD_1h_{name}__{ASOF}.csv")
    if not os.path.exists(p):
        return None
    h = pd.read_csv(p)
    h["time_utc"] = pd.to_datetime(h["time_utc"], utc=True)
    return h.set_index("time_utc").sort_index()


def build_panel(raw):
    spy = s30.load_px(raw, "SPY", ASOF)
    if spy is None:
        sys.exit(f"SPY__{ASOF}.csv not found: run 32a_fetch_long.py first.")
    cal = spy.loc[(spy.index >= START - pd.Timedelta(days=10)) & (spy.index <= END)].index
    px = pd.DataFrame(index=cal)
    for t in ["SPY", "GLD", "TLT", "TIP", "IEF"]:
        s = s30.load_px(raw, t, ASOF)
        if s is not None:
            px[t] = s.reindex(cal)
    uup = s30.load_px(raw, "UUP", ASOF)
    if uup is None:
        sys.exit(f"UUP__{ASOF}.csv not found: run 32a_fetch_long.py first.")
    px["USD"] = uup.reindex(cal)
    s30.EARLY_CLOSE = early_closes()
    cb, bs = load_hourly(raw, "coinbase"), load_hourly(raw, "bitstamp")
    if cb is None and bs is None:
        sys.exit("No hourly Bitcoin bars: run 32a_fetch_long.py first.")
    btc = s30.btc_at_close(cb, cal) if cb is not None else pd.Series(np.nan, index=cal)
    n_fill = 0
    if bs is not None:
        alt = s30.btc_at_close(bs, cal)
        n_fill = int((btc.isna() & alt.notna()).sum())
        btc = btc.fillna(alt)
    px["BTC16"] = btc.values
    R = px.pct_change()
    for sid, col in [("DFII10", "dRY"), ("T10YIE", "dBE"), ("DGS10", "dNOM")]:
        p = os.path.join(raw, f"{sid}__{ASOF}.csv")
        if not os.path.exists(p):
            sys.exit(f"{sid}__{ASOF}.csv not found: run 32a_fetch_long.py first.")
        d = pd.read_csv(p, parse_dates=["Date"]).drop_duplicates("Date").set_index("Date")["Value"].astype(float)
        R[col] = d.reindex(d.index.union(cal)).ffill().reindex(cal).diff() * 100.0
    R = R.loc[(R.index >= START) & (R.index <= END)]
    return R, n_fill


def configure(asof, end, holdout_start):
    """Set snapshot, sample end and final-window start; WIN becomes the number of trading days from
    holdout_start to end (74 for the defaults). Used by scripts 32 and 33."""
    global ASOF, END, WIN, ERAS
    ASOF, END = asof, pd.Timestamp(end)
    s30.HOLDOUT_START = pd.Timestamp(holdout_start)
    raw = os.path.join(HERE, "data", "raw")
    spy = s30.load_px(raw, "SPY", ASOF)
    if spy is not None:
        WIN = int(((spy.index >= s30.HOLDOUT_START) & (spy.index <= END)).sum())
    if (asof, end, holdout_start) != ("20261001H", "2026-09-30", "2026-06-16"):
        ERAS = ERAS[:3] + [(f"{holdout_start} - {end}", holdout_start, end)]


def gres_full(D):
    m = s30.ols_hac(D["GLD"], D[FAC])
    return m.resid.reindex(D.index)


def gres_by_year(D):
    out = pd.Series(np.nan, index=D.index)
    for y, sub in D.groupby(D.index.year):
        sub = sub.dropna(subset=["GLD"] + FAC)
        if len(sub) > 60:
            out.loc[sub.index] = s30.ols_hac(sub["GLD"], sub[FAC]).resid
    return out


def window_gamma(y, X, g):
    Z = np.column_stack([np.ones(len(y)), X, g])
    b, *_ = np.linalg.lstsq(Z, y, rcond=None)
    return b[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bcal", type=int, default=199, help="null replications for the end-of-sample test")
    ap.add_argument("--asof", default=ASOF, help="snapshot suffix (default 20261001H)")
    ap.add_argument("--end", default=str(END.date()))
    ap.add_argument("--holdout-start", default=str(s30.HOLDOUT_START.date()))
    a = ap.parse_args()
    configure(a.asof, a.end, a.holdout_start)
    raw = os.path.join(HERE, "data", "raw")
    tag = "" if (ASOF, str(END.date()), str(s30.HOLDOUT_START.date())) == ("20261001H", "2026-09-30", "2026-06-16") else f"_{ASOF}_{s30.HOLDOUT_START.date()}"
    out = os.path.join(HERE, "out", "32_long_sample" + tag)
    os.makedirs(out, exist_ok=True)
    R, n_fill = build_panel(raw)
    D = R.dropna(subset=["BTC16", "GLD"] + FAC).copy()
    D["Gres"] = gres_full(D)
    fac = FAC + ["Gres"]

    w("# Script 32 — Long sample: is summer 2026 unusual in Bitcoin's history?")
    w()
    w(f"Sample {D.index.min().date()} – {D.index.max().date()}, {len(D)} U.S. trading days with all series. "
      f"Bitcoin at 16:00 ET (13:00 on early-close days) from Coinbase hourly bars; Bitstamp fills {n_fill} days.")
    w()
    w("## 0. Checks")
    w()
    w(md([[c, int(D[c].notna().sum()), f"{D[c].std() * (100 if not c.startswith('d') else 1):.3f}"]
          for c in ["BTC16", "GLD", "SPY", "USD", "dRY", "dBE"]], ["Series", "N", "s.d. (% or bp)"]))
    eta = D.loc["2024-01-12":]
    w(f"Over the ETF period the panel has {len(eta)} days (script 30: 681).")
    w()

    # ---------------------------------------------------------------- L1
    w("## L1. Factor loadings by era")
    w()
    rows = []
    for lab, a0, a1 in ERAS:
        sub = D.loc[a0:a1]
        if len(sub) < 40:
            continue
        for asset in ["GLD", "BTC16"]:
            Xc = fac if asset == "BTC16" else FAC
            m = s30.ols_hac(sub[asset], sub[Xc])
            cells = [lab, asset] + [f"{s30.rep(m.params[f], f):+.3f}{stars(m.pvalues[f])}" for f in FAC]
            cells.append(f"{m.params['Gres']:+.3f}{stars(m.pvalues['Gres'])} ({m.bse['Gres']:.3f})" if asset == "BTC16" else "—")
            cells += [f"{m.rsquared:.2f}", str(int(m.nobs))]
            rows.append(cells)
    w(md(rows, ["Era", "Asset"] + [s30.FLABEL[f] for f in FAC] + ["gamma (s.e.)", "R²", "N"]))
    w("Daily returns; HAC (5 lags). gamma = loading of Bitcoin on the gold-specific shock (GLD residual on the "
      "four factors, full-sample regression); per 1% shock.")
    w()
    A = s30.aggregate(R.dropna(subset=["BTC16", "GLD"] + FAC), "W")
    rows = []
    Aw = A.copy()
    Aw.index = pd.to_datetime([str(i).split("/")[-1] for i in Aw.index])
    for lab, a0, a1 in ERAS[:3] + [("Full sample", "2015-01-01", "2026-09-30")]:
        sub = Aw.loc[a0:a1]
        for asset in ["GLD", "BTC16"]:
            m = s30.ols_hac(sub[asset], sub[FAC])
            rows.append([lab, asset] + [f"{s30.rep(m.params[f], f):+.3f}{stars(m.pvalues[f])}" for f in FAC]
                        + [f"{m.rsquared:.2f}", str(int(m.nobs))])
    w("Weekly (Wednesday-to-Wednesday) returns:")
    w()
    w(md(rows, ["Era", "Asset"] + [s30.FLABEL[f] for f in FAC] + ["R²", "N"]))

    # ---------------------------------------------------------------- L2
    w("## L2. Rolling 120-day gamma since 2015")
    w()
    y, X, g, gld = D["BTC16"].values, D[FAC].values, D["Gres"].values, D["GLD"].values
    recs = []
    for k in range(s30.ROLL, len(D) + 1):
        sl = slice(k - s30.ROLL, k)
        m = s30.ols_hac(pd.Series(y[sl]), pd.DataFrame(np.column_stack([X[sl], g[sl]]), columns=fac))
        bstar = y[sl].std(ddof=1) / gld[sl].std(ddof=1)
        recs.append({"date": D.index[k - 1], "gamma": m.params["Gres"], "se": m.bse["Gres"], "benchmark": bstar,
                     "share": m.params["Gres"] / bstar})
    roll = pd.DataFrame(recs).set_index("date")
    roll.to_csv(os.path.join(out, "rolling_gamma_long.csv"))
    last = roll.iloc[-1]
    pct = (roll["gamma"].iloc[:-1] < last.gamma).mean()
    pct_s = (roll["share"].iloc[:-1] < last.share).mean()
    w(f"Last window (to {roll.index[-1].date()}): gamma {last.gamma:+.3f} (95% band {last.gamma - 1.96 * last.se:+.3f} "
      f"to {last.gamma + 1.96 * last.se:+.3f}); benchmark {last.benchmark:.2f}; share of a gold-like exposure "
      f"{last.share:.0%}. It exceeds {pct:.1%} of all earlier 120-day windows in gamma and {pct_s:.1%} in share. "
      f"Highest earlier 120-day gamma: {roll['gamma'].iloc[:-1].max():+.3f} (window ending "
      f"{roll['gamma'].iloc[:-1].idxmax().date()}).")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(8, 5.2), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
        ax[0].fill_between(roll.index, roll.gamma - 1.96 * roll.se, roll.gamma + 1.96 * roll.se, color="#1f4e79", alpha=0.18, lw=0)
        ax[0].plot(roll.index, roll.gamma, color="#1f4e79", lw=1.3)
        ax[0].axhline(0, color="grey", lw=0.6)
        ax[0].set_ylabel("gamma (120-day)", fontsize=9)
        ax[1].plot(roll.index, roll.share, color="#B8860B", lw=1.3)
        ax[1].axhline(0, color="grey", lw=0.6)
        ax[1].set_ylabel("gamma / gamma*", fontsize=9)
        for a_ in ax:
            a_.axvline(pd.Timestamp("2024-01-11"), color="black", lw=0.8, ls=":")
            a_.tick_params(labelsize=8)
        ax[0].text(pd.Timestamp("2024-02-01"), ax[0].get_ylim()[1] * 0.9, "spot ETFs", fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(out, "fig_long_gamma.png"), dpi=200)
        plt.close(fig)
        w(f"Figure: {os.path.join(out, 'fig_long_gamma.png')}")
    except Exception as e:  # noqa: BLE001
        w(f"(figure skipped: {e!r})")
    w()

    # ---------------------------------------------------------------- L3
    w(f"## L3. The final {WIN}-day window against every earlier {WIN}-day window since 2015")
    w()
    gam, shr, ends = [], [], []
    for k in range(WIN, len(D) + 1):
        sl = slice(k - WIN, k)
        gm = window_gamma(y[sl], X[sl], g[sl])
        gam.append(gm)
        shr.append(gm / (y[sl].std(ddof=1) / gld[sl].std(ddof=1)))
        ends.append(D.index[k - 1])
    W = pd.DataFrame({"gamma": gam, "share": shr}, index=pd.Index(ends, name="window_end"))
    W.to_csv(os.path.join(out, "windows74.csv"))
    fin = W.iloc[-1]
    earlier = W.iloc[:-WIN]                       # windows that do not overlap the final one
    w(md([["gamma", f"{fin.gamma:+.3f}", f"{earlier.gamma.median():+.3f}", f"{earlier.gamma.quantile(0.95):+.3f}",
           f"{earlier.gamma.max():+.3f}", f"{(earlier.gamma >= fin.gamma).mean():.3f}"],
          ["gamma / gamma*", f"{fin.share:.2f}", f"{earlier.share.median():.2f}", f"{earlier.share.quantile(0.95):.2f}",
           f"{earlier.share.max():.2f}", f"{(earlier.share >= fin.share).mean():.3f}"]],
         ["Statistic", "Final window", "Median earlier", "95th pct earlier", "Max earlier", "Share of earlier windows ≥ final"]))
    w(f"{len(earlier)} earlier windows (overlapping), ending before the final window starts. The share in the last "
      "column is a descriptive rank, not a p-value: overlapping windows are dependent (see L4).")
    w()
    # Largest earlier episodes: greedy non-overlapping peaks of gamma
    E = earlier.sort_values("gamma", ascending=False)
    peaks = []
    for t, r in E.iterrows():
        if all(abs((t - p).days) > WIN * 1.45 for p, _ in peaks):
            peaks.append((t, r))
        if len(peaks) == 8:
            break
    w(md([[str((t - pd.tseries.offsets.BDay(WIN - 1)).date()) + " – " + str(t.date()), f"{r.gamma:+.3f}", f"{r.share:.2f}"]
          for t, r in peaks], ["Window (approx.)", "gamma", "gamma / gamma*"]))
    w("Largest earlier episodes: the highest-gamma windows, at least about 74 trading days apart.")
    w()

    # ---------------------------------------------------------------- L4
    w("## L4. End-of-sample instability test on the long sample")
    w()
    sub = D[["BTC16"] + fac].rename(columns={"BTC16": "IBIT"})
    saved = len(s30.LINES)
    s30.end_of_sample_test(sub, fac, B_cal=a.bcal)
    s30.LINES[:] = s30.LINES[:saved] + [l.replace("the data added after the first-pass analysis",
                                                  "the final window") for l in s30.LINES[saved:]]
    w("Here the comparison windows run back to 2015. The S statistic is not informative over this sample, because "
      "Bitcoin's volatility, and with it the residual variance, has fallen several-fold since 2015; use the gamma row.")
    w()

    # ---------------------------------------------------------------- L5
    w("## L5. Gold-specific shock re-estimated year by year")
    w()
    D2 = D.copy()
    D2["Gres"] = gres_by_year(D2)
    D2 = D2.dropna(subset=["Gres"])
    rows = []
    for lab, a0, a1 in ERAS:
        sub2 = D2.loc[a0:a1]
        m = s30.ols_hac(sub2["BTC16"], sub2[fac])
        rows.append([lab, f"{m.params['Gres']:+.3f}{stars(m.pvalues['Gres'])}", f"{m.bse['Gres']:.3f}", str(int(m.nobs))])
    w(md(rows, ["Era", "gamma", "s.e.", "N"]))
    w("The GLD factor regression is re-estimated within each calendar year, so the gold-specific shock allows "
      "gold's own factor loadings to drift over the 12 years.")
    w()
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(s30.LINES) + "\n")
    print(f"\nWrote {out}/report.md")


if __name__ == "__main__":
    main()
