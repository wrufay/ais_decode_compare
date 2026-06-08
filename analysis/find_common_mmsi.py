#!/usr/bin/env python3
"""
find_common_mmsi.py — Find MMSI present in all 5 AIS sources within the
                      Scotian Shelf bounding box for 2025-12-30 UTC.

Prints the intersection size and the top N MMSI ranked by total observation
count across all sources.

Usage:
    .venv/bin/python -u analysis/find_common_mmsi.py
"""

import glob
import sqlite3
import zipfile
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

T_START = 1767052800  # 2025-12-30 00:00 UTC
T_END   = 1767139200  # 2025-12-30 24:00 UTC

BBOX = dict(lat_min=42, lat_max=48, lon_min=-68, lon_max=-55)

REPO_ROOT   = Path(__file__).parent.parent
DATA_DIR    = REPO_ROOT / "data"
REF_CSV_DIR = Path("/home/shared/ccg_ais_claudio/ais_comp/csv")

TOP_N = 10  # how many candidates to print


def load_nc(pattern: str) -> pd.DataFrame:
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"  [warn] no files matched: {pattern}")
        return pd.DataFrame(columns=["mmsi", "lat", "lon"])
    chunks = []
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
                (lat >= BBOX["lat_min"]) & (lat <= BBOX["lat_max"]) &
                (lon >= BBOX["lon_min"]) & (lon <= BBOX["lon_max"])
            )
            if mask.any():
                chunks.append(pd.DataFrame({"mmsi": mmsi[mask], "lat": lat[mask], "lon": lon[mask]}))
        except Exception as e:
            print(f"  [warn] {path}: {e}")
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=["mmsi", "lat", "lon"])


def load_aisdb(db_path: str) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        print(f"  [warn] not found: {db_path}")
        return pd.DataFrame(columns=["mmsi", "lat", "lon"])
    con = sqlite3.connect(db_path)
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) if r[0].endswith("_dynamic")]
    frames = []
    for tbl in tables:
        df = pd.read_sql_query(
            f"""SELECT mmsi, latitude AS lat, longitude AS lon
                FROM {tbl}
                WHERE time >= {T_START} AND time < {T_END}
                  AND latitude  BETWEEN {BBOX['lat_min']} AND {BBOX['lat_max']}
                  AND longitude BETWEEN {BBOX['lon_min']} AND {BBOX['lon_max']}""",
            con,
        )
        frames.append(df)
    con.close()
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["mmsi", "lat", "lon"])


def load_reference(csv_dir: str) -> pd.DataFrame:
    zips = sorted(glob.glob(f"{csv_dir}/*.csv.zip"))
    if not zips:
        print(f"  [warn] no csv.zip in {csv_dir}")
        return pd.DataFrame(columns=["mmsi", "lat", "lon"])
    chunks = []
    for zip_path in zips:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    df = pd.read_csv(f, usecols=["mmsi", "latitude", "longitude", "reception_timestamp"])
                ts = (
                    (pd.to_datetime(df["reception_timestamp"]) - pd.Timestamp("1970-01-01"))
                    // pd.Timedelta("1s")
                )
                mask = (
                    (ts >= T_START) & (ts < T_END) &
                    df["latitude"].between(BBOX["lat_min"], BBOX["lat_max"]) &
                    df["longitude"].between(BBOX["lon_min"], BBOX["lon_max"])
                )
                sub = df[mask][["mmsi", "latitude", "longitude"]].rename(
                    columns={"latitude": "lat", "longitude": "lon"}
                )
                if len(sub):
                    chunks.append(sub)
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=["mmsi", "lat", "lon"])


def main():
    loaders = {
        "original_nm4":       (load_nc,        str(DATA_DIR / "original/nm4/Dynamic_*.nc")),
        "original_streaming": (load_nc,        str(DATA_DIR / "original/streaming/Dynamic_*.nc")),
        "aisdb_nm4":          (load_aisdb,     str(DATA_DIR / "decode_nm4.db")),
        "aisdb_streaming":    (load_aisdb,     str(DATA_DIR / "decode_streaming.db")),
        "reference_csv":      (load_reference, str(REF_CSV_DIR)),
    }

    source_dfs: dict[str, pd.DataFrame] = {}
    for name, (fn, arg) in loaders.items():
        print(f"Loading {name}...")
        df = fn(arg)
        print(f"  {len(df):,} Scotian Shelf records, {df['mmsi'].nunique():,} unique MMSI")
        source_dfs[name] = df

    # Intersect MMSI sets across all sources
    mmsi_sets = [set(df["mmsi"].unique()) for df in source_dfs.values()]
    common = mmsi_sets[0].intersection(*mmsi_sets[1:])
    print(f"\nMMSI present in ALL 5 sources: {len(common)}")

    if not common:
        print("No common MMSI found — check data availability.")
        return

    # Build value_counts per source, then look up counts for common MMSI only
    vc = {name: df["mmsi"].value_counts() for name, df in source_dfs.items()}

    rows = []
    for mmsi in common:
        per = {name: int(vc[name].get(mmsi, 0)) for name in source_dfs}
        rows.append({"mmsi": mmsi, "total": sum(per.values()), **per})

    ranked = sorted(rows, key=lambda x: x["total"], reverse=True)

    src_names = list(source_dfs.keys())
    print(f"\nTop {min(TOP_N, len(ranked))} by total observation count across all sources:")
    header = f"{'MMSI':>12}  {'total':>8}  " + "  ".join(f"{s:>20}" for s in src_names)
    print(header)
    for row in ranked[:TOP_N]:
        per_source = "  ".join(f"{row[s]:>20,}" for s in src_names)
        print(f"{row['mmsi']:>12}  {row['total']:>8,}  {per_source}")


if __name__ == "__main__":
    main()
