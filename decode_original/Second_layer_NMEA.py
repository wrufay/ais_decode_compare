#!/usr/bin/env python
"""
Python functions to decode some ais_data/AIVDM messages:
Original author: Pierre Payen
From https://github.com/pirpyn/pyAISm
 
This code could deal with type 1, 2, 3, 4, 5, 6(2 kinds), 7, 8(2 kinds), 
9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, and
27 AIS messages.  
 
Some functions were built based on the documents, and hadn't been
testified.
  
Edited: Lanli Guo
Publish date: May 01, 2020
"""
#################################################################################
import logging
from decode_original.First_layer_NMEA import *

def decod_data(data):
    # decode AIS payload and return a dictionary with key:value
    # doc : http://catb.org/gpsd/AIVDM.html
    # @param (string) data : '11110011000101....' by pack of 6 bits
    # @return (dict) ais_data : {'type':18, etc...}
    type_nb = int(data[0:6],2)

    def decod_1(data): # Message types 1,2,3
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['status']       = int(data[38:42],2)
        ais_data['turn']         = sign_int(data[42:50])
        ais_data['speed']        = int(data[50:60], 2)
        ais_data['accuracy']     = data[60]
        ais_data['lon']          = sign_int(data[61:89]) / 600000.0
        ais_data['lat']          = sign_int(data[89:116]) / 600000.0
        ais_data['course']       = int(data[116:128],2) * 0.1
        ais_data['heading']      = int(data[128:137],2)
        ais_data['second']       = int(data[137:143],2)
        ais_data['maneuver']     = int(data[143:145],2)
        ais_data['raim']         = data[148]
        ais_data['radio']        = int(data[149:168], 2)
        return ais_data

    def decod_4(data):
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['year']         = int(data[38:52], 2)
        ais_data['month']        = int(data[52:56], 2)
        ais_data['day']          = int(data[56:61], 2)
        ais_data['hour']         = int(data[61:66], 2)
        ais_data['minute']       = int(data[66:72], 2)
        ais_data['second']       = int(data[72:78], 2)
        ais_data['accuracy']     = data[78]
        ais_data['lon']          = sign_int(data[79:107]) / 600000.0
        ais_data['lat']          = sign_int(data[107:134]) / 600000.0
        ais_data['epfd']         = int(data[134:138], 2)
        ais_data['raim']         = data[148]
        ais_data['radio']        = int(data[149:168], 2)
        return ais_data

    def decod_5(data):
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['ais_version']  = int(data[38:40],2)
        ais_data['imo']          = int(data[40:70],2)
        ais_data['callsign']     = decod_str(data[70:112])
        ais_data['shipname']     = decod_str(data[112:232])
        ais_data['shiptype']     = int(data[232:240],2)
        ais_data['to_bow']       = int(data[240:249],2)
        ais_data['to_stern']     = int(data[249:258],2)
        ais_data['to_port']      = int(data[258:264],2)
        ais_data['to_starboard'] = int(data[264:270],2)
        ais_data['epfd']         = int(data[270:274],2)
        ais_data['month']        = int(data[274:278],2)
        ais_data['day']          = int(data[278:283],2)
        ais_data['hour']         = int(data[283:288],2)
        ais_data['minute']       = int(data[288:294],2)
        ais_data['draught']      = float(int(data[294:302],2)/10)
        ais_data['destination']  = decod_str(data[302:422])
        ais_data['dte']          = data[422]
        return ais_data

    def decod_6(data):
        ###### This code is based on the document, ######         
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['seqnumber']    = int(data[38:40],2)
        ais_data['destmmsi']     = int(data[40:70],2)
        ais_data['retransmit']   = data[70]
        ais_data['dac']          = int(data[72:82],2)
        ais_data['fid']          = int(data[82:88],2)
        ais_data['bidata']       = data[88:]
        if ais_data['dac'] == 1:
            if ais_data['fid'] == 18 and len(data) == 360:
                ais_data['linkage']  = int(data[88:98],2)
                ais_data['month']    = int(data[98:102],2)
                ais_data['day']      = int(data[102:107],2)
                ais_data['hour']     = int(data[107:112],2)
                ais_data['minute']   = int(data[112:118],2)
                ais_data['portname'] = decod_str(data[118:238])
                ais_data['destination'] = decod_str(data[238:268])
                ais_data['lon']      = sign_int(data[238:293]) / 60000.0
                ais_data['lat']      = sign_int(data[293:317]) / 60000.0
            if ais_data['fid'] == 20 and len(data) == 360:
                ais_data['linkage']  = int(data[88:98],2)
                ais_data['berthlength'] = int(data[98:107],2)
                ais_data['berthdepth']  = int(data[107:115],2)
                ais_data['berthdepth']  = int(data[107:115],2)
                ais_data['mooring_position'] = int(data[115:118],2)
                ais_data['month']       = int(data[118:122],2)
                ais_data['day']         = int(data[122:127],2)
                ais_data['hour']        = int(data[127:132],2)
                ais_data['minute']      = int(data[132:138],2)
                ais_data['availability']= data[138]
                ais_data['agent']       = int(data[139:141],2)
                ais_data['fuel']        = int(data[141:143],2)
                ais_data['tugs']        = int(data[171:173],2)                              
                ais_data['berthname']   = decod_str(data[191:311])
                ais_data['berthlon']    = sign_int(data[311:336]) / 60000.0
                ais_data['berthlat']    = sign_int(data[336:360]) / 60000.0
        return ais_data
        ###### but hasn't been testified           ######                

    def decod_7(data):
        ###### This code is based on the document, ######         
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['mmsi1']        = int(data[40:70],2)
        ais_data['seqmmsi1']     = int(data[70:72],2)        
        if len(data) > 104:
            ais_data['mmsi2']    = int(data[72:102],2)
            ais_data['seqmmsi2'] = int(data[102:104],2)
        if len(data) > 136:
            ais_data['mmsi3']    = int(data[104:134],2)
            ais_data['seqmmsi3'] = int(data[134:136],2)
        if len(data) > 167:
            ais_data['mmsi4']    = int(data[136:166],2)
            ais_data['seqmmsi4'] = int(data[166:168],2)
        return ais_data
        ###### but hasn't been testified           ######             

    def decod_8(data):
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['dac']          = int(data[40:50],2)
        ais_data['fid']          = int(data[50:56],2)
        if ais_data['dac'] == 1:
            if ais_data['fid'] == 11 and len(data) >=346:
                ais_data['lon']       = sign_int(data[56:80]) / 60000.0
                ais_data['lat']       = sign_int(data[80:105]) / 60000.0
                ais_data['day']       = int(data[105:110],2)
                ais_data['hour']      = int(data[110:115],2)
                ais_data['minute']    = int(data[115:121],2)
                ais_data['wspeed']    = int(data[121:128],2)
                ais_data['wgust']     = int(data[128:135],2)
                ais_data['wdir']      = int(data[135:144],2)
                ais_data['wgustdir']  = int(data[144:153],2)
                ais_data['airtemp']   = int(data[153:164],2)*0.1
                ais_data['rehumidity']= int(data[164:171],2)
                ais_data['dewpoint']  = int(data[171:181],2)*0.1
                ais_data['pressure']  = int(data[181:190],2)
                ais_data['pressuretend']  = int(data[190:192],2)
                ais_data['visibility']= int(data[192:200],2)
                ais_data['waterlevel']= int(data[200:209],2)*0.1
                ais_data['leveltrend']= int(data[209:211],2)
                ais_data['cspeed']    = int(data[211:219],2)*0.1
                ais_data['cdir']      = int(data[219:228],2)
                ais_data['cspeed2']   = int(data[228:236],2)*0.1
                ais_data['cdir2']     = int(data[236:245],2)
                ais_data['cdepth2']   = int(data[245:250],2)*0.1
                ais_data['cspeed3']   = int(data[250:258],2)
                ais_data['cdir3']     = int(data[258:267],2)
                ais_data['cdepth3']   = int(data[267:272],2)*0.1                
                ais_data['waveheight']= int(data[272:280],2)*0.1
                ais_data['waveperiod']= int(data[280:286],2)
                ais_data['wavedir']   = int(data[286:295],2)
                ais_data['swellheight'] = int(data[295:303],2)*0.1
                ais_data['swellperiod'] = int(data[303:309],2)
                ais_data['swelldir']  = int(data[309:318],2)
                ais_data['seastate']  = int(data[318:322],2)
                ais_data['watertemp'] = int(data[322:332],2)*0.1
                ais_data['preciptype']= int(data[332:335],2)
                ais_data['salinity']  = int(data[335:344],2)*0.1
                ais_data['ice']       = int(data[344:346],2)
            if ais_data['fid'] == 31 and len(data) >=350:
                ais_data['lon']       = sign_int(data[56:81]) / 60000.0
                ais_data['lat']       = sign_int(data[81:105]) / 60000.0
                ais_data['day']       = int(data[106:111],2)
                ais_data['hour']      = int(data[111:116],2)
                ais_data['minute']    = int(data[116:122],2)
                ais_data['wspeed']    = int(data[122:129],2)
                ais_data['wgust']     = int(data[129:136],2)
                ais_data['wdir']      = int(data[136:145],2)
                ais_data['wgustdir']  = int(data[145:154],2)
                ais_data['airtemp']   = int(data[154:165],2)*0.1
                ais_data['rehumidity']= int(data[165:172],2)
                ais_data['dewpoint']  = int(data[172:182],2)*0.1
                ais_data['pressure']  = int(data[182:191],2)
                ais_data['pressuretend']  = int(data[191:193],2)
                ais_data['maxvisibility'] = data[193]
                ais_data['visibility']= int(data[194:201],2)
                ais_data['waterlevel']= int(data[201:213],2)*0.01
                ais_data['leveltrend']= int(data[213:215],2)
                ais_data['cspeed']    = int(data[215:223],2)*0.1
                ais_data['cdir']      = int(data[223:232],2)
                ais_data['cspeed2']   = int(data[232:240],2)*0.1
                ais_data['cdir2']     = int(data[240:249],2)
                ais_data['cdepth2']   = int(data[249:254],2)*0.1
                ais_data['cspeed3']   = int(data[254:262],2)*0.1
                ais_data['cdir3']     = int(data[262:271],2)
                ais_data['cdepth3']   = int(data[271:276],2)*0.1             
                ais_data['waveheight']= int(data[276:284],2)*0.1
                ais_data['waveperiod']= int(data[284:290],2)
                ais_data['wavedir']   = int(data[290:299],2)
                ais_data['swellheight'] = int(data[299:307],2)*0.1
                ais_data['swellperiod'] = int(data[307:313],2)
                ais_data['swelldir']  = int(data[313:322],2)
                ais_data['seastate']  = int(data[322:326],2)
                ais_data['watertemp'] = int(data[326:336],2)*0.1
                ais_data['preciptype']= int(data[336:339],2)
                ais_data['salinity']  = int(data[339:348],2)*0.1
                ais_data['ice']       = int(data[348:350],2)                
        return ais_data

    def decod_9(data):
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['altitude']     = int(data[38:50],2)
        ais_data['speed']        = int(data[50:60], 2)/0.1
        ais_data['accuracy']     = data[60]
        ais_data['lon']          = sign_int(data[61:89]) / 600000.0
        ais_data['lat']          = sign_int(data[89:116]) / 600000.0
        ais_data['course']       = int(data[116:128],2) * 0.1
        ais_data['second']       = int(data[128:134],2)
        ais_data['dte']          = data[142]
        ais_data['assigned']     = data[146]        
        ais_data['raim']         = data[147]
        ais_data['radio']        = int(data[148:168], 2)
        return ais_data 

    def decod_10(data):
        ###### This code is based on the document, ######
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['seqnumber']    = int(data[38:40],2)
        ais_data['destmmsi']     = int(data[40:70],2)
        return ais_data
        ###### but hasn't been testified           ######    
    
    def decod_11(data):
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['year']         = int(data[38:52], 2)
        ais_data['month']        = int(data[52:56], 2)
        ais_data['day']          = int(data[56:61], 2)
        ais_data['hour']         = int(data[61:66], 2)
        ais_data['minute']       = int(data[66:72], 2)
        ais_data['second']       = int(data[72:78], 2)
        ais_data['accuracy']     = data[78]
        ais_data['lon']          = sign_int(data[79:107]) / 600000.0
        ais_data['lat']          = sign_int(data[107:134]) / 600000.0
        ais_data['epfd']         = int(data[134:138], 2)
        ais_data['raim']         = data[148]
        ais_data['syncstate']    = int(data[149:151], 2)
        ais_data['slottimeout']  = int(data[151:154], 2)
        ais_data['slotoffset']   = int(data[154:168], 2)
        return ais_data

    def decod_12(data):
        ###### This code is based on the document, ######
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['seqnumber']    = int(data[38:40],2)
        ais_data['destmmsi']     = int(data[40:70],2)
        ais_data['retransmit']   = data[70]
        if len(data) == 1008:
            ais_data['text']     = decod_str(data[72:1008])
        return ais_data
        ###### but hasn't been testified           ######    

    def decod_14(data):
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        xx = int((len(data)-40)/6)*6+41
        ais_data['text']         = decod_str(data[40:xx])
        return ais_data

    def decod_15(data):
        ###### This code is based on the document, ######
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['mmsi1']        = int(data[40:70],2)
        if len(data) > 88:
            ais_data['type11']       = int(data[70:76],2)
            ais_data['offset11']     = int(data[76:88],2)
        if len(data) > 110:
            ais_data['type12']   = int(data[90:96],2)
            ais_data['offset12'] = int(data[96:108],2)
        if len(data) > 158:
            ais_data['mmsi2']    = int(data[110:140],2)
            ais_data['type21']   = int(data[140:146],2)
            ais_data['offset21'] = int(data[146:158],2)            
        return ais_data
        ###### but hasn't been testified           ######    

    def decod_16(data):
        ###### This code is based on the document, ######
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['mmsi1']        = int(data[40:70],2)
        ais_data['offset1']      = int(data[70:82],2)
        ais_data['increment1']   = int(data[82:92],2)
        if len(data) == 144:
            ais_data['mmsi2']        = int(data[92:122],2)
            ais_data['offset2']      = int(data[122:134],2)
            ais_data['increment2']   = int(data[134:144],2)            
        return ais_data
        ###### but hasn't been testified           ######    

    def decod_17(data):
        ###### This code is based on the document, ######        
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['lon']          = sign_int(data[40:58]) / 600.0
        ais_data['lat']          = sign_int(data[58:75]) / 600.0
        ais_data['DGNSSdata']    = data[80:]
        return ais_data
        ###### but hasn't been testified           ######
        
    def decod_18(data):
        ais_data             = {'type':int(data[0:6],2)}
        ais_data['repeat']   = int(data[6:8],2)
        ais_data['mmsi']     = int(data[8:38],2)
        ais_data['speed']    = int(data[46:56],2)
        ais_data['accuracy'] = data[56]
        ais_data['lon']      = sign_int(data[57:85])/600000.0
        ais_data['lat']      = sign_int(data[85:112])/600000.0
        ais_data['course']   = int(data[112:124],2)*0.1
        ais_data['heading']  = int(data[124:133],2)
        ais_data['second']   = int(data[133:139],2)
        ais_data['regional'] = int(data[139:141],2)
        ais_data['cs']       = data[141]
        ais_data['display']  = data[142]
        ais_data['dsc']      = data[143]
        ais_data['band']     = data[144]
        ais_data['msg22']    = data[145]
        ais_data['assigned'] = data[146]
        ais_data['raim']     = data[147]
        ais_data['radio']    = int(data[148:168],2)
        return ais_data

    def decod_19(data):
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['speed']        = int(data[46:56],2)
        ais_data['accuracy']     = data[56]
        ais_data['lon']          = sign_int(data[57:85])/600000.0
        ais_data['lat']          = sign_int(data[85:112])/600000.0
        ais_data['course']       = int(data[112:124],2)*0.1
        ais_data['heading']      = int(data[124:133],2)
        ais_data['second']       = int(data[133:139],2)
        ais_data['regional']     = int(data[139:143],2)
        ais_data['shipname']     = decod_str(data[143:263])
        ais_data['shiptype']     = int(data[263:271],2)
        ais_data['to_bow']       = int(data[271:280],2)
        ais_data['to_stern']     = int(data[280:288],2)
        ais_data['to_port']      = int(data[289:295],2)
        ais_data['to_starboard'] = int(data[295:301],2)
        ais_data['epfd']         = int(data[301:305],2)
        ais_data['raim']         = data[305]
        ais_data['dte']          = data[306]
        ais_data['assigned']     = data[307]
        return ais_data
    
    def decod_20(data):
        ###### This code is based on the document, ######
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['offset1']      = int(data[40:52],2)
        ais_data['number1']      = int(data[52:56],2)
        ais_data['timeout1']     = int(data[56:59],2)
        ais_data['increment1']   = int(data[59:70],2)
        if len(data) > 100:
            ais_data['offset2']  = int(data[70:82],2)
            ais_data['number2']  = int(data[82:86],2)
            ais_data['timeout2'] = int(data[86:89],2)
            ais_data['increment2'] = int(data[89:100],2)
        if len(data) > 130:
            ais_data['offset3']  = int(data[100:112],2)
            ais_data['number3']  = int(data[112:116],2)
            ais_data['timeout3'] = int(data[116:119],2)
            ais_data['increment3'] = int(data[119:130],2)
        if len(data) > 159:
            ais_data['offset4']  = int(data[130:142],2)
            ais_data['number4']  = int(data[142:146],2)
            ais_data['timeout4'] = int(data[146:149],2)
            ais_data['increment4'] = int(data[149:160],2)            
        return ais_data
        ###### but hasn't been testified           ######
    
    def decod_21(data):
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['aid_type']     = int(data[38:43],2)
        ais_data['name']         = decod_str(data[43:163])
        ais_data['accuracy']     = data[163]
        ais_data['lon']          = sign_int(data[164:192]) / 600000.0
        ais_data['lat']          = sign_int(data[192:219]) / 600000.0
        ais_data['to_bow']       = int(data[219:228], 2)
        ais_data['to_stern']     = int(data[228:237], 2)
        ais_data['to_port']      = int(data[237:243], 2)
        ais_data['to_starboard'] = int(data[243:249], 2)
        ais_data['epfd']         = int(data[249:253], 2)
        ais_data['second']       = int(data[253:259], 2)
        ais_data['off_position'] = data[259]
        ais_data['regional']     = int(data[260:268], 2)
        ais_data['raim']         = data[268]
        ais_data['virtual_aid']  = data[269]
        ais_data['assigned']     = data[270]
        ais_data['name_ext']     = decod_str(data[272:361])
        return ais_data
    
    def decod_22(data):
        ###### This code is based on the document, ######
        ais_data                 = {'type':int(data[0:6],2)}
        if len(data) == 168:
            ais_data['repeat']   = int(data[6:8],2)
            ais_data['mmsi']     = int(data[8:38],2)
            ais_data['channela'] = int(data[40:52],2)
            ais_data['channelb'] = int(data[52:64],2)
            ais_data['power']    = data[68]
            ais_data['addressed']= data[139]
            if ais_data['addressed'] == 0:
                ais_data['nelon']    = int(data[69:87],2)/600.0
                ais_data['nelat']    = int(data[87:104],2)/600.0
                ais_data['swlon']    = int(data[104:122],2)/600.0
                ais_data['swlat']    = int(data[122:104],2)/600.0
            else:
                ais_data['destmmsi1']= int(data[69:99],2)
                ais_data['destmmsi2']= int(data[104:134],2)
            ais_data['channelaband'] = data[140]
            ais_data['channelbband'] = data[141]
            ais_data['zonesize']     = int(data[142:145],2)
        return ais_data
        ###### but hasn't been testified           ######
    
    def decod_23(data):
        ###### This code is based on the document, ######
        ais_data                 = {'type':int(data[0:6],2)}
        if len(data) == 160:
            ais_data['repeat']   = int(data[6:8],2)
            ais_data['mmsi']     = int(data[8:38],2)
            ais_data['nelon']    = int(data[40:58],2)/600.0
            ais_data['nelat']    = int(data[58:75],2)/600.0
            ais_data['swlon']    = int(data[75:93],2)/600.0
            ais_data['swlat']    = int(data[93:110],2)/600.0
            ais_data['stationtype'] = int(data[110:114],2) 
            ais_data['txrx']     = int(data[144,146],2) 
            ais_data['interval'] = int(data[146:150],2) 
            ais_data['quiettime']= int(data[150:154],2)
        return ais_data
        ###### but hasn't been testified           ######  
    
    def decod_24(data):
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['partno']       = int(data[38:40],2)
        if not(ais_data['partno']):
            ais_data['shipname']     = decod_str(data[40:160])
        else:
            ais_data['shiptype']     = int(data[40:48],2)
            ais_data['vendorid']     = int(data[48:66],2)
            ais_data['vendorname']   = decod_str(data[48:90]) #Older models. might be garbage
            ais_data['model']        = int(data[66:70],2)
            ais_data['serial']       = int(data[70:90],2)
            ais_data['callsign']     = decod_str(data[90:132])
            if not(is_auxiliary_craft(ais_data['mmsi'])):
                ais_data['to_bow']       = int(data[132:141],2)
                ais_data['to_stern']     = int(data[141:150],2)
                ais_data['to_port']      = int(data[150:156],2)
                ais_data['to_starboard'] = int(data[156:162],2)
            else:
                ais_data['mothership_mmsi'] = int(data[132:162],2)
        return ais_data

    def decod_25(data):
        ###### This code is based on the document, ######
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        if len(data)>70:
            ais_data['addressed']    = data[38]
            ais_data['structrued']   = data[39]
            if ais_data['addressed']:
                ais_data['destmmsi'] = int(data[40:70],2)
            aa = int(ais_data['addressed'])
            if ais_data['structrued']:
                ais_data['dac']      = int(data[40+aa*32:50+aa*32],2)
                ais_data['fid']      = int(data[50+aa*32:56+aa*32],2)
                bb = int(ais_data['structrued'])    
                ais_data['bidata']       = data[40+aa*32+bb*16:]
        return ais_data
        # Type 25 is extremely rare.     
        ###### but hasn't been testified           ######

    def decod_26(data):
        ###### This code is based on the document, ######        
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['addressed']    = data[38]
        ais_data['structrued']   = data[39]
        if ais_data['addressed']:
            ais_data['destmmsi'] = int(data[40:70],2)
        aa = int(ais_data['addressed'])
        if ais_data['structrued']:
            ais_data['dac']      = int(data[40+aa*32:50+aa*32],2)
            ais_data['fid']      = int(data[50+aa*32:56+aa*32],2)
        bb = int(ais_data['structrued'])    
        ais_data['bidata1']       = data[40+aa*32+bb*16:144]
        if len(data) > 367:
            ais_data['bidata2']   = data[144:368]
        if len(data) > 591:
            ais_data['bidata3']   = data[368:592]
        if len(data) > 815:
            ais_data['bidata4']   = data[592:816]
        if len(data) > 1039:
            ais_data['bidata5']   = data[816:1040]            
        return ais_data
        # Type 26 is extremely rare.    
        # The binary data field may span up to 5 slots in addition to 
        # the tail end of the base slot. One documentation says the data
        # length of each slot is 224 and adds the note "Allows for 32
        # bits of bit-stuffing."
        ###### but hasn't been testified           ######

    def decod_27(data):
        ais_data                 = {'type':int(data[0:6],2)}
        ais_data['repeat']       = int(data[6:8],2)
        ais_data['mmsi']         = int(data[8:38],2)
        ais_data['accuracy']     = data[38]
        ais_data['raim']         = data[39]
        ais_data['status']       = int(data[40:44],2)
        ais_data['lon']          = sign_int(data[44:62])/600.0
        ais_data['lat']          = sign_int(data[62:79])/600.0        
        ais_data['speed']        = int(data[79:85], 2)/0.1
        ais_data['course']       = int(data[85:94],2)
        ais_data['gnss']         = data[94]
        return ais_data
        


    decod_type = {  # list of the ais message type we can decode
                    1  : decod_1,
                    2  : decod_1,
                    3  : decod_1,
                    4  : decod_4,
                    5  : decod_5,
                    6  : decod_6,
                    7  : decod_7,
                    8  : decod_8,
                    9  : decod_9,                    
                    10 : decod_10,                     
                    11 : decod_11,                    
                    12 : decod_12,                     
                    14 : decod_14,                    
                    15 : decod_15,                    
                    16 : decod_16,                     
                    17 : decod_17,                    
                    18 : decod_18,
                    19 : decod_19,
                    20 : decod_20,
                    21 : decod_21,
                    22 : decod_22,
                    23 : decod_23,
                    24 : decod_24,
                    25 : decod_25,
                    26 : decod_26, 
                    27 : decod_27             
                 }
    try:
        ais_data = decod_type[type_nb](data)    # try to decode the sentense without assumption of its type
    except (KeyError):                          # if it fails, like a type 13 message, execute following code
        logger.info("Cannot decode message type "+str(type_nb))
        ais_data = {'type':type_nb}
    except:
        raise                                   # raise will raise the last error (WrongKey) and crash the script
    return ais_data

globPayload = '' # in case of multi-lines sentenses, declare global var to store previous payload
logmessage  = ''
def decod_ais(msg,out_log):
    """
    decode AIS messages, AIVDM/AIVDO sentences:
    if the message is split to several lines, return a dict with 'none' key as 'empty' value
    if the checksum doesn't correspond, raise an error
    :param msg: (string) one AIS sentence  '!AIVDO,1,1,,,B00000000868rA6<H7KNswPUoP06,0*6A'
    :return: (dict) ais_data : {'type':18, etc...}
    """
    fout_log = open(out_log, 'a+')
    
    if msg == '':
        return None
    message_type = get_msg_type(msg)
    if not(message_type =='!AIVDM' or message_type == '!AIVDO'):
        log_text = 'This message is neither AIVDM nor AIVDO : '
        fout_log.write(log_text+msg+'\n')
        raise UnrecognizedNMEAMessageError(message_type)
    payload = get_payload(msg)
    s_size  = get_sentence_number(msg)
    s_count = get_sentence_count(msg)
    message = msg


    if (compute_checksum(msg) != get_checksum(msg)):
        log_text = 'The checksum of this message is incorrect : '
        fout_log.write(log_text+msg+'\n')        
        return None
#        logger.error('Checksum not valid (' + str(compute_checksum(msg)) + '!=' + str(
#            get_checksum(msg)) + '), message is broken/corrupted')
#        raise BadChecksumError()


    if s_size != '1' :                          # usefull only if multi-line sentences.
        global globPayload
        global logmessage
        if (globPayload=='' and int(s_count) > 1):
            return {'none': 'empty'}            # This is not the first message and the main payload is empty
        if s_size != s_count:                   # if this isn't the last messages
            globPayload = globPayload + payload # append the current payload to the main payload
            logmessage  = logmessage +msg+' '
            return {'none':'empty'}
        else:
            payload = globPayload + payload     # append the last payload
            globPayload = ''                    # reset the global var for future messages
            message = logmessage+message
            logmessage  = ''
            
    else:
        globPayload = ''                        # incase there are missing messages for the multi-line sentences
        logmessage  = ''
        
    data = decod_payload(payload)
    if len(data)>60:
        try:
            ais_data = decod_data(data)
            return ais_data
        except:
            log_text = 'The useful output of this message is not enough: '
            fout_log.write(log_text+message+'\n')
            print(log_text+message)            
            return None    
    else:
        log_text = 'The data length of this message is too short: '
        fout_log.write(log_text+message+'\n')
        print(log_text+message)        
        return None
    fout_log.close()
    
class UnrecognizedNMEAMessageError(Exception):
    pass
class BadChecksumError(Exception):
    pass

##############################################################################
