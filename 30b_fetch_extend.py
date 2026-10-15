"""
30b_fetch_extend.py — Extended price snapshot for the FRL letter, WITHOUT touching the JRFM snapshot

01d_fetch_scope.py hard-codes END_DATE = 2026-06-16 and the suffix __20260921S. Editing and re-running
it would overwrite the archived JRFM snapshot, whose SHA-256 checksums are published in the
replication repository. This wrapper imports 01d unchanged, overrides its settings in memory and
writes a NEW snapshot with the suffix __20261001F:

  daily (Yahoo):   SPY, IBIT, GLD, TLT, TIP, IEF        -> <TICKER>__20261001F.csv / .json
  hourly BTC-USD:  Coinbase (primary), Bitstamp (backup) -> BTCUSD_1h_<src>__20261001F.csv
  manifest:        manifest__20261001F.json

01d's download code, retry logic and file formats are reused as they are, so the new files have the
same layout as the old ones. (01d also re-downloads the GLD archive and the IBIT NAV file at the end;
those are saved under the new suffix and not used.)

Usage (from the folder that contains 01d_fetch_scope.py and data/raw):
    python 30b_fetch_extend.py                      # 1 Jan 2024 - 30 Sep 2026
    python 30b_fetch_extend.py --end 2026-10-15     # exclusive end date
Then:
    python 30_debasement_drivers.py --asof-prices 20261001F --end 2026-09-30
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEW_AS_OF = "20261001F"
KEEP = ["SPY", "IBIT", "GLD", "TLT", "TIP", "IEF"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", default="2026-10-01", help="exclusive end date (default 2026-10-01)")
    ap.add_argument("--asof", default=NEW_AS_OF)
    a = ap.parse_args()

    src = HERE / "01d_fetch_scope.py"
    if not src.exists():
        sys.exit(f"{src.name} not found next to this script.")
    if a.asof == "20260921S":
        sys.exit("Refusing to write with suffix 20260921S: that is the archived JRFM snapshot.")

    spec = importlib.util.spec_from_file_location("fetch_scope_01d", src)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)          # defines functions only; main() is not run on import

    missing = [t for t in KEEP if t not in m.YAHOO]
    if missing:
        sys.exit(f"Tickers not in 01d's list: {missing}")
    m.YAHOO = {t: m.YAHOO[t] for t in KEEP}
    m.END_DATE = a.end
    m.AS_OF = a.asof
    m.HOURLY_END = f"{a.end}T00:00:00Z"
    print(f"Writing snapshot __{m.AS_OF}: {m.START_DATE} to {m.END_DATE} (exclusive), "
          f"tickers {', '.join(KEEP)}, hourly BTC to {m.HOURLY_END}\n")
    return m.main()


if __name__ == "__main__":
    sys.exit(main())
