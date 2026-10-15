#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01d_fetch_scope.py — 实证范围扩展所需的全部原始数据（审稿意见：扩展比较对象）

审稿人要求 IBIT 不只和 GLD 比，还要和比特币现货、其他现货比特币 ETF、
其他黄金工具、更广的股票与债券基准比；并把比特币本身的属性与
ETF 特有因素（费率、跟踪误差、流动性、交易时间）分开。

本脚本抓取四类数据，写入 data/raw/，文件名带 __20260921S 后缀
（S = scope），与主快照 __20260921、长样本 __20260921L、ETF 附录 __20260921X 并存。

  1. Yahoo 日线（OHLCV + AdjClose + 分红拆股）
  2. 比特币【小时】K 线（Coinbase 主、Bitstamp 备）
  3. SPDR 官网 GLD 历史档案
  4. iShares 官网 IBIT 历史净值

联网方式（沿用主快照已验证可用的方案）
    - Yahoo：query1 + 无 crumb + 代理；价格与事件拆两次请求，避免 events=div,split 触发 429
    - 其它接口：429 单独走长退避（20/40/60s + 抖动）
    - 个别标的失败不中断整轮

注意
    DEFI（Hashdex Bitcoin ETF）已于 2026-08-17 退市清算，Yahoo chart API
    对其返回 HTTP 400，故本脚本不抓 DEFI。

用法：
    python 01d_fetch_scope.py
运行约 8–15 分钟。
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

# ----------------------------------------------------------------------------
# 配置
# ----------------------------------------------------------------------------

YAHOO = {
    # —— 比特币现货与现货 ETF ——
    "BTC-USD": ("bitcoin", "Bitcoin spot, Yahoo composite (daily bar closes 00:00 UTC)"),
    "IBIT": ("bitcoin", "iShares Bitcoin Trust ETF"),
    "FBTC": ("bitcoin", "Fidelity Wise Origin Bitcoin Fund"),
    "ARKB": ("bitcoin", "ARK 21Shares Bitcoin ETF"),
    "BITB": ("bitcoin", "Bitwise Bitcoin ETF"),
    "GBTC": ("bitcoin", "Grayscale Bitcoin Trust ETF"),
    "BTC":  ("bitcoin", "Grayscale Bitcoin Mini Trust (listed 2024-07-31)"),
    "HODL": ("bitcoin", "VanEck Bitcoin ETF"),
    "BTCO": ("bitcoin", "Invesco Galaxy Bitcoin ETF"),
    "BRRR": ("bitcoin", "CoinShares Bitcoin ETF (formerly Valkyrie)"),
    "EZBC": ("bitcoin", "Franklin Bitcoin ETF"),
    "BTCW": ("bitcoin", "WisdomTree Bitcoin Fund"),
    "BITO": ("bitcoin", "ProShares Bitcoin Strategy ETF (futures-based)"),
    # —— 黄金 ——
    "GLD":  ("gold", "SPDR Gold Shares"),
    "IAU":  ("gold", "iShares Gold Trust"),
    "GLDM": ("gold", "SPDR Gold MiniShares Trust"),
    "SGOL": ("gold", "abrdn Physical Gold Shares ETF"),
    "BAR":  ("gold", "GraniteShares Gold Trust"),
    "AAAU": ("gold", "Goldman Sachs Physical Gold ETF"),
    "IAUM": ("gold", "iShares Gold Trust Micro"),
    "GC=F": ("gold", "COMEX gold futures, continuous front month"),
    # —— 股票基准 ——
    "SPY":  ("equity", "SPDR S&P 500 ETF Trust"),
    "VTI":  ("equity", "Vanguard Total Stock Market ETF"),
    "VT":   ("equity", "Vanguard Total World Stock ETF"),
    "QQQ":  ("equity", "Invesco QQQ Trust (Nasdaq-100)"),
    "EFA":  ("equity", "iShares MSCI EAFE ETF"),
    # —— 债券基准 ——
    "TLT":  ("bond", "iShares 20+ Year Treasury Bond ETF"),
    "IEF":  ("bond", "iShares 7-10 Year Treasury Bond ETF"),
    "AGG":  ("bond", "iShares Core U.S. Aggregate Bond ETF"),
    "SHY":  ("bond", "iShares 1-3 Year Treasury Bond ETF"),
    "TIP":  ("bond", "iShares TIPS Bond ETF"),
    # —— 其他 ——
    "^VIX": ("other", "CBOE Volatility Index"),
    "^IRX": ("other", "13-week U.S. Treasury bill yield (annualized, %)"),
}

START_DATE = "2024-01-01"
END_DATE   = "2026-06-16"
AS_OF      = "20260921S"

HERE    = Path(__file__).resolve().parent
RAW_DIR = HERE / "data" / "raw"
PROXY   = "http://127.0.0.1:20171"   # 实测必须走代理
TIMEOUT = 30
RETRIES = 4

YAHOO_URL    = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
COINBASE_URL = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
BITSTAMP_URL = "https://www.bitstamp.net/api/v2/ohlc/btcusd/"
GLD_ARCHIVE  = "https://www.spdrgoldshares.com/assets/dynamic/GLD/GLD_US_archive_EN.csv"
IBIT_NAV     = ("https://www.ishares.com/us/products/333011/ishares-bitcoin-trust-etf/"
                "1467271812596.ajax?fileType=xls&fileName=iShares-Bitcoin-Trust-ETF_fund&dataType=fund")

HOURLY_START = "2023-12-29T00:00:00Z"
HOURLY_END   = "2026-06-16T00:00:00Z"

SLEEP_BETWEEN_CALLS = (5.0, 10.0)   # Yahoo 两请求之间

# ----------------------------------------------------------------------------


def _find_proxy() -> str | None:
    """PROXY 优先；否则环境变量；否则在常见位置的 01_fetch_raw.py 里找 PROXY = "..."。"""
    if PROXY:
        return PROXY
    for k in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        if os.environ.get(k):
            return os.environ[k]
    cands = [HERE / "01_fetch_raw.py", HERE.parent / "01_fetch_raw.py",
             Path.home() / "Desktop" / "PycharmProjects 16.06.44" / "PythonProject" / "01_fetch_raw.py"]
    for c in cands:
        try:
            m = re.search(r'^PROXY\s*=\s*["\']([^"\']+)["\']', c.read_text(encoding="utf-8"), re.M)
            if m:
                print(f"沿用 {c} 里的代理设置：{m.group(1)}")
                return m.group(1)
        except OSError:
            pass
    return None


def _session(proxy: str | None) -> requests.Session:
    s = requests.Session()
    if proxy:
        s.proxies.update({"http": proxy, "https": proxy})
    s.headers.update({
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36"),
    })
    return s


def _get(session, url, params=None, accept="application/json", label=""):
    """带重试的 GET。429 走长退避，其它错误走短退避。"""
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = session.get(url, params=params, timeout=TIMEOUT, headers={"Accept": accept})
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"

            if r.status_code == 429 and attempt < RETRIES:
                wait = 20 * attempt + random.uniform(0, 5)
                print(f"    {label} 429 限流，等 {wait:.0f}s 后重试（第 {attempt}/{RETRIES-1} 次）")
                time.sleep(wait)
                continue
        except requests.RequestException as e:
            last = repr(e)

        if attempt < RETRIES:
            wait = 2 ** attempt + random.uniform(0, 1)
            print(f"    {label} 第 {attempt} 次失败（{last}），{wait:.1f}s 后重试")
            time.sleep(wait)
    raise RuntimeError(f"{label}: {RETRIES} 次尝试后仍失败：{last}")


def _epoch(date_str: str) -> int:
    """本地时区 epoch —— 与实测可用的 7.py 一致。"""
    return int(pd.to_datetime(date_str).timestamp())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(ticker: str) -> str:
    return ticker.replace("^", "IDX_").replace("=", "_")


# ----------------------------------------------------------------------------
# 1. Yahoo 日线（价格与事件拆两次请求）
# ----------------------------------------------------------------------------

def fetch_yahoo_prices(session, ticker):
    """第一次请求：只要价格。events='history' 最轻。"""
    params = {
        "period1": _epoch(START_DATE),
        "period2": _epoch(END_DATE),
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    payload = _get(session, YAHOO_URL.format(ticker=ticker), params,
                   label=f"[{ticker}] 价格").json()
    err = payload.get("chart", {}).get("error")
    if err:
        raise RuntimeError(f"Yahoo 返回错误 {err}")
    res = payload["chart"]["result"][0]
    if not res.get("timestamp"):
        raise RuntimeError("Yahoo 返回空序列（可能已退市或代码有误）")

    meta = res["meta"]
    tz_name = meta["exchangeTimezoneName"]
    ts = pd.to_datetime(res["timestamp"], unit="s", utc=True)
    dates = ts.tz_convert(tz_name).normalize().tz_localize(None)
    q = res["indicators"]["quote"][0]
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose")
    if adj is None:
        adj = q["close"]
    px = pd.DataFrame({"Date": dates, "Open": q["open"], "High": q["high"], "Low": q["low"],
                       "Close": q["close"], "AdjClose": adj, "Volume": q["volume"]})
    px = px.dropna(subset=["Close", "AdjClose"]).drop_duplicates("Date").sort_values("Date")

    first_ts = pd.to_datetime(res["timestamp"][0], unit="s", utc=True)
    info = {"exchange_tz": tz_name, "currency": meta.get("currency"),
            "first_bar_utc": first_ts.isoformat(), "instrument_type": meta.get("instrumentType")}
    return px, payload, info


def fetch_yahoo_events(session, ticker):
    """第二次请求：只要事件。失败返回 (None, None)。"""
    params = {
        "period1": _epoch(START_DATE),
        "period2": _epoch(END_DATE),
        "interval": "1d",
        "events": "div,split",
        "includeAdjustedClose": "false",
    }
    try:
        payload = _get(session, YAHOO_URL.format(ticker=ticker), params,
                       label=f"[{ticker}] 事件").json()
    except RuntimeError as e:
        print(f"    [{ticker}] 事件请求失败：{e}")
        return None, None

    res = payload["chart"]["result"][0]
    tz_name = res["meta"]["exchangeTimezoneName"]
    ev_rows = []
    for kind in ("dividends", "splits"):
        for _, e in (res.get("events", {}).get(kind) or {}).items():
            d = (pd.to_datetime(e["date"], unit="s", utc=True)
                   .tz_convert(tz_name).normalize().tz_localize(None))
            ev_rows.append({"ticker": ticker, "date": d, "type": kind[:-1],
                            "amount": e.get("amount"),
                            "ratio": (e.get("numerator", 1) / e.get("denominator", 1)
                                      if kind == "splits" else None)})
    return pd.DataFrame(ev_rows), payload


# ----------------------------------------------------------------------------
# 2. 比特币小时 K 线
# ----------------------------------------------------------------------------

def fetch_coinbase_hourly(session):
    """Coinbase Exchange 公共接口：每次最多 300 根。"""
    start = pd.Timestamp(HOURLY_START)
    end = pd.Timestamp(HOURLY_END)
    step = pd.Timedelta(hours=300)
    rows, t, n_req = [], start, 0
    while t < end:
        t2 = min(t + step, end)
        params = {"granularity": 3600,
                  "start": t.isoformat().replace("+00:00", "Z"),
                  "end": t2.isoformat().replace("+00:00", "Z")}
        data = _get(session, COINBASE_URL, params, label="[Coinbase]").json()
        if isinstance(data, dict):
            raise RuntimeError(f"Coinbase 返回 {data}")
        rows.extend(data)
        n_req += 1
        if n_req % 10 == 0:
            print(f"    Coinbase 已取到 {t2.date()}（{len(rows)} 根）")
        t = t2
        time.sleep(0.35)
    df = pd.DataFrame(rows, columns=["time", "low", "high", "open", "close", "volume"])
    df["time_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = (df.drop_duplicates("time").sort_values("time")
            [["time_utc", "open", "high", "low", "close", "volume"]])
    return df


def fetch_bitstamp_hourly(session):
    """Bitstamp 公共接口：每次最多 1000 根。"""
    start = int(pd.Timestamp(HOURLY_START).timestamp())
    end = int(pd.Timestamp(HOURLY_END).timestamp())
    rows, t = [], start
    while t < end:
        data = _get(session, BITSTAMP_URL, {"step": 3600, "limit": 1000, "start": t},
                    label="[Bitstamp]").json()
        chunk = data.get("data", {}).get("ohlc", [])
        if not chunk:
            break
        rows.extend(chunk)
        last = int(chunk[-1]["timestamp"])
        if last <= t:
            break
        t = last + 3600
        time.sleep(0.5)
    df = pd.DataFrame(rows)
    for c in ("timestamp", "open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c])
    df["time_utc"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df = df[df.timestamp < end].drop_duplicates("timestamp").sort_values("timestamp")
    return df[["time_utc", "open", "high", "low", "close", "volume"]]


# ----------------------------------------------------------------------------
# 主程序
# ----------------------------------------------------------------------------

def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    proxy = _find_proxy()
    session = _session(proxy)
    print(f"输出目录：{RAW_DIR}\n代理：{proxy or '无'}\n")

    manifest = {
        "as_of": AS_OF,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "start_date": START_DATE, "end_date_exclusive": END_DATE,
        "proxy": proxy,
        "sources": {"daily": "Yahoo Finance chart API v8 (query1, no crumb, via proxy)",
                    "hourly_primary": "Coinbase Exchange public candles (granularity 3600)",
                    "hourly_backup": "Bitstamp public OHLC (step 3600)",
                    "gold_benchmark": GLD_ARCHIVE, "ibit_nav": IBIT_NAV},
        "note": ("DEFI 已于 2026-08-17 退市清算，Yahoo API 对其返回 400，故不纳入。"
                 "价格与事件分两次请求；Yahoo 的 AdjClose 会随新分红回溯重算，"
                 "本目录为某一时点快照，请随论文一并提交。"),
        "files": {}, "tickers": {}, "failed": {},
    }
    ok_list, fail_list = [], []

    # ---- 1. Yahoo 日线
    all_events = []
    for i, (ticker, (group, desc)) in enumerate(YAHOO.items(), 1):
        print(f"[{i:2d}/{len(YAHOO)}] {ticker:8s} {desc}")
        try:
            px, payload_price, info = fetch_yahoo_prices(session, ticker)
        except Exception as e:                       # noqa: BLE001
            print(f"    ✗ 价格请求失败：{e}")
            manifest["failed"][ticker] = str(e)
            fail_list.append(ticker)
            time.sleep(1)
            continue

        # 两请求之间 sleep
        time.sleep(random.uniform(*SLEEP_BETWEEN_CALLS))

        ev, payload_events = fetch_yahoo_events(session, ticker)
        events_missing = ev is None

        base = safe_name(ticker)
        csv_path = RAW_DIR / f"{base}__{AS_OF}.csv"
        json_path = RAW_DIR / f"{base}__{AS_OF}.json"
        px.to_csv(csv_path, index=False)
        json_path.write_text(json.dumps(payload_price, ensure_ascii=False), encoding="utf-8")

        ev_json_path = None
        if not events_missing:
            ev_json_path = RAW_DIR / f"{base}__events__{AS_OF}.json"
            ev_json_path.write_text(json.dumps(payload_events, ensure_ascii=False),
                                    encoding="utf-8")
            if not ev.empty:
                all_events.append(ev)

        manifest["files"][csv_path.name] = sha256(csv_path)
        manifest["files"][json_path.name] = sha256(json_path)
        if ev_json_path is not None:
            manifest["files"][ev_json_path.name] = sha256(ev_json_path)

        n_div = int((ev.type == "dividend").sum()) if (ev is not None and not ev.empty) else 0
        n_spl = int((ev.type == "split").sum())    if (ev is not None and not ev.empty) else 0

        manifest["tickers"][ticker] = dict(
            group=group, description=desc, rows=int(len(px)),
            first_date=str(px.Date.min().date()),
            last_date=str(px.Date.max().date()),
            n_dividends=n_div, n_splits=n_spl,
            events_missing=events_missing,
            close_equals_adjclose=bool((px.Close - px.AdjClose).abs().max() < 1e-8),
            **info,
        )
        flag = "（事件缺失）" if events_missing else ""
        print(f"    ✓ {len(px)} 行  {px.Date.min().date()} → {px.Date.max().date()}{flag}")
        ok_list.append(ticker)
        time.sleep(3)   # 每个标的之间

    if all_events:
        ev_path = RAW_DIR / f"events__{AS_OF}.csv"
        pd.concat(all_events).sort_values(["ticker", "date"]).to_csv(ev_path, index=False)
        manifest["files"][ev_path.name] = sha256(ev_path)
    else:
        print("\n注意：没有任何事件数据，events__*.csv 未生成。")

    # ---- 2. 小时 K 线
    for name, fn in (("coinbase", fetch_coinbase_hourly), ("bitstamp", fetch_bitstamp_hourly)):
        print(f"\n[小时 K 线] {name}")
        try:
            df = fn(session)
            p = RAW_DIR / f"BTCUSD_1h_{name}__{AS_OF}.csv"
            df.to_csv(p, index=False)
            manifest["files"][p.name] = sha256(p)
            manifest["tickers"][f"BTCUSD_1h_{name}"] = dict(
                group="bitcoin_hourly", rows=int(len(df)),
                first=str(df.time_utc.min()), last=str(df.time_utc.max()))
            print(f"    ✓ {len(df)} 根  {df.time_utc.min()} → {df.time_utc.max()}")
            ok_list.append(f"BTC 1h {name}")
        except Exception as e:                       # noqa: BLE001
            print(f"    ✗ 失败：{e}")
            manifest["failed"][f"BTCUSD_1h_{name}"] = str(e)
            fail_list.append(f"BTC 1h {name}")

    # ---- 3/4. 官网档案（原样保存）
    for name, url, ext in (("GLD_archive", GLD_ARCHIVE, "csv"), ("IBIT_nav", IBIT_NAV, "xls")):
        print(f"\n[官网档案] {name}")
        try:
            r = _get(session, url, accept="*/*", label=f"[{name}]")
            if len(r.content) < 500:
                raise RuntimeError(f"返回内容过短（{len(r.content)} 字节）")
            p = RAW_DIR / f"{name}__{AS_OF}.{ext}"
            p.write_bytes(r.content)
            manifest["files"][p.name] = sha256(p)
            print(f"    ✓ {len(r.content) / 1024:.0f} KB")
            ok_list.append(name)
        except Exception as e:                       # noqa: BLE001
            print(f"    ✗ 失败：{e}")
            manifest["failed"][name] = str(e)
            fail_list.append(name)

    man_path = RAW_DIR / f"manifest__{AS_OF}.json"
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"成功 {len(ok_list)} 项；失败 {len(fail_list)} 项")
    if fail_list:
        print("失败：" + ", ".join(fail_list))
        must = {"BTC-USD", "IBIT", "GLD", "SPY", "TLT", "^VIX"}
        if must & set(fail_list) or {"BTC 1h coinbase", "BTC 1h bitstamp"} <= set(fail_list):
            print("⚠️ 有必需项失败（核心标的或两个小时 K 线源都失败），请检查网络/代理后重跑。")
        else:
            print("核心数据齐全；失败项只会在分析中被跳过。")
    print(f"manifest：{man_path}")
    print("完成后告诉 Claude 即可，它会直接读取 data/raw/ 里带 __20260921S 的文件。")


if __name__ == "__main__":
    sys.exit(main())