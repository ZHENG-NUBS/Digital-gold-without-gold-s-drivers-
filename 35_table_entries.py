# -*- coding: utf-8 -*-
"""
35_table_entries.py - The entries of Tables 2 and 3 that script 30 does not print itself.

Script 30 reports the full-sample loading on the gold-specific shock, the end-of-sample test and the
rolling estimates. Five entries of the letter come from the same model but on subsamples, and are
produced here, with script 30's own functions (imported unchanged, so the pre-registered checksums are
unaffected):

  Table 2  gamma through 15 Jun 2026 (607 days)           -> 0.111, t = 1.29
  Table 2  gamma 16 Jun - 30 Sep 2026 (74 days)           -> 0.729, s.e. 0.225
  Table 3  summer gamma excluding 19-21 Aug 2026          -> 0.56 (s.e. 0.15)
  Table 3  summer gamma excluding the 3 / 5 / 10 days
           with the largest |gold-specific shock|         -> 0.86 / 0.85 / 0.79
  Table 3  end-of-sample test excluding 19-21 Aug 2026    -> calibrated p = 0.06

Model: IBIT daily return on SPY, real-yield change, breakeven change, UUP return and the gold-specific
shock g_t (residual of the GLD regression on the four factors over the full sample); Newey-West s.e.
with 5 lags. The full-sample end-of-sample test (p = 0.025) is printed as a check against script 30.

Inputs  data/raw/*__20261001F.* (from 30b) and *__20260921D.* (from 30a)
Output  out/35_table_entries/report.md and table_entries.csv
Usage   python 35_table_entries.py [--asof-prices 20261001F] [--asof-macro 20260921D]
                                   [--end 2026-09-30] [--holdout-start 2026-06-16]
Runtime under a minute (the two end-of-sample tests use 199 null replications each).
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import os
import warnings

import pandas as pd

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s30", os.path.join(HERE, "30_debasement_drivers.py"))
s30 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s30)

EPISODE = ["2026-08-19", "2026-08-20", "2026-08-21"]   # IBIT rose about 6% on days of large gold gains


def gamma(sub, fac):
    m = s30.ols_hac(sub["IBIT"], sub[fac])
    return m.params["Gres"], m.bse["Gres"], m.tvalues["Gres"]


def eos_p(sub, fac):
    """Calibrated end-of-sample p-value for gamma from script 30 (its own printout suppressed)."""
    with contextlib.redirect_stdout(io.StringIO()):
        _, cG = s30.end_of_sample_test(sub, fac)
    return cG


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof-prices", default="20261001F")
    ap.add_argument("--asof-macro", default="20260921D")
    ap.add_argument("--end", default="2026-09-30")
    ap.add_argument("--holdout-start", default="2026-06-16")
    a = ap.parse_args()
    s30.ASOF_S, s30.ASOF_D, s30.END = a.asof_prices, a.asof_macro, pd.Timestamp(a.end)
    s30.HOLDOUT_START = pd.Timestamp(a.holdout_start)

    R, _ = s30.build_panel(os.path.join(HERE, "data", "raw"))
    D = R.copy()
    D["Gres"] = s30.gold_residual(D, s30.FACTORS)
    fac = s30.FACTORS + ["Gres"]
    sub = D[["IBIT"] + fac].dropna()
    pre = sub[sub.index < s30.HOLDOUT_START]
    post = sub[sub.index >= s30.HOLDOUT_START]
    episode = pd.to_datetime(EPISODE)

    rows = []

    def add(table, label, s):
        g, se, t = gamma(s, fac)
        rows.append({"table": table, "entry": label, "days": len(s), "gamma": g, "se": se, "t": t, "p": None})

    add("Table 2", f"gamma through {pre.index.max().date()}", pre)
    add("Table 2", f"gamma {post.index.min().date()} to {post.index.max().date()}", post)
    add("Table 3", "summer gamma excluding 19-21 Aug 2026", post.drop(episode, errors="ignore"))
    for k in (3, 5, 10):
        add("Table 3", f"summer gamma excluding the {k} days with the largest absolute gold-specific shock",
            post.drop(post["Gres"].abs().nlargest(k).index))
    for label, s in [("end-of-sample test, full sample (check: script 30 gives 0.025)", sub),
                     ("end-of-sample test excluding 19-21 Aug 2026", sub.drop(episode, errors="ignore"))]:
        rows.append({"table": "Table 3" if "excluding" in label else "check", "entry": label, "days": len(s),
                     "gamma": None, "se": None, "t": None, "p": eos_p(s, fac)})

    T = pd.DataFrame(rows)
    out = os.path.join(HERE, "out", "35_table_entries")
    os.makedirs(out, exist_ok=True)
    T.to_csv(os.path.join(out, "table_entries.csv"), index=False)

    def f(x, fmt):
        return "" if x is None or pd.isna(x) else format(x, fmt)

    L = ["# Script 35 - Table entries estimated on subsamples", "",
         f"Price snapshot __{s30.ASOF_S}, macro snapshot __{s30.ASOF_D}; sample {sub.index.min().date()} - "
         f"{sub.index.max().date()} ({len(sub)} days); summer window from {s30.HOLDOUT_START.date()}. "
         "Gold-specific shock estimated over the full sample; Newey-West s.e. (5 lags).", "",
         "| Table | Entry | Days | gamma | s.e. | t | Calibrated p |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['table']} | {r['entry']} | {r['days']} | {f(r['gamma'], '+.3f')} | {f(r['se'], '.3f')} | "
                 f"{f(r['t'], '.2f')} | {f(r['p'], '.3f')} |")
    txt = "\n".join(L) + "\n"
    open(os.path.join(out, "report.md"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
