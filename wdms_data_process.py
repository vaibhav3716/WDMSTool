#!/usr/bin/env python3
"""
wdms_data_process.py
====================
Pipeline for white‑dwarf + MS (WD‑MS) photometry:

1. Prompt for the WD‑objects folder and clean every *.bfit.phot.dat
   (remove `#` at line 37).
2. Prompt for the *results/bestfitp.dat* file (or detect recursively)
   and clean line 3 (remove leading '#').
3. Prompt for the theoretical–spectra directory and deduplicate
   BT‑NextGen files (keep one per Teff/logg, drop a±x variants).
4. Summarise everything into <data>/result_dir/ with
      ├─ plots/          (placeholder)
      └─ bestfitp_wdms.csv   (copy of cleaned bestfitp.dat)
"""

import os, glob, shutil, re, csv, pathlib, warnings
from collections import defaultdict
from tqdm import tqdm
import sys

warnings.filterwarnings("ignore", category=FutureWarning)


# ----------------------------------------------------------------------
def clean_photometry(root: pathlib.Path) -> list[pathlib.Path]:
    """Remove leading # at line 37 for every WD .bfit.phot.dat."""
    pattern = root.glob("*/bestfitp/*.bfit.phot.dat")
    cleaned = []
    for fpath in tqdm(sorted(pattern), desc="Photometry", unit="file"):
        lines = fpath.read_text().splitlines()
        if len(lines) >= 37:
            lines[36] = lines[36].lstrip("#")
            fpath.write_text("\n".join(lines) + "\n")
            cleaned.append(fpath)
    return cleaned


# ----------------------------------------------------------------------
def clean_bestfitp(root: pathlib.Path) -> pathlib.Path:
    """Remove leading # at line 3 of first results/bestfitp.dat found."""
    res_files = sorted(root.glob("**/results/bestfitp.dat"))
    if not res_files:
        raise FileNotFoundError("bestfitp.dat not found under any */results/")
    res = res_files[0]
    lines = res.read_text().splitlines()
    if len(lines) >= 3:
        lines[2] = lines[2].lstrip("#")
        res.write_text("\n".join(lines) + "\n")
    return res


# ----------------------------------------------------------------------
def dedup_theoretical(spec_dir: pathlib.Path) -> None:
    """Rename one spectrum per set, drop a±x duplicates."""
    pattern = re.compile(r"a[+-]\d+\.\d+")
    unique: defaultdict[str, list[str]] = defaultdict(list)

    for fname in os.listdir(spec_dir):
        if not fname.endswith(".BT-NextGen.7.dat.txt"):
            continue
        cleaned = pattern.sub("", fname)
        unique[cleaned].append(fname)

    for cleaned, originals in unique.items():
        keep = originals[0]
        if keep != cleaned:
            os.rename(spec_dir / keep, spec_dir / cleaned)
        for dup in originals[1:]:
            os.remove(spec_dir / dup)


# ----------------------------------------------------------------------
def main() -> None:
    import pandas as pd

    args = sys.argv[1:]

    if len(args) >= 3:
        base = pathlib.Path(args[0]).expanduser()
        root_spec = pathlib.Path(args[1]).expanduser()
        ms_folder = pathlib.Path(args[2]).expanduser()
        custom_result = pathlib.Path(args[3]).expanduser() if len(args) >= 4 else None
    else:
        base = pathlib.Path(input("Path to WD objects folder: ").strip()).expanduser()
        root_spec = pathlib.Path(
            input("Path to *parent* folder that contains both MS and WD spectra sub‑folders: ").strip()
        ).expanduser()
        ms_folder = pathlib.Path(input("Path to MS gc/bc folder (contains bestfitp.csv): ").strip()).expanduser()
        custom_result = None

    if not base.is_dir():
        print("❌ Not a directory"); return

    ms_spec_dir = root_spec / "bt-nextgen-agss2009"
    wd_spec_dir = root_spec / "koester2"

    if not ms_spec_dir.is_dir() or not wd_spec_dir.is_dir():
        print("❌ Could not find 'bt-nextgen-agss2009' and 'koester2' inside", root_spec)
        return

    # 1. Clean photometry
    clean_photometry(base)

    # 2. Clean bestfitp.dat
    res_file = clean_bestfitp(base)

    # 3. Deduplicate theoretical spectra
    dedup_theoretical(ms_spec_dir)

    # 4. Decide on result directory ---------------------------------------
    if custom_result:
        result_dir = custom_result
    else:
        use_custom = input(
            f"Save outputs in a different location? (y/N) [default: {base/'result_dir'}] "
        ).strip().lower()
        if use_custom == "y":
            custom_dir = pathlib.Path(input("Enter full path for result_dir: ").strip()).expanduser()
            result_dir = custom_dir
        else:
            result_dir = base / "result_dir"

    result_dir.mkdir(parents=True, exist_ok=True)

    plots_dir = result_dir / "plots"

    # --- prompt for MS good/bad folder ---------------------------------
    ms_csv_list = list(ms_folder.glob("*.csv"))
    if len(ms_csv_list) != 1:
        print("❌ Need exactly one CSV (bestfitp.csv) in the MS folder"); return
    ms_csv = ms_csv_list[0]

    # 4. Create result_dir and placeholder outputs
    #plots_dir  = result_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(res_file, result_dir / "bestfitp_wdms.csv")

    # 5. merge all WD bestfitp.dat into one CSV --------------------------
    wd_dat_files = list(base.glob("**/results/bestfitp.dat"))
    wd_frames = [pd.read_csv(f, sep=r"\s+", comment="#") for f in wd_dat_files]
    wd_combined = pd.concat(wd_frames, ignore_index=True)
    wd_csv = result_dir / "combined_fit_WD.dat"
    wd_combined.to_csv(wd_csv, sep="\t", index=False)

    # 6. merge WD+MS into merged_WD_MS_data.csv --------------------------
    ms_df = pd.read_csv(ms_csv, sep=r"\s+", comment="#")
    wd_df = pd.read_csv(wd_csv, sep=r"\s+", comment="#")
    merged = pd.merge(ms_df, wd_df,
                      on=["Object", "RA", "DEC", "D", "Av"],
                      how="inner", suffixes=("_MS", "_WD"))
    merged_csv = result_dir / "merged_WD_MS_data.csv"
    merged.to_csv(merged_csv, index=False)

    # 7. Plot SEDs with progress bar -------------------------------------
    chunk = int(input("Plot chunk size [default 100]: ") or 100)
    plot_seds(merged_csv,
              phot_base=ms_folder / "objects",
              ms_spec_dir=ms_spec_dir,
              wd_spec_dir=wd_spec_dir,
              out_dir=plots_dir,
              batch=chunk)

    print(f"✅ All done. Outputs in: {result_dir}")
    print(f"WD objects processed: {len(wd_combined)}")
    print(f"Merged objects: {len(merged)}")
    print(f"Plots generated: {len(merged)}")


if __name__ == "__main__":
    main()

# ----------------------------------------------------------------------
def plot_seds(merged_csv, phot_base, ms_spec_dir, wd_spec_dir, out_dir, batch=100):
    import gc, matplotlib.pyplot as plt, numpy as np
    import pandas as pd
    df = pd.read_csv(merged_csv)
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Plotting SEDs", unit="obj"):
        try:
            obj = row["Object"]
            ms_teff = int(row["Teff_MS"]); ms_logg = str(row["logg_MS"]); ms_met = float(row["Meta._MS"])
            wd_teff = int(row["Teff_WD"]);  wd_logg = float(row["logg_WD"])
            scale_ms = float(row["Md_MS"]); scale_wd = float(row["Md_WD"])

            msfile = f"lte{ms_teff//100:03d}-{ms_logg}{'+' if ms_met>0 else '-'}{abs(ms_met):.1f}.BT-NextGen.7.dat.txt"
            wdfile = f"da{wd_teff:05d}_{int(round(wd_logg*100)):03d}.dk.dat.txt"
            ms_path = ms_spec_dir / msfile
            wd_path = wd_spec_dir / wdfile
            phot_path = phot_base / obj / "bestfitp" / f"{obj}.bfit.phot.dat"

            data = pd.read_csv(phot_path, comment="#", sep=r"\s+")
            for c in ["Flux", "FluxMod", "Error"]:
                data[c] = pd.to_numeric(data[c], errors="coerce")
            for c in ["FitExc", "UpLim", "Excess", "Fitted"]:
                data[c] = data[c].replace("---", 0).astype(int)

            prio = np.full(len(data), "none"); prio[data["UpLim"]==1]="uplim"
            prio[(data["FitExc"]==1)&(prio=="none")] ="excess"
            prio[(data["Fitted"]==0)&(prio=="none")] ="nofit"
            fit_mask = prio=="none"

            wl_ms, fl_ms = np.loadtxt(ms_path, comments="#", usecols=(0,1), unpack=True)
            wl_wd, fl_wd = np.loadtxt(wd_path, comments="#", usecols=(0,1), unpack=True)

            obs_wl = data["Wavelength"].values
            interp_ms = np.interp(obs_wl, wl_ms, fl_ms)
            interp_wd = np.interp(obs_wl, wl_wd, fl_wd)
            combined = data["FluxMod"] + scale_wd*interp_wd

            fig, ax = plt.subplots(figsize=(7,4))
            ax.errorbar(obs_wl[fit_mask], data["Flux"][fit_mask],
                        yerr=data["Error"][fit_mask], fmt="o", ms=3, color="black")
            ax.plot(obs_wl, combined, "r-", lw=1, label="Best‑fit")
            ax.set_xscale("log"); ax.set_yscale("log")
            ax.set_xlabel("Wavelength (Å)"); ax.set_ylabel("Flux")
            ax.set_title(obj, fontsize=9)
            ax.legend(fontsize=7)

            fig.savefig(out_dir / f"{obj}_SED.png", dpi=100)
            plt.close(fig); gc.collect()
        except Exception:
            continue