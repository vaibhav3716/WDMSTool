#!/usr/bin/env python3
"""
Interactive_CMD.py
==================
Visualise GALEX (UV) and Gaia (optical) colour‑magnitude diagrams side‑by‑side
with linked interactive highlighting.

Usage
-----
$ python Interactive_CMD.py  input_catalog.csv

A left‑click on a point in either panel outlines the same source in yellow
on both panels.

This script is part of the WDMSpy toolkit.
"""

import argparse
import pathlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_cmd(csv_path: pathlib.Path) -> None:
    """Create interactive GALEX+Gaia CMDs from *csv_path*."""
    df = pd.read_csv(csv_path)

    FUV, NUV, G = df["FUVmag"], df["NUVmag"], df["Gmag"]
    BP_RP = df["BPmag"] - df["RPmag"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    fig.canvas.manager.set_window_title(
        "Color‑Magnitude Diagram – click to cross‑highlight"
    )

    # UV CMD
    ax1.scatter(FUV - NUV, FUV, c="black", s=0.05, alpha=0.15, picker=25)
    ax1.invert_yaxis()
    ax1.set_title("Ultra‑Violet CMD")
    ax1.set_xlabel("FUV − NUV")
    ax1.set_ylabel("FUV")

    # Optical CMD
    ax2.scatter(BP_RP, G, c="black", s=0.05, alpha=0.15, picker=25)
    ax2.invert_yaxis()
    ax2.set_title("Optical CMD")
    ax2.set_xlabel("BP − RP")
    ax2.set_ylabel("G")

    # Interactive highlighting
    def onpick(event):
        ind = event.ind
        uv_high.set_offsets(np.c_[FUV[ind] - NUV[ind], FUV[ind]])
        opt_high.set_offsets(np.c_[BP_RP[ind], G[ind]])
        fig.canvas.draw_idle()

    uv_high = ax1.scatter(
        [], [], facecolors="none", edgecolors="yellow", s=0.5, linewidths=2
    )
    opt_high = ax2.scatter(
        [], [], facecolors="none", edgecolors="yellow", s=0.5, linewidths=2
    )

    fig.canvas.mpl_connect("pick_event", onpick)
    plt.tight_layout()
    plt.show()


def main() -> None:
    p = argparse.ArgumentParser(description="Interactive GALEX+Gaia CMD viewer")
    p.add_argument("catalog", type=pathlib.Path, help="CSV file with photometry")
    args = p.parse_args()

    if not args.catalog.exists():
        p.error(f"File not found: {args.catalog}")
    plot_cmd(args.catalog)


if __name__ == "__main__":
    main()