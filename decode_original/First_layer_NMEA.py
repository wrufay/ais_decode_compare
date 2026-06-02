#!/usr/bin/env python
"""
A bunch of python functions to decode ais_data/AIVDM messages:
Original author: Pierre Payen
From https://github.com/pirpyn/pyAISm
The functions were built based on doc : https://gpsd.gitlab.io/gpsd/AIVDM.html

Try with !AIVDO,1,1,,,B00000000868rA6<H7KNswPUoP06,0*6A
"""
##############################################################################
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
def sign_int(s_bytes):
    # converts signed pack of bytes (as a string) to signed int
    # @param s_bytes (string) : '1001001010010010...'
    # @return (int) : signed integer 
    temp = s_bytes
    if s_bytes[0]=='1':
        l = temp.rfind('1') #find last one
        temp2=temp[:l].replace('1', '2')
        temp2=temp2.replace('0', '1')
        temp2=temp2.replace('2', '0')
        temp=temp2+temp[l:]
        return -int(temp,2)
    else:
        return int(temp,2)

def compute_checksum(msg):
    # compute the checksum of an AIS sentense by XOR every char
    # then confront it to the checksum validator
    # @param (string) msg : one AIS sentense '!AIVDO,1,1,,,B00000000868rA6<H7KNswPUoP06,0*6A'
    # @return (string) : string representation of hexadecimal sum of XORing every char bitwise
    end = msg.rfind('*') # we're gonna read from after '?'' to before '*
    start = 0
    if msg[0] in ('$','!'): start=1 # reading after '!' if it exists
    chcksum = 0
    for c in msg[start:end]: # for every char in the ais sentenses (comma included)
        chcksum = chcksum ^ ord(c) # compare them with the x-or operator '^'
    sumHex = "%x" % chcksum # makes it hexadecimal
    return sumHex.zfill(2).upper()

##############################################################################

def get_msg_type(msg):
    # read the ais sentense and return the message type
    # @param (string) msg : one AIS sentense '!AIVDM,2,1,3,B,55P5TL01VIaAL@7WKO@mBplU@<PDhh000000001S;AJ::4A80?4i@E53,0*3E'
    # @return (string) : the message type '!AIVDM'
    return msg.split(',')[0]

def get_payload(msg):
    # read the ais sentense and return the payload
    # @param (string) msg : one AIS sentense '!AIVDM,2,1,3,B,55P5TL01VIaAL@7WKO@mBplU@<PDhh000000001S;AJ::4A80?4i@E53,0*3E'
    # @return (string) : the payload '55P5TL01VIaAL@7WKO@mBplU@<PDhh000000001S;AJ::4A80?4i@E53'
    return msg.split(',')[5]

def get_sentence_number(msg):
    # read the ais sentense and return the number of sentenses the payload is splitted in
    # @param (string) msg : one AIS sentense '!AIVDM,2,1,3,B,55P5TL01VIaAL@7WKO@mBplU@<PDhh000000001S;AJ::4A80?4i@E53,0*3E'
    # @return (string) number of sentenses: '2'
    return msg.split(',')[1]

def get_sentence_count(msg):
    # read the ais sentense and return the number of the sentense
    # @param (string) msg : one AIS sentense '!AIVDM,2,1,3,B,55P5TL01VIaAL@7WKO@mBplU@<PDhh000000001S;AJ::4A80?4i@E53,0*3E'
    # @return (string) the number of the current: '1'
    return msg.split(',')[2]

def get_checksum(msg):
    # read the ais sentense and return the number of the sentense
    # @param (string) msg : one AIS sentense '!AIVDM,2,1,3,B,55P5TL01VIaAL@7WKO@mBplU@<PDhh000000001S;AJ::4A80?4i@E53,0*3E'
    # @return (string) checksum validator: '3E'
    return msg.split('*')[-1]

##############################################################################

def decod_payload(payload):
    # convert the payload from ASCII char to their 6-bits representation for every char
    # doc : http://catb.org/gpsd/AIVDM.html#_aivdm_aivdo_payload_armoring
    # @param (string) payload : '177KQ' up to 82 chars
    # @return (string) data :  '000001000111000111011011100001'
    data = ''
    for i in range(len(payload)):
        char = ord(payload[i])-48
        if char>40:
            char = char -8
        bit = '{0:b}'.format(char)
        bit = bit.zfill(6) # makes it a full 6 bits
        data = data + bit
    return data

def decod_6bits_ascii(bits):
    # decode 6bits into an ascii char, with respect to the 6bits ascii table
    # doc : http://catb.org/gpsd/AIVDM.html#_ais_payload_data_types
    # @param (string) bits : '101010'
    # @return (char) a ascii charater : '*'
    letter = int(bits,2)
    if letter < 32:
        letter+=64
    return chr(letter)

def decod_str(data):
    # decode a string of bits to an ascii one with respect to the 6bits ascii table
    # doc : http://catb.org/gpsd/AIVDM.html#_ais_payload_data_types
    # @param (string) data : a string of bits  '000001000001000001'
    # @return (string) a string of bits : 'AAA'
    name = ''
    for k in range(len(data)//6):
        letter = decod_6bits_ascii(data[6*k:6*(k+1)])
        if letter != '@':
            name += letter
    return name.rstrip()


def is_auxiliary_craft(mmsi):
    return mmsi//10000000 == 98

##############################################################################
