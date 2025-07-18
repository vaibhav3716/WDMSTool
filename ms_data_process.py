#!/usr/bin/env python3

import os
import glob
import warnings
warnings.filterwarnings("ignore")  # suppress all warnings

from tqdm import tqdm

def process_phot_files(base_path):
    print("\n--- Processing .bfit.phot.dat files ---")
    file_pattern = os.path.join(base_path, "**/objects/*/bestfitp/*.bfit.phot.dat")
    files = glob.glob(file_pattern, recursive=True)

    for file_path in tqdm(files, desc="Processing photometric files", unit="file"):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            if len(lines) >= 41:
                lines[40] = lines[40].lstrip('#')
                with open(file_path, 'w') as f:
                    f.writelines(lines)
                # print(f"[✓] Updated: {file_path}")
            else:
                # print(f"[!] Skipped (not enough lines): {file_path}")
                pass
        except Exception as e:
            # print(f"[✗] Error processing {file_path}: {e}")
            pass

def process_bestfit_dat(base_path):
    print("\n--- Processing bestfitp.dat files ---")
    file_pattern = os.path.join(base_path, "**/results/bestfitp.dat")
    files = glob.glob(file_pattern, recursive=True)

    for file_path in tqdm(files, desc="Processing results files", unit="file"):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            if len(lines) >= 3:
                clean_line = lines[2].lstrip('#').replace('(pc)', '')
                clean_line = clean_line.replace("Object", "      Object").replace("D", "      D", 1)
                lines[2] = clean_line
                with open(file_path, 'w') as f:
                    f.writelines(lines)
                # print(f"[✓] Updated: {file_path}")
            else:
                # print(f"[!] Skipped (not enough lines): {file_path}")
                pass
        except Exception as e:
            # print(f"[✗] Error processing {file_path}: {e}")
            pass


import shutil
import time
import numpy as np
import pandas as pd

def evaluate_candidates(base_dir, result_dir=None):
    ms_object_glob = os.path.join(base_dir, "**/objects/*/bestfitp/*.bfit.phot.dat")
    phot_files = glob.glob(ms_object_glob, recursive=True)

    # --- 1️⃣ First pass: classify without copying ---------------------------
    classification = []          # list of (obj_folder, is_good, row)
    results_path = glob.glob(os.path.join(base_dir, "**/results/bestfitp.dat"),
                             recursive=True)[0]
    results_df = pd.read_csv(results_path, comment="#", sep=r"\s+")

    for file_path in phot_files:
        data = pd.read_csv(file_path, comment="#", sep=r"\s+")
        obj      = os.path.basename(file_path).split(".bfit.phot.dat")[0]
        obj_dir  = os.path.abspath(os.path.join(file_path, "../../"))

        # --- residual + Vgfb tests (same logic) ---
        data["Flux"]     = pd.to_numeric(data["Flux"], errors="coerce")
        data["FluxMod"]  = pd.to_numeric(data["FluxMod"], errors="coerce")
        data["FitExc"]   = data["FitExc"].replace("---", 0).astype(int)
        data.loc[:1, "Residual"] = (data.loc[:1, "Flux"]-data.loc[:1,"FluxMod"])/data.loc[:1,"Flux"]
        data.loc[2:, "Residual"] = np.where((data.loc[2:, "Fitted"]==1)&
                                            (data.loc[2:, "FitExc"]==0),
             (data.loc[2:, "Flux"]-data.loc[2:, "FluxMod"])/data.loc[2:, "Flux"], np.nan)
        std  = np.std(data["Residual"][2:].dropna())
        good = all(data.loc[0:1, "Residual"] >= 3*std)
        row  = results_df[results_df["Object"]==obj]
        try:
            vgfb_value = float(row.iloc[0]["Vgfb"])
            # New rule: good candidate requires Vgfb < 15
            if vgfb_value >= 15:
                good = False
        except (ValueError, TypeError):
            good = False
        except IndexError:
            # row may be empty, so IndexError can occur
            good = False
        classification.append((obj_dir, good, row))

    good_count = sum(g for _, g, _ in classification)
    bad_count  = len(classification) - good_count

    # --- 2️⃣ Prepare result directories ------------------------------------
    if not result_dir:
        # Create result_dir *inside* the supplied data folder
        result_dir = os.path.join(base_dir, "result_dir")
        os.makedirs(result_dir, exist_ok=True)

    gc_dir     = os.path.join(result_dir, f"{good_count}_gc")
    bc_dir     = os.path.join(result_dir, f"{bad_count}_bc")
    gc_obj_dir = os.path.join(gc_dir, "objects")
    bc_obj_dir = os.path.join(bc_dir, "objects")
    for d in (gc_obj_dir, bc_obj_dir): os.makedirs(d, exist_ok=True)

    # --- 3️⃣ Copy folders & accumulate rows ---------------------------------
    good_rows, bad_rows = [], []
    for obj_dir, is_good, row in classification:
        dest = gc_obj_dir if is_good else bc_obj_dir
        if not os.path.exists(os.path.join(dest, os.path.basename(obj_dir))):
            shutil.copytree(obj_dir, os.path.join(dest, os.path.basename(obj_dir)))
        (good_rows if is_good else bad_rows).append(row)

    if good_rows:
        pd.concat(good_rows).to_csv(os.path.join(gc_dir, "gc_bestfitp.csv"), index=False)
    if bad_rows:
        pd.concat(bad_rows).to_csv(os.path.join(bc_dir, "bc_bestfitp.csv"), index=False)

    # --- 4️⃣ Plot -----------------------------------------------------------
    print("\n--- Generating SED plots ---")

    if os.listdir(gc_obj_dir):
        print("Generating SEDs for GOOD candidates...")
        plot_flux_res(gc_obj_dir, os.path.join(gc_dir, "Plots"))

    if os.listdir(bc_obj_dir):
        print("Generating SEDs for BAD candidates...")
        plot_flux_res(bc_obj_dir, os.path.join(bc_dir, "Plots"))

    print(f"✅ Plots saved.  Good candidates: {good_count}, Bad candidates: {bad_count}")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

def plot_flux_res(objects_dir, plots_dir):
    os.makedirs(plots_dir, exist_ok=True)
    phot_glob = os.path.join(objects_dir, "*/bestfitp/*.bfit.phot.dat")
    files = glob.glob(phot_glob)

    for file_path in tqdm(files, desc="Generating plots", unit="plot"):
        try:
            data = pd.read_csv(file_path, comment="#", sep=r"\s+")

            data["Flux"] = pd.to_numeric(data["Flux"], errors='coerce')
            data["FluxMod"] = pd.to_numeric(data["FluxMod"], errors='coerce')
            data["FitExc"] = data["FitExc"].replace("---", 0).astype(int)
            data["UpLim"] = data["UpLim"].replace("---", 0).astype(int)

            data.loc[:1, 'Residual'] = (data.loc[:1, 'Flux'] - data.loc[:1, 'FluxMod']) / data.loc[:1, 'Flux']
            data.loc[2:, 'Residual'] = np.where(
                (data.loc[2:, 'Fitted'] == 1) &
                (data.loc[2:, 'Excess'] == 0) &
                (data.loc[2:, 'UpLim'] == 0) &
                (data.loc[2:, 'FitExc'] == 0),
                (data.loc[2:, 'Flux'] - data.loc[2:, 'FluxMod']) / data.loc[2:, 'Flux'],
                np.nan
            )

            object_name = os.path.basename(file_path).split(".bfit.phot.dat")[0].replace("_", "-")
            residuals = data['Residual']
            std_res = np.std(residuals[2:].dropna())

            mean_res = 0
            two_sigma_pos = mean_res + 2 * std_res
            two_sigma_neg = mean_res - 2 * std_res
            three_sigma_pos = mean_res + 3 * std_res
            three_sigma_neg = mean_res - 3 * std_res

            flux_err = data["Error"] if "Error" in data else np.zeros_like(data["Flux"])

            fig, ax = plt.subplots(2, 1, figsize=(8, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

            priority = np.full(len(data), 'none', dtype=object)
            priority[data["UpLim"] == 1] = 'uplim'
            priority[(data["FitExc"] == 1) & (priority == 'none')] = 'excess'
            priority[(data["Fitted"] == 0) & (priority == 'none')] = 'nofit'
            priority[(data["Fitted"] == 1) & (priority == 'none')] = 'fit'

            uplim_mask = priority == 'uplim'
            excess_mask = priority == 'excess'
            nofit_mask = priority == 'nofit'
            fit_mask = priority == 'fit'

            def get_group_color(f):
                if f.startswith("GALEX"):
                    return "#e41a1c"
                elif f.startswith("GAIA"):
                    return "#377eb8"
                elif f.startswith("SLOAN") or f.startswith("Misc"):
                    return "#4daf4a"
                elif f.startswith("2MASS"):
                    return "#984ea3"
                elif f.startswith("WISE"):
                    return "#ff7f00"
                else:
                    return "#999999"

            ax[0].scatter(data["Wavelength"][uplim_mask], data["Flux"][uplim_mask], color='black', s=60, marker='^', label="Upper Limit")
            ax[0].scatter(data["Wavelength"][excess_mask], data["Flux"][excess_mask], color='black', marker='o', s=20, label="Excess")
            ax[0].scatter(data["Wavelength"][nofit_mask], data["Flux"][nofit_mask], color='red', marker='o', s=20, label="No Fit")

            filter_list = data["FilterID"]
            fit_colors = [get_group_color(f) for f in filter_list[fit_mask]]

            ax[0].errorbar(data["Wavelength"][fit_mask], data["Flux"][fit_mask], yerr=data["Error"][fit_mask],
                           fmt='o', color='none', ecolor='black', elinewidth=0.7, capsize=2, markersize=4)

            for i, idx in enumerate(np.where(fit_mask)[0]):
                ax[0].scatter(data["Wavelength"][idx], data["Flux"][idx], color=fit_colors[i], s=30)

            ax[0].plot(data["Wavelength"], data["FluxMod"], color='tab:orange', linewidth=1.2, label='MS Fit Model')

            ax[0].set_ylabel(r"Flux (erg/cm$^2$/s/Å)", fontsize=11)
            ax[0].set_yscale("log")
            ax[0].legend(fontsize=9, loc="upper right", frameon=False)
            ax[0].grid(True, which='both', linestyle=':', linewidth=0.5)
            ax[0].tick_params(axis='both', which='major', labelsize=9)

            group_legend_handles = [
                Line2D([0], [0], marker='o', color='none', label='GAIA', markerfacecolor='#377eb8', markersize=6),
                Line2D([0], [0], marker='o', color='none', label='APASS', markerfacecolor='#4daf4a', markersize=6),
                Line2D([0], [0], marker='o', color='none', label='2MASS', markerfacecolor='#984ea3', markersize=6),
                Line2D([0], [0], marker='o', color='none', label='ALLWISE', markerfacecolor='#ff7f00', markersize=6),
                Line2D([0], [0], marker='o', color='none', label='PanSTARRS', markerfacecolor='#999999', markersize=6)
            ]
            ax[0].legend(handles=group_legend_handles, title="Fitted Flux by Telescope", fontsize=8, title_fontsize=9, loc='lower center', frameon=False)

            for i in range(len(data)):
                color = 'red' if priority[i] == 'nofit' else ('black' if priority[i] in ('uplim', 'excess') else get_group_color(data["FilterID"].iloc[i]))
                ax[1].errorbar(data["Wavelength"].iloc[i], residuals.iloc[i], yerr=data["Error"].iloc[i],
                               fmt='o', color=color, ecolor=color, elinewidth=0.8, capsize=3, markersize=4)

            ax[1].axhline(mean_res, color='blue', linestyle='-', linewidth=1.0, label=r"$\mu$")
            ax[1].axhline(two_sigma_pos, color='green', linestyle='--', linewidth=1.0, label=r"$2\sigma$")
            ax[1].axhline(two_sigma_neg, color='green', linestyle='--', linewidth=1.0)
            ax[1].axhline(three_sigma_pos, color='red', linestyle=':', linewidth=1.0, label=r"$3\sigma$")
            ax[1].axhline(three_sigma_neg, color='red', linestyle=':', linewidth=1.0)

            ax[1].set_xscale("log")
            ax[1].set_ylim(-2, 2)
            ax[1].set_xlabel(r"Wavelength", fontsize=11)
            ax[1].set_ylabel(r"$\frac{F_{\lambda} - F_{\mathrm{model}}}{F_{\lambda}}$", fontsize=11)
            ax[1].legend(fontsize=9, loc="best", frameon=False)
            ax[1].grid(True, which='both', linestyle=':', linewidth=0.5)
            ax[1].tick_params(axis='both', which='major', labelsize=9)

            fig.suptitle(object_name, fontsize=12, y=0.98)
            plt.tight_layout(h_pad=0.3, rect=[0, 0, 1, 0.97])
            plt.subplots_adjust(top=0.94)
            png_path = os.path.join(plots_dir, f"{object_name}_p.png")
            fig.savefig(png_path, dpi=150, bbox_inches='tight')
            plt.close(fig)

        except Exception as e:
            print(f"[✗] Error plotting {file_path}: {e}")

def main():
    base_path = input("Enter the base directory for raw data: ").strip()
    if not os.path.isdir(base_path):
        print(f"Invalid directory: {base_path}")
        return

    print(f"Enter result directory (leave blank to use a 'result_dir' folder inside the raw data directory: {base_path})")
    result_dir = input("Result directory: ").strip()
    if not result_dir:
        result_dir = os.path.join(base_path, "result_dir")
    os.makedirs(result_dir, exist_ok=True)

    process_phot_files(base_path)
    process_bestfit_dat(base_path)
    print("\n✅ Success. ")
    print("Evaluating candidates &  Generating SED plots 📉 ......")
    print()
    print("This may take a while... ⏳\nPerfect time to grab a coffee ☕️ or stretch your legs 🏃.")

    evaluate_candidates(base_path, result_dir)

if __name__ == "__main__":
    main()