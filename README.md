# WDMSTool
**WDMSTool** is a modular and user-friendly command-line toolkit for the processing and characterisation of **White Dwarf–Main Sequence (WD–MS)** binary systems using multi-wavelength photometric data. It is designed to support pipeline development for candidate identification, VOSA ASCII generation, and SED model comparison with theoretical spectra.

---

## 📦 Features

- 📊 **Interactive CMD Viewer**  
  View Gaia CMD interactively from CSV catalogs.

- ⚙️ **MS Data Processing Pipeline**  
  - Cleans `.bfit.phot.dat` and `bestfitp.dat` files.  
  - Filters WD-MS candidates based on residuals and Vgfb metrics.  
  - Categorises objects into **Good** and **Bad** candidates.

- 📝 **Generate VOSA ASCII for MS**  
  Formats MS photometry into `.txt` files (excluding UV bands) suitable for **VOSA** SED fitting.

- 📝 **Generate VOSA ASCII for WD**  
  Converts processed WD data into VOSA-compatible format.

- 🔀 **WD–MS Data Processing Pipeline**  
  - Processes `.bfit.phot.dat` and `bestfitp.dat` files for WD.  
  - Cleans theoretical spectra files (Koester and BT-Settl).  
  - Merges WD and MS bestfit data.  
  - Plots combined SEDs with scaling and saves images per candidate.

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/WDMSTool.git
cd WDMSTool 
```

### 2. Make the Script Executable

```bash
chmod +x setup.sh
./setup.sh
```

✅ The setup.sh script automatically checks and installs these dependencies if not already available. 

### 3. Run the Tool

```bash
wdmstool
```

You will see a list of options like this 👇 
```
Choose an operation to perform:
1. Interactive CMD viewer
2. Generate VOSA ASCII for MS (no-UV)
3. MS data processing pipeline
4. Generate VOSA ASCII for WD
5. WD–MS data processing pipeline
6. Exit
```


