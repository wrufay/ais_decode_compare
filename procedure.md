# AIS Decoder Comparison — Procedure

## Overview

We compare two AIS decoders against each other and against pre-decoded reference data, using a single day of data (2025-12-30).

| Decoder | Script | Output format |
|---|---|---|
| Original | `decode_original/Process_AIS_Serial.py` | NetCDF (`.nc`) — one Dynamic + one Static file per input file |
| AISDB | `decode_aisdb.py` | SQLite (`.db`) — one database per source |

**Data sources** at `/home/shared/ccg_ais_claudio/ais_comp/`:

| Directory | Format | Contents |
|---|---|---|
| `NM4/` | 288 × `.nmea.zip` | Raw NMEA, 5-min chunks |
| `streaming/` | 1 × `.csv` | Raw NMEA, full day accumulation |
| `csv/` | 288 × `.csv.zip` | Pre-decoded tabular data (reference ground truth) |

---

## Step 1 — Verify environment and dependencies

Check that the required Python packages are available:

```bash
python -c "import aisdb; print('aisdb ok')"
python -c "import netCDF4; print('netCDF4 ok')"
python -c "import numpy, pandas, matplotlib; print('numpy/pandas/matplotlib ok')"
```

Install anything missing via `pip install <package>`.

Create the output directory structure inside this repo:

```
data/
  original/
    nm4/        ← Dynamic_*.nc and Static_*.nc from original decoder on NM4 data
    streaming/  ← Dynamic_*.nc and Static_*.nc from original decoder on streaming data
  aisdb/        ← decode_nm4.db and decode_streaming.db from aisdb decoder
  plots/        ← comparison figures
```

```bash
mkdir -p data/original/nm4 data/original/streaming data/aisdb data/plots
```

---

## Step 2 — Run the AISDB decoder

The AISDB decoder (`decode_aisdb.py`) handles both sources natively.

**NM4 source** — extracts all 288 `.nmea.zip` files into a temp dir and decodes them in one batch:

```bash
python decode_aisdb.py nm4
# Output: data/aisdb/decode_nm4.db
```

**Streaming source** — creates a `.nm4` symlink to trick aisdb into treating the `.csv` file as raw NMEA:

```bash
python decode_aisdb.py streaming
# Output: data/aisdb/decode_streaming.db
```

---

## Step 3 — Run the original decoder

The original decoder (`decode_original/Process_AIS_Serial.py`) must be run with `decode_original/` on the Python path because it uses relative imports (`from Second_layer_NMEA import *`, etc.).

Usage: `python Process_AIS_Serial.py <input_dir> <output_dir> <part_str>`

- `part_str` is a substring filter — only files whose name contains it are processed.

**Streaming source** — the streaming file (`CCG_AIS_UTC_Log_2025-12-30.csv`) ends in `.csv` so it is handled directly:

```bash
cd decode_original
python Process_AIS_Serial.py \
    /home/shared/ccg_ais_claudio/ais_comp/streaming \
    ../data/original/streaming \
    CCG_AIS_UTC_Log
cd ..
# Output: data/original/streaming/Dynamic_CCG_AIS_UTC_Log_2025-12-30.nc
#         data/original/streaming/Static_CCG_AIS_UTC_Log_2025-12-30.nc
```

**NM4 source** — the 288 `.nmea.zip` files need to be extracted and renamed to `.csv` first, because the original decoder only handles `.txt` and `.csv` extensions, and the NM4 format (`\s:...\!AIVDM,...`) is identical to the streaming CSV format.

Write a small helper script `prepare_nm4.py` to extract and rename:

```python
# prepare_nm4.py
import glob, os, zipfile
from pathlib import Path

NM4_DIR = "/home/shared/ccg_ais_claudio/ais_comp/NM4"
OUT_DIR = "data/original/nm4_raw"
os.makedirs(OUT_DIR, exist_ok=True)

for zip_path in sorted(glob.glob(f"{NM4_DIR}/*.nmea.zip")):
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            data = zf.read(name)
            # rename .nmea → .csv so the original decoder picks it up
            out_name = Path(name).stem + ".csv"
            with open(f"{OUT_DIR}/{out_name}", "wb") as f:
                f.write(data)
print("Done.")
```

```bash
python prepare_nm4.py
# produces data/original/nm4_raw/ais-2025-12-30-00-00.csv ... (288 files)
```

Then run the original decoder on the extracted files (use `ais-2025-12-30` as part_str to match all of them):

```bash
cd decode_original
python Process_AIS_Serial.py \
    ../data/original/nm4_raw \
    ../data/original/nm4 \
    ais-2025-12-30
cd ..
# Output: data/original/nm4/Dynamic_ais-2025-12-30-*.nc (288 files)
#         data/original/nm4/Static_ais-2025-12-30-*.nc  (288 files)
```

> Note: `Process_AIS_Parallel.py` is not used here because it hardcodes paths and depends on `ray`; the serial version is cleaner and sufficient for comparison.

---

## Step 4 — Parse the reference CSV data

The pre-decoded CSVs in `csv/` are tabular (columns: mmsi, message_type, latitude, longitude, speed, course, …) and serve as the ground-truth reference.

They don't need a decoder — they are loaded directly in the comparison script (Step 5).

---

## Step 5 — Build the comparison script

### Time-window strategy

Before comparing the full day, start with two 3-hour UTC windows to keep the data volume manageable and spot issues quickly:

| Window | UTC time | Unix epoch (seconds) |
|---|---|---|
| Early morning | 00:00 – 03:00 | 1767052800 – 1767063600 |
| Late evening  | 21:00 – 24:00 | 1767128400 – 1767139200 |

All timestamps are UTC. Apply the window filter when loading each source. If the windowed results look consistent, re-run on the full day.

Timestamp column per source:

| Source | Column | Type | Notes |
|---|---|---|---|
| Original `.nc` | `date_num` | Unix epoch int | Filter directly against epoch bounds |
| aisdb SQLite | `time` | Unix epoch int | Filter directly against epoch bounds |
| Reference CSV | `reception_timestamp` | Datetime string (`2025-12-30 HH:MM:SS`) | Parse with `pd.to_datetime`, then compare; **do not use `ais_seconds`** — that field is the second-of-minute from the AIS message payload (0–59), not a Unix timestamp |

---

Write `compare.py` at the repo root. It reads all four decoder outputs plus the reference CSVs and produces:

1. **A comparison table** (printed and saved as `data/comparison_table.csv`) with:
   - Source name
   - Time window applied
   - Number of records in window
   - Number of unique MMSI (vessels)
   - Lat/lon bounding box (min/max)

2. **Route plots** saved to `data/plots/`:
   - One scatter/map plot per source per window
   - A side-by-side or overlaid plot comparing all five sources

### Inputs the script must read

| Label | How to read |
|---|---|
| `original_nm4` | Glob `data/original/nm4/Dynamic_*.nc`, combine `mmsi`, `date_num`, `longitude`, `latitude` across all files using `netCDF4` |
| `original_streaming` | Read `data/original/streaming/Dynamic_CCG_AIS_UTC_Log_2025-12-30.nc` |
| `aisdb_nm4` | Query `data/aisdb/decode_nm4.db` — table is `ais_202512_dynamic` (aisdb names tables `ais_YYYYMM_dynamic`); extract `mmsi`, `time`, `lon`, `lat` |
| `aisdb_streaming` | Query `data/aisdb/decode_streaming.db` — same table naming convention |
| `reference_csv` | Unzip and read all `csv/*.csv.zip`; filter on `reception_timestamp` (parse as datetime); columns include `mmsi`, `latitude`, `longitude` |

### Outline of compare.py

```python
import glob, zipfile, io
import sqlite3
import netCDF4
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# UTC epoch bounds for the two 3-hour windows (2025-12-30)
WINDOWS = {
    "00h-03h": (1767052800, 1767063600),
    "21h-24h": (1767128400, 1767139200),
}

# --- Load helpers ---

def load_original_nc(pattern):
    """Read all Dynamic *.nc files matching pattern, return DataFrame with columns mmsi/ts/lat/lon."""
    ...

def load_aisdb(db_path):
    """Query SQLite DB for mmsi/ts/lat/lon, return DataFrame.
    aisdb names tables ais_YYYYMM_dynamic — discover the name at runtime:
        con = sqlite3.connect(db_path)
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        dyn_table = next(t for t in tables if t.endswith('_dynamic'))
    """
    ...

def load_reference_csv(csv_dir):
    """Unzip and concatenate all reference CSVs, return DataFrame with mmsi/ts/lat/lon.
    Time filter uses reception_timestamp (datetime string), NOT ais_seconds
    (ais_seconds is the AIS payload second-of-minute field, not a Unix timestamp).
    Parse with pd.to_datetime(df['reception_timestamp'], utc=True) then convert to epoch.
    """
    ...

def apply_window(df, ts_col, t_start, t_end):
    return df[(df[ts_col] >= t_start) & (df[ts_col] < t_end)]

# --- Load all sources (full day) ---
sources = {
    "original_nm4":       load_original_nc("data/original/nm4/Dynamic_*.nc"),
    "original_streaming": load_original_nc("data/original/streaming/Dynamic_*.nc"),
    "aisdb_nm4":          load_aisdb("data/aisdb/decode_nm4.db"),
    "aisdb_streaming":    load_aisdb("data/aisdb/decode_streaming.db"),
    "reference_csv":      load_reference_csv("/home/shared/ccg_ais_claudio/ais_comp/csv"),
}

# --- Comparison table (per window) ---
rows = []
for win_name, (t0, t1) in WINDOWS.items():
    for src_name, df in sources.items():
        ts_col = "ts"   # normalise timestamp column name in load helpers
        subset = apply_window(df, ts_col, t0, t1)
        rows.append({
            "window":         win_name,
            "source":         src_name,
            "total_messages": len(subset),
            "unique_mmsi":    subset["mmsi"].nunique(),
            "lat_min":        subset["lat"].min(),
            "lat_max":        subset["lat"].max(),
            "lon_min":        subset["lon"].min(),
            "lon_max":        subset["lon"].max(),
        })

table = pd.DataFrame(rows)
print(table.to_string(index=False))
table.to_csv("data/comparison_table.csv", index=False)

# --- Route plots (one figure per window) ---
for win_name, (t0, t1) in WINDOWS.items():
    fig, axes = plt.subplots(1, len(sources), figsize=(20, 4))
    for ax, (src_name, df) in zip(axes, sources.items()):
        subset = apply_window(df, "ts", t0, t1)
        ax.scatter(subset["lon"], subset["lat"], s=0.3, alpha=0.4)
        ax.set_title(f"{src_name}\n{subset['mmsi'].nunique()} vessels")
        ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    fig.suptitle(f"Routes — {win_name} UTC")
    plt.tight_layout()
    plt.savefig(f"data/plots/routes_{win_name}.png", dpi=150)
    plt.close()
```

Run the script:

```bash
python compare.py
```

---

## Step 6 — Review results

Open `data/comparison_table.csv` and the plots in `data/plots/` (`routes_00h-03h.png`, `routes_21h-24h.png`).

Key things to check:
- Do the two decoders (original vs aisdb) produce the same unique MMSI count for the same source (NM4 or streaming) within each time window?
- Do NM4 and streaming produce the same counts for the same window (they contain the same day's data)?
- How do both decoders compare to the pre-decoded reference CSV for each window?
- Are there systematic lat/lon differences (e.g., missing regions) between decoders?
- Are the early-morning and late-evening windows consistent with each other, or do one of the decoders show drop-off at day boundaries?

If the windowed results look good and consistent, re-run `compare.py` without the window filter to validate the full day.

---

## File structure after all steps

```
ais_decode_compare/
├── decode_aisdb.py
├── decode_original/
│   ├── Process_AIS_Serial.py
│   └── ... (helper modules)
├── prepare_nm4.py          ← new helper to extract/rename NM4 zips
├── compare.py              ← new comparison + plotting script
├── procedure.md            ← this file
└── data/
    ├── original/
    │   ├── nm4_raw/        ← 288 extracted .csv files (intermediate)
    │   ├── nm4/            ← 288 × Dynamic_*.nc + Static_*.nc
    │   └── streaming/      ← Dynamic_*.nc + Static_*.nc
    ├── aisdb/
    │   ├── decode_nm4.db
    │   └── decode_streaming.db
    ├── comparison_table.csv   ← rows per source × window
    └── plots/
        ├── routes_00h-03h.png  ← 00:00–03:00 UTC
        └── routes_21h-24h.png  ← 21:00–24:00 UTC
```
