#!/usr/bin/env python3
"""
compare.py — Compare outputs of the two AIS decoders against reference data.

Loads five sources across two 3-hour windows of 2025-12-30 UTC and writes a
comparison table (records, unique MMSI, coverage, load time) to
data/comparison_table.csv.

Sources:
  original_nm4       data/original/nm4/Dynamic_*.nc
  original_streaming data/original/streaming/Dynamic_*.nc
  aisdb_nm4          data/decode_nm4.db
  aisdb_streaming    data/decode_streaming.db
  reference_csv      /home/shared/ccg_ais_claudio/ais_comp/csv/

Time windows (3-hour slices to avoid OOM on ~140M full-day records):
  00h-03h  1767052800–1767063600
  21h-24h  1767128400–1767139200

Timestamp columns differ per source:
  NetCDF       date_num            Unix epoch integer
  aisdb        time                Unix epoch integer
  reference    reception_timestamp UTC datetime string

Usage:
    .venv/bin/python -u analysis/compare.py
"""

import gc
import glob
import os
import sqlite3
import time
import zipfile
from pathlib import Path

import netCDF4
import numpy as np
import pandas as pd

WINDOWS = {
    "00h-03h": (1767052800, 1767063600),
    "21h-24h": (1767128400, 1767139200),
}

REPO_ROOT   = Path(__file__).parent.parent
DATA_DIR    = REPO_ROOT / "data"
REF_CSV_DIR = Path("/home/shared/ccg_ais_claudio/ais_comp/csv")


def file_size_mb(path: str) -> float | None:
    p = Path(path)
    if not p.exists():
        return None
    if p.is_file():
        return p.stat().st_size / 1e6
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6


def load_original_nc(pattern: str) -> tuple[pd.DataFrame, dict]:
    files = sorted(glob.glob(pattern))
    t0 = time.perf_counter()
    meta = {
        "input_files":   len(files),
        "input_size_mb": round(sum(os.path.getsize(f) for f in files) / 1e6, 2) if files else 0,
    }

    if not files:
        print(f"  [warn] no files matched: {pattern}")
        meta.update({"load_s": 0, "raw_records": 0, "valid_records": 0, "yield_pct": 0})
        return pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"]), meta

    chunks = []
    raw_total = 0
    for path in files:
        try:
            ds = netCDF4.Dataset(path)
            mmsi = np.array(ds.variables["mmsi"][:], dtype=np.int64)
            ts   = np.array(ds.variables["date_num"][:], dtype=np.int64)
            lat  = np.array(ds.variables["latitude"][:], dtype=float)
            lon  = np.array(ds.variables["longitude"][:], dtype=float)
            ds.close()
            raw_total += len(mmsi)
            in_window = np.zeros(len(ts), dtype=bool)
            for w0, w1 in WINDOWS.values():
                in_window |= (ts >= w0) & (ts < w1)
            mask = (
                in_window &
                (mmsi != -9999) &
                ~np.isnan(lat) & ~np.isnan(lon) &
                (lat >= -90) & (lat <= 90) &
                (lon >= -180) & (lon <= 180)
            )
            if mask.any():
                chunks.append(pd.DataFrame({
                    "mmsi": mmsi[mask], "ts": ts[mask],
                    "lat": lat[mask],   "lon": lon[mask],
                }))
        except Exception as e:
            print(f"  [warn] could not read {path}: {e}")

    if not chunks:
        meta.update({"load_s": round(time.perf_counter() - t0, 2), "raw_records": 0,
                     "valid_records": 0, "yield_pct": 0})
        return pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"]), meta

    valid = pd.concat(chunks, ignore_index=True)
    elapsed = round(time.perf_counter() - t0, 2)
    meta.update({
        "load_s":        elapsed,
        "load_rate":     round(raw_total / elapsed) if elapsed > 0 else None,
        "raw_records":   raw_total,
        "valid_records": len(valid),
        "yield_pct":     round(100 * len(valid) / raw_total, 2) if raw_total else 0,
    })
    return valid, meta


def load_aisdb(db_path: str) -> tuple[pd.DataFrame, dict]:
    path = Path(db_path)
    size = file_size_mb(db_path)
    meta = {
        "input_files":   1,
        "input_size_mb": round(size, 2) if size else 0,
    }
    t0 = time.perf_counter()

    if not path.exists():
        print(f"  [warn] database not found: {db_path}")
        meta.update({"load_s": 0, "raw_records": 0, "valid_records": 0, "yield_pct": 0})
        return pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"]), meta

    con = sqlite3.connect(db_path)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    dyn_tables = [t for t in tables if t.endswith("_dynamic")]

    if not dyn_tables:
        print(f"  [warn] no *_dynamic table in {db_path}. Tables: {tables}")
        con.close()
        meta.update({"load_s": 0, "raw_records": 0, "valid_records": 0, "yield_pct": 0})
        return pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"]), meta

    frames = []
    raw_total = 0
    for tbl in dyn_tables:
        raw_total += con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        win_clauses = " OR ".join(
            f"(time >= {w0} AND time < {w1})" for w0, w1 in WINDOWS.values()
        )
        df = pd.read_sql_query(
            f"""SELECT mmsi, time AS ts, latitude AS lat, longitude AS lon
                FROM {tbl}
                WHERE ({win_clauses})
                  AND latitude BETWEEN -90 AND 90
                  AND longitude BETWEEN -180 AND 180""",
            con,
        )
        frames.append(df)
    con.close()

    valid = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"])
    elapsed = round(time.perf_counter() - t0, 2)
    meta.update({
        "load_s":        elapsed,
        "load_rate":     round(raw_total / elapsed) if elapsed > 0 else None,
        "raw_records":   raw_total,
        "valid_records": len(valid),
        "yield_pct":     round(100 * len(valid) / raw_total, 2) if raw_total else 0,
        "tables":        dyn_tables,
    })
    return valid, meta


def load_reference_csv(csv_dir: str) -> tuple[pd.DataFrame, dict]:
    zips = sorted(glob.glob(f"{csv_dir}/*.csv.zip"))
    meta = {
        "input_files":   len(zips),
        "input_size_mb": round(sum(os.path.getsize(z) for z in zips) / 1e6, 2) if zips else 0,
    }
    t0 = time.perf_counter()

    if not zips:
        print(f"  [warn] no csv.zip files in {csv_dir}")
        meta.update({"load_s": 0, "raw_records": 0, "valid_records": 0, "yield_pct": 0})
        return pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"]), meta

    chunks = []
    raw_total = 0
    for zip_path in zips:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    df = pd.read_csv(f, usecols=["mmsi", "latitude", "longitude", "reception_timestamp"])
                raw_total += len(df)
                df["ts"] = (
                    (pd.to_datetime(df["reception_timestamp"]) - pd.Timestamp("1970-01-01"))
                    // pd.Timedelta("1s")
                )
                df = df.rename(columns={"latitude": "lat", "longitude": "lon"})[["mmsi", "ts", "lat", "lon"]]
                in_window = pd.Series(False, index=df.index)
                for w0, w1 in WINDOWS.values():
                    in_window |= (df["ts"] >= w0) & (df["ts"] < w1)
                df = df[in_window & df["lat"].between(-90, 90) & df["lon"].between(-180, 180)]
                if len(df):
                    chunks.append(df)

    valid = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"])
    elapsed = round(time.perf_counter() - t0, 2)
    meta.update({
        "load_s":        elapsed,
        "load_rate":     round(raw_total / elapsed) if elapsed > 0 else None,
        "raw_records":   raw_total,
        "valid_records": len(valid),
        "yield_pct":     round(100 * len(valid) / raw_total, 2) if raw_total else 0,
    })
    return valid, meta


def apply_window(df: pd.DataFrame, t_start: int, t_end: int) -> pd.DataFrame:
    return df[(df["ts"] >= t_start) & (df["ts"] < t_end)]


def main():
    print("=" * 70)
    print("Loading sources (one at a time to limit memory usage)")
    print("=" * 70)

    loaders = {
        "original_nm4":       (load_original_nc, str(DATA_DIR / "original/nm4/Dynamic_*.nc")),
        "original_streaming": (load_original_nc, str(DATA_DIR / "original/streaming/Dynamic_*.nc")),
        "aisdb_nm4":          (load_aisdb,        str(DATA_DIR / "decode_nm4.db")),
        "aisdb_streaming":    (load_aisdb,        str(DATA_DIR / "decode_streaming.db")),
        "reference_csv":      (load_reference_csv, str(REF_CSV_DIR)),
    }

    all_rows = []

    for name, (fn, arg) in loaders.items():
        print(f"\n  Loading {name}...")
        df, meta = fn(arg)

        print(f"    input files:    {meta['input_files']}  ({meta['input_size_mb']} MB)")
        print(f"    raw records:    {meta['raw_records']:,}")
        print(f"    valid records:  {meta['valid_records']:,}  (yield: {meta['yield_pct']}%)")
        print(f"    unique MMSI:    {df['mmsi'].nunique():,}")
        if meta.get("load_rate"):
            print(f"    load speed:     {meta['load_rate']:,} records/s  ({meta['load_s']}s)")
        if len(df):
            print(f"    avg msgs/vessel:{len(df) / max(df['mmsi'].nunique(), 1):.1f}")

        for win_name, (w0, w1) in WINDOWS.items():
            subset = apply_window(df, w0, w1)
            n = len(subset)
            u = subset["mmsi"].nunique()
            all_rows.append({
                "window":           win_name,
                "source":           name,
                "records":          n,
                "unique_mmsi":      u,
                "avg_msgs_vessel":  round(n / u, 1) if u else None,
                "lat_min":          round(float(subset["lat"].min()), 4) if n else None,
                "lat_max":          round(float(subset["lat"].max()), 4) if n else None,
                "lon_min":          round(float(subset["lon"].min()), 4) if n else None,
                "lon_max":          round(float(subset["lon"].max()), 4) if n else None,
                "load_s":           meta["load_s"],
                "input_size_mb":    meta["input_size_mb"],
                "valid_records":    meta["valid_records"],
                "yield_pct":        meta["yield_pct"],
            })

        del df
        gc.collect()

    print("\n" + "=" * 70)
    print("Windowed comparison")
    print("=" * 70)
    table = pd.DataFrame(all_rows)
    print("\n" + table.to_string(index=False))
    out_csv = DATA_DIR / "comparison_table.csv"
    table.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}")


if __name__ == "__main__":
    main()
