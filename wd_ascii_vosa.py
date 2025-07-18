#!/usr/bin/env python3
"""
wd_ascii_vosa.py
---------------------
• Prompts for the *result_dir* produced by ms_data_process.py
• Lets the user choose GC, BC, or BOTH
• Prompts for an output directory and chunk size
• Generates VOSA-ready residual files in batches of ≤ chunk objects
"""

import os
import glob
import pathlib
import pandas as pd
import numpy as np
from tqdm import tqdm


def build_entries(objects_glob: str) -> list[dict]:
    """Return a list of residual-dicts for every .bfit.phot.dat in *objects_glob*."""
    entries: list[dict] = []

    for fpath in tqdm(sorted(glob.glob(objects_glob, recursive=True)),
                      desc="Parsing photometry", unit="file"):
        # ---- metadata block ------------
        with open(fpath) as fh:
            meta = {}
            for line in fh.readlines()[2:39]:
                line = line.strip().lstrip("# ")
                if "=" in line:
                    k, v = [s.strip() for s in line.split("=", 1)]
                    try:
                        v = float(v.split()[0])
                    except ValueError:
                        pass
                    ren = {"RA": "RA(deg)", "DEC": "DEC(deg)",
                           "D (pc)": "D(pc)", "Av": "Av"}
                    meta[ren.get(k, k)] = v

        # ---- data block ----------------
        try:
            df = pd.read_csv(fpath, comment="#", sep=r"\s+")
        except Exception as exc:
            print(f"[skip] {fpath}: {exc}")
            continue

        for c in ["Flux", "FluxMod", "Error"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        for c in ["FitExc", "UpLim", "Excess", "Fitted"]:
            df[c] = df[c].replace("---", 0).astype(int)

        df["Residual"] = np.nan
        df["ResidualErr"] = np.nan

        # first two rows (FUV/NUV)
        df.loc[:1, "Residual"] = df.loc[:1, "Flux"] - df.loc[:1, "FluxMod"]
        df.loc[:1, "ResidualErr"] = df.loc[:1, "Error"]

        mask = ((df.index >= 2) & (df["Fitted"] == 1) &
                (df["Excess"] == 0) & (df["UpLim"] == 0) &
                (df["FitExc"] == 0))
        df.loc[mask, "Residual"] = df.loc[mask, "Flux"] - df.loc[mask, "FluxMod"]
        df.loc[mask, "ResidualErr"] = df.loc[mask, "Error"]
        df = df[df["Residual"].notna()]

        obj = pathlib.Path(fpath).stem.replace("_", "-")
        for _, r in df.iterrows():
            entries.append({
                "object": obj,
                "RA": meta.get("RA(deg)", "---"),
                "DEC": meta.get("DEC(deg)", "---"),
                "D": meta.get("D(pc)", "---"),
                "Av": meta.get("Av", 0.0),
                "filter": r["FilterID"],
                "flux": r["Residual"],
                "error": r["ResidualErr"],
            })
    return entries


def write_batches(entries: list[dict], out_dir: pathlib.Path, chunk: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(entries)
    unique_objs = df["object"].unique()
    chunks = [unique_objs[i:i + chunk] for i in range(0, len(unique_objs), chunk)]

    for idx, obj_subset in enumerate(chunks, start=1):
        df_chunk = df[df["object"].isin(obj_subset)]
        out_path = out_dir / f"{idx}.txt"
        with out_path.open("w") as fh:
            fh.write("object\tRA\tDEC\tdis\tAv\tfilter\tflux\terror\tpntopts\tobjopts\n")
            for _, row in df_chunk.iterrows():
                fh.write(f"{row['object']}\t{row['RA']}\t{row['DEC']}\t{row['D']}\t"
                         f"{row['Av']}\t{row['filter']}\t{row['flux']}\t{row['error']}\terg\t---\n")
    print(f"✅ Wrote {len(chunks)} files to {out_dir}")


def main() -> None:
    base = input("Path to ms_process_pipeline *result_dir*: ").strip()
    base_path = pathlib.Path(base).expanduser().resolve()
    if not base_path.is_dir():
        print("Error: path not found.")
        return

    choice = input("Generate (g)ood, (b)ad, or (a)ll candidates? [g/b/a]: ").lower()
    if choice not in {"g", "b", "a"}:
        print("Invalid choice."); return

    out_root = pathlib.Path(input("Output directory for ASCII files: ").strip() or
                            (base_path / "WD_VOSA"))
    chunk = int(input("Chunk size [default 1000]: ") or 1000)

    if choice in {"g", "a"}:
        gc_dir = next(base_path.glob("*_gc"), None)
        if gc_dir:
            entries = build_entries(str(gc_dir / "objects/*/bestfitp/*.bfit.phot.dat"))
            write_batches(entries, out_root / "good", chunk)

    if choice in {"b", "a"}:
        bc_dir = next(base_path.glob("*_bc"), None)
        if bc_dir:
            entries = build_entries(str(bc_dir / "objects/*/bestfitp/*.bfit.phot.dat"))
            write_batches(entries, out_root / "bad", chunk)

    print("Done.")


if __name__ == "__main__":
    main()