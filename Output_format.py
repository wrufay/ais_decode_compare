#!/usr/bin/env python
"""
Python functions to deal with the format of the decoded ais_data/AIVDM messages:
Original author: Pierre Payen
From https://github.com/pirpyn/pyAISm
  
Edited: Lanli Guo
Publish date: May 01, 2020
"""
#################################################################################
import logging

def format_coord(coord_dec,Dir=''):
    """
    get position in decimal base and return a string with position in arc-base
    :param coord_dec: (int) degree decimal coordinate 43.29492333333334
    :param Dir: (char) char to specify the direction like 'N' for North. By default, nothing.
    :return: (string) a degree,minute,second coordinate + direction  43Â°17'41.7"N
    """
#####Format 1 to output in '°'+"'" +'"'
#    tmp = str(coord_dec).split('.')
#    deg = abs(float(tmp[0]))
#    mnt = float('0.'+tmp[1])*60
#    tmp = str(mnt).split('.')
#    sec = float('0.'+tmp[1])*60
#    return str(int(deg))+'°'+str(int(mnt))+"'"+str(sec)[:4]+'"'+Dir
#####Format 2 to output in '°' 
#    return str('{:.1f}'.format(coord_dec))+Dir
#####Format 3 to output in float 
    return float('{:.1f}'.format(coord_dec))

def format_mmsi(mmsi):
#####Format mmsi in 9 character
    return "{:0>9d}".format(mmsi) 

def format_lat(lat):
#####Format 1 to output with 'N' and 'S'
#    return (format_coord(lat,'N') if lat > 0 else format_coord(lat,'S'))
#####Format 2 to output without 'N' and 'S'
    return (format_coord(lat) if lat > 0 else format_coord(lat))

def format_lon(lon):
#####Format 1 to output with 'E' and 'W'
#    return (format_coord(lon,'E') if lon > 0 else format_coord(lon,'W'))
#####Format 2 to output without 'E' and 'W'    
    return (format_coord(lon) if lon > 0 else format_coord(lon))

def format_altitude(altitude):
    if speed == 4095:
        return 'N/A'
    elif speed == 4094:
        return ' > 4094 meters'
    elif speed == 0:
        return "0 meters"
    else:
        return "{0:.1f} meters".format(altitude)
    
def format_course(course):
#####Format 1 to output with '°' 
#    return 'N/A' if course == 3600 else "{:3.1f}°".format(course).zfill(6) #with leading zeroes
#####Format 2 to output without '°' in string     
#    return 'N/A' if course == 3600 else "{:3.1f}".format(course) #with leading zeroes
#####Format 3 to output without '°' in float
    #return float('nan') if course == 3600 else float("{:3.1f}".format(course)) #with leading zeroes
    return float('nan') if course == 3600 else course

def format_speed(speed):
    if speed == 1023:
        return float('nan')
    else:
        return speed*0.1 

def format_heading(heading):
    #return 'N/A' if heading == 511 else "{:3.1f}°".format(heading).zfill(6) #with leading zeroes
    #return 'N/A' if heading == 511 else "{:3.1f}".format(heading) #with leading zeroes
    return float('nan') if heading == 511 else  heading 

def format_month(month):
    return 'N/A' if month == 0 else month

def format_day(day):
    return 'N/A' if day == 0 else day

def format_hour(hour):
    return 'N/A' if hour == 24 else hour

def format_minute(minute):
    return 'N/A' if minute == 60 else minute

def format_second(second):
    if second == 60:
        return 'N/A'
    elif second == 61:
        return 'manual mode'
    elif second == 62:
        return 'EPFS in estimated mode'
    elif second == 63:
        return 'PS inoperative'
    else:
        return second

def format_cs(cs):
    return 'Class B SOTDMA' if cs == '0' else 'Class B CS'

def format_display(display):
    return 'N/A' if display == '0' else 'Display available'

def format_dsc(dsc):
    if dsc == '1':
      return 'VHF voice radio with DSC capability'

def format_band(band):
    if band == '1':
        return 'Can use any frequency of the marine channel'

def format_msg22(msg22):
    if msg22 == '1':
        return 'Accepts channel assignment via Type 22 Message'

def format_assigned(assigned):
    if assigned == '0':
        return 'Autonomous mode'

def format_dte(dte):
    return 'Data terminal ready' if dte == '0' else 'Data terminal N/A'

def format_epfd(epfd):
    epfd_types = [  'Undefined',
                    'GPS',
                    'GLONASS',
                    'GPS/GLONASS',
                    'Loran-C',
                    'Chayka',
                    'Integrated',
                    'Surveyed',
                    'Galileo',
                    'Undefined',
                    'Undefined',
                    'Undefined',
                    'Undefined',
                    'Undefined',
                    'Undefined',
                    'Undefined']
    return epfd_types[epfd]


def format_shiptype(shiptype):
    if shiptype>99 or shiptype<0:
        return float('nan')
    else:
        return shiptype 

def format_turn(rot):
    if rot >= 1 and rot <= 126:
        return "{0:.1f}° Right".format((rot/4.733)**2)
    elif rot >= -126 and rot <= -1:
        return "{0:.1f}° Left".format((rot/4.733)**2)
    elif rot==127:
        return '> 5°/30sec Right (No TI available)'
    elif rot == -127:
        return '> 5°/30sec Left (No TI available)'
    return 'N/A'

def format_status(status):
    status_list = [
        "Under way using engine",
        "At anchor",
        "Not under command",
        "Restricted manoeuverability",
        "Constrained by her draught",
        "Moored",
        "Aground",
        "Engaged in Fishing",
        "Under way sailing",
        "Reserved for future amendment of Navigational Status for HSC", #TODO: Check if this is the future
        "Reserved for future amendment of Navigational Status for WIG", #TODO: Check if this is the future
        "Reserved for future use",
        "Reserved for future use",
        "Reserved for future use",
        "AIS-SART is active",
        "Not defined (default)",
    ]
    return status_list[status]

def format_aid_type(aid_type):
    aid_type_list = [
        "Default, Type of Aid to Navigation not specified",
        "Reference point",
        "RACON (radar transponder marking a navigation hazard)",
        "Fixed structure off shore, such as oil platforms, wind farms, rigs. (Note: This code should identify an obstruction that is fitted with an Aid-to-Navigation AIS station.)",
        "Spare, Reserved for future use",
        "Light, without sectors",
        "Light, with sectors",
        "Leading Light Front",
        "Leading Light Rear",
        "Beacon, Cardinal N",
        "Beacon, Cardinal E",
        "Beacon, Cardinal S",
        "Beacon, Cardinal W",
        "Beacon, Port hand",
        "Beacon, Starboard hand",
        "Beacon, Preferred Channel port hand",
        "Beacon, Preferred Channel starboard hand",
        "Beacon, Isolated danger",
        "Beacon, Safe water",
        "Beacon, Special mark",
        "Cardinal Mark N",
        "Cardinal Mark E",
        "Cardinal Mark S",
        "Cardinal Mark W",
        "Port hand Mark",
        "Starboard hand Mark",
        "Preferred Channel Port hand",
        "Preferred Channel Starboard hand",
        "Isolated danger",
        "Safe Water",
        "Special Mark",
        "Light Vessel / LANBY / Rigs",
    ]
    return aid_type_list[aid_type]

format_list = {#list of all the key that can/want to be formatted
#              'lat'      : format_lat,
#              'lon'      : format_lon,
#              'status'   : format_status,    
#              'mmsi'     : format_mmsi,
              'course'   : format_course,
              'speed'    : format_speed,
              'heading'  : format_heading,
              'second'   : format_second,
              'cs'       : format_cs,
              'display'  : format_display,
              'dsc'      : format_dsc,
              'band'     : format_band,
              'msg22'    : format_msg22,
              'assigned' : format_assigned,
              'dte'      : format_dte,
              'epfd'     : format_epfd,
              'shiptype' : format_shiptype,
              'month'    : format_month,
              'day'      : format_day,
              'hour'     : format_hour,
              'minute'   : format_minute,
              'turn'     : format_turn,
              'aid_type' : format_aid_type
              }

def format_ais(ais_base,style):
    """
    format the ais_data database to a more user-friendly display
    :param ais_base: (dict) the ais_data base to format
    :return: (dict) ais_format : a dictionary with the same kay as ais_data but other value,
            None if ais_base is None
    """
    if (ais_base == None):
        return None
    ais_format_0 = ais_base.copy()

    if style == 'dyn':
        ais_format = {'Station region':'N/A','Station name':'N/A','datenum': -9999,
                      'type': -9999,'repeat':-9999,'mmsi':-9999,'status':-9999,'turn':'N/A',
                      'speed':float('nan'),'accuracy':-9999,'lon':float('nan'),'lat':float('nan'),
                      'course':float('nan'),'heading':float('nan'),'second':-9999,'maneuver':-9999,
                      'raim':-9999,'radio':-9999}
    else:
        ais_format = {'Station region':'N/A','Station name':'N/A','datenum': -9999,
                      'type': -9999,'repeat':-9999,'mmsi':-9999,'shipname':'N/A','shiptype':-9999,
                      'to_stern':float('nan'),'to_port':float('nan'),'to_starboard':float('nan'),
                      'to_bow':float('nan'),'draught':float('nan'),'destination':'N/A'}


    for key in list(ais_base.keys()):                              #for every key we have
        if key in format_list:                                     #if we can format it
            ais_format_0[key] = format_list[key](ais_format_0[key])#format it

    if len(ais_format_0)<4:                                        #ingore the short messages
        return None
    else:
        for key in list(ais_format.keys()):                        #for the order we want
            if key in list(ais_base.keys()):                       #if we have the keys
                ais_format[key] = ais_format_0[key]                #organize them 

        return ais_format

#################################################################################
