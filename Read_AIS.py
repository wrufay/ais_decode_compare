#!/usr/bin/env python
"""
This code is to collect the decoded data from each message, and prepare to
save the output of AIS decoded data in nc files:
 
Author: Lanli Guo
Publish date: May 01, 2020
"""
###########For Dynamic Output#################################################
def read_dyn(ais_format,staregion_dyn,staname_dyn,datenum_dyn,type_dyn,repeat_dyn,
             mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,course_dyn,
             heading_dyn,Dindex):
   
    staregion_dyn.append(ais_format['Station region'])
    staname_dyn.append(ais_format['Station name'])
    datenum_dyn.append(ais_format['Datenum'])
    type_dyn.append(ais_format['type'])
    repeat_dyn.append(ais_format['repeat'])
    mmsi_dyn.append(ais_format['mmsi'])
    status_dyn.append(ais_format['status'])
    speed_dyn.append(ais_format['speed'])
    accuracy_dyn.append(ais_format['accuracy'])
    lon_dyn.append(ais_format['lon'])
    lat_dyn.append(ais_format['lat'])
    course_dyn.append(ais_format['course'])
    heading_dyn.append(ais_format['heading'])
    Dindex += 1

    return staregion_dyn,staname_dyn,datenum_dyn,type_dyn,repeat_dyn,mmsi_dyn,status_dyn,\
           speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,course_dyn,heading_dyn,Dindex

##############For Static Output###############################################
def read_sta(ais_format,staregion_sta,staname_sta,datenum_sta,type_sta,repeat_sta,
             mmsi_sta,shipname_sta,shiptype_sta,stern_sta,port_sta,starboard_sta,
             bow_sta,draught_sta,destination_sta,Sindex):

    staregion_sta.append(ais_format['Station region'])
    staname_sta.append(ais_format['Station name'])
    datenum_sta.append(ais_format['Datenum'])
    type_sta.append(ais_format['type'])
    repeat_sta.append(ais_format['repeat'])
    mmsi_sta.append(ais_format['mmsi'])
    shipname_sta.append(ais_format['shipname'])
    shiptype_sta.append(ais_format['shiptype'])
    stern_sta.append(ais_format['to_stern'])
    port_sta.append(ais_format['to_port'])
    starboard_sta.append(ais_format['to_starboard'])
    bow_sta.append(ais_format['to_bow'])
    draught_sta.append(ais_format['draught'])
    destination_sta.append(ais_format['destination'])
    Sindex += 1

    return staregion_sta,staname_sta,datenum_sta,type_sta,repeat_sta,mmsi_sta,shipname_sta,\
           shiptype_sta,stern_sta,port_sta,starboard_sta,bow_sta,draught_sta,destination_sta,Sindex

##############################################################################
