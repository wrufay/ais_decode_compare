#!/usr/bin/env python3
"""
extract.py — Extract lat/lon arrays from all 5 AIS sources for the full day
             (2025-12-30 UTC) and save to data/plot_cache.npz.

Run once. The cache is then used by plotting scripts.

Usage:
    .venv/bin/python -u analysis/extract.py
"""

import gc
import glob
import sqlite3
import time
import zipfile
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

T_START = 1767052800  # 2025-12-30 00:00 UTC
T_END   = 1767139200  # 2025-12-30 24:00 UTC

# Allow the script to be run from any working directory
REPO_ROOT   = Path(__file__).parent.parent
# Path to the decoded data including NetCDF and SQLite files
DATA_DIR    = REPO_ROOT / "data"
# Hard coded path to the reference CSV on the Linux machine
REF_CSV_DIR = Path("/home/shared/ccg_ais_claudio/ais_comp/csv")
# Destination for the extracted lat/lon arrays
CACHE_PATH  = DATA_DIR / "plot_cache.npz"


def load_original_nc(pattern: str) -> tuple[np.ndarray, np.ndarray]:
    files = sorted(glob.glob(pattern))

    # Error handling if no files match the pattern
    if not files:
        print(f"  [warn] no files matched: {pattern}")
        return np.array([]), np.array([])
    
    
    lons, lats = [], []
    for path in files:
        try:
            ds = netCDF4.Dataset(path)
            mmsi = np.array(ds.variables["mmsi"][:], dtype=np.int64)
            ts   = np.array(ds.variables["date_num"][:], dtype=np.int64)
            lat  = np.array(ds.variables["latitude"][:], dtype=float)
            lon  = np.array(ds.variables["longitude"][:], dtype=float)
            ds.close()
            mask = (
                (ts >= T_START) & (ts < T_END) &
                (mmsi != -9999) &
                ~np.isnan(lat) & ~np.isnan(lon) &
                (lat >= -90) & (lat <= 90) &
                (lon >= -180) & (lon <= 180)
            )
            lats.append(lat[mask])
            lons.append(lon[mask])
        except Exception as e:
            print(f"  [warn] could not read {path}: {e}")

    return (np.concatenate(lons) if lons else np.array([]),
            np.concatenate(lats) if lats else np.array([]))


def load_aisdb(db_path: str) -> tuple[np.ndarray, np.ndarray]:
    path = Path(db_path)
    if not path.exists():
        print(f"  [warn] database not found: {db_path}")
        return np.array([]), np.array([])

    con = sqlite3.connect(db_path)
    dyn_tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) if r[0].endswith("_dynamic")]

    if not dyn_tables:
        con.close()
        print(f"  [warn] no *_dynamic table in {db_path}")
        return np.array([]), np.array([])

    # Chunked reads to avoid loading the full table into memory at once
    # (temporary workaround for SQLite's lack of native streaming)
    lons_list, lats_list = [], []
    for tbl in dyn_tables:
        for chunk in pd.read_sql_query(
            f"""SELECT latitude AS lat, longitude AS lon
                FROM {tbl}
                WHERE time >= {T_START} AND time < {T_END}
                  AND latitude BETWEEN -90 AND 90
                  AND longitude BETWEEN -180 AND 180""",
            con,
            chunksize=500_000,
        ):
            lons_list.append(chunk["lon"].to_numpy())
            lats_list.append(chunk["lat"].to_numpy())
    con.close()

    return (np.concatenate(lons_list) if lons_list else np.array([]),
            np.concatenate(lats_list) if lats_list else np.array([]))


def load_reference_csv(csv_dir: str) -> tuple[np.ndarray, np.ndarray]:
    zips = sorted(glob.glob(f"{csv_dir}/*.csv.zip"))
    if not zips:
        print(f"  [warn] no csv.zip files in {csv_dir}")
        return np.array([]), np.array([])

    lons, lats = [], []
    for zip_path in zips:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    df = pd.read_csv(f, usecols=["latitude", "longitude", "reception_timestamp"])
                ts = (
                    (pd.to_datetime(df["reception_timestamp"]) - pd.Timestamp("1970-01-01"))
                    // pd.Timedelta("1s")
                )
                mask = (
                    (ts >= T_START) & (ts < T_END) &
                    df["latitude"].between(-90, 90) &
                    df["longitude"].between(-180, 180)
                )
                lats.append(df["latitude"][mask].to_numpy())
                lons.append(df["longitude"][mask].to_numpy())

    return (np.concatenate(lons) if lons else np.array([]),
            np.concatenate(lats) if lats else np.array([]))


def main():
    sources = {
        "original_nm4":       (load_original_nc, str(DATA_DIR / "original/nm4/Dynamic_*.nc")),
        "original_streaming": (load_original_nc, str(DATA_DIR / "original/streaming/Dynamic_*.nc")),
        "aisdb_nm4":          (load_aisdb,        str(DATA_DIR / "decode_nm4.db")),
        "aisdb_streaming":    (load_aisdb,        str(DATA_DIR / "decode_streaming.db")),
        "reference_csv":      (load_reference_csv, str(REF_CSV_DIR)),
    }

    cache = {}
    for name, (fn, arg) in sources.items():
        print(f"Loading {name}...")
        t0 = time.perf_counter()
        lons, lats = fn(arg)
        elapsed = round(time.perf_counter() - t0, 2)
        print(f"  {len(lons):,} points in {elapsed}s")
        cache[f"{name}_lons"] = lons
        cache[f"{name}_lats"] = lats
        gc.collect()

    np.savez(CACHE_PATH, **cache)
    print(f"\nSaved: {CACHE_PATH}")


if __name__ == "__main__":
    main()
