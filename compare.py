#!/usr/bin/env python3
"""
compare.py — Compare outputs of the two AIS decoders against the reference CSVs.

Produces:
  data/comparison_table.csv   — metrics per source × window
  data/plots/routes_*.png     — scatter plots of vessel positions per window
"""

import glob
import os
import sqlite3
import time
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Time windows — two 3-hour slices of 2025-12-30 UTC
# ---------------------------------------------------------------------------
WINDOWS = {
    "00h-03h": (1767052800, 1767063600),  # 00:00–03:00 UTC
    "21h-24h": (1767128400, 1767139200),  # 21:00–24:00 UTC
}

DATA_DIR    = Path("data")
PLOTS_DIR   = DATA_DIR / "plots"
REF_CSV_DIR = Path("/home/shared/ccg_ais_claudio/ais_comp/csv")

PLOTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def file_size_mb(path: str) -> float | None:
    """Return file/dir size in MB, or None if path does not exist."""
    p = Path(path)
    if not p.exists():
        return None
    if p.is_file():
        return p.stat().st_size / 1e6
    # directory: sum all files
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6


def count_source_files(pattern: str) -> int:
    return len(glob.glob(pattern))


# ---------------------------------------------------------------------------
# Loaders — each returns (DataFrame, metadata_dict)
# DataFrame columns: mmsi, ts, lat, lon
# metadata includes load time, raw record count, file size, etc.
# ---------------------------------------------------------------------------

def load_original_nc(pattern: str) -> tuple[pd.DataFrame, dict]:
    files = sorted(glob.glob(pattern))
    t0 = time.perf_counter()
    meta = {
        "input_files":    len(files),
        "input_size_mb":  round(sum(os.path.getsize(f) for f in files) / 1e6, 2) if files else 0,
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
            # Keep only records inside one of the two time windows
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
    meta = {
        "input_files":   1,
        "input_size_mb": round(file_size_mb(db_path), 2) if file_size_mb(db_path) else 0,
    }
    t0 = time.perf_counter()

    if not path.exists():
        print(f"  [warn] database not found: {db_path}")
        meta.update({"load_s": 0, "raw_records": 0, "valid_records": 0, "yield_pct": 0})
        return pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"]), meta

    con = sqlite3.connect(db_path)
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )]
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
        # Build OR clause for each window — only load the two 3-hour slices
        win_clauses = " OR ".join(
            f"(time >= {t0} AND time < {t1})" for t0, t1 in WINDOWS.values()
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

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"])
    valid = df.copy()

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

    # Stream one zip at a time and filter to time windows before accumulating
    # to avoid loading all 288 zips (~24GB) into memory at once.
    chunks = []
    raw_total = 0
    for zip_path in zips:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    df = pd.read_csv(
                        f,
                        usecols=["mmsi", "latitude", "longitude", "reception_timestamp"],
                    )
                raw_total += len(df)
                # Parse naive UTC datetime string → epoch seconds (pandas 3.x safe)
                df["ts"] = (
                    (pd.to_datetime(df["reception_timestamp"]) - pd.Timestamp("1970-01-01"))
                    // pd.Timedelta("1s")
                )
                df = df.rename(columns={"latitude": "lat", "longitude": "lon"})
                df = df[["mmsi", "ts", "lat", "lon"]]
                # Keep only records inside one of the two time windows
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


# ---------------------------------------------------------------------------
# Window filter
# ---------------------------------------------------------------------------

def apply_window(df: pd.DataFrame, t_start: int, t_end: int) -> pd.DataFrame:
    return df[(df["ts"] >= t_start) & (df["ts"] < t_end)]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Loading sources (one at a time to limit memory usage)")
    print("=" * 70)

    loaders = {
        "original_nm4":       (load_original_nc, "data/original/nm4/Dynamic_*.nc"),
        "original_streaming": (load_original_nc, "data/original/streaming/Dynamic_*.nc"),
        "aisdb_nm4":          (load_aisdb,        "data/decode_nm4.db"),
        "aisdb_streaming":    (load_aisdb,         "data/decode_streaming.db"),
        "reference_csv":      (load_reference_csv, str(REF_CSV_DIR)),
    }

    all_rows   = []   # comparison table rows accumulated across sources
    plot_data  = {win: {} for win in WINDOWS}  # {window: {src: (lons, lats, n_vessels)}}

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

        # Compute per-window stats and save plot data while df is in memory
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
                "full_day_records": meta["valid_records"],
                "yield_pct":        meta["yield_pct"],
            })
            # Store only the arrays needed for plotting (much smaller than full df)
            plot_data[win_name][name] = (
                subset["lon"].to_numpy(),
                subset["lat"].to_numpy(),
                u,
                n,
            )

        # Explicitly free memory before loading the next source
        del df
        import gc; gc.collect()

    # --- Comparison table -------------------------------------------------
    print("\n" + "=" * 70)
    print("Windowed comparison")
    print("=" * 70)
    table = pd.DataFrame(all_rows)
    print("\n" + table.to_string(index=False))
    out_csv = DATA_DIR / "comparison_table.csv"
    table.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}")

    # --- Route plots -------------------------------------------------------
    src_names = list(loaders.keys())
    for win_name in WINDOWS:
        n_src = len(src_names)
        fig, axes = plt.subplots(1, n_src, figsize=(5 * n_src, 5), constrained_layout=True)
        fig.suptitle(f"Vessel positions — {win_name} UTC  (2025-12-30)", fontsize=13)

        for ax, src_name in zip(axes, src_names):
            lons, lats, u, n = plot_data[win_name][src_name]
            ax.scatter(lons, lats, s=0.3, alpha=0.4, linewidths=0)
            ax.set_title(f"{src_name}\n{u:,} vessels | {n:,} pts", fontsize=8)
            ax.set_xlabel("Longitude", fontsize=7)
            ax.set_ylabel("Latitude", fontsize=7)
            ax.tick_params(labelsize=6)

        out_png = PLOTS_DIR / f"routes_{win_name}.png"
        plt.savefig(out_png, dpi=150)
        plt.close()
        print(f"Saved: {out_png}")


if __name__ == "__main__":
    main()
