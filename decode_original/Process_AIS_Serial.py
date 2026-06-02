#!/usr/bin/env python
"""
The main process to deal with the AIS messages from Canadian Coast Guard:
 
To run the code need to set up the input and output folders!
 
The format of the .txt file should be  
    c:1506815999,C:2234,s:P-Calvert*4F
    !AIVDM,1,1,9,B,H4eGD9PP5=@D000000000000000,2*01
The format of the .csv file should be
    \c:1573012863,C:135,s:P-Gil*6F\!AIVDM,1,1,2,B,34Vf7j1000njujHNq31<sP840Dg:,0*28
Otherwise the code can't work
 
Author: Lanli Guo
Publish date: May 01, 2020
"""
##############################################################################  
from Second_layer_NMEA import *
from Output_format import *
from Read_AIS import *
from Write_netcdf import *
import time
import os
import csv
import sys

###############File Directory#################################################

if len(sys.argv) != 4:
    print("Usage:  <input_directory> <output_directory> <part_str>")
    sys.exit(1)

Input_Directory = sys.argv[1]
Output_Directory = sys.argv[2]
part_str = sys.argv[3]
####Need to set up!!!
#Outlog_Directory = '/tank0/store0/sli/data/ais_test_output'
Outlog_Directory = Output_Directory 
def lineDecode(ais_data,Station_region,Station_name,Station_time,dt_time,staregion_dyn,staname_dyn,
               datenum_dyn,type_dyn,repeat_dyn,mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,
               lat_dyn,course_dyn,heading_dyn,Dindex,staregion_sta,staname_sta,datenum_sta,
               type_sta,repeat_sta,mmsi_sta,shipname_sta,shiptype_sta,stern_sta,port_sta,
               starboard_sta,bow_sta,draught_sta,destination_sta,Sindex):
        
    if ais_data['type'] == 19:
        ais_format = format_ais(ais_data,'dyn')
        if ais_format == None:
            pass
        else:
            ais_format['Station region'] = Station_region
            ais_format['Station name']   = Station_name
            ais_format['Station time']   = Station_time
            ais_format['Datenum']        = dt_time
                        
            read_dyn(ais_format,staregion_dyn,staname_dyn,datenum_dyn,type_dyn,
                     repeat_dyn,mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,
                     lat_dyn,course_dyn,heading_dyn,Dindex)                               
                        
        ais_format = format_ais(ais_data,'sta')
        if ais_format == None:
                pass
        else:
            ais_format['Station region'] = Station_region
            ais_format['Station name']   = Station_name
            ais_format['Station time']   = Station_time
            ais_format['Datenum']        = dt_time
            
            read_sta(ais_format,staregion_sta,staname_sta,datenum_sta,type_sta,
                     repeat_sta,mmsi_sta,shipname_sta,shiptype_sta,stern_sta,port_sta,
                     starboard_sta,bow_sta,draught_sta,destination_sta,Sindex)
                                                              
    elif ais_data['type'] == 5 or ais_data['type'] == 24:
        ais_format = format_ais(ais_data,'sta')
        if ais_format == None:
            pass
        else:
            ais_format['Station region'] = Station_region
            ais_format['Station name']   = Station_name
            ais_format['Station time']   = Station_time
            ais_format['Datenum']        = dt_time
                        
            read_sta(ais_format,staregion_sta,staname_sta,datenum_sta,type_sta,
                     repeat_sta,mmsi_sta,shipname_sta,shiptype_sta,stern_sta,port_sta,
                     starboard_sta,bow_sta,draught_sta,destination_sta,Sindex)
                                 
    else:
        ais_format = format_ais(ais_data,'dyn')
        if ais_format == None:
            pass
        else:
            ais_format['Station region'] = Station_region
            ais_format['Station name']   = Station_name
            ais_format['Station time']   = Station_time
            ais_format['Datenum']        = dt_time
            
            read_dyn(ais_format,staregion_dyn,staname_dyn,datenum_dyn,type_dyn,
                     repeat_dyn,mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,
                     course_dyn,heading_dyn,Dindex)
    return

def main():
    mid_dir=os.listdir(Input_Directory)
    
    for f_name in os.listdir(Input_Directory):
        if part_str in f_name:
            infile  = Input_Directory+ "/ ".strip()+f_name
            out_dyn = Output_Directory+ "/ ".strip()+'Dynamic_'+f_name[:-4]+'.nc'
            out_sta = Output_Directory+ "/ ".strip()+'Static_'+f_name[:-4]+'.nc'
            out_log = Outlog_Directory+ "/ ".strip()+'Outlog_'+f_name[:-4]+'.txt'
    
            staregion_dyn = []
            staname_dyn   = []
            datenum_dyn   = []
            type_dyn      = []
            repeat_dyn    = []
            mmsi_dyn      = []
            status_dyn    = []
            speed_dyn     = []
            accuracy_dyn  = []
            lon_dyn       = []
            lat_dyn       = []
            course_dyn    = []
            heading_dyn   = []
            Dindex        = 0   
    
            staregion_sta = []
            staname_sta   = []
            datenum_sta   = []
            type_sta      = []
            repeat_sta    = []
            mmsi_sta      = []
            shipname_sta  = []
            shiptype_sta  = []
            stern_sta     = []
            port_sta      = []
            starboard_sta = []
            bow_sta       = []
            draught_sta   = []
            destination_sta = []
            Sindex        = 0
            
        ########To deal with .txt file################################################
            if f_name.endswith('.txt'):
    
                fin = open(infile, "r")
                Station_region = 'N/A'
                Station_name   = 'N/A'
                Station_time   = 'N/A'
                dt_time        = -9999
    
                for x in fin:                
                    if x.split(',')[0][0:2]=='c:' or x.split(',')[0][0:2]=='s:' or x.split(',')[0][0:2]=='C:':
                        Station_time   = 'N/A'
                        dt_time        = -9999
                        x  = x.replace("*",",")
                        x0 = x.replace("c:","$")
                        x1 = x0.split('$')[1]
                        x2 = x1.split(',')[0]
                        dt_obj=time.gmtime(float(x2)) 
                        dt_time = int(x2)
                        Station_time = time.strftime("%d-%b-%Y %H:%M:%S",dt_obj)
    
                        s0 = x.replace("s:","$")
                        if s0.find('-') != -1:
                            s1 = s0.split('$')[1]
                            s2 = s1.split(',')[0]
                            Station_region = s2.split('-')[0]
                            Station_name   = s2.split('-')[1]
                        else:
                            Station_region = 'N/A'
                            Station_name   = 'N/A'
                                
                    elif x.split(',')[0][0:5]=='!AIVD' and len(x.split(','))>6:
                        msg = x.rstrip('\n')
                        ais_data = decod_ais(msg,out_log)
                        if ais_data == None:
                            pass
                        else:
                            if len(ais_data)>4:
                                output = lineDecode(ais_data,Station_region,Station_name,Station_time,dt_time,staregion_dyn,staname_dyn,
                                                    datenum_dyn,type_dyn,repeat_dyn,mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,
                                                    lat_dyn,course_dyn,heading_dyn,Dindex,staregion_sta,staname_sta,datenum_sta,
                                                    type_sta,repeat_sta,mmsi_sta,shipname_sta,shiptype_sta,stern_sta,port_sta,
                                                    starboard_sta,bow_sta,draught_sta,destination_sta,Sindex)                               
                                    
                fin.close()
        ########To deal with .csv file################################################    
            if f_name.endswith('.csv'):
                     
                with open(infile, newline='') as csvfile:
                    spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|') 
                    for row in spamreader:
                        try:
                            xx = ''
                            for i in range(len(row)):
                                xx = xx+row[i]
                            if xx.find('\\',10) !=-1 and xx.count('AIVD')==1 :       
                                x = xx.split('!')[0]
                                x = x.replace('\\','')
                                x = x.replace("*",",")
                                if x.find('c:') != -1 and x.count('c:')==1 :
                                    Station_time   = 'N/A'
                                    dt_time        = -9999
                                    x0 = x.replace("c:","$")
                                    x1 = x0.split('$')[1]
                                    x2 = x1.split(',')[0]
                                    dt_obj=time.gmtime(float(x2))
                                    Station_time = time.strftime("%d-%b-%Y %H:%M:%S",dt_obj)
                                    dt_time = int(x2) 
                                
                                s0 = x.replace("s:","$")
                                if s0.find('-') != -1:
                                    s1 = s0.split('$')[1]
                                    s2 = s1.split(',')[0]
                                    Station_region = s2.split('-')[0]
                                    Station_name   = s2.split('-')[1]
                                else:
                                    Station_region = 'N/A'
                                    Station_name   = 'N/A'
        
                                yy = xx.replace('\\','$')
                                y = yy.split('$')[2]
                                if len(y.split(','))>6 and y.split(',')[6]!='' :
                                    if y.split(',')[0][0:5]=='!AIVD' :
                                    #    print(y)
                                        msg = y.rstrip('\n')
                                        
                                        ais_data = decod_ais(msg,out_log)
                                        if ais_data == None:
                                            pass
                                        else:
                                            if len(ais_data)>4:
                                                #try: 
                                                   output = lineDecode(ais_data,Station_region,Station_name,Station_time,dt_time,staregion_dyn,staname_dyn,
                                                                       datenum_dyn,type_dyn,repeat_dyn,mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,
                                                                       lat_dyn,course_dyn,heading_dyn,Dindex,staregion_sta,staname_sta,datenum_sta,
                                                                       type_sta,repeat_sta,mmsi_sta,shipname_sta,shiptype_sta,stern_sta,port_sta,
                                                                       starboard_sta,bow_sta,draught_sta,destination_sta,Sindex)                               
                        except:
                            pass
        ########Save the output to .nc file###########################################
            #write_dyn(out_dyn,datenum_dyn,type_dyn,repeat_dyn,mmsi_dyn,status_dyn,
            #          speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,course_dyn,heading_dyn,Dindex)
            write_dyn(out_dyn,staregion_dyn,staname_dyn,datenum_dyn,type_dyn,repeat_dyn,mmsi_dyn,status_dyn,
                      speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,course_dyn,heading_dyn,Dindex)
            
            write_sta(out_sta,staregion_sta,staname_sta,datenum_sta,type_sta,repeat_sta,mmsi_sta,shipname_sta,
                      shiptype_sta,stern_sta,port_sta,starboard_sta,bow_sta,draught_sta,destination_sta,Sindex)
           # write_sta(out_sta,datenum_sta,type_sta,repeat_sta,mmsi_sta,
            #          shiptype_sta,stern_sta,port_sta,starboard_sta,bow_sta,draught_sta,Sindex)


if __name__ == '__main__':
    
    main()

##############################################################################
