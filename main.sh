#!/usr/bin/env bash
# Resolve absolute path to this script so all subordinate Python calls work
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# ── WDMSpy: Data Processing and Characterisation Tool ────────────────────────
# ── Colours / styles ─────────────────────────────────────────────────────────
RESET="\033[0m"; BOLD="\033[1m"
FG_CYAN="\033[96m"; FG_MAGENTA="\033[95m"
FG_YELLOW="\033[93m"

# ── Text content ─────────────────────────────────────────────────────────────
TITLE=" WDMSTool"
SUB="Data Processing and Characterisation Tool"

# ── Layout parameters ────────────────────────────────────────────────────────
PADDING=2; MARGIN=1
TL='╔'; TR='╗'; BL='╚'; BR='╝'; H='═'; V='║'   # assumes UTF-8 terminal

# ── Width calculation ────────────────────────────────────────────────────────
inner_width=${#TITLE}
(( ${#SUB} > inner_width )) && inner_width=${#SUB}
box_width=$(( inner_width + PADDING*2 ))
hr=$(printf '%*s' "$box_width" | tr ' ' "$H")

# ── Draw static banner -------------------------------------------------------
tput civis
trap 'tput cnorm; printf "\n"; exit' INT TERM

 # Position banner near the top without leaving leading blank lines
top_row=1
tput clear          # clear screen so we start at a clean top
tput cup "$top_row" 0
printf "${FG_MAGENTA}%s%s%s\n" "$TL" "$hr" "$TR"
for _ in $(seq 1 $MARGIN); do printf "${V}%*s${V}\n" "$box_width" ''; done
printf "${V}%*s${BOLD}${FG_CYAN}%s${RESET}${FG_MAGENTA}%*s${V}\n" \
       $(((box_width-${#TITLE})/2)) '' "$TITLE" $(((box_width-${#TITLE}+1)/2)) ''
printf "${V}%*s${FG_YELLOW}%s${RESET}${FG_MAGENTA}%*s${V}\n" \
       $(((box_width-${#SUB})/2))  '' "$SUB"  $(((box_width-${#SUB}+1)/2))  ''
for _ in $(seq 1 $MARGIN); do printf "${V}%*s${V}\n" "$box_width" ''; done
printf "%s%s%s${RESET}\n" "$BL" "$hr" "$BR"

# ── Main script logic --------------------------------------------------------
while true; do
    echo
    echo "Choose an operation to perform:"
    echo "1. Interactive CMD viewer"
    echo "2. Generate VOSA ASCII for MS (no-UV)"
    echo "3. MS data processing pipeline"
    echo "4. Generate VOSA ASCII for WD"
    echo "5. WD‑MS data processing pipeline"
    echo "6. Exit"

    read -p "Enter your choice [1-6]: " choice

    case $choice in
        1)
            echo "You chose: Interactive CMD viewer"
            read -p "Enter CSV data file path: " csv_file
            python3 "$SCRIPT_DIR/Scripts/Interactive_CMD.py" "$csv_file"
            ;;
        2)
            echo "You chose: Generate VOSA ASCII for MS (no-UV)"
            read -p "Enter merged catalog path: " catalog
            read -p "Enter output directory: " outdir
            read -p "Chunk size (objects per file) [default 1000]: " chunk
            chunk=${chunk:-1000}
            python3 "$SCRIPT_DIR/Scripts/ms_ascii_noUV_vosa.py" "$catalog" "$outdir" --chunk "$chunk"
            ;;
        3)
            echo "You chose: MS data processing pipeline"
            python3 "$SCRIPT_DIR/Scripts/ms_data_process.py"
            ;;
        4)
            echo "You chose: Generate VOSA ASCII for WD"
            read -p "Path to ms_process result_dir: " result_dir
            read -p "Generate for (g)ood, (b)ad, or (a)ll candidates? [g/b/a]: " which
            read -p "Output directory (leave blank for default): " vd_out
            read -p "Chunk size (objects per file) [default 1000]: " wd_chunk
            wd_chunk=${wd_chunk:-1000}
            python3 "$SCRIPT_DIR/Scripts/wd_ascii_vosa.py" "$result_dir" --which "$which" --out "$vd_out" --chunk "$wd_chunk"
            ;;
        5)
            echo "You chose: WD‑MS data processing pipeline"
            read -p "Path to WD objects folder: " wd_obj
            read -p "Parent spectra folder (bt-nextgen-agss2009 & koester2): " spec_parent
            read -p "Path to MS gc/bc folder (has bestfitp.csv): " ms_folder
            read -p "Custom result_dir (leave blank for default): " custom_res
            if [[ -z "$custom_res" ]]; then
                python3 "$SCRIPT_DIR/Scripts/wdms_data_process.py" \
                        "$wd_obj" "$spec_parent" "$ms_folder"
            else
                python3 "$SCRIPT_DIR/Scripts/wdms_data_process.py" \
                        "$wd_obj" "$spec_parent" "$ms_folder" "$custom_res"
            fi
            ;;
        6)
            echo "Exiting..."
            tput cnorm
            exit 0
            ;;
        *)
            echo "Invalid choice. Try again."
            ;;
    esac
done

tput cnorm