# -*- coding: utf-8 -*-
"""
34_figures.py - Publication figures for the FRL letter (drawing only; no estimation).

Reads the CSVs already written by the registered scripts and redraws the two figures as
separate, high-resolution files for submission. It does not import or modify any
pre-registered script (01d, 30a, 30b, 30, 31, 32a, 32, 33), so their checksums are unaffected.

Inputs
  out/30_debasement_20261001F_2026-09-30/rolling_gres_loading.csv   (script 30, extended run)
  out/32_long_sample/rolling_gamma_long.csv                        (script 32)
Outputs (out/34_figures/)
  Figure1.pdf, Figure1.png (600 dpi), Figure1.tif
  Figure2.pdf, Figure2.png (600 dpi), Figure2.tif

Usage   python 34_figures.py [--fig1 PATH] [--fig2 PATH] [--out DIR]
"""
from __future__ import annotations

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BLUE, GOLD = "#1f4e79", "#9a6f00"
ETF_LAUNCH = pd.Timestamp("2024-01-11")

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 9, "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
})


def save(fig, out, name):
    for ext, kw in (("pdf", {}), ("png", {"dpi": 600}), ("tif", {"dpi": 600, "pil_kwargs": {"compression": "tiff_lzw"}})):
        fig.savefig(os.path.join(out, f"{name}.{ext}"), **kw)
    plt.close(fig)
    print(f"wrote {name}.pdf/.png/.tif")


def figure1(path, out):
    r = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    fig, ax = plt.subplots(figsize=(6.3, 3.0))
    ax.fill_between(r.index, r.beta_Gres - 1.96 * r.se, r.beta_Gres + 1.96 * r.se,
                    color=BLUE, alpha=0.18, lw=0, label="95% band")
    ax.plot(r.index, r.beta_Gres, color=BLUE, lw=1.4, label=r"IBIT loading on gold-specific shocks, $\gamma$")
    ax.plot(r.index, r.benchmark, color=GOLD, lw=1.2, ls="--", label=r"Digital-gold benchmark, $\gamma^{*}$")
    ax.axhline(0, color="grey", lw=0.6)
    ax.set_ylabel("120-day rolling loading")
    ax.set_xlim(r.index.min(), r.index.max())
    # legend below the plotting area, so it cannot cover either line
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False,
              handlelength=2.2, columnspacing=1.4)
    save(fig, out, "Figure1")


def figure2(path, out):
    r = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    fig, ax = plt.subplots(2, 1, figsize=(6.3, 4.4), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    ax[0].fill_between(r.index, r.gamma - 1.96 * r.se, r.gamma + 1.96 * r.se, color=BLUE, alpha=0.18, lw=0)
    ax[0].plot(r.index, r.gamma, color=BLUE, lw=1.1)
    ax[0].set_ylabel(r"$\gamma$ (120-day)")
    ax[1].plot(r.index, r.share, color=GOLD, lw=1.1)
    ax[1].set_ylabel(r"$\gamma\,/\,\gamma^{*}$")
    for a in ax:
        a.axhline(0, color="grey", lw=0.6)
        a.axvline(ETF_LAUNCH, color="black", lw=0.8, ls=":")
    ax[0].annotate("Spot ETFs", xy=(ETF_LAUNCH, 1), xycoords=("data", "axes fraction"),
                   xytext=(-4, -2), textcoords="offset points", ha="right", va="top", fontsize=8)
    ax[1].set_xlim(r.index.min(), r.index.max())
    fig.align_ylabels(ax)
    save(fig, out, "Figure2")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fig1", default=os.path.join(HERE, "out", "30_debasement_20261001F_2026-09-30", "rolling_gres_loading.csv"))
    ap.add_argument("--fig2", default=os.path.join(HERE, "out", "32_long_sample", "rolling_gamma_long.csv"))
    ap.add_argument("--out", default=os.path.join(HERE, "out", "34_figures"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    figure1(a.fig1, a.out)
    figure2(a.fig2, a.out)


if __name__ == "__main__":
    main()
