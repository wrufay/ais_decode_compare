#!/usr/bin/env python3
"""
proof/oob_coordinates.py

Demonstrates that the original decoder passes through physically impossible
lat/lon coordinates — specifically the AIS spec sentinel values (lat=91,
lon=181) which indicate "position not available" but are stored as-is rather
than treated as null.

Run from repo root:
    .venv/bin/python proof/oob_coordinates.py
"""

import netCDF4
import numpy as np

NC_PATH = "data/original/streaming/Dynamic_CCG_AIS_UTC_Log_2025-12-30.nc"

ds = netCDF4.Dataset(NC_PATH)
mmsi = np.array(ds.variables["mmsi"][:], dtype=np.int64)
lat  = np.array(ds.variables["latitude"][:], dtype=float)
lon  = np.array(ds.variables["longitude"][:], dtype=float)
ds.close()

not_sentinel = mmsi != -9999
not_nan      = ~np.isnan(lat) & ~np.isnan(lon)
in_bounds    = (lat >= -90) & (lat <= 90) & (lon >= -180) & (lon <= 180)

total        = not_sentinel.sum()
out_of_bounds = (not_sentinel & not_nan & ~in_bounds).sum()
pct          = 100 * out_of_bounds / total

print("=" * 60)
print("Out-of-bounds coordinate check")
print(f"Source: {NC_PATH}")
print("=" * 60)
print(f"\nTotal valid records:     {total:,}")
print(f"Out-of-bounds lat/lon:   {out_of_bounds:,}  ({pct:.2f}%)")
print(f"\nFull lat range:  {lat[not_sentinel & not_nan].min():.4f}  to  {lat[not_sentinel & not_nan].max():.4f}  (valid: -90 to 90)")
print(f"Full lon range:  {lon[not_sentinel & not_nan].min():.4f}  to  {lon[not_sentinel & not_nan].max():.4f}  (valid: -180 to 180)")

# Breakdown by sentinel type
oob_mask = not_sentinel & not_nan & ~in_bounds
oob_lat  = lat[oob_mask]
oob_lon  = lon[oob_mask]

print("\nMost common out-of-bounds coordinate pairs:")
import pandas as pd
pairs = pd.DataFrame({"lat": oob_lat, "lon": oob_lon})
print(pairs.value_counts().head(10).to_string())

print("""
Note: lat=91.0 and lon=181.0 are the AIS specification sentinel values
meaning "position not available". The original decoder stores them as-is.
aisdb filters these out. Neither is wrong — they made different design
choices about how to handle missing position data.
""")

print("Sample out-of-bounds records:")
oob_mmsi = mmsi[oob_mask][:10]
print(f"  {'MMSI':>12}  {'lat':>10}  {'lon':>10}")
for m, la, lo in zip(oob_mmsi, oob_lat[:10], oob_lon[:10]):
    print(f"  {m:>12}  {la:>10.4f}  {lo:>10.4f}")
