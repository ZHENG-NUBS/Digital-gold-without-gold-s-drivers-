# Pre-registration: does Bitcoin's exposure to gold-specific shocks persist after summer 2026?

**Authors:** Jingjing Wang, Ziyi Zheng
**Registered:** 15 October 2026. The authors have analysed no data dated after 30 September 2026.
**Related work:** a Finance Research Letters submission in preparation ("Digital gold without gold's drivers? Spot Bitcoin ETFs, real yields, the dollar and gold-specific shocks").

## Background
Using 681 trading days (12 Jan 2024 – 30 Sep 2026), we find that the loading γ of a spot Bitcoin ETF (IBIT) on gold-specific shocks was about 0.1 until mid-June 2026 and about 0.7 from 16 June to 30 September 2026. Over 2015–2026, Bitcoin priced at 16:00 ET shows its highest volatility-adjusted exposure to gold-specific shocks in that window. We noticed this rise when we extended the sample. We therefore register in advance a test on data that did not exist when the rise was found.

## Hold-out period
All U.S. trading days from **15 October 2026 to 15 January 2027** inclusive (about 62 days). The period starts on the registration date, so none of its data could have been seen. The analysis will be run no earlier than 20 January 2027.

## Code
The code is fixed at the versions below, identified by SHA-256 checksum. It will not be modified before the registered analysis is run.

| File | SHA-256 |
|---|---|
| 01d_fetch_scope.py | a8c5b4f84bf8d378137996f5a2b864d0a368f2f2b9ae9deda3bbe31b48dee40f |
| 30a_fetch_macro.py | 5f60026c9fc7de36deb735f6d5792bcb81e2a2dcabd98061efced48e145c6c25 |
| 30b_fetch_extend.py | 0473e98dba3f3c80eacc9b7f176ec61517710ef8fd7416c20f995f67ab364a28 |
| 30_debasement_drivers.py | 5714c49ad14cbc722d17cd8f4ec2e73b88b19b305f0295f3c1eb716a9f03a578 |
| 31_placebo_twostep.py | 109daa57ae93f94785d8a904c8aa1fe4b65294ad982887b261aceae706d3e60d |
| 32a_fetch_long.py | 7a01c400da4b5286bcd413cc1e503f5ac26fcb121a831a562434e22bcc7a655f |
| 32_long_sample.py | 3ad91494a20da098ce016b6114f7ec42312fca4061ce7df2e3d0286f259f393c |
| 33_share_tests.py | 953e660d775c1dad5798abcbb96dd3b9e1ef8a1829f3af6801776b99d5d87955 |

## Data
- **Sources:** the same as in the paper.
  - IBIT, GLD, SPY and UUP adjusted closes from Yahoo Finance.
  - 10-year real and nominal par yields from the U.S. Treasury (FRED DFII10/DGS10 if reachable); breakeven = nominal − real.
  - Bitcoin at 16:00 ET from Coinbase hourly bars, with Bitstamp as backup.
- **Download commands** (Python 3.11; new snapshot suffixes, so no existing snapshot is overwritten):
  ```
  python 30b_fetch_extend.py --end 2027-01-16 --asof 20270120F
  python 30a_fetch_macro.py --start 2023-12-01 --end 2027-01-16 --asof 20270120D
  python 32a_fetch_long.py --end 2027-01-16 --asof 20270120H
  ```

## Model
Unchanged from the paper:
- **Gold-specific shock g_t:** the residual from regressing GLD returns on SPY returns, real-yield changes, breakeven changes and UUP returns, over the full sample (12 Jan 2024 – 15 Jan 2027).
- **Regression:** IBIT returns on the same four factors plus g_t. Newey–West standard errors with 5 lags. γ is the coefficient on g_t.

## Hypotheses, tests and commands
- **H1 (primary): γ in the hold-out period is unusually high relative to earlier windows of the same length since 12 Jan 2024.** These windows include the summer-2026 period.
  - Test: Andrews (2003) end-of-sample test, one-sided, with p-values calibrated by 199 null replications (seed 20261014). The γ row is reported in section E.
  - Reject at the 5% level.
  - Command:
    ```
    python 30_debasement_drivers.py --asof-prices 20270120F --asof-macro 20270120D --end 2027-01-15 --holdout-start 2026-10-15
    ```
- **H2 (secondary): γ in the hold-out period is positive.**
  - Test: two-step block bootstrap with 999 draws and mean block length 5 (seed 20261014). The gold shock is re-estimated in every draw.
  - Supported if the lower bound of the 95% interval for the hold-out γ is above 0. The script labels this row "Summer 2026"; in this run it refers to the hold-out period.
  - Command:
    ```
    python 31_placebo_twostep.py --asof-prices 20270120F --asof-macro 20270120D --end 2027-01-15 --holdout-start 2026-10-15 --boot 999
    ```
- **H3 (secondary, long sample): H1 for Bitcoin at 16:00 ET, with comparison windows back to January 2015.**
  - Test T1: calibrated under a constant loading by a wild block bootstrap that preserves Bitcoin's volatility path (999 replications, blocks of 5 days, seed 20261014). One-sided, 5% level.
  - Both raw γ and the share γ/γ\* are reported. The share statistic was added after we had seen the 2015–2026 results, so it is labelled as such.
  - Command:
    ```
    python 33_share_tests.py --asof 20270120H --end 2027-01-15 --holdout-start 2026-10-15 --reps 999
    ```

## How the results will be read
| Outcome | Interpretation |
|---|---|
| H1 rejects | The exposure that appeared in summer 2026 persisted into the hold-out period |
| H1 does not reject, H2 holds | γ remained positive but is not unusual relative to the recent past |
| Neither | Summer 2026 was an episode, not a lasting change |

Every outcome will be reported, whichever it is.

## No changes
The factors, sample start, lag length, window definition, bootstrap settings, seeds and code versions above will not be changed. If a data source fails, the documented fallbacks in the code are used, and this will be reported. Any additional analysis will be labelled exploratory.
