#!/usr/bin/env python3
"""
Extract NM4 zip files and rename .nmea → .csv so Process_AIS_Serial.py
can read them (it only handles .csv and .txt extensions).
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
