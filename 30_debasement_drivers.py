# -*- coding: utf-8 -*-
"""
30_debasement_drivers.py — Does Bitcoin respond to gold's drivers? (FRL letter, first pass)

Question
    The JRFM paper compares Bitcoin with gold through their relation to *equities*
    (hedge / safe haven, tail risk in portfolios). It never asks whether Bitcoin responds to
    what moves *gold*. If Bitcoin is "digital gold" in the sense of the 2025-26 "debasement
    trade", a spot Bitcoin ETF should load on gold's macro drivers with gold's signs:
        H1  real yields       gold falls when real yields rise           (beta_RY  < 0)
        H2  breakeven infl.   gold rises with inflation expectations     (beta_BE  > 0)
        H3  U.S. dollar       gold falls when the dollar rises           (beta_USD < 0)
        H4  gold-specific     Bitcoin loads on the part of gold's return that the
            shocks            equity, rate and dollar factors do not explain (beta_G > 0)
    and these loadings should be comparable once scaled by volatility.

Design
    Daily close-to-close returns on U.S. trading days, 12 Jan 2024 - 15 Jun 2026 (same calendar as
    the JRFM paper). Factors: SPY return; change in the 10-year TIPS yield (DFII10, bp); change in
    10-year breakeven inflation (T10YIE, bp); UUP return (dollar, 16:00 ET close). Assets: IBIT,
    Bitcoin at 16:00 ET (hourly Coinbase bars, Bitstamp as fallback), GLD, and TLT as a sanity check
    (a long-duration bond must load strongly negatively on both yield factors).

    A  Factor regressions, HAC (Newey-West, 5 lags) t-statistics; coefficients per 10 bp / per 1%.
       Standardized loadings (beta * sd(factor) / sd(asset)) make IBIT and GLD comparable.
       IBIT-minus-GLD differences in standardized loadings: stationary block bootstrap (rows
       resampled jointly, so cross-asset dependence is kept).
    B  Gold-conditioned co-movement: correlation and partial correlation of IBIT with GLD;
       co-exceedance probabilities in GLD's upper / lower 10% tails vs 0.10 under independence;
       IBIT's mean return on "debasement days" (top decile of the gold-specific shock).
    C  Stability: the regressions by calendar period (2024, 2025, 2026H1) and rolling 120-day
       standardized loadings (figure).
    D  Robustness: 2-day and weekly (Wed-Wed) returns for the timing mismatch between FRED
       end-of-day yields and 16:00 ET closes; broad dollar index (DTWEXBGS) instead of UUP;
       TIP-IEF return spread as a market-based real-rate proxy.

Inputs   data/raw/*__20260921S.csv (existing snapshot, read only) and data/raw/*__20260921D.csv
         (from 30a_fetch_macro.py).
Output   out/30_debasement/report.md, tables_*.csv, fig_rolling_loadings.png
Usage    python 30_debasement_drivers.py [--raw data/raw] [--boot 2000]
         python 30_debasement_drivers.py --selftest      # synthetic data with known loadings
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import tempfile
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
ASOF_S, ASOF_D = "20260921S", "20260921D"
SEED = 20261014
START, END = pd.Timestamp("2024-01-12"), pd.Timestamp("2026-06-15")
B_BOOT, L_BOOT, L_TAIL = 2000, 5, 10
HAC_LAGS = 5
ROLL = 120
HOLDOUT_START = pd.Timestamp("2026-06-16")   # first day after the first-pass sample
EARLY_CLOSE = {"2024-07-03", "2024-11-29", "2024-12-24", "2025-07-03", "2025-11-28", "2025-12-24"}
FACTORS = ["SPY", "dRY", "dBE", "USD"]
FLABEL = {"SPY": "S&P 500 (per 1%)", "dRY": "Real yield (per +10 bp)",
          "dBE": "Breakeven infl. (per +10 bp)", "USD": "Dollar, UUP (per 1%)",
          "Gres": "Gold-specific shock (per 1%)"}
# Reported coefficient = % return of the asset per UNIT of the factor (1% for returns, 10 bp for yields).
UNIT = {"SPY": 0.01, "dRY": 10.0, "dBE": 10.0, "USD": 0.01, "Gres": 0.01, "INF": 0.01}
FLABEL["INF"] = "TIP − IEF return (per 1%)"


def rep(b, f):
    return b * UNIT[f] * 100.0

LINES: list[str] = []
CHECKS: list[str] = []


def w(s=""):
    LINES.append(s)
    print(s)


def check(label, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    CHECKS.append(f"[{tag}] {label} {detail}")
    w(f"   CHECK [{tag}] {label} {detail}")
    return ok


def md(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


# ============================================================ kernels ====
def stationary_boot(n, R, L, rng):
    """Row-index matrix (n x R), stationary block bootstrap (Politis-Romano), as in scripts 11/20."""
    p = 1.0 / L
    idx = np.empty((n, R), dtype=np.int64)
    idx[0] = rng.integers(0, n, R)
    newblk = rng.random((n, R)) < p
    jump = rng.integers(0, n, (n, R))
    for t in range(1, n):
        idx[t] = np.where(newblk[t], jump[t], (idx[t - 1] + 1) % n)
    return idx


def pvalue(bs, null=0.0):
    bs = np.asarray(bs, float)
    bs = bs[np.isfinite(bs)]
    return float(min(1.0, 2 * min((bs <= null).mean(), (bs >= null).mean())))


def ols_hac(y, X, lags=HAC_LAGS):
    Xc = sm.add_constant(X, has_constant="add")
    return sm.OLS(y, Xc, missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": lags})


def ols_beta(y, X):
    """Plain OLS slopes (no constant in output) for the bootstrap; X is n x k."""
    Xc = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(Xc, y, rcond=None)
    return b[1:]


def std_load(b, X, y):
    return b * X.std(0, ddof=1) / y.std(ddof=1)


# ============================================================ loading ====
def find_raw_dir(arg):
    for c in ([arg] if arg else []) + [os.path.join(HERE, "data", "raw"), os.path.join(os.getcwd(), "data", "raw")]:
        if c and os.path.exists(os.path.join(c, f"SPY__{ASOF_S}.csv")):  # ASOF_S may be set by --asof-prices
            return c
    return None


def load_px(raw, t, asof):
    p = os.path.join(raw, f"{t}__{asof}.csv")
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, parse_dates=["Date"]).sort_values("Date").drop_duplicates("Date").set_index("Date")
    return d["AdjClose"]


def load_fred(raw, sid):
    p = os.path.join(raw, f"{sid}__{ASOF_D}.csv")
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, parse_dates=["Date"]).sort_values("Date").drop_duplicates("Date").set_index("Date")
    return d["Value"].astype(float)


def load_hourly(raw, name):
    p = os.path.join(raw, f"BTCUSD_1h_{name}__{ASOF_S}.csv")
    if not os.path.exists(p):
        return None
    h = pd.read_csv(p)
    h["time_utc"] = pd.to_datetime(h["time_utc"], utc=True)
    return h.set_index("time_utc").sort_index()


def btc_at_close(h, dates):
    """Close of the hourly bar ending at 16:00 ET (13:00 on early-close days); identical rule to script 20."""
    out = []
    starts, close = h.index, h["close"].values
    for d in dates:
        hh = 13 if d.strftime("%Y-%m-%d") in EARLY_CLOSE else 16
        t_end = pd.Timestamp(d.year, d.month, d.day, hh, tz="America/New_York").tz_convert("UTC")
        k = starts.searchsorted(t_end - pd.Timedelta(hours=1), side="right") - 1
        out.append(close[k] if k >= 0 and t_end - starts[k] <= pd.Timedelta(hours=4) else np.nan)
    return pd.Series(out, index=dates)


def build_panel(raw):
    spy = load_px(raw, "SPY", ASOF_S)
    cal = spy.loc[(spy.index >= START - pd.Timedelta(days=10)) & (spy.index <= END)].index
    px = pd.DataFrame(index=cal)
    for t in ["SPY", "IBIT", "GLD", "TLT", "TIP", "IEF"]:
        s = load_px(raw, t, ASOF_S)
        if s is not None:
            px[t] = s.reindex(cal)
    uup = load_px(raw, "UUP", ASOF_D)
    if uup is None:
        sys.exit(f"UUP__{ASOF_D}.csv missing: run 30a_fetch_macro.py first.")
    px["USD"] = uup.reindex(cal)
    h = load_hourly(raw, "coinbase")
    if h is None:
        h = load_hourly(raw, "bitstamp")
    if h is not None:
        px["BTC16"] = btc_at_close(h, cal).values
    R = px.pct_change()
    # FRED yields: levels forward-filled over bond-market holidays, so the change on such a day is 0
    # and the next day's change covers one day of news. Changes in basis points.
    for sid, col in [("DFII10", "dRY"), ("T10YIE", "dBE"), ("DGS10", "dNOM")]:
        s = load_fred(raw, sid)
        if s is None:
            sys.exit(f"{sid}__{ASOF_D}.csv missing: run 30a_fetch_macro.py first.")
        R[col] = s.reindex(s.index.union(cal)).ffill().reindex(cal).diff() * 100.0
    dx = load_fred(raw, "DTWEXBGS")
    if dx is not None:
        R["USDbroad"] = dx.reindex(dx.index.union(cal)).ffill().reindex(cal).pct_change()
    if "TIP" in R and "IEF" in R:
        R["TIPmIEF"] = R["TIP"] - R["IEF"]
    R = R.loc[(R.index >= START) & (R.index <= END)]
    return R, px


def aggregate(R, how):
    """Non-overlapping multi-day returns/changes: '2d' pairs of days, 'W' Wednesday-to-Wednesday."""
    ret_cols = [c for c in R.columns if not c.startswith("d")]
    chg_cols = [c for c in R.columns if c.startswith("d")]
    if how == "2d":
        g = np.arange(len(R)) // 2
    else:
        g = R.index.to_period("W-WED").astype(str)   # Thursday..Wednesday = Wednesday-close to Wednesday-close
    a = pd.DataFrame(index=pd.Index(pd.unique(g)))
    grp = R.groupby(g)
    for c in ret_cols:
        a[c] = grp[c].apply(lambda x: np.prod(1 + x.values) - 1 if x.notna().all() else np.nan)
    for c in chg_cols:
        a[c] = grp[c].sum(min_count=1)
    return a.dropna(subset=["SPY", "GLD"])


# ============================================================ analyses ====
def gold_residual(D, fac):
    m = ols_hac(D["GLD"], D[fac])
    return m.resid.reindex(D.index)


def section_A(D, assets, fac, label, rng, B, boot=True, out_csv=None):
    rows, recs = [], []
    X = D[fac].values
    for a in assets:
        y = D[a]
        m = ols_hac(y, D[fac])
        sl = std_load(m.params[fac].values, D[fac].loc[y.notna()].values, y.dropna().values)
        cells = [a]
        for i, f in enumerate(fac):
            cells.append(f"{rep(m.params[f], f):+.3f}{stars(m.pvalues[f])} ({m.tvalues[f]:+.2f})")
            recs.append({"spec": label, "asset": a, "factor": f, "coef_pct_per_unit": rep(m.params[f], f),
                         "t_hac": m.tvalues[f], "p_hac": m.pvalues[f], "std_loading": sl[i]})
        cells.append(f"{m.rsquared:.3f}")
        cells.append(str(int(m.nobs)))
        rows.append(cells)
    w(md(rows, ["Asset"] + [FLABEL.get(f, f) for f in fac] + ["R²", "N"]))
    w("Coefficients are % return per unit of the factor shown; HAC t-statistics in parentheses; "
      "*, **, *** = 10%, 5%, 1%.")
    w()
    # standardized loadings, IBIT vs GLD, with bootstrap difference
    if boot and "IBIT" in assets and "GLD" in assets:
        sub = D[["IBIT", "GLD"] + fac].dropna()
        Xs, yi, yg = sub[fac].values, sub["IBIT"].values, sub["GLD"].values
        si = std_load(ols_beta(yi, Xs), Xs, yi)
        sg = std_load(ols_beta(yg, Xs), Xs, yg)
        idx = stationary_boot(len(sub), B, L_BOOT, rng)
        bi = np.array([std_load(ols_beta(yi[idx[:, r]], Xs[idx[:, r]]), Xs[idx[:, r]], yi[idx[:, r]]) for r in range(B)])
        bg = np.array([std_load(ols_beta(yg[idx[:, r]], Xs[idx[:, r]]), Xs[idx[:, r]], yg[idx[:, r]]) for r in range(B)])
        rows2 = []
        for i, f in enumerate(fac):
            lo_i, hi_i = np.percentile(bi[:, i], [2.5, 97.5])
            lo_g, hi_g = np.percentile(bg[:, i], [2.5, 97.5])
            dd = bi[:, i] - bg[:, i]
            lo_d, hi_d = np.percentile(dd, [2.5, 97.5])
            rows2.append([FLABEL.get(f, f), f"{sg[i]:+.3f} [{lo_g:+.3f}, {hi_g:+.3f}]",
                          f"{si[i]:+.3f} [{lo_i:+.3f}, {hi_i:+.3f}]",
                          f"{si[i]-sg[i]:+.3f} [{lo_d:+.3f}, {hi_d:+.3f}]", f"{pvalue(dd):.3f}",
                          "yes" if np.sign(si[i]) == np.sign(sg[i]) and np.sign(lo_i) == np.sign(hi_i) else "no"])
            for rec in recs:
                if rec["factor"] == f and rec["asset"] in ("IBIT", "GLD"):
                    rec["std_ci_lo"], rec["std_ci_hi"] = (lo_i, hi_i) if rec["asset"] == "IBIT" else (lo_g, hi_g)
            recs.append({"spec": label, "asset": "IBIT-GLD", "factor": f, "std_loading": si[i] - sg[i],
                         "std_ci_lo": lo_d, "std_ci_hi": hi_d, "p_boot": pvalue(dd)})
        w(f"Standardized loadings (beta x sd(factor) / sd(asset)), 95% stationary-bootstrap intervals "
          f"(B = {B}, mean block {L_BOOT} days):")
        w()
        w(md(rows2, ["Factor", "GLD", "IBIT", "IBIT − GLD", "p (diff)", "IBIT same sign as GLD, CI excludes 0"]))
    if out_csv:
        pd.DataFrame(recs).to_csv(out_csv, index=False)
    return recs


def benchmark_test(D):
    """Is the H4 null informative? A 'digital gold' that carried gold-specific shocks as gold does would
    have the same standardized loading on them as GLD has on its own shock, i.e. an unstandardized
    loading beta* = sd(IBIT) / sd(GLD). Test beta = beta*, beta = beta*/2, and report the minimum
    detectable effect (80% power, 5% two-sided: 2.80 x SE)."""
    from scipy import stats as st
    rows = []
    for a in [x for x in ["IBIT", "BTC16"] if x in D]:
        sub = D[[a, "GLD"] + FACTORS + ["Gres"]].dropna()
        m = ols_hac(sub[a], sub[FACTORS + ["Gres"]])
        b, se = m.params["Gres"], m.bse["Gres"]
        bstar = sub[a].std() / sub["GLD"].std()
        p_full = 2 * st.norm.sf(abs((b - bstar) / se))
        p_half = 2 * st.norm.sf(abs((b - bstar / 2) / se))
        rows.append([a, f"{b:+.3f}", f"[{b - 1.96 * se:+.3f}, {b + 1.96 * se:+.3f}]", f"{bstar:.2f}",
                     f"{p_full:.2g}", f"{p_half:.2g}", f"{2.80 * se:.2f}"])
    w("Benchmark test for H4: loading on the gold-specific shock (per 1% shock = per 1% return) against a "
      "'digital gold' benchmark beta* = sd(asset)/sd(GLD), the loading that gives the asset the same "
      "standardized exposure to gold's own shock as GLD itself; HAC standard errors.")
    w()
    w(md(rows, ["Asset", "Loading", "95% CI", "Benchmark beta*", "p (beta = beta*)", "p (beta = beta*/2)",
                "Min. detectable effect"]))


def section_B(D, rng, B):
    sub = D[["IBIT", "GLD", "SPY", "Gres"]].dropna()
    i, g, s, gr = (sub[c].values for c in ["IBIT", "GLD", "SPY", "Gres"])
    n = len(sub)
    idx = stationary_boot(n, B, L_TAIL, rng)

    def corr(x, y):
        x = x - x.mean(0); y = y - y.mean(0)
        return (x * y).sum(0) / np.sqrt((x ** 2).sum(0) * (y ** 2).sum(0))

    def pcorr(x, y, z):
        rx = x - np.polyval(np.polyfit(z, x, 1), z)
        ry = y - np.polyval(np.polyfit(z, y, 1), z)
        return corr(rx, ry)

    def coex(x, y, q, upper):
        if upper:
            return float(((y >= np.quantile(y, 1 - q)) & (x >= np.quantile(x, 1 - q))).sum() / (y >= np.quantile(y, 1 - q)).sum())
        return float(((y <= np.quantile(y, q)) & (x <= np.quantile(x, q))).sum() / (y <= np.quantile(y, q)).sum())

    def res(x, z):
        return x - np.polyval(np.polyfit(z, x, 1), z)

    def deb_day(x, z):
        m = z >= np.quantile(z, 0.9)
        return float(x[m].mean() - x[~m].mean()) * 100

    stats = {
        "corr(IBIT, GLD)": (lambda a, b, c, d: corr(a, b), 0.0),
        "partial corr(IBIT, GLD | SPY)": (lambda a, b, c, d: pcorr(a, b, c), 0.0),
        "corr(IBIT, gold-specific shock)": (lambda a, b, c, d: corr(a, d), 0.0),
        "P(IBIT top 10% | GLD top 10%)": (lambda a, b, c, d: coex(a, b, 0.10, True), 0.10),
        "P(IBIT bottom 10% | GLD bottom 10%)": (lambda a, b, c, d: coex(a, b, 0.10, False), 0.10),
        "P(IBIT top 10% | GLD top 10%), SPY removed from both": (lambda a, b, c, d: coex(res(a, c), res(b, c), 0.10, True), 0.10),
        "P(IBIT bottom 10% | GLD bottom 10%), SPY removed from both": (lambda a, b, c, d: coex(res(a, c), res(b, c), 0.10, False), 0.10),
        "IBIT mean return on debasement days − other days (%)": (lambda a, b, c, d: deb_day(a, d), 0.0),
        "GLD mean return on debasement days − other days (%)": (lambda a, b, c, d: deb_day(b, d), 0.0),
    }
    rows = []
    for name, (fn, null) in stats.items():
        pt = fn(i, g, s, gr)
        bs = np.array([fn(i[idx[:, r]], g[idx[:, r]], s[idx[:, r]], gr[idx[:, r]]) for r in range(B)])
        lo, hi = np.percentile(bs, [2.5, 97.5])
        rows.append([name, f"{pt:.3f}", f"[{lo:.3f}, {hi:.3f}]", f"{null:.2f}", f"{pvalue(bs - null + 0.0, 0.0):.3f}"])
    w(md(rows, ["Statistic", "Estimate", "95% CI", "Null (independence)", "p"]))
    w(f"Bootstrap: stationary, mean block {L_TAIL} days, B = {B}. 'Debasement days' are the top decile of the "
      "gold-specific shock (GLD return orthogonal to SPY, real-yield, breakeven and dollar factors), "
      f"{int(round(0.1 * n))} of {n} days.")
    w()
    return rows


def sup_wald_pvalue(stat, lo=0.15, hi=0.85, n_grid=1000, n_sim=20000, seed=SEED):
    """Asymptotic p-value of the Andrews (1993) sup-Wald statistic for a break in ONE coefficient:
    sup over pi in [lo, hi] of B(pi)^2 / (pi (1 - pi)), B a Brownian bridge; simulated."""
    rng = np.random.default_rng(seed)
    grid = np.arange(1, n_grid + 1) / n_grid
    keep = (grid >= lo) & (grid <= hi)
    sup = np.empty(n_sim)
    for k in range(0, n_sim, 2000):
        m = min(2000, n_sim - k)
        W = np.cumsum(rng.normal(0, 1 / math.sqrt(n_grid), (m, n_grid)), axis=1)
        Bb = W - grid * W[:, -1:]
        sup[k:k + m] = (Bb[:, keep] ** 2 / (grid[keep] * (1 - grid[keep]))).max(axis=1)
    return float((sup >= stat).mean())


def end_of_sample_test(sub, fac, B_cal=199, seed=SEED):
    """End-of-sample instability (Andrews 2003): are the last m days -- the data added after the first-pass
    analysis (from HOLDOUT_START) -- unusual relative to every other m-day window of the earlier sample?
    Two statistics: S (sum of squared out-of-window residuals; all coefficients and the residual variance)
    and the loading on the gold-specific shock estimated inside the window. Because the comparison windows
    overlap, raw subsampling p-values over-reject in samples of this size (about 10% at a nominal 5% in
    simulations of this design), so they are calibrated by a residual block bootstrap under the null of no
    change: the calibrated p-value is the share of null replications whose raw p-value is at least as small."""
    n = len(sub)
    m_days = int((sub.index >= HOLDOUT_START).sum())
    if not (20 <= m_days < n // 3):
        w(f"(End-of-sample test skipped: {m_days} days after {HOLDOUT_START.date()}.)")
        w()
        return None, None
    y0 = sub["IBIT"].values
    Xf = np.column_stack([np.ones(n), sub[fac].values])
    npre = n - m_days
    jg = fac.index("Gres") + 1
    starts = np.arange(0, npre - m_days + 1)

    def raw_p(y):
        def fit(mask):
            b, *_ = np.linalg.lstsq(Xf[mask], y[mask], rcond=None)
            return b

        def gres_in(lo_, hi_, b_out):
            e = y[lo_:hi_] - Xf[lo_:hi_] @ b_out + Xf[lo_:hi_, jg] * b_out[jg]
            g = Xf[lo_:hi_, jg]
            return float((g * e).sum() / (g * g).sum())

        b_pre = fit(np.arange(n) < npre)
        S_last = float(((y[npre:] - Xf[npre:] @ b_pre) ** 2).sum())
        G_last = gres_in(npre, n, b_pre)
        S_j, G_j = np.empty(len(starts)), np.empty(len(starts))
        for k, j0 in enumerate(starts):
            mask = np.arange(n) < npre
            mask[j0:j0 + m_days] = False
            b_j = fit(mask)
            S_j[k] = float(((y[j0:j0 + m_days] - Xf[j0:j0 + m_days] @ b_j) ** 2).sum())
            G_j[k] = gres_in(j0, j0 + m_days, b_j)
        return S_last, G_last, S_j, G_j, (S_j >= S_last).mean(), (G_j >= G_last).mean(), b_pre

    S_last, G_last, S_j, G_j, pS, pG, b_pre = raw_p(y0)
    # Null calibration: y* = X b_pre + block-resampled pre-period residuals (whole sample, no change)
    rng = np.random.default_rng(seed)
    e_pre = (y0 - Xf @ b_pre)[:npre]
    idx = stationary_boot(npre, B_cal, L_BOOT, rng)
    pS_star, pG_star = np.empty(B_cal), np.empty(B_cal)
    for r in range(B_cal):
        e_star = e_pre[np.concatenate([idx[:, r], idx[:m_days, r]])][:n] if n > npre else e_pre[idx[:, r]]
        y_star = Xf @ b_pre + e_star
        *_, pS_star[r], pG_star[r], _ = raw_p(y_star)
    cS = (np.sum(pS_star <= pS) + 1) / (B_cal + 1)
    cG = (np.sum(pG_star <= pG) + 1) / (B_cal + 1)
    w(f"End-of-sample test (Andrews 2003): the last {m_days} days (from {HOLDOUT_START.date()}) "
      f"against all {len(starts)} other {m_days}-day windows of the earlier sample; "
      f"p-values calibrated by {B_cal} null bootstrap replications.")
    w()
    w(md([["S (all coefficients and residual variance)", f"{S_last * 1e4:.2f}", f"{np.median(S_j) * 1e4:.2f}",
           f"{pS:.3f}", f"{cS:.3f}"],
          ["Loading on the gold-specific shock (one-sided: higher)", f"{G_last:+.3f}", f"{np.median(G_j):+.3f}",
           f"{pG:.3f}", f"{cG:.3f}"]],
         ["Statistic", "Last window", "Median of earlier windows", "Raw p", "Calibrated p"]))
    w("S is scaled by 10⁴.")
    w()
    return cS, cG


def section_E(D, out_dir):
    """Is the loading on gold-specific shocks stable? Rolling estimate and a break test with unknown date."""
    fac = FACTORS + ["Gres"]
    sub = D[["IBIT"] + fac].dropna()
    n = len(sub)
    # 1. Andrews (1993) sup-Wald test for a break in the Gres loading only (other loadings held constant),
    #    HAC Wald statistic at every candidate date; standard 15% trimming and 10% trimming, which lets the
    #    break fall later in the sample.
    rows, results = [], {}
    for trim in (0.15, 0.10):
        lo, hi = int(trim * n), int((1 - trim) * n)
        waldv = []
        for k in range(lo, hi + 1):
            X = sub[fac].copy()
            X["Gres_post"] = X["Gres"] * (np.arange(n) >= k)
            m = ols_hac(sub["IBIT"], X)
            waldv.append((m.tvalues["Gres_post"] ** 2, sub.index[k], m.params["Gres"],
                          m.params["Gres"] + m.params["Gres_post"]))
        best = max(waldv, key=lambda t: t[0])
        pv = sup_wald_pvalue(best[0], lo=trim, hi=1 - trim)
        results[trim] = (best, pv)
        rows.append([f"{trim:.0%}", f"{sub.index[lo].date()} – {sub.index[hi].date()}", f"{best[0]:.2f}", f"{pv:.3f}",
                     str(best[1].date()), f"{best[2]:+.3f}", f"{best[3]:+.3f}", str(int((sub.index >= best[1]).sum()))])
    w("Andrews (1993) sup-Wald test for a single break in the IBIT loading on the gold-specific shock "
      "(HAC Wald statistics; asymptotic p-values simulated):")
    w()
    w(md(rows, ["Trimming", "Break dates searched", "sup-Wald", "p-value", "Most likely break", "Loading before",
                "Loading after", "Days after break"]))
    w("A break in the last part of the sample, beyond the searched range, cannot be located by this test; "
      "the rolling estimate below covers the end of the sample.")
    w()
    best, pv = results[0.15]
    end_of_sample_test(sub, fac)

    # 2. Rolling 120-day loading with +/- 1.96 HAC s.e.
    recs = []
    for k in range(ROLL, n + 1):
        win = sub.iloc[k - ROLL:k]
        m = ols_hac(win["IBIT"], win[fac])
        recs.append({"date": win.index[-1], "beta_Gres": m.params["Gres"], "se": m.bse["Gres"],
                     "benchmark": win["IBIT"].std() / D.loc[win.index, "GLD"].std()})
    roll = pd.DataFrame(recs).set_index("date")
    roll.to_csv(os.path.join(out_dir, "rolling_gres_loading.csv"))
    last = roll.iloc[-1]
    w(f"Rolling {ROLL}-day loading on the gold-specific shock: last window (to {roll.index[-1].date()}) "
      f"{last.beta_Gres:+.3f} (95% band {last.beta_Gres - 1.96 * last.se:+.3f} to {last.beta_Gres + 1.96 * last.se:+.3f}); "
      f"'digital gold' benchmark in that window {last.benchmark:.2f}. Share of windows whose band excludes 0: "
      f"{((roll.beta_Gres - 1.96 * roll.se) > 0).mean():.0%}.")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 3.2))
        ax.fill_between(roll.index, roll.beta_Gres - 1.96 * roll.se, roll.beta_Gres + 1.96 * roll.se,
                        color="#1f4e79", alpha=0.18, lw=0)
        ax.plot(roll.index, roll.beta_Gres, color="#1f4e79", lw=1.5, label="IBIT loading on gold-specific shock")
        ax.plot(roll.index, roll.benchmark, color="#B8860B", lw=1.2, ls="--", label="'Digital gold' benchmark")
        ax.axhline(0, color="grey", lw=0.6)
        ax.set_ylabel(f"{ROLL}-day rolling loading", fontsize=9)
        ax.tick_params(labelsize=8)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "fig_rolling_gres.png"), dpi=200)
        plt.close(fig)
        w(f"Figure: {os.path.join(out_dir, 'fig_rolling_gres.png')}")
    except Exception as e:  # noqa: BLE001
        w(f"(figure skipped: {e!r})")
    w()
    return best, pv, roll


def section_C(D, out_dir):
    rows = []
    periods = [("2024", "2024-01-01", "2024-12-31"), ("2025", "2025-01-01", "2025-12-31"),
               ("2026", "2026-01-01", "2026-12-31")]
    fac = FACTORS
    for lab, a, b in periods:
        sub = D.loc[a:b]
        if len(sub) < 60:
            continue
        for asset in ["GLD", "IBIT"]:
            m = ols_hac(sub[asset], sub[fac])
            rows.append([lab, asset] + [f"{rep(m.params[f], f):+.3f}{stars(m.pvalues[f])}" for f in fac]
                        + [f"{m.rsquared:.2f}", str(int(m.nobs))])
    w(md(rows, ["Period", "Asset"] + [FLABEL[f] for f in fac] + ["R²", "N"]))
    # rolling standardized loadings
    recs = []
    sub = D[["IBIT", "GLD"] + fac].dropna()
    for k in range(ROLL, len(sub) + 1):
        win = sub.iloc[k - ROLL:k]
        X = win[fac].values
        r = {"date": win.index[-1]}
        for asset in ["IBIT", "GLD"]:
            y = win[asset].values
            sl = std_load(ols_beta(y, X), X, y)
            for j, f in enumerate(fac):
                r[f"{asset}_{f}"] = sl[j]
        recs.append(r)
    roll = pd.DataFrame(recs).set_index("date")
    roll.to_csv(os.path.join(out_dir, "rolling_std_loadings.csv"))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 3, figsize=(12, 3.4), sharey=True)
        for ax, f in zip(axes, ["dRY", "dBE", "USD"]):
            ax.plot(roll.index, roll[f"GLD_{f}"], color="#B8860B", lw=1.4, label="GLD")
            ax.plot(roll.index, roll[f"IBIT_{f}"], color="#1f4e79", lw=1.4, label="IBIT")
            ax.axhline(0, color="grey", lw=0.6)
            ax.set_title(FLABEL[f].split(" (")[0], fontsize=10)
            ax.tick_params(labelsize=8)
            for lab_ in ax.get_xticklabels():
                lab_.set_rotation(30)
        axes[0].set_ylabel(f"Standardized loading ({ROLL}-day rolling)", fontsize=9)
        axes[0].legend(frameon=False, fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "fig_rolling_loadings.png"), dpi=200)
        plt.close(fig)
        w(f"Figure: {os.path.join(out_dir, 'fig_rolling_loadings.png')} ({ROLL}-day rolling standardized loadings).")
    except Exception as e:  # matplotlib optional
        w(f"(figure skipped: {e!r})")
    w()
    return roll


# ============================================================ main ====
def run(raw, out_dir, B):
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(SEED)
    R, _ = build_panel(raw)
    D = R.copy()
    D["Gres"] = gold_residual(D, FACTORS)
    w("# Script 30 — Does Bitcoin respond to gold's drivers?")
    w()
    w(f"Sample: {D.index.min().date()} – {D.index.max().date()}, {len(D)} U.S. trading days. "
      f"Price snapshot __{ASOF_S}, macro snapshot __{ASOF_D}. Seed {SEED}.")
    w()
    w("## 0. Data checks")
    w()
    ok_cols = [c for c in ["IBIT", "GLD", "SPY", "TLT", "BTC16", "USD", "dRY", "dBE"] if c in D]
    w(md([[c, int(D[c].notna().sum()), f"{D[c].std()* (100 if not c.startswith('d') else 1):.3f}"] for c in ok_cols],
         ["Series", "N", "s.d. (% or bp)"]))
    if {"dNOM", "dRY", "dBE"} <= set(D.columns):
        gap = (D["dNOM"] - D["dRY"] - D["dBE"]).abs()
        check("0a. Δnominal ≈ Δreal + Δbreakeven (max abs gap < 2 bp; trivially 0 when T10YIE is computed from the other two)", gap.max() < 2.0, f"max {gap.max():.2f} bp")
    mt = ols_hac(D["TLT"], D[FACTORS])
    check("0b. TLT loads negatively on real yields and breakevens (sanity)", mt.params["dRY"] < 0 and mt.params["dBE"] < 0,
          f"{rep(mt.params['dRY'], 'dRY'):+.2f}, {rep(mt.params['dBE'], 'dBE'):+.2f} % per 10 bp")
    if "BTC16" in D:
        c = D[["IBIT", "BTC16"]].dropna().corr().iloc[0, 1]
        check("0c. IBIT vs Bitcoin at 16:00 ET daily correlation > 0.98", c > 0.98, f"{c:.4f}")
    w()

    w("## A. Factor regressions (daily)")
    w()
    assets = [a for a in ["GLD", "IBIT", "BTC16", "TLT"] if a in D]
    section_A(D, assets, FACTORS, "daily", rng, B, out_csv=os.path.join(out_dir, "tables_A_daily.csv"))
    w()
    w("### A2. Adding the gold-specific shock (H4)")
    w()
    section_A(D, [a for a in ["IBIT", "BTC16"] if a in D], FACTORS + ["Gres"], "daily+Gres", rng, B, boot=False,
              out_csv=os.path.join(out_dir, "tables_A2_gres.csv"))
    w()
    benchmark_test(D)

    w("## B. Gold-conditioned co-movement")
    w()
    section_B(D, rng, B)

    w("## C. Stability over time")
    w()
    section_C(D, out_dir)

    w("## E. Is the gold-specific loading stable?")
    w()
    section_E(D, out_dir)

    w("## D. Robustness")
    w()
    for how, lab in [("2d", "Two-day non-overlapping returns"), ("W", "Weekly (Wednesday-to-Wednesday) returns")]:
        w(f"### D{1 if how == '2d' else 2}. {lab}")
        w()
        A = aggregate(R[[c for c in R.columns]], how)
        section_A(A, [a for a in ["GLD", "IBIT"] if a in A], FACTORS, lab, rng, B,
                  out_csv=os.path.join(out_dir, f"tables_D_{how}.csv"))
        w()
    if "USDbroad" in D:
        w("### D3. Broad dollar index (DTWEXBGS, noon) instead of UUP")
        w()
        D2 = D.rename(columns={"USD": "UUP_", "USDbroad": "USD"})
        section_A(D2, ["GLD", "IBIT"], FACTORS, "broad dollar", rng, B, boot=False)
        w()
    if "TIPmIEF" in D:
        w("### D4. Market-based inflation proxy: TIP − IEF return instead of Δbreakeven")
        w()
        D3 = D.rename(columns={"TIPmIEF": "INF"})
        section_A(D3, ["GLD", "IBIT"], ["SPY", "dRY", "INF", "USD"], "TIP-IEF", rng, B, boot=False)
        w()

    w("## Checks")
    w()
    for c in CHECKS:
        w(f"- {c}")
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"\nWrote {out_dir}/report.md")
    return D


# ============================================================ self-test ====
def selftest():
    """Synthetic data with known loadings: 'gold' has gold's signs, 'bitcoin' loads only on equities and
    on gold-specific shocks with a known coefficient. Checks that the script recovers them."""
    rng = np.random.default_rng(1)
    tmp = tempfile.mkdtemp()
    raw = os.path.join(tmp, "data", "raw")
    os.makedirs(raw)
    dates = pd.bdate_range("2023-12-20", "2026-06-16")
    n = len(dates)
    spy = rng.normal(0.0004, 0.010, n)
    dry = rng.normal(0, 5.0, n)        # bp
    dbe = rng.normal(0, 3.0, n)
    usd = rng.normal(0, 0.004, n)
    g_spec = rng.normal(0, 0.007, n)
    gld = 0.05 * spy - 0.0010 * dry + 0.0008 * dbe - 0.60 * usd + g_spec
    ibit = 1.2 * spy + 0.0 * dry + 0.0 * dbe + 0.0 * usd + 0.5 * g_spec + rng.normal(0, 0.025, n)
    tlt = -0.0016 * dry - 0.0016 * dbe + rng.normal(0, 0.003, n)

    def px(r):
        return 100 * np.cumprod(1 + r)
    for t, r in [("SPY", spy), ("GLD", gld), ("IBIT", ibit), ("TLT", tlt),
                 ("TIP", -0.0007 * dry + rng.normal(0, 0.002, n)), ("IEF", -0.0007 * (dry + dbe) + rng.normal(0, 0.002, n))]:
        p = px(r)
        pd.DataFrame({"Date": dates, "Open": p, "High": p, "Low": p, "Close": p, "AdjClose": p, "Volume": 1}).to_csv(
            os.path.join(raw, f"{t}__{ASOF_S}.csv"), index=False)
    p = px(usd)
    pd.DataFrame({"Date": dates, "Open": p, "High": p, "Low": p, "Close": p, "AdjClose": p, "Volume": 1}).to_csv(
        os.path.join(raw, f"UUP__{ASOF_D}.csv"), index=False)
    ry = 2.0 + np.cumsum(dry) / 100
    be = 2.3 + np.cumsum(dbe) / 100
    for sid, v in [("DFII10", ry), ("T10YIE", be), ("DGS10", ry + be), ("DTWEXBGS", 120 * np.cumprod(1 + usd))]:
        pd.DataFrame({"Date": dates, "Value": np.round(v, 4)}).to_csv(os.path.join(raw, f"{sid}__{ASOF_D}.csv"), index=False)
    out = os.path.join(tmp, "out")
    D = run(raw, out, 200)
    m = ols_hac(D["IBIT"], D[FACTORS + ["Gres"]])
    mg = ols_hac(D["GLD"], D[FACTORS])
    ok = True
    ok &= check("S1. GLD real-yield coef ≈ −1.0% per 10 bp", abs(rep(mg.params["dRY"], "dRY") - (-1.0)) < 0.15, f"{rep(mg.params['dRY'], 'dRY'):+.3f}")
    ok &= check("S2. GLD dollar coef ≈ −0.60", abs(mg.params["USD"] - (-0.60)) < 0.12, f"{mg.params['USD']:+.3f}")
    ok &= check("S3. IBIT real-yield coef insignificant", m.pvalues["dRY"] > 0.01, f"p={m.pvalues['dRY']:.3f}")
    ok &= check("S4. IBIT gold-specific loading ≈ 0.5", abs(m.params["Gres"] - 0.5) < 0.2, f"{m.params['Gres']:+.3f}")
    print("\nSELFTEST", "PASSED" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    # (module-level settings below are rebound from the command line; the functions read them at call time)
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=None)
    ap.add_argument("--boot", type=int, default=B_BOOT)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--asof-prices", default=ASOF_S,
                    help="suffix of the price snapshot (default 20260921S = JRFM; 20261001F = extended, from 30b)")
    ap.add_argument("--asof-macro", default=ASOF_D, help="suffix of the macro snapshot from 30a")
    ap.add_argument("--end", default=str(END.date()), help="last date of the sample (inclusive)")
    ap.add_argument("--holdout-start", default=str(HOLDOUT_START.date()),
                    help="first day of the end-of-sample window (default 2026-06-16)")
    a = ap.parse_args()
    ASOF_S, ASOF_D, END = a.asof_prices, a.asof_macro, pd.Timestamp(a.end)
    HOLDOUT_START = pd.Timestamp(a.holdout_start)
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    raw = find_raw_dir(a.raw)
    if raw is None:
        sys.exit(f"data/raw with the __{ASOF_S} snapshot not found; pass --raw.")
    tag = "" if ASOF_S == "20260921S" and END == pd.Timestamp("2026-06-15") else f"_{ASOF_S}_{END.date()}"
    run(raw, os.path.join(HERE, "out", "30_debasement" + tag), a.boot)
