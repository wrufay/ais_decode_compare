#!/usr/bin/env python3
"""
proof/oob_coordinates.py — Verify Finding #2 from findings.md.

PURPOSE
-------
Provides concrete, reproducible proof that the original decoder
(Process_AIS_Serial.py) stores AIS sentinel coordinate values as numbers
rather than filtering them out, while aisdb treats them as null.

BACKGROUND
----------
The AIS specification defines two sentinel values to indicate that a vessel's
position is not currently available:
  - latitude  = 91.0°   (outside the valid range of -90 to 90)
  - longitude = 181.0°  (outside the valid range of -180 to 180)

When a vessel's GPS is off or not yet locked, its AIS transponder transmits
these exact values. A decoder can either:
  (a) Store them as numbers — what Process_AIS_Serial.py does
  (b) Treat them as null and drop the record — what aisdb does

Neither approach is wrong; they are different design choices. However, the
difference means the original decoder's output contains physically impossible
coordinates that must be filtered before analysis.

WHAT THIS SCRIPT SHOWS
-----------------------
- Total records and what % have out-of-bounds coordinates
- The full lat/lon range (shows extreme values from sentinel + corrupt data)
- That 98% of out-of-bounds records are exactly lat=91, lon=181 (the sentinel)
- The remaining ~2% are from genuinely corrupt NMEA payloads
- Sample rows showing specific affected MMSIs

EXPECTED OUTPUT (2025-12-30 streaming source)
---------------------------------------------
  Total valid records:     24,386,393
  Out-of-bounds lat/lon:   304,279  (1.25%)
  Most common pair:        lat=91.0, lon=181.0  →  298,573 records (98%)

INPUT
-----
  data/original/streaming/Dynamic_CCG_AIS_UTC_Log_2025-12-30.nc
  (output of Process_AIS_Serial.py on the streaming source)

USAGE
-----
  .venv/bin/python proof/oob_coordinates.py

Must be run from the repo root directory.
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
