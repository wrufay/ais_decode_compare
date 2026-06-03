# AIS Decoder Comparison

Comparison study of two AIS NMEA decoders on Canadian Coast Guard data (2025-12-30).

## Decoders

| Decoder | Script | Output |
|---|---|---|
| Original (DFO) | `decode_original/Process_AIS_Serial.py` | NetCDF `.nc` files |
| aisdb | `decode_aisdb.py` | SQLite `.db` |

Documentation for the original decoder: https://publications.gc.ca/collections/collection_2023/mpo-dfo/Fs97-18-360-eng.pdf  
Documentation for aisdb: https://aisviz.cs.dal.ca/AISdb/api/aisdb.database.decoder.html

## Data sources

Located at `/home/shared/ccg_ais_claudio/ais_comp/` (read-only):

| Directory | Contents |
|---|---|
| `NM4/` | 288 × `.nmea.zip` — raw NMEA, 5-minute chunks |
| `streaming/` | 1 × `.csv` — raw NMEA, full day |
| `csv/` | 288 × `.csv.zip` — pre-decoded reference data |

## Key findings

- **NM4 and streaming are different datasets** — NM4 has ~170,000 unique vessels, streaming has ~3,200. NM4 contains raw per-station messages; streaming is pre-aggregated.
- **Original decoder matches reference CSV at 99.2%** (Jaccard 0.989)
- **aisdb matches reference CSV at 91.4%** — missing ~17,309 vessels vs the reference
- **aisdb is 2x faster end-to-end** than the original serial decoder on small data (29s vs 60s for 3 files). SQLite writes account for 81% of aisdb's time.

See `markdown/findings.md` for full details.

## Reproducing results

```bash
# Setup
python3 -m venv .venv
.venv/bin/pip install aisdb netCDF4 numpy pandas matplotlib

# Run comparison (requires decoded data in data/)
.venv/bin/python -u analysis/compare.py      # ~7 min
.venv/bin/python -u analysis/validate.py     # ~15 min
.venv/bin/python -u profile_aisdb.py 3       # ~2 min
```

See `markdown/commands.md` for full commands including the decode steps.

## Repository structure

```
├── decode_aisdb.py          ← aisdb decoder
├── prepare_nm4.py           ← NM4 preprocessing for original decoder
├── profile_aisdb.py         ← performance profiling
├── decode_original/         ← original DFO decoder (unmodified)
├── analysis/
│   ├── compare.py           ← main comparison + plots
│   └── validate.py          ← deep accuracy validation
├── proof/
│   └── oob_coordinates.py   ← reproduces sentinel coordinate finding
├── doc_notes/               ← reading notes
├── markdown/
│   ├── findings.md          ← key findings
│   ├── procedure.md         ← what was done and why
│   └── commands.md          ← exact commands used
└── data/
    ├── comparison_table.csv
    ├── plots/
    └── validation/
```
