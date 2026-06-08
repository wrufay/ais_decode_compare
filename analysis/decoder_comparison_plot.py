#!/usr/bin/env python3
"""
decoder_comparison_plot.py — Lat / lon vs time for a single vessel, comparing
                              the two NM4 decoders against the reference CSV.

MMSI:    352001367  (highest obs count + spread among common Scotian Shelf vessels)
Sources: original_nm4, aisdb_nm4, reference_csv

Usage:
    .venv/bin/python -u analysis/decoder_comparison_plot.py
"""

import glob
import sqlite3
import zipfile
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

T_START = 1767052800  # 2025-12-30 00:00 UTC
T_END   = 1767139200  # 2025-12-30 24:00 UTC
MMSI    = 352001367

REPO_ROOT   = Path(__file__).parent.parent
DATA_DIR    = REPO_ROOT / "data"
PLOTS_DIR   = DATA_DIR / "plots"
REF_CSV_DIR = Path("/home/shared/ccg_ais_claudio/ais_comp/csv")

SOURCES = {
    "original_nm4": {"color": "steelblue",   "lw": 1.2, "ls": "-",  "zorder": 2},
    "aisdb_nm4":    {"color": "darkorange",  "lw": 1.2, "ls": "-",  "zorder": 2},
    "reference":    {"color": "black",       "lw": 0.8, "ls": "--", "zorder": 1},
}


def load_nc(pattern: str) -> pd.DataFrame:
    import netCDF4, numpy as np
    files = sorted(glob.glob(pattern))
    if not files:
        return pd.DataFrame(columns=["ts", "lat", "lon"])
    chunks = []
    for path in files:
        ds = netCDF4.Dataset(path)
        mmsi = np.array(ds.variables["mmsi"][:],    dtype=np.int64)
        ts   = np.array(ds.variables["date_num"][:], dtype=np.int64)
        lat  = np.array(ds.variables["latitude"][:], dtype=float)
        lon  = np.array(ds.variables["longitude"][:], dtype=float)
        ds.close()
        mask = (mmsi == MMSI) & (ts >= T_START) & (ts < T_END)
        if mask.any():
            chunks.append(pd.DataFrame({"ts": ts[mask], "lat": lat[mask], "lon": lon[mask]}))
    return pd.concat(chunks, ignore_index=True).sort_values("ts") if chunks else pd.DataFrame(columns=["ts", "lat", "lon"])


def load_aisdb(db_path: str) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        return pd.DataFrame(columns=["ts", "lat", "lon"])
    con = sqlite3.connect(db_path)
    tbl = next(r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) if r[0].endswith("_dynamic"))
    df = pd.read_sql_query(
        f"""SELECT time AS ts, latitude AS lat, longitude AS lon
            FROM {tbl}
            WHERE mmsi = {MMSI} AND time >= {T_START} AND time < {T_END}""",
        con,
    )
    con.close()
    return df.sort_values("ts")


def load_reference(csv_dir: str) -> pd.DataFrame:
    zips = sorted(glob.glob(f"{csv_dir}/*.csv.zip"))
    chunks = []
    for zip_path in zips:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    df = pd.read_csv(f, usecols=["mmsi", "latitude", "longitude", "reception_timestamp"])
                df = df[df["mmsi"] == MMSI].copy()
                if df.empty:
                    continue
                df["ts"] = (
                    (pd.to_datetime(df["reception_timestamp"]) - pd.Timestamp("1970-01-01"))
                    // pd.Timedelta("1s")
                )
                df = df[(df["ts"] >= T_START) & (df["ts"] < T_END)]
                chunks.append(df[["ts", "latitude", "longitude"]].rename(
                    columns={"latitude": "lat", "longitude": "lon"}
                ))
    return pd.concat(chunks, ignore_index=True).sort_values("ts") if chunks else pd.DataFrame(columns=["ts", "lat", "lon"])


def make_plot(decoders: list, source: str) -> None:
    def to_dt(ts): return pd.to_datetime(ts, unit="s", utc=True)

    fig, axes = plt.subplots(2, len(decoders), figsize=(7 * len(decoders), 6), constrained_layout=True, sharex=True)
    fig.suptitle(f"MMSI {MMSI} — {source} source — decoder comparison (2025-12-30 UTC)", fontsize=12)

    fmt = mdates.DateFormatter("%H:%M")
    loc = mdates.HourLocator(interval=3)
    colors = ["steelblue", "darkorange", "green"]

    for col, (label, df) in enumerate(decoders):
        ax_lat = axes[0, col]
        ax_lon = axes[1, col]
        t = to_dt(df["ts"])
        ax_lat.scatter(t, df["lat"], s=1, color=colors[col], alpha=0.5, linewidths=0)
        ax_lon.scatter(t, df["lon"], s=1, color=colors[col], alpha=0.5, linewidths=0)
        ax_lat.set_title(f"{label}\n({len(df):,} pts)", fontsize=10)
        ax_lon.xaxis.set_major_formatter(fmt)
        ax_lon.xaxis.set_major_locator(loc)
        plt.setp(ax_lon.xaxis.get_majorticklabels(), rotation=30, ha="right")
        for ax in (ax_lat, ax_lon):
            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=8)

    axes[0, 0].set_ylabel("Latitude (°N)", fontsize=10)
    axes[1, 0].set_ylabel("Longitude (°E)", fontsize=10)
    for ax in axes[1]:
        ax.set_xlabel("Time (UTC)", fontsize=10)

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    out = PLOTS_DIR / f"decoder_comparison_{source}.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved: {out}")


def make_reference_plot(df: pd.DataFrame, suffix: str = "") -> None:
    def to_dt(ts): return pd.to_datetime(ts, unit="s", utc=True)

    fig, (ax_lat, ax_lon) = plt.subplots(2, 1, figsize=(10, 6), constrained_layout=True, sharex=True)
    fig.suptitle(f"MMSI {MMSI} — reference CSV (2025-12-30 UTC)", fontsize=12)

    t = to_dt(df["ts"])
    ax_lat.scatter(t, df["lat"], s=1, color="green", alpha=0.5, linewidths=0)
    ax_lon.scatter(t, df["lon"], s=1, color="green", alpha=0.5, linewidths=0)
    ax_lat.set_title(f"reference\n({len(df):,} pts)", fontsize=10)

    fmt = mdates.DateFormatter("%H:%M")
    loc = mdates.HourLocator(interval=3)
    ax_lon.xaxis.set_major_formatter(fmt)
    ax_lon.xaxis.set_major_locator(loc)
    plt.setp(ax_lon.xaxis.get_majorticklabels(), rotation=30, ha="right")

    ax_lat.set_ylabel("Latitude (°N)", fontsize=10)
    ax_lon.set_ylabel("Longitude (°E)", fontsize=10)
    ax_lon.set_xlabel("Time (UTC)", fontsize=10)
    for ax in (ax_lat, ax_lon):
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    out = PLOTS_DIR / f"decoder_comparison_reference{suffix}.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved: {out}")


def main():
    print("Loading nm4 sources...")
    orig_nm4     = load_nc(str(DATA_DIR / "original/nm4/Dynamic_*.nc"))
    aisdb_nm4    = load_aisdb(str(DATA_DIR / "aisdb/decode_nm4.db"))
    print(f"  original_nm4: {len(orig_nm4):,}  aisdb_nm4: {len(aisdb_nm4):,}")

    print("Loading streaming sources...")
    orig_stream  = load_nc(str(DATA_DIR / "original/streaming/Dynamic_*.nc"))
    aisdb_stream = load_aisdb(str(DATA_DIR / "aisdb/decode_streaming.db"))
    print(f"  original_streaming: {len(orig_stream):,}  aisdb_streaming: {len(aisdb_stream):,}")

    print("Loading reference...")
    ref = load_reference(str(REF_CSV_DIR))
    print(f"  reference: {len(ref):,}")

    make_plot([("original_nm4", orig_nm4), ("aisdb_nm4", aisdb_nm4), ("reference", ref)], "nm4")
    make_plot([("original_streaming", orig_stream), ("aisdb_streaming", aisdb_stream), ("reference", ref)], "streaming")


if __name__ == "__main__":
    main()
