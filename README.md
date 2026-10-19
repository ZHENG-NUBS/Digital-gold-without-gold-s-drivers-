# Digital gold without gold's drivers? Spot Bitcoin ETFs, real yields, the dollar and gold-specific shocks

Replication code for the letter of the same title by **Jingjing Wang and Ziyi Zheng**, 
draft for *Finance Research Letters*.

The letter asks whether a spot Bitcoin ETF (IBIT) responds to the drivers of gold (GLD):
- real yields;
- breakeven inflation;
- the U.S. dollar;
- gold's own idiosyncratic ("gold-specific") shocks.

Main sample: 12 Jan 2024 – 30 Sep 2026 (681 trading days). Long sample: Bitcoin at 16:00 ET, Jan 2015 – Sep 2026 (2,952 trading days).

The test of whether the summer-2026 change persists is **pre-registered on AsPredicted (#317553)**, on the
hold-out period 15 Oct 2026 – 15 Jan 2027. See [Pre-registration](#pre-registration) below.

## Repository contents

| File | What it does |
|---|---|
| `01d_fetch_scope.py` | Download engine: Yahoo Finance daily prices, Coinbase/Bitstamp hourly Bitcoin. Shared with the companion paper; used here only through `30b` and `32a`, never run directly. |
| `30a_fetch_macro.py` | Macro series: UUP (Yahoo), 10-year real and nominal par yields (FRED, or U.S. Treasury yield-curve files if FRED is unreachable); breakeven = nominal − real. Writes snapshot `__20260921D`. |
| `30b_fetch_extend.py` | Main-sample prices to 30 Sep 2026 (SPY, IBIT, GLD, TLT, TIP, IEF, hourly Bitcoin). Runs `01d` unchanged under a new suffix `__20261001F`. |
| `30_debasement_drivers.py` | Main analysis: factor loadings, gold-specific shock and its benchmark, sup-Wald and end-of-sample tests, rolling estimates, robustness. |
| `31_placebo_twostep.py` | Placebo ETFs (QQQ, EFA, TLT, AGG) and the two-step bootstrap that re-estimates the gold shock in every draw. |
| `32a_fetch_long.py` | Long-sample snapshot `__20261001H`: daily prices from Sep 2014, hourly Bitcoin from Jan 2015, macro series. |
| `32_long_sample.py` | Long-sample analysis: loadings by era, rolling γ and γ/γ\*, ranks of 74-day windows, end-of-sample test. |
| `33_share_tests.py` | Calibrated tests on the long sample: rank of the final window (T1) and episodic variation (T2), by wild block bootstrap. |
| `34_figures.py` | Draws Figures 1 and 2 for submission from the CSVs written by `30` and `32` (no estimation). |
| `35_table_entries.py` | Table entries estimated on subsamples: γ before and after 16 Jun 2026, the drop-day checks and the end-of-sample test without 19–21 Aug 2026. Uses script 30's functions unchanged. |
| `PREREGISTRATION_checksums.sha256` | SHA-256 of the eight pre-registered scripts (all of the above except `34` and `35`). |
| `preregistration/` | Full protocol (`PREREGISTRATION_FRL.md`) and the answers submitted to AsPredicted. |
| `data/raw/manifest__*.json` | Sources, request windows, download times and SHA-256 of every data file used. |
| `out/` | The outputs behind the letter (reports, CSVs, figures). |
| `requirements.txt` | Python packages and the versions used. |

## Which output backs which part of the letter

| Letter | Output |
|---|---|
| Table 1 (daily and weekly factor loadings) | `out/30_debasement_20261001F_2026-09-30/report.md` sections A and D2; `tables_A_daily.csv`, `tables_D_W.csv` |
| Table 2 (gold-specific shocks, stability) | `30…/report.md` sections A2, B, C and E (`report_sectionE.md`); γ before and after 16 Jun 2026 from `out/35_table_entries/report.md`; long-sample rows from `out/32_long_sample/report.md` (L3, L4) and `out/33_share_tests/report.md` |
| Table 3 (robustness) | `30…/report.md` section D (D1, D4; `tables_D_2d.csv`); drop-day checks from `out/35_table_entries/report.md`; placebo and two-step rows from `out/31_placebo_twostep/report.md` |
| Figure 1 | `out/34_figures/Figure1.*`, drawn from `30…/rolling_gres_loading.csv` |
| Figure 2 | `out/34_figures/Figure2.*`, drawn from `out/32_long_sample/rolling_gamma_long.csv` |

## Data

The raw price files are **not** included. Yahoo Finance's terms do not allow redistribution. Each
`manifest__<suffix>.json` lists the source, request window and SHA-256 checksum of every file, so
a copy can be verified byte for byte. The authors' snapshot files are available on request.

| Snapshot suffix | Contents | Written by |
|---|---|---|
| `__20261001F` | SPY, IBIT, GLD, TLT, TIP, IEF daily; hourly Bitcoin; 1 Jan 2024 – 30 Sep 2026 | `30b` |
| `__20260921D` | UUP, DFII10, DGS10, T10YIE; 1 Dec 2023 – 30 Sep 2026 | `30a` |
| `__20261001H` | Long sample: daily from Sep 2014, hourly Bitcoin from Jan 2015, macro series | `32a` |
| `__20260921S` | QQQ, EFA and AGG for the placebo tests (snapshot of the companion paper) | `01d` |

**Note on `__20260921S`.** These files come from the replication package of the companion paper
(Jiang, Wang and Zheng, under review). The original files were overwritten on 14 October 2026, when
`01d` was re-run with a later end date. The files used here are that replacement download, which runs
to 30 Sep 2026. Their checksums are in `manifest__20260921S_replacement_20261014.json`.
`manifest__20260921S.json` keeps the checksums of the original files for the record.

A new download will not be byte-identical to the authors' snapshots. Yahoo Finance recomputes
adjusted closes after each distribution, so results can differ in the last digits.

**Proxy.** The authors' network needs a local proxy, so `01d_fetch_scope.py` sets
`PROXY = "http://127.0.0.1:20171"` on line 98, and the manifests record that address. Elsewhere, set
`PROXY = None` on that line before downloading (`30a` reads `HTTPS_PROXY` from the environment).
This edit changes the file's checksum. The checksums apply to the authors' own run of the
pre-registered analysis, not to downloads by others.

## Reproducing the results

Python 3.11, with `pip install -r requirements.txt`. Run everything from the repository root.
Scripts read from `data/raw/` and write to `out/`.

```bash
# 1. Data (skip if you have the authors' snapshot files in data/raw/)
python 30a_fetch_macro.py                     # -> __20260921D
python 30b_fetch_extend.py                    # -> __20261001F
python 32a_fetch_long.py                      # -> __20261001H (10-15 minutes)

# 2. Analysis
python 30_debasement_drivers.py --asof-prices 20261001F --end 2026-09-30   # Tables 1-3
python 31_placebo_twostep.py                  # placebo ETFs and two-step bootstrap (Table 3)
python 32_long_sample.py                      # long sample (Table 2, Figure 2 data)
python 33_share_tests.py                      # calibrated long-sample tests (Table 2)
python 34_figures.py                          # Figures 1 and 2
python 35_table_entries.py                    # subsample entries of Tables 2-3
```

`python 30_debasement_drivers.py --selftest` checks the estimators on synthetic data with known loadings. All bootstraps
use the seed 20261014.

## Pre-registration

The summer-2026 rise in Bitcoin's loading on gold-specific shocks was found, not predicted. We
therefore registered a test of whether it persists on data that did not exist at registration:
- **Hold-out period:** 15 Oct 2026 – 15 Jan 2027.
- **Registered:** 15 Oct 2026, AsPredicted #317553.
- **Approved by:** both authors.

The eight scripts in this repository are byte-identical to the registered versions, so
`sha256sum -c PREREGISTRATION_checksums.sha256` reports `OK` for each. For the same reason their
comments are left as registered, partly in Chinese, and refer to the companion (JRFM) paper and the
letter (FRL). The eight scripts are fixed by the SHA-256 checksums in `PREREGISTRATION_checksums.sha256`, and they
will not be edited before the registered analysis is run. The protocol, hypotheses (H1–H3) and the
reading of each outcome are in `preregistration/PREREGISTRATION_FRL.md`.

Run on or after 20 Jan 2027:

```bash
sha256sum -c PREREGISTRATION_checksums.sha256   # on macOS: shasum -a 256 -c PREREGISTRATION_checksums.sha256
python 30b_fetch_extend.py --end 2027-01-16 --asof 20270120F
python 30a_fetch_macro.py --start 2023-12-01 --end 2027-01-16 --asof 20270120D
python 32a_fetch_long.py --end 2027-01-16 --asof 20270120H
python 30_debasement_drivers.py --asof-prices 20270120F --asof-macro 20270120D --end 2027-01-15 --holdout-start 2026-10-15   # H1
python 31_placebo_twostep.py --asof-prices 20270120F --asof-macro 20270120D --end 2027-01-15 --holdout-start 2026-10-15 --boot 999   # H2
python 33_share_tests.py --asof 20270120H --end 2027-01-15 --holdout-start 2026-10-15 --reps 999   # H3
```

The result will be reported whatever it shows.

## Citation

Wang, J., Zheng, Z., 2026. Digital gold without gold's drivers? Spot Bitcoin ETFs, real yields, the
dollar and gold-specific shocks. Manuscript prepared for *Finance Research Letters*.

## AI assistance

Code in this repository was partially written and run with the help of Claude (Anthropic) and reviewed by the authors, as stated in the letter's declaration.

## License

Code: MIT License (see `LICENSE`). Data are not redistributed; see [Data](#data).
