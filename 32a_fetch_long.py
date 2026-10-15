"""
32a_fetch_long.py — Long-history snapshot (2014-2026) , written under a NEW suffix

Reuses the download code of 01d_fetch_scope.py and 30a_fetch_macro.py unchanged (both are imported and
their settings overridden in memory) and writes everything with the suffix __20261001H, so neither the
 snapshot (__20260921S) nor the snapshots (__20261001F, __20260921D) are touched:

  Yahoo daily:   SPY, GLD, TLT, TIP, IEF, QQQ, EFA, AGG   2014-09-01 -> end
  Hourly BTC:    Coinbase (primary), Bitstamp (backup)    2015-01-01 -> end
  Macro:         UUP (Yahoo); 10-year real and nominal yields (FRED or U.S. Treasury fallback);
                 breakeven = nominal - real; broad dollar index if FRED is reachable

The hourly download is long (about 11 years): expect 10-15 minutes.

Usage (from the folder with 01d_fetch_scope.py, 30a_fetch_macro.py and data/raw):
    python 32a_fetch_long.py                     # to 30 Sep 2026
    python 32a_fetch_long.py --end 2026-10-15    # exclusive end date
Then:
    python 32_long_sample.py
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AS_OF = "20261001H"
KEEP = ["SPY", "GLD", "TLT", "TIP", "IEF", "QQQ", "EFA", "AGG"]
PROTECTED = {"20260921S", "20260921", "20260921L", "20260921X", "20261001F", "20260921D"}


def load(name):
    p = HERE / name
    if not p.exists():
        sys.exit(f"{name} not found next to this script.")
    spec = importlib.util.spec_from_file_location(name.replace(".py", "").replace("-", "_"), p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    global AS_OF
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2014-09-01")
    ap.add_argument("--hourly-start", default="2015-01-01")
    ap.add_argument("--end", default="2026-10-01", help="exclusive end date")
    ap.add_argument("--skip-prices", action="store_true", help="only fetch the macro series")
    ap.add_argument("--skip-macro", action="store_true", help="only fetch prices and hourly Bitcoin")
    ap.add_argument("--asof", default=AS_OF, help="snapshot suffix (default 20261001H)")
    a = ap.parse_args()
    AS_OF = a.asof
    if AS_OF in PROTECTED:
        sys.exit("Refusing to write over an existing snapshot suffix.")

    if not a.skip_prices:
        d = load("01d_fetch_scope.py")
        missing = [t for t in KEEP if t not in d.YAHOO]
        if missing:
            sys.exit(f"Tickers not in 01d's list: {missing}")
        d.YAHOO = {t: d.YAHOO[t] for t in KEEP}
        d.START_DATE, d.END_DATE, d.AS_OF = a.start, a.end, AS_OF
        d.HOURLY_START = f"{a.hourly_start}T00:00:00Z"
        d.HOURLY_END = f"{a.end}T00:00:00Z"
        print(f"[prices] snapshot __{AS_OF}: {a.start} to {a.end}; hourly from {a.hourly_start}\n")
        d.main()
        # 30a writes manifest__<AS_OF>.json too: keep the price manifest under its own name
        man = d.RAW_DIR / f"manifest__{AS_OF}.json"
        if man.exists():
            man.replace(d.RAW_DIR / f"manifest__{AS_OF}_prices.json")
            print(f"price manifest: data/raw/manifest__{AS_OF}_prices.json")

    if not a.skip_macro:
        m = load("30a_fetch_macro.py")
        m.AS_OF = AS_OF
        print(f"\n[macro] snapshot __{AS_OF}: {a.start} to {a.end}\n")
        sys.argv = [sys.argv[0], "--start", a.start, "--end", a.end]
        m.main()


if __name__ == "__main__":
    main()
