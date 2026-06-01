#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 22 17:28:44 2020

update AIS processing data with Lanli's May 15 Code
a) netcdf output
b) using ray for parallel processing 

@author: xuj
"""

# from process_AIS_Onefile_Parallel_0427 import groupList,lineDecode

from Second_layer_NMEA import *
from Output_format import * 

from Read_AIS import *
from Write_netcdf import *

import time
import ray
import os
import sys
import csv
import numpy as np 

# numCpu=51
numCpu=20

ray.init(num_cpus = numCpu)

def lineDecode(row,staregion_dyn,staname_dyn,datenum_dyn,type_dyn,
                  repeat_dyn,mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,
                  course_dyn,heading_dyn,Dindex,staregion_sta,staname_sta,datenum_sta,type_sta,
                  repeat_sta,mmsi_sta,shipname_sta,shiptype_sta,stern_sta,port_sta,
              starboard_sta,bow_sta,draught_sta,destination_sta,Sindex):
    
    xx = ''
    for i in range(len(row)):
        xx = xx+row[i]
    if xx.find('\\',10) !=-1 and xx.count('AIVD')==1 :       
        x = xx.split('!')[0]
        x = x.replace('\\','')
        x  = x.replace("*",",")
        if x.find('c:') != -1 and x.count('c:')==1 :
            x0 = x.replace("c:","$")
            x1 = x0.split('$')[1]
            x2 = x1.split(',')[0]
            dt_time = float(x2) 
        else:
            dt_time  = float('nan')
        
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
                msg = y.rstrip('\n')
                
                #ais_data = decod_ais(msg,out_log)
                if ais_data == None:
                    pass
                else:
                    if len(ais_data)>4:
                        if ais_data['type'] == 19:
                            ais_format = format_ais(ais_data,'dyn')
                            if ais_format == None:
                                pass
                            else:
                                ais_format['Station region'] = Station_region
                                ais_format['Station name']   = Station_name
                                ais_format['Datenum']        = dt_time
                                
                                read_dyn(ais_format,staregion_dyn,staname_dyn,datenum_dyn,type_dyn,
                                         repeat_dyn,mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,
                                         course_dyn,heading_dyn,Dindex)
                                
                            ais_format = format_ais(ais_data,'sta')
                            if ais_format == None:
                                pass
                            else:
                                ais_format['Station region'] = Station_region
                                ais_format['Station name']   = Station_name
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
                                ais_format['Datenum']        = dt_time
                                
                                read_dyn(ais_format,staregion_dyn,staname_dyn,datenum_dyn,type_dyn,
                                         repeat_dyn,mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,
                                         course_dyn,heading_dyn,Dindex)     
    pass

    return 
                    

def groupList(total,numGroups):
    countofgroups = np.floor(total/numGroups)
    remain = total%numGroups
    
    print(remain)
    
    segs =[]
    
    for i in np.arange(numGroups):
        segi = np.arange(countofgroups*i,countofgroups*(i+1))
        segs.append(segi)
        
    
    segRemain=np.arange(countofgroups*(i+1),countofgroups*(i+1)+remain)
    
    segs.append(segRemain)
    # print(len(segs))
    # print(segs)
    
    return(segs)

def process_incremental(sum, result): 
    # time.sleep(1) # Replace this with some processing code. 
    return sum + result 

def groupDecode(rows,i,out_dyn,out_sta):

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
    
    out_dyni = out_dyn+'_'+str(i).rjust(3,'0')+'.nc'
    out_stai = out_sta+'_'+str(i).rjust(3,'0')+'.nc'
    
    decodeI=0   # count all the messages been decoded
    for row in rows:

        output = lineDecode(row,staregion_dyn,staname_dyn,datenum_dyn,type_dyn,
                  repeat_dyn,mmsi_dyn,status_dyn,speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,
                  course_dyn,heading_dyn,Dindex,staregion_sta,staname_sta,datenum_sta,type_sta,
                  repeat_sta,mmsi_sta,shipname_sta,shiptype_sta,stern_sta,port_sta,
              starboard_sta,bow_sta,draught_sta,destination_sta,Sindex)
        
        decodeI+=1

    if len(staregion_dyn)> 0:
        write_dyn(out_dyni,staregion_dyn,staname_dyn,datenum_dyn,type_dyn,repeat_dyn,mmsi_dyn,status_dyn,
              speed_dyn,accuracy_dyn,lon_dyn,lat_dyn,course_dyn,heading_dyn,Dindex)

    if len(staregion_sta)> 0:
        write_sta(out_stai,staregion_sta,staname_sta,datenum_sta,type_sta,repeat_sta,mmsi_sta,shipname_sta,
              shiptype_sta,stern_sta,port_sta,starboard_sta,bow_sta,draught_sta,destination_sta,Sindex)

    return decodeI


@ray.remote
def work(spami,ii,out_dyn,out_sta):
     
    numberofDecoded= groupDecode(spami,ii,out_dyn,out_sta)
    return len(spami),ii,numberofDecoded


def main():
    ###############File Directory###############################
    ####Need to set up!!!
    Input_Directory  = '/tank0/store0/sli/data/ais_decode_test/'
    ####Need to set up!!!
    Output_Directory = '/tank0/store0/sli/data/ais_test_output/parr_test/'
    ####Need to set up!!!
    Outlog_Directory = '/tank0/store0/sli/data/ais_test_output/parr_test/'
    
    for f_name in os.listdir(Input_Directory):
        print(f_name)
        out_log = Outlog_Directory+ "\ ".strip()+'Outlog_'+f_name[:-4]+'.txt'    
        ####To deal with .csv file    
        if f_name.endswith('.csv'):

            infile  = Input_Directory+ f_name
            out_dyn = Output_Directory+ 'Dynamic_'+f_name[:-4]
            out_sta = Output_Directory+ 'Static_'+f_name[:-4]
    
            
            with open(infile, newline='') as csvfile:
                spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|') 
                spamreader = list(spamreader)
            
            numofProcess= numCpu-1
                            
            totalLines= len(spamreader)
            print(totalLines)
            
            segs = groupList(totalLines,numofProcess)

            allSpam = np.array(spamreader) 
            spamreader =[]

            start = time.time() 
            totalSeg = len(segs)
            totalI = np.arange(0,totalSeg)
            
            spamSeg=[]
            for segi,ii in zip(segs,totalI):
                segIdx= segi.astype(int)
                spami = allSpam[segIdx]     
                spamSeg.append(spami)
            
            allSpam=[]
            
            result_ids = [work.remote(spamSeg[ii],ii,out_dyn,out_sta) for ii in totalI] 
            
            
            if True:
                sum = 0 
                while len(result_ids): 
                    done_id, result_ids = ray.wait(result_ids) 
                    
                    orginalNum,ii,decodedNum = ray.get(done_id[0])
                    
                    sum = process_incremental(sum,decodedNum) 
                    print("duration =", time.time() - start, "\nresult = ", sum)



##############################################################################

if __name__ == '__main__':
    t0 = time.perf_counter()

    main()
    t1 = time.perf_counter()
    
    print("Time elapsed: ", t1-t0)
