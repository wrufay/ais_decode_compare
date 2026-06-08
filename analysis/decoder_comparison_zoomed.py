#!/usr/bin/env python3
"""
decoder_comparison_zoomed.py — Same as decoder_comparison_plot.py but zoomed
                                into a 3-hour window so individual points are
                                visible.

Produces:
  data/plots/decoder_comparison_nm4_zoomed.png
  data/plots/decoder_comparison_streaming_zoomed.png

Usage:
    .venv/bin/python -u analysis/decoder_comparison_zoomed.py
"""

import glob
import sqlite3
import zipfile
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

# 30-minute window: 06:00 – 06:30 UTC on 2025-12-30
T_START = 1767052800 + 6 * 3600          # 06:00
T_END   = 1767052800 + 6 * 3600 + 1800   # 06:30
MMSI    = 352001367

REPO_ROOT   = Path(__file__).parent.parent
DATA_DIR    = REPO_ROOT / "data"
PLOTS_DIR   = DATA_DIR / "plots"


def load_nc(pattern: str) -> pd.DataFrame:
    import netCDF4, numpy as np
    files = sorted(glob.glob(pattern))
    if not files:
        return pd.DataFrame(columns=["ts", "lat", "lon"])
    chunks = []
    for path in files:
        ds = netCDF4.Dataset(path)
        mmsi = np.array(ds.variables["mmsi"][:],     dtype=np.int64)
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


def make_plot(decoders: list, source: str) -> None:
    def to_dt(ts): return pd.to_datetime(ts, unit="s", utc=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 6), constrained_layout=True, sharex=True)
    fig.suptitle(f"MMSI {MMSI} — {source} — 06:00–06:30 UTC (2025-12-30)", fontsize=12)

    fmt = mdates.DateFormatter("%H:%M")
    loc = mdates.MinuteLocator(interval=5)
    colors = ["steelblue", "darkorange"]

    for col, (label, df) in enumerate(decoders):
        ax_lat = axes[0, col]
        ax_lon = axes[1, col]
        t = to_dt(df["ts"])
        ax_lat.scatter(t, df["lat"], s=4, color=colors[col], alpha=0.6, linewidths=0)
        ax_lon.scatter(t, df["lon"], s=4, color=colors[col], alpha=0.6, linewidths=0)
        ax_lat.set_title(f"{label}\n({len(df):,} pts)", fontsize=10)
        ax_lon.xaxis.set_major_formatter(fmt)
        ax_lon.xaxis.set_major_locator(loc)
        plt.setp(ax_lon.xaxis.get_majorticklabels(), rotation=30, ha="right")
        for ax in (ax_lat, ax_lon):
            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=8)

    axes[0, 0].set_ylabel("Latitude (°N)", fontsize=10)
    axes[1, 0].set_ylabel("Longitude (°E)", fontsize=10)
    axes[1, 0].set_xlabel("Time (UTC)", fontsize=10)
    axes[1, 1].set_xlabel("Time (UTC)", fontsize=10)

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    out = PLOTS_DIR / f"decoder_comparison_{source}_zoomed.png"
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

    make_plot([("original_nm4", orig_nm4), ("aisdb_nm4", aisdb_nm4)], "nm4")
    make_plot([("original_streaming", orig_stream), ("aisdb_streaming", aisdb_stream)], "streaming")


if __name__ == "__main__":
    main()
