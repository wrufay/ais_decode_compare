# Findings

## 1. NM4 and streaming are not equivalent datasets

Despite both covering the same day (2025-12-30), the NM4 and streaming sources contain fundamentally different volumes of data:

- Each 5-minute NM4 file contains ~450,000–570,000 messages
- The first 3 hours of NM4 alone (~18M messages) equals the entire streaming day (17.9M messages)

**Reason:** NM4 contains raw messages from every individual receiving station — the same vessel broadcast is logged once per station that picked it up. The streaming source appears to be a pre-aggregated feed, already deduplicated across stations. This is visible in the metadata: NM4 files carry specific station names (e.g. `s:roam`) while the streaming file carries `s:ALL`.

## 2. The original decoder passes through invalid coordinates

The original decoder (`Process_AIS_Serial.py`) does not validate lat/lon values after decoding. Approximately **1.35% of records** in the streaming output contained physically impossible coordinates (e.g. lat = 105°, lon = 212°). These come from corrupt or malformed NMEA payloads that decode to garbage values.

The aisdb decoder appears to handle this more strictly. This difference in permissiveness is worth investigating in the final comparison.

**Fix applied:** `compare.py` filters all sources to `lat ∈ [-90, 90]` and `lon ∈ [-180, 180]` before any analysis.

## 3. Runtime difference between decoders is not a measure of quality

The original decoder finished the NM4 job in ~2 hours; the aisdb decoder took 3.5+ hours on the same data. This does not mean the original decoder is faster or better. The difference is entirely due to output format:

- **Original decoder** writes simple binary `.nc` files — no constraints, no indexing, no deduplication. Fast by design.
- **aisdb** writes to a structured SQLite database with primary key deduplication, index maintenance, and post-processing (checksum generation, static aggregation). These are useful features but add significant I/O overhead, especially as the database grows (12GB+).

The actual NMEA parsing speed is likely comparable between the two since aisdb uses compiled Rust under the hood.

## 4. Accuracy comparison results

Comparison run on two 3-hour UTC windows (00:00–03:00 and 21:00–24:00) of 2025-12-30 NM4 data against the pre-decoded reference CSVs.

| Source | 00h–03h vessels | 21h–24h vessels |
|---|---|---|
| original decoder (NM4) | 169,121 | 163,513 |
| reference CSV | 168,299 | 162,944 |
| aisdb (NM4) | 156,524 | 152,832 |
| original decoder (streaming) | 3,244 | 3,369 |
| aisdb (streaming) | 2,906 | 3,033 |

**Key finding:** The original decoder matches the reference CSV within ~0.5% on unique MMSI counts. aisdb is consistently ~7% lower than both.

**Why aisdb is lower:** aisdb deduplicates records using a primary key on `(mmsi, time, longitude, latitude, sog, cog, source)`. When the same vessel broadcast is received by multiple stations with slightly different timestamps, the original decoder counts each reception separately while aisdb may merge or drop some. This likely accounts for the ~7% gap.

**Streaming vs NM4:** Both streaming sources show only ~3,000 unique vessels vs ~160,000+ from NM4, confirming that streaming is a heavily filtered/aggregated subset of the data, not an equivalent representation of the full day.

Full results: `data/comparison_table.csv` | Plots: `data/plots/`
