# Procedure

This document describes what was done, in order, to compare the two AIS decoders.
For the exact commands used at each step, see `commands.md`.

---

## Overview

Two AIS decoders were run on the same raw data and their outputs compared against pre-decoded reference data.

| Decoder | Script | Output |
|---|---|---|
| Original | `decode_original/Process_AIS_Serial.py` | NetCDF `.nc` files — one Dynamic + one Static per input file |
| aisdb | `decode_aisdb.py` | SQLite `.db` — one database per source |

**Data sources** at `/home/shared/ccg_ais_claudio/ais_comp/` (read-only):

| Directory | Format | Contents |
|---|---|---|
| `NM4/` | 288 × `.nmea.zip` | Raw NMEA, 5-minute chunks |
| `streaming/` | 1 × `.csv` | Raw NMEA, full day accumulation |
| `csv/` | 288 × `.csv.zip` | Pre-decoded tabular data (reference) |

---

## Step 1 — Environment setup

Created a Python virtual environment at `.venv/` and installed:
- `aisdb` — AIS decoding library (Rust-based parser + SQLite output)
- `netCDF4` — reading `.nc` files from the original decoder
- `numpy`, `pandas`, `matplotlib` — analysis and plotting

---

## Step 2 — Run the aisdb decoder

`decode_aisdb.py` was run on both sources:

- **NM4:** extracts all 288 `.nmea.zip` files to a temp directory and decodes in one batch → `data/decode_nm4.db` (~17GB, ~5.5 hours on SQLite)
- **Streaming:** creates a `.nm4` symlink so aisdb treats the `.csv` file as raw NMEA → `data/decode_streaming.db` (~1.1GB, ~6 minutes)

**Why the NM4 decode took so long:** SQLite performance degrades as the database grows. Decode rate dropped from ~76k msgs/s at the start to ~43k msgs/s by file 3 as the DB reached 17GB. Using PostgreSQL would avoid this. This was the serial, SQLite configuration — the production configuration uses PostgreSQL on HPC.

---

## Step 3 — Run the original decoder

The original decoder (`Process_AIS_Serial.py`) only handles `.csv` and `.txt` extensions. The NM4 files are `.nmea.zip` archives, so a helper script (`prepare_nm4.py`) was written to extract and rename them to `.csv` first (content is identical, only the extension changes).

Both sources were decoded using the **serial version** (`Process_AIS_Serial.py`). The parallel version (`Process_AIS_Parallel.py`, using Ray) was not used because it has hardcoded paths and an unfixed bug. The serial version took ~2 hours for NM4 (288 files) and ~30 minutes for streaming.

Output:
- `data/original/nm4/` — 288 × Dynamic + 288 × Static `.nc` files
- `data/original/streaming/` — 1 Dynamic + 1 Static `.nc` file

---

## Step 4 — Compare outputs

`analysis/compare.py` loads all five sources and compares them across two 3-hour UTC time windows:
- **00:00–03:00 UTC** (epoch 1767052800–1767063600)
- **21:00–24:00 UTC** (epoch 1767128400–1767139200)

Two windows were used instead of the full day to keep memory usage manageable (~35M records per window instead of ~140M for the full day). The windows were chosen as representative slices — the temporal coverage plot confirms activity is consistent throughout the day.

**Timestamp handling per source:**

| Source | Column | Notes |
|---|---|---|
| Original `.nc` | `date_num` | Unix epoch integer |
| aisdb SQLite | `time` | Unix epoch integer |
| Reference CSV | `reception_timestamp` | UTC datetime string — **not** `ais_seconds`, which is the AIS payload second-of-minute (0–59) |

**Coordinate filtering:** Records with `lat` outside [-90, 90] or `lon` outside [-180, 180] are dropped. This removes AIS sentinel values (`lat=91, lon=181`) that the original decoder stores as numbers.

**Memory design:** Sources are loaded one at a time and freed after stats are extracted. This was necessary to avoid OOM kills — all five sources in memory simultaneously would exceed available RAM.

Output: `data/comparison_table.csv`, `data/plots/routes_*.png`

---

## Step 5 — Validate accuracy

`analysis/validate.py` provides deeper evidence for the comparison results:

1. **MMSI pairwise overlap** — Jaccard similarity between all source pairs → `data/validation/mmsi_overlap.csv` + heatmap
2. **Coordinate agreement** — mean lat/lon error for 1,000 shared vessels between original_nm4 and reference_csv → `data/validation/coord_agreement.csv` + error distribution plot
3. **Vessel track spot checks** — side-by-side track plots for 5 most active shared vessels
4. **Temporal coverage** — records per UTC hour for all sources → confirms windows are representative
5. **Top 20 vessels** — most active vessels per source for cross-checking
6. **Missing MMSI analysis** — classifies vessels missing from aisdb by type and message count

Output: `data/validation/`

---

## Step 6 — Profile decoder performance

`profile_aisdb.py` was written in response to a supervisor suggestion to time each phase of aisdb decoding to find the bottleneck. It tests three modes on the same 3 NM4 files and also runs the original decoder for comparison.

Key finding: SQLite writes account for 81% of aisdb's total time. The parser itself is fast.

Output: `data/profile_output.log`

---

## Repository structure

```
ais_decode_compare/
├── decode_aisdb.py          ← aisdb decoder (NM4 + streaming)
├── prepare_nm4.py           ← extracts NM4 zips for original decoder
├── profile_aisdb.py         ← decoder performance profiling
├── decode_original/         ← original DFO decoder (unmodified)
├── analysis/
│   ├── compare.py           ← main comparison script
│   └── validate.py          ← deep validation script
├── proof/
│   └── oob_coordinates.py   ← reproduces sentinel coordinate finding
├── doc_notes/               ← reading notes and diagrams
├── markdown/
│   ├── findings.md          ← key findings
│   ├── procedure.md         ← this file
│   └── commands.md          ← exact commands used
├── README.md
└── data/                    ← all outputs (large files gitignored)
    ├── comparison_table.csv
    ├── compare_output.log
    ├── profile_output.log
    ├── plots/
    └── validation/
```
