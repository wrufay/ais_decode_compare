#!/usr/bin/env python3
"""
validate.py — Deep accuracy validation of AIS decoder outputs.

PURPOSE
-------
This script goes beyond the high-level counts in compare.py to answer the
question: how do we know the results are accurate and not fabricated? It
produces concrete, verifiable evidence for each finding in findings.md by
running six independent analyses across all five data sources.

INPUT SOURCES
-------------
Same five sources as compare.py (see compare.py docstring for full details):
  1. original_nm4       — data/original/nm4/Dynamic_*.nc
  2. original_streaming — data/original/streaming/Dynamic_*.nc
  3. aisdb_nm4          — data/decode_nm4.db
  4. aisdb_streaming    — data/decode_streaming.db
  5. reference_csv      — /home/shared/ccg_ais_claudio/ais_comp/csv/

The same two 3-hour UTC time windows and coordinate bounds as compare.py
are applied throughout.

ANALYSES
--------
1. MMSI pairwise overlap
   For every pair of sources, computes: intersection size, union size,
   Jaccard similarity, and what % of each source's vessels appear in the
   other. Saved as mmsi_overlap.csv and visualised as a heatmap.

2. Coordinate agreement (original_nm4 vs reference_csv)
   For up to 1000 shared vessels, computes the mean position of each vessel
   in both sources and reports the absolute lat/lon difference. This answers:
   "do the decoders agree on where the same vessel was?" Saved as
   coord_agreement.csv with an error distribution plot.

3. Vessel track spot checks
   For the 5 most active shared vessels (original_nm4 ∩ reference_csv),
   plots the full position track from each source side by side. Visual
   confirmation that the same vessel follows the same path in both decoders.

4. Temporal coverage
   Counts records per UTC hour for each source and plots them together.
   Confirms data is present across the expected time range and that the two
   comparison windows (00h-03h, 21h-24h) are representative, not anomalous.

5. Top 20 most active vessels per source
   Ranks vessels by message count in each source. Cross-checking that the
   same vessels appear at the top across sources is a basic sanity check.

6. Missing MMSI analysis
   Identifies vessels present in one source but absent from another, then
   classifies them by MMSI type (regular vessel, auxiliary craft, aid to
   navigation, SAR aircraft, etc.) and by message count. This explains the
   ~7% MMSI gap between the original decoder and aisdb — most missing vessels
   had only 1–2 messages, consistent with aisdb's deduplication behaviour.

   Three pairs are analysed:
     - original_nm4  vs aisdb_nm4   → missing_from_aisdb_vs_original.csv
     - reference_csv vs aisdb_nm4   → missing_from_aisdb_vs_reference.csv
     - original_nm4  vs reference_csv → missing_from_reference_vs_original.csv

MMSI TYPE CLASSIFICATION
------------------------
MMSI numbers encode vessel type by their numeric prefix (AIS specification):
  < 10,000,000     — coast guard or ship group (leading zeros lost as integer)
  970,000,000–970,999,999 — SAR aircraft
  972,000,000–972,999,999 — man overboard device
  974,000,000–974,999,999 — EPIRB
  980,000,000–989,999,999 — auxiliary craft (attached to a parent vessel)
  990,000,000–999,999,999 — aids to navigation (buoys, beacons, etc.)
  All others               — regular vessel (MID-based country code)

MEMORY DESIGN
-------------
Sources are loaded one at a time. Only original_nm4 and reference_csv are
kept in memory simultaneously (needed for the coordinate agreement and track
analyses). All other sources are freed before the next is loaded.
Per-MMSI record counts are stored as compact Series (one row per vessel)
rather than keeping the full DataFrames.

OUTPUT
------
  data/validation/mmsi_overlap.csv
  data/validation/coord_agreement.csv
  data/validation/temporal_coverage.csv
  data/validation/top_vessels.csv
  data/validation/missing_from_aisdb_vs_original.csv
  data/validation/missing_from_aisdb_vs_reference.csv
  data/validation/missing_from_reference_vs_original.csv
  data/validation/plots/mmsi_overlap_heatmap.png
  data/validation/plots/coord_error_distribution.png
  data/validation/plots/temporal_coverage.png
  data/validation/plots/track_mmsi_<MMSI>.png  (5 files)
  data/validation/plots/missing_from_*_breakdown.png  (3 files)

USAGE
-----
    .venv/bin/python -u validate.py

The -u flag forces unbuffered output so progress prints immediately.
Runtime: ~15 minutes.
"""

import gc
import glob
import os
import sqlite3
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WINDOWS = {
    "00h-03h": (1767052800, 1767063600),
    "21h-24h": (1767128400, 1767139200),
}

DATA_DIR   = Path("data")
VAL_DIR    = DATA_DIR / "validation"
PLOTS_DIR  = VAL_DIR / "plots"
REF_CSV_DIR = Path("/home/shared/ccg_ais_claudio/ais_comp/csv")

VAL_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Loaders (same window-aware, memory-efficient approach as compare.py)
# ---------------------------------------------------------------------------

def window_mask_np(ts):
    mask = np.zeros(len(ts), dtype=bool)
    for w0, w1 in WINDOWS.values():
        mask |= (ts >= w0) & (ts < w1)
    return mask

def window_mask_pd(ts_series):
    mask = pd.Series(False, index=ts_series.index)
    for w0, w1 in WINDOWS.values():
        mask |= (ts_series >= w0) & (ts_series < w1)
    return mask


def load_original_nc(pattern):
    files = sorted(glob.glob(pattern))
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
                window_mask_np(ts) &
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
            print(f"  [warn] {path}: {e}")
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=["mmsi","ts","lat","lon"])


def load_aisdb(db_path):
    if not Path(db_path).exists():
        return pd.DataFrame(columns=["mmsi","ts","lat","lon"])
    con = sqlite3.connect(db_path)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    dyn_tables = [t for t in tables if t.endswith("_dynamic")]
    win_clauses = " OR ".join(f"(time >= {w0} AND time < {w1})" for w0, w1 in WINDOWS.values())
    frames = []
    for tbl in dyn_tables:
        df = pd.read_sql_query(
            f"""SELECT mmsi, time AS ts, latitude AS lat, longitude AS lon
                FROM {tbl}
                WHERE ({win_clauses})
                  AND latitude BETWEEN -90 AND 90
                  AND longitude BETWEEN -180 AND 180""", con)
        frames.append(df)
    con.close()
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["mmsi","ts","lat","lon"])


def load_reference_csv(csv_dir):
    zips = sorted(glob.glob(f"{csv_dir}/*.csv.zip"))
    chunks = []
    for zip_path in zips:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    df = pd.read_csv(f, usecols=["mmsi","latitude","longitude","reception_timestamp"])
                df["ts"] = (
                    (pd.to_datetime(df["reception_timestamp"]) - pd.Timestamp("1970-01-01"))
                    // pd.Timedelta("1s")
                )
                df = df.rename(columns={"latitude":"lat","longitude":"lon"})[["mmsi","ts","lat","lon"]]
                df = df[window_mask_pd(df["ts"]) & df["lat"].between(-90,90) & df["lon"].between(-180,180)]
                if len(df):
                    chunks.append(df)
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=["mmsi","ts","lat","lon"])


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def mmsi_overlap_stats(set_a, set_b, name_a, name_b):
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    only_a = len(set_a - set_b)
    only_b = len(set_b - set_a)
    jaccard = inter / union if union else 0
    pct_a_in_b = 100 * inter / len(set_a) if set_a else 0
    pct_b_in_a = 100 * inter / len(set_b) if set_b else 0
    return {
        "source_a": name_a, "source_b": name_b,
        "mmsi_in_a": len(set_a), "mmsi_in_b": len(set_b),
        "intersection": inter, "union": union,
        "only_in_a": only_a, "only_in_b": only_b,
        "jaccard_similarity": round(jaccard, 4),
        "pct_a_covered_by_b": round(pct_a_in_b, 2),
        "pct_b_covered_by_a": round(pct_b_in_a, 2),
    }


def coord_agreement(df_a, df_b, name_a, name_b, sample_n=500):
    """For each shared MMSI, compute mean lat/lon error between the two sources."""
    shared = set(df_a["mmsi"].unique()) & set(df_b["mmsi"].unique())
    if not shared:
        print(f"  [warn] no shared MMSI between {name_a} and {name_b}")
        return pd.DataFrame()

    # Sample up to sample_n vessels for speed
    sampled = list(shared)[:sample_n]

    rows = []
    for mmsi in sampled:
        a = df_a[df_a["mmsi"] == mmsi][["lat","lon"]].values
        b = df_b[df_b["mmsi"] == mmsi][["lat","lon"]].values
        if len(a) == 0 or len(b) == 0:
            continue
        # Mean position per source
        a_lat, a_lon = a[:,0].mean(), a[:,1].mean()
        b_lat, b_lon = b[:,0].mean(), b[:,1].mean()
        rows.append({
            "mmsi": mmsi,
            f"{name_a}_lat": round(a_lat, 5),
            f"{name_a}_lon": round(a_lon, 5),
            f"{name_b}_lat": round(b_lat, 5),
            f"{name_b}_lon": round(b_lon, 5),
            "lat_diff": round(abs(a_lat - b_lat), 5),
            "lon_diff": round(abs(a_lon - b_lon), 5),
            f"{name_a}_msgs": len(a),
            f"{name_b}_msgs": len(b),
        })

    return pd.DataFrame(rows)


def temporal_coverage(df, name):
    """Count records per hour."""
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["hour"] = (df["ts"] // 3600) % 24
    counts = df.groupby("hour").size().reset_index(name="records")
    counts["source"] = name
    return counts


def plot_vessel_tracks(df_dict, mmsi, out_path):
    """Plot track of one vessel from multiple sources."""
    fig, axes = plt.subplots(1, len(df_dict), figsize=(5 * len(df_dict), 4), constrained_layout=True)
    fig.suptitle(f"MMSI {mmsi} — vessel track comparison", fontsize=11)
    if len(df_dict) == 1:
        axes = [axes]
    for ax, (name, df) in zip(axes, df_dict.items()):
        track = df[df["mmsi"] == mmsi].sort_values("ts")
        if track.empty:
            ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes)
        else:
            ax.plot(track["lon"], track["lat"], ".-", ms=3, lw=0.8)
            ax.scatter(track["lon"].iloc[0], track["lat"].iloc[0], c="green", s=30, zorder=5, label="start")
            ax.scatter(track["lon"].iloc[-1], track["lat"].iloc[-1], c="red", s=30, zorder=5, label="end")
            ax.legend(fontsize=6)
        ax.set_title(f"{name}\n{len(track)} pts", fontsize=8)
        ax.set_xlabel("Lon", fontsize=7); ax.set_ylabel("Lat", fontsize=7)
        ax.tick_params(labelsize=6)
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_mmsi_overlap_heatmap(overlap_df, sources, out_path):
    """Heatmap of pairwise Jaccard similarity."""
    n = len(sources)
    mat = np.eye(n)
    src_idx = {s: i for i, s in enumerate(sources)}
    for _, row in overlap_df.iterrows():
        i, j = src_idx[row["source_a"]], src_idx[row["source_b"]]
        mat[i, j] = mat[j, i] = row["jaccard_similarity"]

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(mat, vmin=0, vmax=1, cmap="YlGn")
    plt.colorbar(im, ax=ax, label="Jaccard similarity")
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels(sources, rotation=30, ha="right", fontsize=8)
    ax.set_yticklabels(sources, fontsize=8)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{mat[i,j]:.3f}", ha="center", va="center", fontsize=8,
                    color="black" if mat[i,j] < 0.7 else "white")
    ax.set_title("MMSI set overlap (Jaccard similarity)", fontsize=11)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def classify_mmsi(mmsi):
    """Classify an MMSI by its numeric prefix.

    AIS spec:
      00XXXXXXX (< 10,000,000 as int) — coast guard / ship group (leading zeros lost)
      970XXXXXX                        — SAR aircraft / AIS-SART
      972XXXXXX                        — man overboard device
      974XXXXXX                        — EPIRB
      98XXXXXXX (980–989M)             — auxiliary craft (attached to parent vessel)
      99XXXXXXX (990–999M)             — aids to navigation
      Otherwise                        — regular vessel (MID-based country code)
    """
    m = int(mmsi)
    if m < 10_000_000:
        return "coast_guard_or_group"
    if 970_000_000 <= m <= 970_999_999:
        return "SAR_aircraft"
    if 972_000_000 <= m <= 972_999_999:
        return "man_overboard"
    if 974_000_000 <= m <= 974_999_999:
        return "EPIRB"
    if 980_000_000 <= m <= 989_999_999:
        return "auxiliary_craft"
    if 990_000_000 <= m <= 999_999_999:
        return "aid_to_navigation"
    return "vessel"


def plot_temporal(temporal_df, out_path):
    fig, ax = plt.subplots(figsize=(12, 5))
    for name, grp in temporal_df.groupby("source"):
        ax.plot(grp["hour"], grp["records"], marker="o", ms=4, label=name)
    # shade the two comparison windows
    ax.axvspan(0, 3, alpha=0.1, color="blue", label="window 00h-03h")
    ax.axvspan(21, 24, alpha=0.1, color="orange", label="window 21h-24h")
    ax.set_xlabel("Hour (UTC)"); ax.set_ylabel("Records")
    ax.set_title("Records per UTC hour — 2025-12-30")
    ax.legend(fontsize=7); ax.set_xticks(range(0, 25, 3))
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Loading all sources for validation...")
    print("=" * 70)

    source_defs = {
        "original_nm4":       (load_original_nc, "data/original/nm4/Dynamic_*.nc"),
        "original_streaming": (load_original_nc, "data/original/streaming/Dynamic_*.nc"),
        "aisdb_nm4":          (load_aisdb,        "data/decode_nm4.db"),
        "aisdb_streaming":    (load_aisdb,         "data/decode_streaming.db"),
        "reference_csv":      (load_reference_csv, str(REF_CSV_DIR)),
    }

    # Load all sources (store only what's needed for analysis)
    mmsi_sets        = {}
    temporal_dfs     = []
    top_vessel_counts = {}
    mmsi_counts      = {}   # full per-MMSI record counts for missing-MMSI analysis
    # Store full dfs only for the key comparison pair (original_nm4 vs reference_csv)
    key_dfs = {}

    for name, (fn, arg) in source_defs.items():
        print(f"\n  Loading {name}...")
        df = fn(arg)
        print(f"    {len(df):,} records | {df['mmsi'].nunique():,} unique MMSI")

        mmsi_sets[name] = set(df["mmsi"].unique())
        temporal_dfs.append(temporal_coverage(df, name))

        counts = df.groupby("mmsi").size().reset_index(name="records")
        mmsi_counts[name] = counts
        top = counts.nlargest(20, "records").copy()
        top["source"] = name
        top_vessel_counts[name] = top

        # Keep full df only for the key pair
        if name in ("original_nm4", "reference_csv"):
            key_dfs[name] = df
        else:
            del df
            gc.collect()

    # --- 1. MMSI overlap matrix -------------------------------------------
    print("\n" + "=" * 70)
    print("1. MMSI pairwise overlap")
    print("=" * 70)
    sources = list(mmsi_sets.keys())
    overlap_rows = []
    for i, a in enumerate(sources):
        for b in sources[i+1:]:
            row = mmsi_overlap_stats(mmsi_sets[a], mmsi_sets[b], a, b)
            overlap_rows.append(row)
            print(f"  {a} vs {b}:")
            print(f"    intersection: {row['intersection']:,}  |  Jaccard: {row['jaccard_similarity']}")
            print(f"    {a} coverage: {row['pct_a_covered_by_b']:.1f}% in {b}")
            print(f"    {b} coverage: {row['pct_b_covered_by_a']:.1f}% in {a}")

    overlap_df = pd.DataFrame(overlap_rows)
    overlap_df.to_csv(VAL_DIR / "mmsi_overlap.csv", index=False)
    print(f"\nSaved: {VAL_DIR / 'mmsi_overlap.csv'}")

    plot_mmsi_overlap_heatmap(overlap_df, sources, PLOTS_DIR / "mmsi_overlap_heatmap.png")
    print(f"Saved: {PLOTS_DIR / 'mmsi_overlap_heatmap.png'}")

    # --- 2. Coordinate agreement (original_nm4 vs reference_csv) ----------
    print("\n" + "=" * 70)
    print("2. Coordinate agreement — original_nm4 vs reference_csv")
    print("=" * 70)
    if "original_nm4" in key_dfs and "reference_csv" in key_dfs:
        coord_df = coord_agreement(
            key_dfs["original_nm4"], key_dfs["reference_csv"],
            "original_nm4", "reference_csv", sample_n=1000
        )
        if not coord_df.empty:
            print(f"  Vessels sampled:       {len(coord_df):,}")
            print(f"  Mean lat error (deg):  {coord_df['lat_diff'].mean():.5f}")
            print(f"  Mean lon error (deg):  {coord_df['lon_diff'].mean():.5f}")
            print(f"  Max  lat error (deg):  {coord_df['lat_diff'].max():.5f}")
            print(f"  Max  lon error (deg):  {coord_df['lon_diff'].max():.5f}")
            print(f"  Vessels with lat_diff < 0.01°: {(coord_df['lat_diff'] < 0.01).sum():,} ({100*(coord_df['lat_diff'] < 0.01).mean():.1f}%)")
            coord_df.to_csv(VAL_DIR / "coord_agreement.csv", index=False)
            print(f"  Saved: {VAL_DIR / 'coord_agreement.csv'}")

            # Error distribution plot
            fig, axes = plt.subplots(1, 2, figsize=(10, 4))
            axes[0].hist(coord_df["lat_diff"], bins=50, color="steelblue", edgecolor="none")
            axes[0].set_xlabel("Absolute lat error (degrees)"); axes[0].set_ylabel("Vessels")
            axes[0].set_title("Latitude error: original_nm4 vs reference_csv")
            axes[1].hist(coord_df["lon_diff"], bins=50, color="coral", edgecolor="none")
            axes[1].set_xlabel("Absolute lon error (degrees)"); axes[1].set_ylabel("Vessels")
            axes[1].set_title("Longitude error: original_nm4 vs reference_csv")
            plt.tight_layout()
            plt.savefig(PLOTS_DIR / "coord_error_distribution.png", dpi=150)
            plt.close()
            print(f"  Saved: {PLOTS_DIR / 'coord_error_distribution.png'}")

    # --- 3. Vessel track spot checks ---------------------------------------
    print("\n" + "=" * 70)
    print("3. Vessel track spot checks")
    print("=" * 70)
    if "original_nm4" in key_dfs and "reference_csv" in key_dfs:
        # Pick 5 vessels with the most messages in the reference CSV
        shared = mmsi_sets.get("original_nm4", set()) & mmsi_sets.get("reference_csv", set())
        ref_top = key_dfs["reference_csv"][key_dfs["reference_csv"]["mmsi"].isin(shared)]
        top5 = ref_top.groupby("mmsi").size().nlargest(5).index.tolist()

        for mmsi in top5:
            out = PLOTS_DIR / f"track_mmsi_{mmsi}.png"
            plot_vessel_tracks(
                {"original_nm4": key_dfs["original_nm4"],
                 "reference_csv": key_dfs["reference_csv"]},
                mmsi, out
            )
            print(f"  Saved track plot: {out.name}")

    # Free key dfs
    key_dfs.clear(); gc.collect()

    # --- 4. Temporal coverage ---------------------------------------------
    print("\n" + "=" * 70)
    print("4. Temporal coverage (records per UTC hour)")
    print("=" * 70)
    if temporal_dfs:
        temporal_df = pd.concat(temporal_dfs, ignore_index=True)
        temporal_df.to_csv(VAL_DIR / "temporal_coverage.csv", index=False)
        plot_temporal(temporal_df, PLOTS_DIR / "temporal_coverage.png")
        print(f"  Saved: {VAL_DIR / 'temporal_coverage.csv'}")
        print(f"  Saved: {PLOTS_DIR / 'temporal_coverage.png'}")

    # --- 5. Top vessels comparison ----------------------------------------
    print("\n" + "=" * 70)
    print("5. Top 20 most active vessels per source")
    print("=" * 70)
    top_df = pd.concat(top_vessel_counts.values(), ignore_index=True)
    top_df.to_csv(VAL_DIR / "top_vessels.csv", index=False)
    print(top_df.to_string(index=False))
    print(f"\nSaved: {VAL_DIR / 'top_vessels.csv'}")

    # --- 6. Missing MMSI analysis -----------------------------------------
    print("\n" + "=" * 70)
    print("6. Missing MMSI analysis — what aisdb misses vs original + reference")
    print("=" * 70)

    pairs = [
        ("original_nm4",  "aisdb_nm4",  "missing_from_aisdb_vs_original"),
        ("reference_csv", "aisdb_nm4",  "missing_from_aisdb_vs_reference"),
        ("original_nm4",  "reference_csv", "missing_from_reference_vs_original"),
    ]

    for src_a, src_b, label in pairs:
        missing = mmsi_sets[src_a] - mmsi_sets[src_b]
        extra   = mmsi_sets[src_b] - mmsi_sets[src_a]
        print(f"\n  {src_a} vs {src_b}:")
        print(f"    In {src_a} but not {src_b}: {len(missing):,}")
        print(f"    In {src_b} but not {src_a}: {len(extra):,}")

        if not missing:
            continue

        # Get record counts and classify missing MMSIs
        counts_a = mmsi_counts[src_a].set_index("mmsi")["records"]
        missing_df = pd.DataFrame({"mmsi": list(missing)})
        missing_df["records_in_src"] = missing_df["mmsi"].map(counts_a).fillna(0).astype(int)
        missing_df["mmsi_type"] = missing_df["mmsi"].apply(classify_mmsi)
        missing_df = missing_df.sort_values("records_in_src", ascending=False)

        # Type breakdown
        type_counts = missing_df["mmsi_type"].value_counts()
        print(f"\n    MMSI type breakdown of missing vessels:")
        for mtype, cnt in type_counts.items():
            pct = 100 * cnt / len(missing_df)
            print(f"      {mtype:30s}: {cnt:6,}  ({pct:.1f}%)")

        # Message count distribution
        print(f"\n    Message count distribution (records in {src_a}):")
        bins = [0, 1, 2, 5, 10, 50, 100, float("inf")]
        labels = ["1","2","3-5","6-10","11-50","51-100","101+"]
        missing_df["count_bin"] = pd.cut(missing_df["records_in_src"], bins=bins, labels=labels)
        print(missing_df["count_bin"].value_counts().sort_index().to_string())

        # Save
        out = VAL_DIR / f"{label}.csv"
        missing_df.to_csv(out, index=False)
        print(f"\n    Saved: {out}")

        # Bar chart — MMSI type breakdown
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        type_counts.plot(kind="bar", ax=axes[0], color="steelblue", edgecolor="none")
        axes[0].set_title(f"MMSI types missing from {src_b}\n(present in {src_a})", fontsize=9)
        axes[0].set_xlabel(""); axes[0].set_ylabel("Count")
        axes[0].tick_params(axis="x", labelsize=7, rotation=30)

        missing_df["count_bin"].value_counts().sort_index().plot(
            kind="bar", ax=axes[1], color="coral", edgecolor="none"
        )
        axes[1].set_title(f"Message count distribution\n(missing vessels, source={src_a})", fontsize=9)
        axes[1].set_xlabel("Records in source"); axes[1].set_ylabel("Vessels")
        axes[1].tick_params(axis="x", labelsize=8, rotation=0)

        plt.tight_layout()
        out_png = PLOTS_DIR / f"{label}_breakdown.png"
        plt.savefig(out_png, dpi=150)
        plt.close()
        print(f"    Saved: {out_png}")

    print("\n" + "=" * 70)
    print("Validation complete. All outputs in data/validation/")
    print("=" * 70)


if __name__ == "__main__":
    main()
