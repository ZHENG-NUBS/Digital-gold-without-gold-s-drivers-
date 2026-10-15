"""
30a_fetch_macro.py —  ("Is Bitcoin in the debasement trade?")

Fetches the series and writes them to data/raw/ with the
suffix __20260921D, next to the existing snapshots (which are read, not modified):

  FRED  DFII10    10-year TIPS yield (real yield, % p.a.)            -> DFII10__20260921D.csv
  FRED  DGS10     10-year nominal Treasury yield (% p.a.)            -> DGS10__20260921D.csv
  FRED  T10YIE    10-year breakeven inflation (% p.a.)               -> T10YIE__20260921D.csv
  FRED  DTWEXBGS  Nominal broad U.S. dollar index (Fed H.10, noon)   -> DTWEXBGS__20260921D.csv
  Yahoo UUP       Invesco DB US Dollar Index Bullish ETF (16:00 ET)  -> UUP__20260921D.csv

UUP is the main dollar factor because it closes at 16:00 ET with the ETFs; DTWEXBGS (noon
rates) is a robustness check. FRED Treasury yields are end-of-day H.15 values.

Fallbacks (FRED is often slow or unreachable from mainland China):
  DFII10 -> U.S. Treasury "Daily Treasury Par Real Yield Curve Rates", 10 YR (the source of DFII10)
  DGS10  -> U.S. Treasury "Daily Treasury Par Yield Curve Rates", 10 Yr (the source of DGS10),
            then Yahoo ^TNX
  T10YIE -> computed as DGS10 - DFII10 (FRED defines T10YIE exactly this way)
  DTWEXBGS is optional (robustness only): skipped with a warning if FRED cannot be reached.
The source actually used for each series is recorded in the manifest.

Usage (from the repository root):
    python 30a_fetch_macro.py                 # same window as the main sample
    python 30a_fetch_macro.py --end 2026-10-01  # extend (then re-run 01d for the ETFs too)

Writes a manifest with SHA-256 checksums, as 01a-01e do.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import random
import time
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
RAW_DIR = HERE / "data" / "raw"
AS_OF = "20260921D"
START_DATE = "2023-12-01"
END_DATE = "2026-10-01"            # exclusive, as in 01a-01e
TIMEOUT, RETRIES = 60, 4
FRED_TIMEOUT, FRED_RETRIES = 20, 2   # fail fast, then use the Treasury fallback

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
TREASURY_URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                "daily-treasury-rates.csv/{year}/all")
YAHOO_TICKERS = ["UUP"]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    for k in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        if os.environ.get(k):
            s.proxies.update({"http": os.environ[k], "https": os.environ[k]})
            break
    return s


def _get(s, url, params, label, timeout=TIMEOUT, retries=RETRIES):
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = s.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
            if r.status_code == 429 and attempt < retries:
                time.sleep(20 * attempt + random.uniform(0, 5))
                continue
        except requests.RequestException as e:
            last = repr(e)
        if attempt < retries:
            time.sleep(2 ** attempt + random.uniform(0, 1))
    raise RuntimeError(f"{label}: failed after {retries} attempts: {last}")


def _epoch(d: str) -> int:
    return int(pd.Timestamp(d, tz="Etc/GMT-8").timestamp())   # same convention as 01e


def fetch_fred(s, sid, start, end) -> pd.DataFrame:
    r = _get(s, FRED_URL, {"id": sid, "cosd": start, "coed": end}, f"FRED {sid}",
             timeout=FRED_TIMEOUT, retries=FRED_RETRIES)
    if sid not in r.text[:200]:
        raise RuntimeError(f"FRED {sid} did not return CSV: {r.text[:200]!r}")
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["Date", "Value"]
    df["Date"] = pd.to_datetime(df["Date"])
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")   # FRED marks holidays with "."
    return df.dropna()


def fetch_yahoo(s, ticker, start, end) -> pd.DataFrame:
    params = {"period1": _epoch(start), "period2": _epoch(end), "interval": "1d",
              "events": "div,split", "includeAdjustedClose": "true"}
    js = _get(s, YAHOO_URL.format(ticker=ticker), params, f"Yahoo {ticker}").json()
    if js.get("chart", {}).get("error"):
        raise RuntimeError(f"Yahoo {ticker}: {js['chart']['error']}")
    res = js["chart"]["result"][0]
    tz = res["meta"]["exchangeTimezoneName"]
    dates = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz).normalize().tz_localize(None)
    q = res["indicators"]["quote"][0]
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose", q["close"])
    df = pd.DataFrame({"Date": dates, "Open": q["open"], "High": q["high"], "Low": q["low"],
                       "Close": q["close"], "AdjClose": adj, "Volume": q["volume"]})
    return df.dropna(subset=["AdjClose"]).drop_duplicates("Date").sort_values("Date")


def fetch_treasury(s, kind, start, end) -> pd.DataFrame:
    """10-year par yield from the U.S. Treasury's yearly CSV files. kind: 'real' or 'nominal'."""
    typ = "daily_treasury_real_yield_curve" if kind == "real" else "daily_treasury_yield_curve"
    frames = []
    for year in range(pd.Timestamp(start).year, pd.Timestamp(end).year + 1):
        params = {"type": typ, "field_tdr_date_value": str(year), "page": "", "_format": "csv"}
        r = _get(s, TREASURY_URL.format(year=year), params, f"Treasury {kind} {year}")
        df = pd.read_csv(io.StringIO(r.text))
        col = [c for c in df.columns if c.strip().lower().replace(" ", "") == "10yr"]
        if "Date" not in df.columns or not col:
            raise RuntimeError(f"Treasury {kind} {year}: unexpected columns {list(df.columns)[:8]}")
        frames.append(pd.DataFrame({"Date": pd.to_datetime(df["Date"], format="%m/%d/%Y"),
                                    "Value": pd.to_numeric(df[col[0]], errors="coerce")}))
        time.sleep(0.5)
    df = pd.concat(frames).dropna().drop_duplicates("Date").sort_values("Date")
    return df[(df["Date"] >= pd.Timestamp(start)) & (df["Date"] < pd.Timestamp(end))]


def fetch_tnx(s, start, end) -> pd.DataFrame:
    d = fetch_yahoo(s, "^TNX", start, end)
    return pd.DataFrame({"Date": d["Date"], "Value": d["Close"]})   # ^TNX quotes the yield in %


def first_ok(label, attempts):
    """Try (source_name, fn) in order; return (df, source_name)."""
    errs = []
    for src, fn in attempts:
        try:
            df = fn()
            if len(df) < 20:
                raise RuntimeError(f"only {len(df)} rows")
            return df, src
        except Exception as e:  # noqa: BLE001
            errs.append(f"{src}: {e}")
            print(f"  {label}: {src} failed ({str(e)[:120]}); trying next source")
    raise RuntimeError(f"{label}: all sources failed:\n  " + "\n  ".join(errs))


def main():
    global AS_OF
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=START_DATE)
    ap.add_argument("--end", default=END_DATE)
    ap.add_argument("--asof", default=None, help="snapshot suffix (default %s)" % AS_OF)
    a = ap.parse_args()
    if a.asof:
        AS_OF = a.asof
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    s = _session()
    manifest = {"as_of": AS_OF, "start": a.start, "end": a.end,
                "downloaded_utc": pd.Timestamp.now("UTC").isoformat(), "files": {}}

    def save(name, df, src):
        p = RAW_DIR / f"{name}__{AS_OF}.csv"
        df.to_csv(p, index=False, date_format="%Y-%m-%d")
        manifest["files"][p.name] = {"source": src, "rows": len(df), "first": str(df["Date"].min().date()),
                                     "last": str(df["Date"].max().date()),
                                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        print(f"  {p.name}: {len(df)} rows, {df['Date'].min().date()} - {df['Date'].max().date()}  [{src}]")

    # 1. Dollar ETF (Yahoo, which already works for the main snapshot)
    for t in YAHOO_TICKERS:
        save(t, fetch_yahoo(s, t, a.start, a.end), f"Yahoo {t}")

    # 2. Real and nominal 10-year yields: FRED, else the U.S. Treasury (the same underlying data)
    real, src_r = first_ok("DFII10", [("FRED DFII10", lambda: fetch_fred(s, "DFII10", a.start, a.end)),
                                      ("U.S. Treasury real 10 YR", lambda: fetch_treasury(s, "real", a.start, a.end))])
    save("DFII10", real, src_r)
    nom, src_n = first_ok("DGS10", [("FRED DGS10", lambda: fetch_fred(s, "DGS10", a.start, a.end)),
                                    ("U.S. Treasury nominal 10 Yr", lambda: fetch_treasury(s, "nominal", a.start, a.end)),
                                    ("Yahoo ^TNX", lambda: fetch_tnx(s, a.start, a.end))])
    save("DGS10", nom, src_n)

    # 3. Breakeven: FRED if reachable, else DGS10 - DFII10 (FRED's own definition)
    try:
        be, src_b = first_ok("T10YIE", [("FRED T10YIE", lambda: fetch_fred(s, "T10YIE", a.start, a.end))])
    except RuntimeError:
        m = nom.merge(real, on="Date", suffixes=("_n", "_r"))
        be = pd.DataFrame({"Date": m["Date"], "Value": (m["Value_n"] - m["Value_r"]).round(4)})
        src_b = f"computed: DGS10 ({src_n}) - DFII10 ({src_r})"
    save("T10YIE", be, src_b)

    # 4. Broad dollar index: optional robustness series
    try:
        dx, src_d = first_ok("DTWEXBGS", [("FRED DTWEXBGS", lambda: fetch_fred(s, "DTWEXBGS", a.start, a.end))])
        save("DTWEXBGS", dx, src_d)
    except RuntimeError:
        print("  DTWEXBGS skipped (FRED unreachable); script 30 then omits robustness check D3.")

    (RAW_DIR / f"manifest__{AS_OF}.json").write_text(json.dumps(manifest, indent=2))
    print(f"Manifest: data/raw/manifest__{AS_OF}.json")


if __name__ == "__main__":
    main()