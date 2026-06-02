In this repository we have two scripts to decode raw AIS data - the original, which writes to .nc files, and the aisdb one which writes to a SQLite database.

We are trying to compare the outputs of these files, primarily number of unique vessels (MMSI) as well as the routes by plotting their lat and long points.

We have three data sources, found at the destination /home/shared/ccg_ais_claudio/ais_comp
Inside this directory, there are three directories names csv, NM4 and streaming. We want to run both of the scripts on the NM4 and streaming files, then comparing the output to each other as WELL as the csv data, which is comprised of already decoded AIS data.

Please read through all of the files to understand how each of the scripts work, determine the best way to run them safely, have the outputs all be inside this repository and eventually create a nice table or visual for comparison, either through running a Python script or something else. 

Please list all the steps that you will take, inside an md file called procedure.