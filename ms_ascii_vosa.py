#!/usr/bin/env python3
"""
ms_ascii_vosa.py
=============

Convert a merged photometric dataframe (e.g. after GALEX–Gaia–PS1
cross-match) into one or more tab-separated text files ready for VOSA
(no-UV version).  Each output file contains ≤ N objects, where *N*
defaults to 1000 (Max object limit for VOSA).

Usage
-----
* output_dir         : Folder to receive 0-1000.txt, 1000-2000.txt, …
* --chunk            : Objects per file (default 1000)

The script is designed for integration into the WDMSpy package but can
also run stand-alone.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd


# ----------------------------------------------------------------------
# Filter mapping: (mag column, error column, VOSA filter-name, pntopts)
FILTER_COLUMNS = [
    ("FUVmag", "e_FUVmag", "GALEX/GALEX.FUV", "nofit"),
    ("NUVmag", "e_NUVmag", "GALEX/GALEX.NUV", "nofit"),
    ("BPmag", "e_BPmag", "GAIA/GAIA3.Gbp", "mag"),
    ("Gmag", "e_Gmag", "GAIA/GAIA3.G", "mag"),
    ("RPmag", "e_RPmag", "GAIA/GAIA3.Grp", "mag"),
    ("Bmag", "e_Bmag", "Misc/APASS.B", "mag"),
    ("gmag_x", "e_gmag_x", "PAN-STARRS/PS1.g", "mag"),
    ("Vmag", "e_Vmag", "Misc/APASS.V", "mag"),
    ("rmag", "e_rmag", "PAN-STARRS/PS1.r", "mag"),
    ("imag", "e_imag", "PAN-STARRS/PS1.i", "mag"),
    ("zmag", "e_zmag", "PAN-STARRS/PS1.z", "mag"),
    ("ymag", "e_ymag", "PAN-STARRS/PS1.y", "mag"),
    ("Jmag", "e_Jmag", "2MASS/2MASS.H", "mag"),
    ("Hmag", "e_Hmag", "2MASS/2MASS.J", "mag"),
    ("Kmag", "e_Kmag", "2MASS/2MASS.Ks", "mag"),
    ("W1mag", "e_W1mag", "WISE/WISE.W1", "mag"),
    ("W2mag", "e_W2mag", "WISE/WISE.W2", "mag"),
    ("W3mag", "e_W3mag", "WISE/WISE.W3", "mag"),
    ("W4mag", "e_W4mag", "WISE/WISE.W4", "mag"),
]


# ----------------------------------------------------------------------
def ms_ascii_noUV_VOSA(df: pd.DataFrame, output_dir: Path, chunk_size: int = 1000) -> None:
    """
    Split *df* into chunks of *chunk_size* rows and write VOSA-ready
    ASCII files to *output_dir* (created if absent).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    total_rows = len(df)

    for start in range(0, total_rows, chunk_size):
        end = min(start + chunk_size, total_rows)
        chunk = df.iloc[start:end]

        file_path = output_dir / f"{start}-{end}.txt"
        with file_path.open("w") as fh:
            fh.write(
                "object\tRA\tDEC\tdis\tAv\tfilter\tflux\terror\tpntopts\tobjopts\n"
            )

            for _, row in chunk.iterrows():
                # Sanitise object name for VOSA
                obj = row["Name"].replace(" ", "_").replace("*", "_AST_")
                ra, dec = row["RAJ2000"], row["DEJ2000"]
                dist, av = row["rpgeo"], row["Av"]
                objopts = "---"

                for mag_col, err_col, filt, pntopts in FILTER_COLUMNS:
                    mag = row.get(mag_col, "---")
                    err = row.get(err_col, "---")

                    if pd.notna(mag) and pd.notna(err):
                        flux, flux_err = mag, err
                    else:
                        flux, flux_err, pntopts = "---", "---", "---"

                    fh.write(
                        f"{obj}\t{ra}\t{dec}\t{dist}\t{av}\t"
                        f"{filt}\t{flux}\t{flux_err}\t{pntopts}\t{objopts}\n"
                    )

        print(f"[ms_ascii_noUV_VOSA] wrote {file_path}")


# ----------------------------------------------------------------------
def read_catalog(path: Path) -> pd.DataFrame:
    """
    Load a catalog file using pandas.  Format is inferred from extension.
    """
    ext = path.suffix.lower()
    if ext in {".pkl", ".pickle"}:
        return pd.read_pickle(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    if ext in {".feather", ".ft"}:
        return pd.read_feather(path)
    if ext in {".csv", ".tsv", ".txt"}:
        sep = "," if ext == ".csv" else "\t"
        return pd.read_csv(path, sep=sep)
    raise ValueError(f"Unsupported catalog extension: {ext}")


# ----------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Export merged catalog to VOSA-ready ASCII chunks (no UV)"
    )
    p.add_argument("catalog", type=Path, help="Merged catalog file (pickle/CSV/…)")
    p.add_argument("outdir", type=Path, help="Output directory")
    p.add_argument(
        "--chunk",
        type=int,
        default=1000,
        metavar="N",
        help="Rows per output file (default: 1000)",
    )
    return p.parse_args(argv)


# ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    # Sanity checks
    if not args.catalog.exists():
        sys.exit(f"Error: catalog not found: {args.catalog}")
    if args.chunk <= 0:
        sys.exit("Error: --chunk must be a positive integer")
    if args.chunk > 1000:
        sys.exit("Error: --chunk too large, max 1000 for VOSA compatibility")

    df = read_catalog(args.catalog)
    ms_ascii_noUV_VOSA(df, args.outdir, chunk_size=args.chunk)


if __name__ == "__main__":
    main()