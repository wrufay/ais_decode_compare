#!/usr/bin/env python
"""
This code is to generate the output of AIS decoded data in nc files:
  
Author: Lanli Guo
Publish date: May 01, 2020
"""
############################################################################## 
#from scipy.io import netcdf
import netCDF4  
import numpy as np

##############For Dynamic Output##############################################
#def write_dyn(fnameout,datenum_dyn,type_dyn,
#              repeat_dyn,mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,
#              course_dyn,heading_dyn,Dindex):
def write_dyn(fnameout,staregion_dyn,staname_dyn,datenum_dyn,type_dyn,
              repeat_dyn,mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,
              course_dyn,heading_dyn,Dindex):
    Dim = Dindex
    
    ncfout = netCDF4.Dataset(fnameout,'w')
    ncfout.description = "AIS_CCG Dynamic Information"
    ncfout.createDimension('Dindex',Dim)

    station_region =  ncfout.createVariable('station_region','S3',('Dindex',))  
    station_region[:]=np.array(staregion_dyn, dtype=object)
    station_region.long_name = "Station Region"
    station_region.missing_value = 'N/A'

    station_name =  ncfout.createVariable('station_name','S20',('Dindex',))  
    station_name[:]=np.array(staname_dyn, dtype=object)
    station_name.long_name = "Station Name"
    station_name.missing_value = 'N/A'

    date_num     =  ncfout.createVariable('date_num','i',('Dindex',))
    date_num[:]  =  np.array(datenum_dyn)
    date_num.long_name = "Seconds since 1970-Jan-01 00:00:00"
    date_num.missing_value = -9999    

    message_type   =  ncfout.createVariable('message_type','i',('Dindex',))
    message_type[:]=  np.array(type_dyn)
    message_type.long_name = "Message Type"
    message_type.missing_value = -9999
    
    repeat       =  ncfout.createVariable('repeat','i',('Dindex',))
    repeat[:]    =  np.array(repeat_dyn)
    repeat.long_name = "Repeat"
    repeat.missing_value = -9999

    mmsi       =  ncfout.createVariable('mmsi','i',('Dindex',))
    mmsi[:]    =  np.array(mmsi_dyn)
    mmsi.long_name = "MMSI"
    mmsi.missing_value = -9999
    mmsi.description = "Less than 9 digits, add '0' to the left"
    
    status     =  ncfout.createVariable('status','i',('Dindex',))
    status[:]  =  np.array(status_dyn)
    status.long_name = "Status"
    status.missing_value = -9999

    speed     =  ncfout.createVariable('speed','f',('Dindex',))
    speed[:]  =  np.array(speed_dyn)
    speed.long_name = "Speed"
    speed.units     = "knot"
    speed.missing_value = np.nan
    speed.description = "Value 102.2 indicates 102.2 knots or higher"

    accuracy  =  ncfout.createVariable('accuracy','i',('Dindex',))
    accuracy[:]  =  np.array(accuracy_dyn)
    accuracy.long_name = "Accuracy"
    accuracy.missing_value = -9999

    longitude  =  ncfout.createVariable('longitude','d',('Dindex',))
    longitude[:]  =  np.array(lon_dyn)
    longitude.long_name = "Longitude"
    longitude.units     = "degree"
    longitude.missing_value = np.nan

    latitude  =  ncfout.createVariable('latitude','d',('Dindex',))
    latitude[:]  =  np.array(lat_dyn)
    latitude.long_name = "Latitude"
    latitude.units     = "degree"
    latitude.missing_value = np.nan

    course  =  ncfout.createVariable('course','f',('Dindex',))
    course[:]  =  np.array(course_dyn)
    course.long_name = "Course"
    course.units     = "degree"
    course.missing_value = np.nan

    heading =  ncfout.createVariable('heading','f',('Dindex',))
    heading[:]  =  np.array(heading_dyn)
    heading.long_name = "Heading"
    heading.units     = "degree"
    heading.missing_value = np.nan

    ncfout.close()
    
    return fnameout

#################For Static Output############################################

#def write_sta(fnameout,datenum_sta,type_sta,
#              repeat_sta,mmsi_sta,shiptype_sta,stern_sta,port_sta,
#              starboard_sta,bow_sta,draught_sta,Sindex):
def write_sta(fnameout,staregion_sta,staname_sta,datenum_sta,type_sta,
              repeat_sta,mmsi_sta,shipname_sta,shiptype_sta,stern_sta,port_sta,
              starboard_sta,bow_sta,draught_sta,destination_sta,Sindex):
    Dim = Sindex
    
    ncfout = netCDF4.Dataset(fnameout,'w')
    ncfout.description = "AIS_CCG Static Information"
    
    ncfout.createDimension('Sindex',Dim)

    station_region =  ncfout.createVariable('station_region','S3',('Sindex',))  
    station_region[:]=np.array(staregion_sta, dtype=object)
    station_region.long_name = "Station Region"
    station_region.missing_value = "N/A"
    
    station_name =  ncfout.createVariable('station_name','S20',('Sindex',))  
    station_name[:]=np.array(staname_sta, dtype=object)
    station_name.long_name = "Station Name"
    station_name.missing_value = "N/A"

    date_num     =  ncfout.createVariable('date_num','i',('Sindex',))
    date_num[:]  =  np.array(datenum_sta)
    date_num.long_name = "Seconds since 1970-Jan-01 00:00:00"
    date_num.missing_value = -9999    

    message_type   =  ncfout.createVariable('message_type','i',('Sindex',))
    message_type[:]=  np.array(type_sta)
    message_type.long_name = "Message Type"
    message_type.missing_value = -9999

    repeat       =  ncfout.createVariable('repeat','i',('Sindex',))
    repeat[:]    =  np.array(repeat_sta)
    repeat.long_name = "Repeat"
    repeat.missing_value = -9999

    mmsi       =  ncfout.createVariable('mmsi','i',('Sindex',))
    mmsi[:]    =  np.array(mmsi_sta)
    mmsi.long_name = "MMSI"
    mmsi.missing_value = -9999
    mmsi.description = "less than 9 digits, add '0' to the left"
    
    shipname     =  ncfout.createVariable('shipname','S20',('Sindex',))
    shipname[:]  =  np.array(shipname_sta, dtype=object)
    shipname.long_name = "Ship Name"
    shipname.missing_value = "N/A"
    
    shiptype     =  ncfout.createVariable('shiptype','i',('Sindex',))
    shiptype[:]  =  np.array(shiptype_sta)
    shiptype.long_name = "Ship Type"
    shiptype.missing_value = -9999

    stern  =  ncfout.createVariable('stern','f',('Sindex',))
    stern[:]  =  np.array(stern_sta)
    stern.long_name = "Dimension to Stern meters"
    stern.units     = "m"
    stern.missing_value = np.nan

    port  =  ncfout.createVariable('port','f',('Sindex',))
    port[:]  =  np.array(port_sta)
    port.long_name = "Dimension to Port meters"
    port.units     = "m"
    port.missing_value = np.nan

    starboard  =  ncfout.createVariable('starboard','f',('Sindex',))
    starboard[:]  =  np.array(starboard_sta)
    starboard.long_name = "Dimension to Starboard meters"
    starboard.units     = "m"
    starboard.missing_value = np.nan

    bow  =  ncfout.createVariable('bow','f',('Sindex',))
    bow[:]  =  np.array(bow_sta)
    bow.long_name = "Dimension to Bow meters"
    bow.units     = "m"
    bow.missing_value = np.nan
    
    draught =  ncfout.createVariable('draught','f',('Sindex',))
    draught[:]  =  np.array(draught_sta)
    draught.long_name = "Draught"
    draught.units     = "m"
    draught.missing_value = np.nan
    
    destination     =  ncfout.createVariable('destination','S20',('Sindex',))
    destination[:]  =  np.array(destination_sta, dtype=object)
    destination.long_name = "Destination"
    destination.missing_value = "N/A"
    
    ncfout.close()
    
    return fnameout

#############################################################################
