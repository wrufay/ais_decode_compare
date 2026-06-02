# Comparing AIS binary data decoding scripts

## The scripts

- _decode_original_ directory = original Python script written by DFO, documentation here:
  https://publications.gc.ca/collections/collection_2023/mpo-dfo/Fs97-18-360-eng.pdf

  - Key notes: Creates .nc files as output

- _decode_aisdb.py_ = new decoding script using AISdb package, notably using the decode_msgs function, documentation here: https://aisviz.cs.dal.ca/AISdb/api/aisdb.database.decoder.html
  - Key notes: Writes to a SQLite database as output

## Objective

Compare the outputs of both scripts. Primarily:

1. **Number of unique vessels (MMSI)**
2. **Routes by plotting lat. and long.**

Additionally, observe differences in speed and efficiency of both scripts.

## Data sources

Destination of source data on CSRF Linux computer:
_/home/shared/ccg_ais_claudio/ais_comp_

After running both scripts on the two raw data sources (**streaming** and **NM4** directories) producing a total of four different outputs, we compare the results against pre-decoded data in the **csv** directory.

## Ongoing observations - June 1st, 2026

- The original script finished decoding faster than the AISdb script, perhaps because of the use of parallel programming. It took 115 minutes to run on the .nm4 in the NM4 directory, producing 288 Dynamic + 288 Static .nc files.
