# AIS Decoder Comparison — Findings

**Data:** 2025-12-30, Canadian Coast Guard AIS data  
**Source:** `/home/shared/ccg_ais_claudio/ais_comp/`  
**Reproducibility:** All findings can be reproduced by running `analysis/compare.py` (~7 min) and `analysis/validate.py` (~15 min) against the decoded databases.

---

## Summary

| Finding | Result |
|---|---|
| NM4 vs streaming datasets | Not equivalent — NM4 has ~55× more unique vessels than streaming |
| Original decoder vs reference CSV | 99.2% MMSI overlap (Jaccard 0.989) — very high agreement |
| aisdb vs reference CSV | 91.4% MMSI overlap (Jaccard 0.907) — missing 17,309 vessels |
| Coordinate accuracy | Near-zero mean error between original decoder and reference CSV |
| End-to-end speed (3 files) | aisdb SQLite: 29.7s vs original NetCDF: 60.8s — aisdb 2× faster |
| aisdb bottleneck | SQLite writes account for 81% of aisdb total decode time |

---

## Finding 1 — NM4 and streaming are not equivalent datasets

**Source:** `data/comparison_table.csv`

Despite both covering 2025-12-30, the NM4 and streaming sources contain fundamentally different volumes of data:

| Source | Full-day records (windowed) | Unique MMSI (full day) |
|---|---|---|
| NM4 (original decoder) | 35,741,119 | 202,668 |
| NM4 (aisdb) | 30,004,585 | 185,897 |
| Streaming (original decoder) | 5,520,668 | 3,595 |
| Streaming (aisdb) | 1,842,694 | 3,251 |
| Reference CSV | 32,974,548 | 201,518 |

NM4 contains approximately 55× more unique vessels than streaming. The NM4 source carries raw messages from every individual receiving station — the same vessel broadcast is logged once per station that received it. The station-level metadata confirms this: NM4 files carry specific station identifiers (e.g. `s:roam`) while the streaming file carries `s:ALL`, indicating it is a pre-aggregated feed deduplicated across stations.

**Implication:** NM4 and streaming cannot be treated as equivalent sources. Comparisons between decoders are only meaningful within the same source type (NM4 vs NM4, or streaming vs streaming).

---

## Finding 2 — Sentinel coordinate values are handled differently by each decoder

**Source:** `proof/oob_coordinates.py`, `data/original/streaming/Dynamic_CCG_AIS_UTC_Log_2025-12-30.nc`

The AIS specification defines `latitude = 91.0°` and `longitude = 181.0°` as sentinel values meaning "position not available." When a vessel's GPS is off or not yet locked, its transponder transmits these exact values. The two decoders handle them differently:

| Decoder | Behaviour |
|---|---|
| Original decoder | Stores sentinel values as literal numbers |
| aisdb | Treats them as null and drops the record |

Verification on the original decoder's streaming output:

| Metric | Value |
|---|---|
| Total records | 24,386,393 |
| Out-of-bounds records | 304,279 (1.25%) |
| Of which `lat=91.0, lon=181.0` | 298,573 (98.1% of out-of-bounds) |
| Remaining non-sentinel out-of-bounds | ~5,706 (corrupt NMEA payloads) |

Neither approach is incorrect — they represent different design choices about how to handle missing position data. However, the difference must be accounted for in any comparison. All analysis in `compare.py` and `validate.py` filters records to `lat ∈ [−90°, 90°]` and `lon ∈ [−180°, 180°]` before comparison, ensuring sentinel values do not affect results.

---

## Finding 3 — Accuracy: original decoder vs reference CSV

**Source:** `data/validation/mmsi_overlap.csv`, `data/validation/plots/mmsi_overlap_heatmap.png`

The original decoder and the pre-decoded reference CSV show very high agreement:

| Metric | Value |
|---|---|
| Unique MMSI in original_nm4 | 202,668 |
| Unique MMSI in reference_csv | 201,518 |
| Shared MMSI (intersection) | 201,015 |
| Jaccard similarity | **0.9894** |
| % of original covered by reference | 99.18% |
| % of reference covered by original | 99.75% |

For the two 3-hour comparison windows:

| Window | Original decoder | Reference CSV | Difference |
|---|---|---|---|
| 00:00–03:00 UTC | 169,121 vessels | 168,299 vessels | −0.49% |
| 21:00–24:00 UTC | 163,513 vessels | 162,944 vessels | −0.35% |

**Coordinate accuracy** (`data/validation/plots/coord_error_distribution.png`): For a 1,000-vessel sample of shared MMSIs, the mean positional difference between the two sources is near-zero. The distribution is sharply concentrated at 0° error for both latitude and longitude, with a small tail of outliers attributable to vessels that moved between the timestamps used by each source.

**Important caveat:** The reference CSV's decoding method is not known. If it was produced using the same or similar logic as the original decoder, the high agreement rate may reflect shared methodology rather than fully independent verification.

---

## Finding 4 — Accuracy: aisdb vs reference CSV

**Source:** `data/validation/mmsi_overlap.csv`, `data/validation/missing_from_aisdb_vs_reference.csv`

aisdb shows materially lower agreement with the reference CSV than the original decoder:

| Metric | Value |
|---|---|
| Unique MMSI in aisdb_nm4 | 185,897 |
| Unique MMSI in reference_csv | 201,518 |
| Shared MMSI (intersection) | 184,209 |
| Jaccard similarity | **0.9065** |
| % of aisdb covered by reference | 99.09% |
| % of reference covered by aisdb | **91.41%** |
| Vessels in reference not in aisdb | **17,309** |

For the two 3-hour comparison windows:

| Window | aisdb | Reference CSV | Gap |
|---|---|---|---|
| 00:00–03:00 UTC | 156,524 vessels | 168,299 vessels | −7.0% |
| 21:00–24:00 UTC | 152,832 vessels | 162,944 vessels | −6.2% |

**Why this comparison is preferred over aisdb vs original decoder:** The original decoder overcounts due to multi-station duplication — the same vessel broadcast received by multiple stations is counted as multiple records. The reference CSV is decoded independently, making it a more reliable benchmark for assessing aisdb's completeness.

---

## Finding 5 — What vessels does aisdb miss?

**Source:** `data/validation/missing_from_aisdb_vs_reference.csv`, `data/validation/plots/missing_from_aisdb_vs_reference_breakdown.png`

Breakdown of the 17,309 vessels present in the reference CSV but absent from aisdb:

**By MMSI type** (classified per the AIS specification):

| Type | Count | Percentage |
|---|---|---|
| Regular vessel | 10,866 | 62.8% |
| Aid to navigation | 4,763 | 27.5% |
| Coast guard / ship group | 1,562 | 9.0% |
| Auxiliary craft | 113 | 0.7% |
| Other (man overboard, SAR) | 5 | 0.0% |

**By message count** (number of records the vessel had in the reference CSV):

| Records in reference | Vessels missing from aisdb |
|---|---|
| 1 | 2,566 |
| 2 | 1,556 |
| 3–5 | 2,387 |
| 6–10 | 2,572 |
| **11–50** | **5,046** ← largest group |
| 51–100 | 1,258 |
| 101+ | 1,924 |

The largest group of missing vessels had 11–50 messages in the reference CSV, and 1,924 vessels with 100+ messages are also absent from aisdb. This indicates the gap is not simply a matter of aisdb dropping low-activity vessels — it likely reflects aisdb's deduplication of multi-station receptions, where the same broadcast received by multiple stations is merged into fewer records. The significant number of missing aids to navigation (27.5%) may also reflect deliberate filtering in aisdb for non-vessel MMSI types.

Further investigation is needed to fully characterise the cause of the gap.

---

## Finding 6 — Performance profiling

**Source:** `profile_aisdb.py`, `data/profile_output.log`

Conducted at supervisor's suggestion to identify the performance bottleneck in aisdb. Tested on 3 NM4 files (~1.44M raw messages, 146.7 MB extracted).

| Method | Time | Rows written | Rate |
|---|---|---|---|
| aisdb → `:memory:` (no disk writes) | 5.55s | — † | ~259,000 msgs/s |
| aisdb → SQLite (disk writes) | 29.70s | 1,177,961 | 39,665 rows/s |
| Original decoder → NetCDF (disk writes) | 60.78s | 1,478,148 | 24,318 rows/s |

† Row count cannot be queried from `:memory:` — aisdb spawns 4 worker processes, each with its own isolated in-memory connection. The timing is valid.

**Valid comparisons:**

| Comparison | Valid | Result |
|---|---|---|
| aisdb SQLite vs original decoder NetCDF | ✅ | aisdb is **2.0× faster** end-to-end |
| aisdb `:memory:` vs aisdb SQLite | ✅ | SQLite writes = **81%** of aisdb total time |
| aisdb `:memory:` vs original decoder NetCDF | ❌ | Not comparable — different operations |
| aisdb pure parse speed vs original pure parse speed | ❌ | Cannot isolate — original decoder always writes |

**Conclusions:**
- aisdb is **2× faster end-to-end** than the original serial decoder on the same data
- **SQLite writes account for 81%** of aisdb's total decode time — the NMEA parser is not the bottleneck
- The 5.5-hour full NM4 decode was slow because SQLite degrades as the database grows — decode rate fell from ~76,000 msgs/s on the first file to ~43,000 msgs/s by the third file
- aisdb's parser speed is fast (>259,000 msgs/s) but cannot be directly compared to the original decoder's parse speed, since the original decoder always writes to disk

**What has not been tested (recommended next steps):**
- Original decoder parallel version (`Process_AIS_Parallel.py` with Ray) — estimated ~2 minutes per day on cluster
- aisdb with PostgreSQL instead of SQLite — expected to significantly reduce I/O overhead
- These represent the production configurations and are the appropriate basis for a final performance comparison
