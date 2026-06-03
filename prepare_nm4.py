#!/usr/bin/env python3
"""
prepare_nm4.py — Extract and rename NM4 zip files for the original decoder.

PURPOSE
-------
This is a pre-processing step required before running Process_AIS_Serial.py
on the NM4 data source. The original decoder only recognises two file
extensions: .csv and .txt. The NM4 source files are delivered as zipped
.nmea archives (.nmea.zip), so they cannot be read directly.

This script extracts each zip and renames the contained .nmea file to .csv.
The file contents are identical — both formats contain raw NMEA sentences
in the format:
    \\s:StationName,c:UnixTimestamp*XX\\!AIVDM,...

No data is modified — only the file extension changes.

INPUT
-----
Source directory (read-only, not modified):
    /home/shared/ccg_ais_claudio/ais_comp/NM4/
    288 files:  ais-2025-12-30-HH-MM.nmea.zip
    Each zip contains one .nmea file covering a 5-minute window.
    288 × 5 min = 24 hours of data.

OUTPUT
------
    data/original/nm4_raw/
    288 files:  ais-2025-12-30-HH-MM.csv
    Ready to be passed to Process_AIS_Serial.py.

NOTE
----
These 288 extracted files are intermediate — they are large (~several GB
total) and are excluded from version control via .gitignore. They can be
safely deleted after the original decoder has finished running.

USAGE
-----
    python prepare_nm4.py

Must be run from the repo root. Run before:
    Process_AIS_Serial.py data/original/nm4_raw data/original/nm4 ais-2025-12-30
"""
import glob
import os
import zipfile
from pathlib import Path

NM4_DIR = "/home/shared/ccg_ais_claudio/ais_comp/NM4"
OUT_DIR = Path(__file__).parent / "data/original/nm4_raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

zips = sorted(glob.glob(f"{NM4_DIR}/*.nmea.zip"))
print(f"Extracting {len(zips)} zip files to {OUT_DIR} ...")

for zip_path in zips:
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            data = zf.read(name)
            out_name = Path(name).stem + ".csv"
            (OUT_DIR / out_name).write_bytes(data)

print(f"Done. {len(list(OUT_DIR.glob('*.csv')))} files written.")
