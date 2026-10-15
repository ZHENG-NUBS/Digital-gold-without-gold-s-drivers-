# AsPredicted form: answers to paste

Title: **Does Bitcoin's exposure to gold-specific shocks persist after summer 2026?**
Authors: Jingjing Wang, Ziyi Zheng. Each author receives an email and must approve before the pre-registration is final.
Attach `PREREGISTRATION_FRL.md` as a PDF if the form allows it, or put its link in question 8.

---

**1) Data collection. Have any data been collected for this study already?**
It's complicated. We have analysed daily market data up to 30 September 2026, which motivated this registration. The test is on the hold-out period from 15 October 2026 to 15 January 2027, which starts on the registration date; none of those data exist yet or have been seen. The data are public market prices and yields, downloaded no earlier than 20 January 2027.

**2) Hypothesis. What's the main question being asked or hypothesis being tested in this study?**
From 16 June to 30 September 2026, the loading γ of a spot Bitcoin ETF (IBIT) on gold-specific shocks rose from about 0.1 to about 0.7. Gold-specific shocks are the part of gold's (GLD's) daily return not explained by equities, real yields, breakeven inflation and the dollar. We test whether this exposure persists. H1 (primary): γ estimated over the hold-out period is unusually high relative to all earlier windows of the same length since 12 January 2024, including summer 2026. H2: γ in the hold-out period is positive. H3: H1 holds for Bitcoin priced at 16:00 ET relative to windows since January 2015.

**3) Dependent variable. Describe the key dependent variable(s) specifying how they will be measured.**
Daily simple returns of IBIT (H1, H2) and of Bitcoin at 16:00 ET from Coinbase hourly bars (H3), on U.S. trading days. The key quantity is γ, the coefficient on the gold-specific shock in an OLS regression of these returns on SPY returns, 10-year real-yield changes, 10-year breakeven changes and UUP returns, plus the gold-specific shock. The shock is the residual of the same regression for GLD, estimated over the full sample. Yields come from U.S. Treasury par curves.

**4) Conditions. How many and which conditions will participants be assigned to?**
None. This is an observational time-series study with no assigned conditions. The comparison is between the hold-out window and earlier windows of equal length.

**5) Analyses. Specify exactly which analyses you will conduct to examine the main question/hypothesis.**
H1: the Andrews (2003) end-of-sample instability test for γ, one-sided, with p-values calibrated by 199 null residual block-bootstrap replications (seed 20261014); reject at 5%. H2: a two-step stationary block bootstrap (999 draws, mean block length 5, seed 20261014) that re-estimates the gold shock in each draw; supported if the lower bound of the 95% interval for hold-out γ exceeds 0. H3: test T1 of our script 33, calibrated under a constant loading by a wild block bootstrap preserving Bitcoin's volatility path (999 replications, blocks of 5, seed 20261014), reporting raw γ and γ/γ* (γ* = sd(Bitcoin)/sd(GLD)). The γ/γ* statistic was added after we saw 2015–2026 data. Newey–West standard errors with 5 lags throughout. Code is fixed by SHA-256 checksums listed in the attached document. Exact commands are also listed there.

**6) Outliers and Exclusions. Describe exactly how outliers will be defined and handled, and your precise rule(s) for excluding observations.**
None. All U.S. trading days in the sample are used. Returns are not winsorized. Days on which a series is missing are dropped only if the regression cannot be estimated without them. If FRED is unreachable, U.S. Treasury yield files are used, as documented in the code.

**7) Sample Size. How many observations will be collected or what will determine sample size?**
All U.S. trading days from 15 October 2026 to 15 January 2027 (about 62 days). The comparison sample runs from 12 January 2024 (H1, H2) or 5 January 2015 (H3) to 14 October 2026.

**8) Other. Anything else you would like to pre-register?**
Interpretation, fixed in advance: if H1 rejects, the summer-2026 exposure persisted. If H1 does not reject but H2 holds, γ stayed positive but is not unusual. If neither holds, summer 2026 was an episode. All outcomes will be reported. Specifications will not be changed, and any further analysis will be labelled exploratory. Full protocol with code checksums and commands: [attach or link PREREGISTRATION_FRL.md].
