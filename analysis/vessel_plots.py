#!/usr/bin/env python3
"""
vessel_plots.py — Two figures for selected MMSI on the Scotian Shelf.

Figure 1  vessel_tracks_map.png
  1 row × 5 columns (one per source). Each panel shows position scatter
  for all selected MMSI, coloured by MMSI.

Figure 2  vessel_latlon_time.png
  5 rows × 2 columns (one row per MMSI, left = latitude, right = longitude).
  Each panel has one line per source.

Usage:
    .venv/bin/python -u analysis/vessel_plots.py
"""

import glob
import sqlite3
import zipfile
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

T_START = 1767052800  # 2025-12-30 00:00 UTC
T_END   = 1767139200  # 2025-12-30 24:00 UTC
BBOX    = dict(lat_min=42, lat_max=48, lon_min=-68, lon_max=-55)

MMSI_LIST = [355623000, 477114500, 431228000, 352001367, 538005539]

REPO_ROOT   = Path(__file__).parent.parent
DATA_DIR    = REPO_ROOT / "data"
PLOTS_DIR   = DATA_DIR / "plots"
REF_CSV_DIR = Path("/home/shared/ccg_ais_claudio/ais_comp/csv")

SOURCES = [
    "original_nm4",
    "original_streaming",
    "aisdb_nm4",
    "aisdb_streaming",
    "reference_csv",
]
SRC_COLORS = dict(zip(SOURCES, plt.cm.tab10(np.arange(len(SOURCES)) / 10)))
MMSI_COLORS = dict(zip(MMSI_LIST, plt.cm.Set1(np.arange(len(MMSI_LIST)) / 9)))


# ---------------------------------------------------------------------------
# Loaders — return DataFrame with columns [mmsi, ts, lat, lon]
# ---------------------------------------------------------------------------

def load_nc(pattern: str) -> pd.DataFrame:
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"  [warn] no files matched: {pattern}")
        return pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"])
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
                np.isin(mmsi, MMSI_LIST) &
                (lat >= BBOX["lat_min"]) & (lat <= BBOX["lat_max"]) &
                (lon >= BBOX["lon_min"]) & (lon <= BBOX["lon_max"])
            )
            if mask.any():
                chunks.append(pd.DataFrame({
                    "mmsi": mmsi[mask], "ts": ts[mask],
                    "lat": lat[mask],   "lon": lon[mask],
                }))
        except Exception as e:
            print(f"  [warn] {path}: {e}")
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"])


def load_aisdb(db_path: str) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        print(f"  [warn] not found: {db_path}")
        return pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"])
    mmsi_str = ",".join(str(m) for m in MMSI_LIST)
    con = sqlite3.connect(db_path)
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) if r[0].endswith("_dynamic")]
    frames = []
    for tbl in tables:
        df = pd.read_sql_query(
            f"""SELECT mmsi, time AS ts, latitude AS lat, longitude AS lon
                FROM {tbl}
                WHERE time >= {T_START} AND time < {T_END}
                  AND mmsi IN ({mmsi_str})
                  AND latitude  BETWEEN {BBOX['lat_min']} AND {BBOX['lat_max']}
                  AND longitude BETWEEN {BBOX['lon_min']} AND {BBOX['lon_max']}""",
            con,
        )
        frames.append(df)
    con.close()
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"])


def load_reference(csv_dir: str) -> pd.DataFrame:
    zips = sorted(glob.glob(f"{csv_dir}/*.csv.zip"))
    if not zips:
        print(f"  [warn] no csv.zip in {csv_dir}")
        return pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"])
    chunks = []
    for zip_path in zips:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    df = pd.read_csv(f, usecols=["mmsi", "latitude", "longitude", "reception_timestamp"])
                df = df[df["mmsi"].isin(MMSI_LIST)].copy()
                if df.empty:
                    continue
                df["ts"] = (
                    (pd.to_datetime(df["reception_timestamp"]) - pd.Timestamp("1970-01-01"))
                    // pd.Timedelta("1s")
                )
                df = df[
                    (df["ts"] >= T_START) & (df["ts"] < T_END) &
                    df["latitude"].between(BBOX["lat_min"], BBOX["lat_max"]) &
                    df["longitude"].between(BBOX["lon_min"], BBOX["lon_max"])
                ][["mmsi", "ts", "latitude", "longitude"]].rename(
                    columns={"latitude": "lat", "longitude": "lon"}
                )
                if len(df):
                    chunks.append(df)
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=["mmsi", "ts", "lat", "lon"])


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_map(data: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(1, len(SOURCES), figsize=(5 * len(SOURCES), 5), constrained_layout=True)
    fig.suptitle("Scotian Shelf vessel tracks — 2025-12-30 UTC", fontsize=12)

    for ax, src in zip(axes, SOURCES):
        df = data[src]
        for mmsi in MMSI_LIST:
            sub = df[df["mmsi"] == mmsi].sort_values("ts")
            if sub.empty:
                continue
            ax.scatter(sub["lon"], sub["lat"], s=1.5, color=MMSI_COLORS[mmsi],
                       alpha=0.6, linewidths=0)
        ax.set_xlim(BBOX["lon_min"], BBOX["lon_max"])
        ax.set_ylim(BBOX["lat_min"], BBOX["lat_max"])
        n = len(df)
        ax.set_title(f"{src}\n({n:,} pts)", fontsize=8)
        ax.set_xlabel("Longitude", fontsize=7)
        ax.set_ylabel("Latitude", fontsize=7)
        ax.tick_params(labelsize=6)

    legend_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=MMSI_COLORS[m],
               markersize=6, label=str(m))
        for m in MMSI_LIST
    ]
    axes[-1].legend(handles=legend_handles, title="MMSI", fontsize=6,
                    title_fontsize=7, loc="lower right")

    out = PLOTS_DIR / "vessel_tracks_map.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved: {out}")


def plot_latlon_time(data: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(
        len(MMSI_LIST), 2,
        figsize=(14, 3 * len(MMSI_LIST)),
        constrained_layout=True,
        sharex=False,
    )
    fig.suptitle("Latitude / Longitude vs time — Scotian Shelf — 2025-12-30 UTC", fontsize=12)

    axes[0, 0].set_title("Latitude", fontsize=9)
    axes[0, 1].set_title("Longitude", fontsize=9)

    fmt = mdates.DateFormatter("%H:%M")
    loc = mdates.HourLocator(interval=3)

    for row, mmsi in enumerate(MMSI_LIST):
        ax_lat = axes[row, 0]
        ax_lon = axes[row, 1]

        ax_lat.set_ylabel(f"MMSI\n{mmsi}", fontsize=7, labelpad=4)

        for src in SOURCES:
            sub = data[src][data[src]["mmsi"] == mmsi].sort_values("ts")
            if sub.empty:
                continue
            t = pd.to_datetime(sub["ts"], unit="s", utc=True)
            c = SRC_COLORS[src]
            ax_lat.plot(t, sub["lat"], lw=0.8, alpha=0.8, color=c, label=src)
            ax_lon.plot(t, sub["lon"], lw=0.8, alpha=0.8, color=c, label=src)

        for ax in (ax_lat, ax_lon):
            ax.xaxis.set_major_formatter(fmt)
            ax.xaxis.set_major_locator(loc)
            ax.tick_params(labelsize=6)
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")

        if row == 0:
            ax_lon.legend(fontsize=6, loc="upper right", title="source", title_fontsize=7)

    out = PLOTS_DIR / "vessel_latlon_time.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved: {out}")


# ---------------------------------------------------------------------------

def main():
    loaders = {
        "original_nm4":       (load_nc,        str(DATA_DIR / "original/nm4/Dynamic_*.nc")),
        "original_streaming": (load_nc,        str(DATA_DIR / "original/streaming/Dynamic_*.nc")),
        "aisdb_nm4":          (load_aisdb,     str(DATA_DIR / "decode_nm4.db")),
        "aisdb_streaming":    (load_aisdb,     str(DATA_DIR / "decode_streaming.db")),
        "reference_csv":      (load_reference, str(REF_CSV_DIR)),
    }

    data: dict[str, pd.DataFrame] = {}
    for name, (fn, arg) in loaders.items():
        print(f"Loading {name}...")
        df = fn(arg)
        print(f"  {len(df):,} records, {df['mmsi'].nunique()} MMSI found")
        data[name] = df

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    print("\nGenerating map plot...")
    plot_map(data)
    print("Generating lat/lon vs time plot...")
    plot_latlon_time(data)


if __name__ == "__main__":
    main()
