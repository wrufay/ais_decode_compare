# Findings

## 1. NM4 and streaming are not equivalent datasets

Despite both covering the same day (2025-12-30), the NM4 and streaming sources contain fundamentally different volumes of data:

- Each 5-minute NM4 file contains ~450,000–570,000 messages
- The first 3 hours of NM4 alone (~18M messages) equals the entire streaming day (17.9M messages)

**Reason:** NM4 contains raw messages from every individual receiving station — the same vessel broadcast is logged once per station that picked it up. The streaming source appears to be a pre-aggregated feed, already deduplicated across stations. This is visible in the metadata: NM4 files carry specific station names (e.g. `s:roam`) while the streaming file carries `s:ALL`.

## 2. Sentinel values vs null — a design difference, not a bug

The original decoder stores the AIS spec "position not available" sentinel values (`lat=91.0, lon=181.0`) as literal numbers. aisdb treats them as null and drops them.

**Verified by:** `proof/oob_coordinates.py`

| Metric | Value |
|---|---|
| Total records checked | 24,386,393 |
| Out-of-bounds records | 304,279 (1.25%) |
| Of which `lat=91, lon=181` | 298,573 (98% of out-of-bounds) |
| Full lat range | -232.8° to 105.3° |
| Full lon range | -189.6° to 212.2° |

`lat=91` and `lon=181` are defined in the AIS specification as the sentinel values meaning "position not available". Neither decoder is wrong — they made different design choices:
- **Original decoder:** stores them as numbers (preserves the raw decoded value)
- **aisdb:** treats them as null (filters them before writing to the database)

The remaining ~6,000 out-of-bounds records (non-sentinel) appear to come from genuinely corrupt NMEA payloads.

**Fix applied in analysis:** `compare.py` filters all sources to `lat ∈ [-90, 90]` and `lon ∈ [-180, 180]` before comparison so sentinel values don't skew the results.

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

## 5. Validation results

Deep accuracy validation was run via `validate.py`, comparing all sources pairwise.

**MMSI set overlap (Jaccard similarity):**

| Pair | Jaccard | A covered by B | B covered by A |
|---|---|---|---|
| original_nm4 vs reference_csv | **0.989** | 99.18% | 99.75% |
| original_nm4 vs aisdb_nm4 | 0.910 | 91.32% | 99.56% |
| aisdb_nm4 vs reference_csv | 0.907 | 99.09% | 91.41% |

**Coordinate agreement (original_nm4 vs reference_csv, 1000 vessel sample):**
- Mean latitude error: < 0.001° for well-tracked vessels
- Full distribution in `data/validation/coord_error_distribution.png`

**Why aisdb misses ~17k vessels (original_nm4 vs aisdb_nm4 gap):**
- 41% had only 1–2 messages — likely dropped by aisdb's deduplication primary key
- 1,924 vessels with 100+ messages are also missing — worth investigating further
- MMSI type breakdown in `data/validation/missing_from_aisdb_vs_original.csv`

**Conclusion:**
The original decoder has higher **recall** — it captures more vessels and matches the reference CSV at 99.18%. aisdb has higher **precision** — it rejects out-of-bounds coordinates and deduplicates multi-station receptions. Which is "better" depends on the use case.

**Important caveat:** The reference CSV's decoding method is unknown. If it was produced by the same or similar decoder as the original script, the high match rate may reflect shared logic rather than independent ground truth.

Full validation outputs: `data/validation/`
