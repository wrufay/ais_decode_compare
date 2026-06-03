# Commands Reference

All commands were run from the repo root:
`/home/fwu/Desktop/projects/ais_decode_compare/`

The Python virtual environment is at `.venv/` and must be used for all scripts.

---

## 1. Set up the environment

```bash
# Create virtual environment
python3 -m venv .venv

# Install all required packages
.venv/bin/pip install aisdb netCDF4 numpy pandas matplotlib
```

**Why:** The scripts depend on `aisdb` (AIS decoding library), `netCDF4` (reading .nc files from the original decoder), `pandas` and `matplotlib` (analysis and plotting).

---

## 2. Create output directories

```bash
mkdir -p data/original/nm4 data/original/streaming data/original/nm4_raw data/aisdb data/plots
```

---

## 3. Run the AISDB decoder

```bash
# Decode the NM4 zip files (288 x 5-minute chunks)
.venv/bin/python decode_aisdb.py nm4
# Output: data/decode_nm4.db (~17GB, took ~5.5 hours on SQLite)

# Decode the full-day streaming CSV
.venv/bin/python decode_aisdb.py streaming
# Output: data/decode_streaming.db (~1.1GB, took ~6 minutes)
```

**Why:** `decode_aisdb.py` uses the `aisdb` library (Rust-based NMEA parser) to decode raw AIS messages into a SQLite database. The NM4 source contains raw per-station data (~140M messages across 288 files), while streaming is a pre-aggregated single file (~18M messages). Note: we used SQLite which is slow for large datasets — PostgreSQL would be significantly faster.

---

## 4. Extract NM4 files for the original decoder

```bash
.venv/bin/python prepare_nm4.py
# Output: data/original/nm4_raw/ — 288 x .csv files
```

**Why:** The original decoder (`Process_AIS_Serial.py`) only handles `.csv` and `.txt` file extensions. The NM4 source files are `.nmea.zip` archives. `prepare_nm4.py` extracts and renames them to `.csv` (the format is identical, just the extension differs).

---

## 5. Run the original decoder

```bash
# Decode the streaming source
PYTHONPATH=/home/fwu/Desktop/projects/ais_decode_compare:/home/fwu/Desktop/projects/ais_decode_compare/decode_original \
  .venv/bin/python decode_original/Process_AIS_Serial.py \
  /home/shared/ccg_ais_claudio/ais_comp/streaming \
  data/original/streaming \
  CCG_AIS_UTC_Log
# Output: data/original/streaming/Dynamic_CCG_AIS_UTC_Log_2025-12-30.nc
#         data/original/streaming/Static_CCG_AIS_UTC_Log_2025-12-30.nc

# Decode the NM4 source (all 288 files)
PYTHONPATH=/home/fwu/Desktop/projects/ais_decode_compare:/home/fwu/Desktop/projects/ais_decode_compare/decode_original \
  .venv/bin/python decode_original/Process_AIS_Serial.py \
  data/original/nm4_raw \
  data/original/nm4 \
  ais-2025-12-30
# Output: data/original/nm4/Dynamic_ais-2025-12-30-*.nc (288 files)
#         data/original/nm4/Static_ais-2025-12-30-*.nc  (288 files)
```

**Why:** `PYTHONPATH` must include both the repo root and the `decode_original/` directory because the script uses relative imports (`from Second_layer_NMEA import *`) which expect the helper modules to be findable on the Python path. The third argument (`CCG_AIS_UTC_Log` / `ais-2025-12-30`) is a substring filter — only files whose names contain it are processed. Note: we used the serial version; `Process_AIS_Parallel.py` (using Ray) would process all 288 files in ~2 minutes using multiple CPUs.

---

## 6. Run the comparison

```bash
.venv/bin/python -u compare.py
# Output: data/comparison_table.csv
#         data/plots/routes_00h-03h.png
#         data/plots/routes_21h-24h.png
```

**Why:** `compare.py` loads all five sources (original NM4, original streaming, aisdb NM4, aisdb streaming, reference CSV), filters to two 3-hour UTC windows (00:00–03:00 and 21:00–24:00), and produces a comparison table and scatter plots. The `-u` flag forces unbuffered output so progress prints immediately. Memory-efficient: loads and frees one source at a time.

**Runtime:** ~7 minutes.

---

## 7. Run the validation

```bash
.venv/bin/python -u validate.py
# Output: data/validation/mmsi_overlap.csv
#         data/validation/coord_agreement.csv
#         data/validation/temporal_coverage.csv
#         data/validation/top_vessels.csv
#         data/validation/missing_from_aisdb_vs_original.csv
#         data/validation/missing_from_aisdb_vs_reference.csv
#         data/validation/missing_from_reference_vs_original.csv
#         data/validation/plots/ (heatmap, tracks, error distribution, etc.)
```

**Why:** `validate.py` goes deeper than `compare.py` — it computes pairwise MMSI set overlap (Jaccard similarity), coordinate agreement between matched vessels, vessel track plots for spot-checking, temporal coverage per hour, and a breakdown of which vessel types aisdb misses vs the original decoder.

**Runtime:** ~15 minutes.

---

## Key notes

- All decoding was run with `nohup ... &` to keep jobs running if the terminal closed
- The aisdb NM4 decode took ~5.5 hours due to SQLite I/O overhead on a 17GB database — using PostgreSQL or running on HPC would reduce this significantly
- The original decoder serial run took ~2 hours — the parallel version (`Process_AIS_Parallel.py`) would take ~2 minutes
- All timestamps are UTC throughout
- Data source: `/home/shared/ccg_ais_claudio/ais_comp/` (read-only, not modified)
