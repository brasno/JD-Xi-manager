#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 31 23:10:39 2023

@author: brasno
"""
import time
import threading
import smtplib
import datetime
import json
import re
import os
import logging
import sys
import argparse
import collections
import pandas as pd
import PySimpleGUI as psg
import mido
from collections import deque

# change to True if you want more data in runtime
DEBUG=True
#DEBUG=False

# call with current line, message, call it like:
# printdebug(sys._getframe().f_lineno, str(<put your message here>))
def printdebug(lineno, message):
    global DEBUG
    if (DEBUG==True):
        print("FILE="+__file__+", LINE="+str(lineno)+": "+message)

# All configs are in config file: <CONFIG_FILE>
# Put here default config file
CONFIG_FILE='./jdxi_controller.json'
TONES_FILE=''

# get script name without extension
scriptname=os.path.split(os.path.splitext(__file__)[0])[-1]

PROCESS_TEXT=scriptname
PROCESS_NAME=scriptname.replace('_',' ').replace('-',' ')

# global vars with defaults, to simplify 
logpath="."
logfile=scriptname.replace('_','-').replace(' ','-')	
loglevel="DEBUG"
logger=[]
conf_file=''
testingnote=40
testingch=9
testingvolume=30
testingduration=.2
notesstring='awsedftgzhujkolpčćđž'
inport=''
outport=''

devicefamiliycode=''
DeviceFamilyNumberCode=''
Manufacturer=''
ManufacturerID=''
ManufacturerName=''
ManufacturerSysExIDsFile=''
# for JD-Xi synth
PC=16
programcontrol=[]
analogsynth=[]
digitalsynth=[]
drums=[]
devicename=''
tonelistDS=[]
tonelistAS=[]
drumkitDR=[]
instrumentlist=[]
defaultinstrument=[]


music = b'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'
s_and_h = b'iVBORw0KGgoAAAANSUhEUgAAAHgAAABQCAYAAADSm7GJAAAABmJLR0QAAAAAAAD5Q7t/AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5woTFS0BgklqqAAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAABjklEQVR42u3dMUrDYACG4U8bFcFCHVy8i15B0MXN+7i7indx8AI6OqiDkyCCg5WqQzppLLY2bdI+D2QJkib/m/ylJY0JAAAwH/dJPmtcDhp2vIc1H+/DtHZ0dUrb6TvHm2lagTcN5WIHRmAERmAERmCB63CcZD3JSsVyNeE2L2r+wuH8H8d7m2S/4liLJEcTbnP7D/v8Pq/AN99ffME9JrmsWD9IcrdsU/RgyWbON+/BCIzAAhsCgRG40U6TdCo+j24lORO4/Z6SfFSsf015J4rACIzAzDtwL8lLRn+R3TNk7Q38HDfPmaIRGIERGIERWGBDIDACIzCtCNytWNdxotTSpahYvzPuhoox//7e2M/Ebqb0IwFXnikagREYgREYgRn5OXitofvZ++Xk7LZ03K9T/rrCFTx0kZ93eA5SPjMSU7TACIzACIzACMxfFQ3Zjz0pXMEIjMACIzACI3AbDARebL/dANGapw0VGo50kvJ/TfRTPtsymdGdGALPzsZwMUUjMAIjMAIjMAAATOYLfr13Aq+RR30AAAAASUVORK5CYII='


def start_logger():
    global logpath, logfile,logger, loglevel, PROCESS_NAME, PROCESS_TEXT
    printdebug(sys._getframe().f_lineno, str("var scriptname="+scriptname))
    utctm = datetime.datetime.utcnow()
    logger = logging.getLogger(PROCESS_NAME)
    logFH = logging.FileHandler(logpath+'/'+logfile+'.log')
    logger.setLevel(logging.getLevelName(loglevel))
    logFH.setLevel(logging.getLevelName(loglevel))
    logformt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',datefmt='%Y-%m-%d,%H:%M:%S')
    logFH.setFormatter(logformt)

    if not logger.handlers :
        logger.addHandler(logFH)
    # evidence for start program
    logFH.setLevel(logging.getLevelName("INFO"))
    logger.setLevel(logging.getLevelName("INFO"))
    logger.info("#################### Starting "+PROCESS_TEXT+" #####################")
    logFH.setLevel(logging.getLevelName(loglevel))
    logger.setLevel(logging.getLevelName(loglevel))

def stop_logger():
    global loglevel, logger
    # evidence for stap program
    logger.setLevel(logging.getLevelName("INFO"))
    for handler in logger.handlers:
        handler.setLevel(logging.getLevelName("INFO"))
    loglevel
    logger.info("#################### Ending "+PROCESS_TEXT+" #######################")
    logger.setLevel(logging.getLevelName(loglevel))
    for handler in logger.handlers:
        handler.setLevel(logging.getLevelName(loglevel))

def change_log_level(level):
    global loglevel, logger
    logger.info("Change log level from "+loglevel+" to "+level.upper())
    printdebug(sys._getframe().f_lineno, str("Change log level from "+loglevel+" to "+str(level.upper())))

    logger.setLevel(logging.getLevelName(level.upper()))
    for handler in logger.handlers:
        handler.setLevel(logging.getLevelName(level.upper()))
    
def delayed_event(window, delay, event, value):
    i=0.001
    delta=.1
    while i<=delay:
        time.sleep(delta)
        i+=delta
#        print(i)
    window.write_event_value(event, value)

def get_manufacturer_name(ManufacturerTupleINT):
  global ManufacturerSysExIDsFile, ManufacturerIDs
  if(ManufacturerTupleINT[0]) != 0:
      ManufacturerINT=ManufacturerTupleINT[0]*65536
  else:
      ManufacturerINT=ManufacturerTupleINT[0]*65536+ManufacturerTupleINT[1]*256+ManufacturerTupleINT[2]
  ManufacturerHEXSTR=str(hex(ManufacturerINT))
  with open(ManufacturerSysExIDsFile) as json_file:
    ManufacturerIDs = json.load(json_file)
    if ManufacturerHEXSTR in ManufacturerIDs:
      return ManufacturerIDs[ManufacturerHEXSTR]
    else:
      return "Unknown Manufacturer"

def identify_device():
    global ManufacturerID, Manufacturer, devicename,ManufacturerSysExIDsFile
    global outport, inport
    """
    This is how to use Universal Non-realtime System Exclusive Messages with Identity Request Message
    F0H  Exclusive status
    7EH  ID number (Universal Non-realtime Message)
    dev  Device ID (dev: 10H, 7FH). For 7FH device should respond regardless of what <device ID> it is set to.
    06H  Sub ID#1 (General Information)
    01H  Sub    ID#2 (Identity Request)
    F7H  EOX (End Of Exclusive)
    """
    msg=mido.Message('sysex', data=[0x7E,0x7F, 0x06, 0x01])
    outport.send(msg)
    time.sleep(1)
    counter=0
    found=False
    while True:
        counter+=1
        msg=inport.poll()
        if msg is not None:
            if msg.type=='clock':
                continue
            printdebug(sys._getframe().f_lineno, str("Msg type: "+msg.type))
            if msg.type=='sysex':
                printdebug(sys._getframe().f_lineno, str("Msg data: "+str(msg.data)))
                printdebug(sys._getframe().f_lineno, str("Msg hex: "+"".join('%02x' % i for i in msg.data)))
#               
                if (list(msg.data)[:4]!=[0x7e,0x10,0x06,0x02]):
                    printdebug(sys._getframe().f_lineno, "Not good sysex msg.")
                    continue
                ManufacturerID=list(msg.data)[4:7]
#                ManufacturerID=[0,0,22]
                ManufacturerName=get_manufacturer_name(tuple(ManufacturerID))
                if ManufacturerID[0]!=0:
                    ManufacturerHEX="".join('%02x' % ManufacturerID[0])
                else:
                    ManufacturerHEX="".join('%02x' % i for i in ManufacturerID)
# this IS JD-Xi response: 
#    0x10 Device ID, 0x06 General Information, 0x02 Identity Reply, 0x41 is Roland,
#    0x0e 0x03 Device family code, 0x00 0x00 Device family number code
                if(list(msg.data)[:9]==[0x7e,0x10,0x06,0x02,0x41,0x0e,0x03,0x00,0x00]):
                    printdebug(sys._getframe().f_lineno, 
                    str("This is "+ManufacturerHEX+" ("+ManufacturerName+") "+  devicename+"."))
                    found=True
                else:
                    ManufacturerID=list(msg.data)[4]
                    printdebug(sys._getframe().f_lineno, "ManufacturerName: "+ManufacturerName)
                    printdebug(sys._getframe().f_lineno, "This is ManufacturerID:"+ ManufacturerHEX+" ("+ManufacturerName+"). Don't know how to work with it.")
                    break
        else:
            break
        if counter>100:
            logger.warning("Waiting too log for stauts identification.")
            break
    if(found):
        return devicename
    else:
        return 'unknown'
    
def tone(func, channel, pitch, velocity, duration):
    """
    Parameters
    ----------
    func: 'note_on' or 'note_off'\n
    channel : int - channel to use for tone\n
    pitch : int - pitch of tone\n
    velocity : int - velocity of tone\n
    duration : float - duration in seconds\n
    Returns : None.

    """
    global outport, inport
    msg=mido.Message(func, channel=channel, note=pitch, 
                 velocity=velocity, time=duration)
    printdebug(sys._getframe().f_lineno, str(msg))
    outport.send(msg)
    
def tone_on(channel, pitch, velocity, duration):
    global outport, inport
    tone('note_on', channel, pitch, velocity, duration)
    time.sleep(duration/64)
    
def tone_off(channel, pitch, velocity, duration):
    global outport, inport
    tone('note_off', channel, pitch, velocity, duration)

def test_tone(pitch):
    global outport, inport, testingnote, testingch, testingvolume, testingduration
    tone_on(testingch, pitch, testingvolume, testingduration)
    time.sleep(.2)
    tone_off(testingch, pitch, testingvolume, testingduration)
    
def test_tone_on(pitch):
    global outport, inport, testingnote, testingch, testingvolume, testingduration
    tone_on(testingch, pitch, testingvolume, testingduration)

def test_tone_off(pitch):
    global outport, inport, testingnote, testingch, testingvolume, testingduration
    tone_off(testingch, pitch, testingvolume, testingduration)

def get_io_ports():
    global outport, inport, current_inport, current_outport, output_ports, input_ports
    output_ports=mido.get_output_names()
    input_ports=mido.get_input_names()
    printdebug(sys._getframe().f_lineno, str(output_ports)) # To list the output ports
    printdebug(sys._getframe().f_lineno, str(input_ports)) # To list the input ports

def get_ports():
    global outport, inport, current_inport, current_outport, output_ports, input_ports
    get_io_ports()
    current_outport='JD-Xi:JD-Xi MIDI 1'
    if current_outport not in output_ports:
        current_outport=output_ports[0]
    # outport=mido.open_output(current_outport)
    current_inport='JD-Xi:JD-Xi MIDI 1'
    if current_inport not in input_ports:
        current_inport=input_ports[0]
    outport=mido.open_output(current_outport)
    port_panic()
    port_reset()
    printdebug(sys._getframe().f_lineno, str(outport))
    inport=mido.open_input(current_inport)
    printdebug(sys._getframe().f_lineno, str(inport))
    get_device=identify_device()
    if get_device=='JD-Xi':
       printdebug(sys._getframe().f_lineno, str('Testing '+get_device))
       jdxi_test()
       return('JD-Xi')
    else:
        return('7OF9')
    
def port_open():
    global outport, inport, current_inport, current_outport
    outport=mido.open_output(current_outport)
    printdebug(sys._getframe().f_lineno, str(outport))
    outport.reset()
    logger.info("Open port "+current_outport+" "+str(outport))
    
def port_close():
    global outport,inport, current_inport, current_outport
    outport.close()
    counter=0
    while True:
        msg=inport.poll()
        counter+=1
        if msg is not None:
            if msg.type!='clock':
                printdebug(sys._getframe().f_lineno, str(msg))
                time.sleep(.01)
            if counter>=3:
                break
    logger.warning("Closing out port "+ str(outport))
    inport.close()
    logger.warning("Closing i)n port "+ str(inport))
    
def port_panic():
    global outport, inport, current_inport, current_outport
    outport.panic()
    logger.warning("Sent panic to "+ str(outport))

def port_reset():
    global outport, inport, current_inport, current_outport
    outport.reset()
    logger.warning("Sent reset to "+ str(outport))


def add_digital_synth(chid, desc):
  global digitalsynth
  printdebug(sys._getframe().f_lineno, "Adding Channel id:"+str(chid)+" desc:"+ desc)
  shortname="DS"+str(len(digitalsynth))
  digitalsynth.append([shortname,chid, desc])

def add_analog_synth(chid, desc):  
  global analogsynth
  printdebug(sys._getframe().f_lineno, "Adding Channel id:"+str(chid)+" desc:"+ desc)
  shortname="AS"+str(len(analogsynth))
  analogsynth.append([shortname,chid, desc])

def add_drums(chid, desc):  
  global drums
  printdebug(sys._getframe().f_lineno, "Adding Channel id:"+str(chid)+" desc:"+ desc)
  shortname="DR"+str(len(analogsynth))
  drums.append([shortname,chid, desc])
  
def setup_program_control(chid, desc):
  global programcontrol
  printdebug(sys._getframe().f_lineno, "Adding Channel id:"+str(chid)+" desc:"+ desc)
  PC=int(chid)
  # there can be the only one, so clear old one
  programcontrol=[]
  shortname="PC"+str(len(analogsynth))
  programcontrol.append([shortname,chid, desc])
  
def control_change(chid,func, value):
    printdebug(sys._getframe().f_lineno, str("in CC:"+str(chid)+" "+func+" "+str(value)))
    if func in ('Bank Select','Modulation','Portamento Time','Data Entry','Volume','Panpot', 
                'Expression','Hold 1','Portamento','Resonance','Release Time','Attack time',
                'Cutoff','Decay Time','Vibrato Rate','Vibrato Depth','Vibrato Delay'):
        printdebug(sys._getframe().f_lineno, "Control change: "+ func)
        if func== 'Bank Select': #(Controller number 0, 32)
            PC=value
            if chid in (0,1): #Digital Synth
                MSB=95
                if value>=128:
                    LSB=65
                    PC=value-128
                else:
                    LSB=64
            elif chid==2: # Analog Synth
                MSB=94
                LSB=64
            elif chid==9: # Drums
                MSB=86
                LSB=64
            elif chid==15:  # Preset program
               MSB=85
               if value>=128:
                   LSB=65
                   PC=value-128
               else:
                   LSB=64
                
            msg=mido.Message('control_change', channel=chid, control=0, value=MSB, time=0)
            outport.send(msg)
            msg=mido.Message('control_change', channel=chid, control=32, value=LSB, time=0)
            outport.send(msg)
            msg=mido.Message('program_change', channel=chid, program=PC, time=0)
            outport.send(msg)

    else:
        printdebug(sys._getframe().f_lineno, "Don't know controller': "+ func)

def jdxi_test():
    # send few drums testing notes
    ch=9
    tone_on(ch, 40, 50, .5)
    time.sleep(.25)
    tone_off(ch, 40, 50, 0)
    tone_on(ch, 36, 50, .5)
    time.sleep(.25)
    tone_off(ch, 36, 50, 0)
    tone_on(ch, 39, 50, .5)
    time.sleep(.25)
    tone_off(ch, 49, 50, 0)
    time.sleep(1)
   
    counter=0
    while True:
      msg=inport.poll()
      counter+=1
      if msg is not None:
        if msg.type!='clock':
          printdebug(sys._getframe().f_lineno, str(msg))
          time.sleep(.01)
        if counter>=3:
          break

def make_effects_window(theme,loc,siz):
    prefix='-EFFECTS-'
    psg.theme(theme)
    layout = [[psg.Text('This is the Effects window'), psg.Text('      ', k=prefix+'OUTPUT-')],
              [psg.Button('FAKE'), psg.Button('PopupEFFECTS'), psg.Button('Exit')]]
    return psg.Window('Effects', layout, location=loc, resizable=True, size=siz, finalize=True, icon= music)

def make_vocalFX_window(theme,loc,siz):
    prefix='-VOCAL_FX-'
    psg.theme(theme)
    layout = [[psg.Text('This is the VocalFX window'), psg.Text('      ', k=prefix+'OUTPUT-')],
              [psg.Button('FAKE'), psg.Button('PopupVOCAL_FX'), psg.Button('Exit')]]
    return psg.Window('Vocal FX', layout, location=loc, resizable=True, size=siz, finalize=True, icon= music)

def make_arpeggio_window(theme,loc,siz):
    prefix='-ARPEGGIO-'
    psg.theme(theme)
    layout = [[psg.Text('This is the Arpeggio window'), psg.Text('      ', k=prefix+'OUTPUT-')],
              [psg.Button('FAKE'), psg.Button('PopupARPEGGIO'), psg.Button('Exit')]]
    return psg.Window('Arpeggio', layout, location=loc, resizable=True, size=siz, finalize=True, icon= music)

def make_program_window(theme,loc,siz):
    global presetprogramlist, presetprogramall
    prefix='-PROGRAM-'
    key_value=prefix
    key_value.replace(' ','_')

    psg.theme(theme)
    layout = [[psg.Button('Exit')],
              [psg.Combo(presetprogramlist, default_value=presetprogramlist[0], key=key_value+'LIST-',
                                  readonly=True,enable_events=True,size=20),
               psg.Button('Activate program')],
              [psg.Frame('',[[psg.Text('Program:',size=(8),font=('Arial',10,'bold'),text_color='black',background_color='yellow'),
               psg.Text(presetprogramall[0][1],k=key_value+'Program',text_color='black',background_color='yellow'),
              psg.Text('Name:',size=(8),font=('Arial',10,'bold'),text_color='black',background_color='yellow'),
              psg.Text(presetprogramall[0][2],k=key_value+'Name',text_color='black',background_color='yellow')]],
                         background_color='yellow',border_width=0,expand_x=True)],
              [psg.Text('Genre:',size=(8),font=('Arial',10,'bold')),
               psg.Text(presetprogramall[0][10],k=key_value+'Genre')],
              [psg.Column(
              [
               
               [psg.Text('D1:',size=(4),font=('Arial',10,'bold')),psg.Text(presetprogramall[0][3],k=key_value+'D1')],
               [psg.Text('D2:',size=(4),font=('Arial',10,'bold')),psg.Text(presetprogramall[0][4],k=key_value+'D2')],
               [psg.Text('DR:',size=(4),font=('Arial',10,'bold')),psg.Text(presetprogramall[0][5],k=key_value+'DR')],
               [psg.Text('AN:',size=(4),font=('Arial',10,'bold')),psg.Text(presetprogramall[0][6],k=key_value+'AN')]]),
               psg.Column(
               [[psg.Text('MSB:',size=(7),font=('Arial',10,'bold')),psg.Text(presetprogramall[0][7],k=key_value+'MSB')],
                [psg.Text('LSB:',size=(7),font=('Arial',10,'bold')),psg.Text(presetprogramall[0][8],k=key_value+'LSB')],
                [psg.Text('PC:',size=(7),font=('Arial',10,'bold')),psg.Text(presetprogramall[0][9],k=key_value+'PC')],
                [psg.Text('Tempo:',size=(7),font=('Arial',10,'bold')),psg.Text(presetprogramall[0][11],k=key_value+'Tempo')]])],
              [psg.Button('Program start'),psg.Button('Program stop')]
              ]
    return psg.Window('Program', layout, location=loc, resizable=True, size=siz, finalize=True, icon= music)


def send_sysex_DT1(instrument, address, values):
    """
    This message sends data to the other device. The address
and size indicate the type and amount of data that is requested.
    instrument : List   of data for specific instrument
    address : base address where to save data (last byte,base address will be defined in the instrument)
    values : list of values
    Returns: None.
    """
    sysexdata=instrument.sysexsetlist+[address]+values+[0] #zero is checksum, i. e. not needed to calculate
    printdebug(sys._getframe().f_lineno, "sysex"+str(sysexdata))
    msg=mido.Message('sysex', data=sysexdata) 
    outport.send(msg)

def send_sysex_RQ1(deviceID, address, size):
    """
    This message requests the other device to transmit data. The address
and size indicate the type and amount of data that is requested.
    Parameters
    ----------
    deviceID : List of data for specific device - [0x41,0x10,0x00,0x00,0x00,0x0e] for Roland JD-Xi
    address : base address where to save data (last byte,base address will be defined in the instrument)
    size : list of four bytes- [MSB, 2nd, 3rd, LSB]
    """
    sysexdata=deviceID+[0x11]+address+size+[0]
    printdebug(sys._getframe().f_lineno, "sysex"+str(sysexdata))
    msg=mido.Message('sysex', data=sysexdata) 
    outport.send(msg)

    time.sleep(.2)
    counter=0
    found=False
    while True:
        counter+=1
        msg=inport.poll()
        if msg is not None:
            if msg.type=='clock':
                continue
            printdebug(sys._getframe().f_lineno, str("Msg type: "+msg.type))
            if msg.type=='sysex':
                printdebug(sys._getframe().f_lineno, str("Msg data: "+str(msg.data)))
                printdebug(sys._getframe().f_lineno, str("Msg hex: "+"".join('%02x' % i for i in msg.data)))
                if(list(msg.data)[:11]==deviceID+[0x12]+address):
                    printdebug(sys._getframe().f_lineno, 
                    str("This is good message from Roland JD-Xi."))
                    found=True
                    break
                else:
                    continue
        if counter>100:
            logger.warning("Waiting too log for stauts identification.")
            break
    if(found):
        return (list(msg.data)[11:-1])
    else:
        return 'unknown'

class System_Setup():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['ProgramBSMSB']=[40,4,1]
        self.attributes['ProgramBSLSB']=[127,5,1]
        self.attributes['ProgramPC']=[15,6,1]

        self.baseaddress=[0x01,0x00,0x00]
        self.offset=[0x00,0x00]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x3B]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
# required for SysEx Data set 1 (DT1=0x12). Last byte must be added at the end
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]
        self.devicestatus='unknown'
    
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
                self.attributes[attr][0]=data[self.attributes[attr][1]]
        print(data)
        return

class System_Common():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['MasterTune']=[[0x00,0x04,0x00,0x00],0,4]
        self.attributes['MasterKeyShift']=[40,4,1]
        self.attributes['MasterLevel']=[127,5,1]
        self.attributes['ProgramCC']=[15,17,1]
        self.attributes['ReceiveProgramChange']=[1,41,1]
        self.attributes['ReceiveBankSelect']=[1,42,1]
        self.baseaddress=[0x02,0x00,0x00]
        self.offset=[0x00,0x00]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x2B]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
# required for SysEx Data set 1 (DT1=0x12) 
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]
        self.devicestatus='unknown'
    
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr!='MasterTune':
                self.attributes[attr][0]=data[self.attributes[attr][1]]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
        print(data)
        return


class System_Controller():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['TransmitProgramChange']=[1,0,1]
        self.attributes['TransmitBankSelect']=[1,1,1]
        self.attributes['KeyboardVelocity']=[0,2,1]
        self.attributes['KeyboardVelocityCurve']=[0,3,1]
        self.attributes['KeyboardVelocityCurveOffset']=[1,4,1]

        self.baseaddress=[0x02,0x00,0x00]
        self.offset=[0x00,0x03]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x11]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
# required for SysEx Data set 1 (DT1=0x12) 
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]
        self.devicestatus='unknown'
    
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            self.attributes[attr][0]=data[self.attributes[attr][1]]
        print(data)
        return


class Program_Common():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x04,0x00,0x00,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x00]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x1f]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][2]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif attr=='ProgramTempo':
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]
        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Vocal_Effect():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Level']=[127,0,1]
        self.attributes['Pan']=[64,1,1]
        self.attributes['DelaySendLevel']=[0,2,1]
        self.attributes['ReverbSendLevel']=[0,3,1]
        self.attributes['OutputAssign']=[2,4,1]
        self.attributes['AutoPitchSwitch']=[1,5,1]
        self.attributes['AutoPitchType']=[0,6,1]
        self.attributes['AutoPitchScale']=[1,7,1]
        self.attributes['AutoPitchKey']=[0,8,1]
        self.attributes['AutoPitchNote']=[0,9,1]
        self.attributes['AutoPitchGender']=[10,10,1]
        self.attributes['AutoPitchOctave']=[1,11,1]
        self.attributes['AutoPitchBalance']=[100,12,1]
        self.attributes['VocoderSwitch']=[1,13,1]
        self.attributes['VocoderEnvelope']=[0,14,1]
        self.attributes['Vocoder???']=[40,15,1]
        self.attributes['VocoderMicSens']=[40,16,1]
        self.attributes['VocoderSynthLevel']=[0,17,1]
        self.attributes['VocoderMicMixLevel']=[2,18,1]
        self.attributes['VocoderMicHPF']=[0,19,1]
        
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x01]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x18]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            self.attributes[attr][0]=data[self.attributes[attr][1]]
        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Effect1():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['EFX1Type']=[0,0,1]
        self.attributes['EFX1Level']=[127,1,1]
        self.attributes['EFX1DelaySendLevel']=[50,2,1]
        self.attributes['EFX1ReverbSendLevel']=[50,3,1]
        self.attributes['EFX1OutputAssign']=[1,4,1]
        self.attributes['EFX1Parameter1']=[[8,0,0,0],17,4]
        self.attributes['EFX1Parameter2']=[[8,0,0,0],21,4]
        self.attributes['EFX1Parameter3']=[[8,0,0,0],25,4]
        self.attributes['EFX1Parameter4']=[[8,0,0,0],29,4]
        self.attributes['EFX1Parameter5']=[[8,0,0,0],33,4]
        self.attributes['EFX1Parameter6']=[[8,0,0,0],37,4]
        self.attributes['EFX1Parameter7']=[[8,0,0,0],41,4]
        self.attributes['EFX1Parameter8']=[[8,0,0,0],45,4]
        self.attributes['EFX1Parameter9']=[[8,0,0,0],49,4]
        self.attributes['EFX1Parameter10']=[[8,0,0,0],53,4]
        self.attributes['EFX1Parameter11']=[[8,0,0,0],57,4]
        self.attributes['EFX1Parameter12']=[[8,0,0,0],61,4]
        self.attributes['EFX1Parameter13']=[[8,0,0,0],65,4]
        self.attributes['EFX1Parameter14']=[[8,0,0,0],69,4]
        self.attributes['EFX1Parameter15']=[[8,0,0,0],73,4]
        self.attributes['EFX1Parameter16']=[[8,0,0,0],77,4]
        self.attributes['EFX1Parameter17']=[[8,0,0,0],81,4]
        self.attributes['EFX1Parameter18']=[[8,0,0,0],85,4]
        self.attributes['EFX1Parameter19']=[[8,0,0,0],89,4]
        self.attributes['EFX1Parameter20']=[[8,0,0,0],93,4]
        self.attributes['EFX1Parameter21']=[[8,0,0,0],97,4]
        self.attributes['EFX1Parameter22']=[[8,0,0,0],101,4]
        self.attributes['EFX1Parameter23']=[[8,0,0,0],105,4]
        self.attributes['EFX1Parameter24']=[[8,0,0,0],109,4]
        self.attributes['EFX1Parameter25']=[[8,0,0,0],113,4]
        self.attributes['EFX1Parameter26']=[[8,0,0,0],117,4]
        self.attributes['EFX1Parameter27']=[[8,0,0,0],121,4]
        self.attributes['EFX1Parameter28']=[[8,0,0,0],125,4]
        self.attributes['EFX1Parameter29']=[[8,0,0,0],129,4]
        self.attributes['EFX1Parameter30']=[[8,0,0,0],133,4]
        self.attributes['EFX1Parameter31']=[[8,0,0,0],137,4]
        self.attributes['EFX1Parameter32']=[[8,0,0,0],141,4]

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x02]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x01,0x11]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if str(attr).startswith('EFX1Parameter'):
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][2]]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Effect2():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x03,0x06,0x0b,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x04]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x01,0x11]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif self.attributes[attr][2]==4:
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Delay():
    
    attributes={}
    attributes['DelayEnable']=[1,0,1]
    attributes['reserved']=[0,1,1]
    attributes['reserved']=[0,2,1]
    attributes['DelayReverbSendLevel']=[50,3,1]
    attributes['DelayType']=[[8,0,0,0],4,4]
    attributes['DelayUnits']=[[8,0,0,0],8,4]
    attributes['Delayms']=[[8,0,0,0],12,4]
    attributes['Delaynote']=[[8,0,0,0],16,4]
    attributes['DelayTapTime']=[[8,0,0,0],20,4]
    attributes['DelayFeedback']=[[8,0,0,0],24,4]
    attributes['DelayHFDamp']=[[8,0,0,0],28,4]
    attributes['DelayLevel']=[[8,0,0,0],32,4]
    def __init__(self, *args, **kwargs):
#        self.attributes={}
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x06]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x64]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif self.attributes[attr][2]==4:
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Reverb():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x03,0x06,0x0b,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x08]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x63]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif attr=='ProgramTempo':
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Part_DS1():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x03,0x06,0x0b,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x20]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x24]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif attr=='ProgramTempo':
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Part_DS2():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x03,0x06,0x0b,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x21]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x24]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif attr=='ProgramTempo':
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Part_AS():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x03,0x06,0x0b,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x22]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x24]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif attr=='ProgramTempo':
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Part_DR():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x03,0x06,0x0b,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x23]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x24]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif attr=='ProgramTempo':
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Zone_DS1():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x03,0x06,0x0b,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x30]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x24]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif attr=='ProgramTempo':
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Zone_DS2():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x03,0x06,0x0b,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x31]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x24]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif attr=='ProgramTempo':
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return
    
class Program_Zone_AS():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x03,0x06,0x0b,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x32]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x24]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif attr=='ProgramTempo':
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Zone_DR():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x03,0x06,0x0b,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x33]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x24]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif attr=='ProgramTempo':
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Program_Controller():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[0x03,0x06,0x0b,0x00],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[0,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x40]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x0c]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='Name':
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+self.attributes[attr][1]]:
                    name+=chr(c)
                self.attributes[attr][0]=name
            elif attr=='ProgramTempo':
                self.attributes[attr][0]=data[self.attributes[attr][1]:self.attributes[attr][1]+4]
            else:
                self.attributes[attr][0]=data[self.attributes[attr][1]]

        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        return

class Digital_Synth():
    def __init__(self, *args, **kwargs):
        #self.attributes={}
        self.attributes['Name']=['INIT TONE',0,12]
        self.attributes['ToneLevel']=[127,12,1]
        self.attributes['PortamentoSw']=[0,18,1]
        self.attributes['PortamentoTime']=[20,19,1]
        self.attributes['MonoSw']=[0,20,1]
        self.attributes['OctaveShift']=[64,21,1]
        self.attributes['PitchBendRangeUp']=[2,22,1]
        self.attributes['PitchBendRangeDown']=[2,23,1]
        self.attributes['Partial1Sw']=[0,25,1]
        self.attributes['Partial1Sel']=[0,26,1]
        self.attributes['Partial2Sw']=[0,27,1]
        self.attributes['Partial2Sel']=[0,28,1]
        self.attributes['Partial3Sw']=[0,29,1]
        self.attributes['Partial3Sel']=[0,30,1]
        self.attributes['RINGSw']=[0,31,1]
        self.attributes['UnisonSw']=[0,46,1]
        self.attributes['PortamentoMode']=[0,49,1]
        self.attributes['LegatoSw']=[0,50,1]
        self.attributes['AnalogFeel']=[20,52,1]
        self.attributes['WaveShape']=[20,53,1]
        self.attributes['ToneCategory']=[20,54,1]
        self.attributes['UnisonSize']=[0,60,1]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.id=0
        self.baseaddress=[0x19,0x00,0x00]
        self.offset=[0x01,0x00]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x40]
        self.devicestatus='unknown'
 
    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr!='Name':
                self.attributes[attr][0]=data[self.attributes[attr][1]]
            else:
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+12]:
                    name+=chr(c)
                self.attributes[attr][0]=name
        return('OK')
    def push_data(self):
        return

class Digital_Synth_Modify():
    dsm_attributes={}
    dsm_attributes['AttTimIntSens']=[0,1,1]
    dsm_attributes['RelTimIntSens']=[0,2,1]
    dsm_attributes['PortTimIntSens']=[0,3,1]
    dsm_attributes['EnvLooMod']=[0,4,1]
    dsm_attributes['EnvLooSynNot']=[11,5,1]
    dsm_attributes['ChrPort']=[0,6,1]

    deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
    dsm_baseaddress=[0x19,0x00,0x00]
    dsm_offset=[0x00,0x50]
    dsm_address=[dsm_baseaddress[0],dsm_baseaddress[1]+dsm_offset[0],dsm_baseaddress[2]+dsm_offset[1]]
    dsm_datelength=[0x00,0x00,0x00,0x25]
    devicestatus='unknown'
 
    def __init__(self, *args, **kwargs):
        pass

    def get__modify_data(self):
        data=send_sysex_RQ1(self.deviceID, self.dsm_address+[0x00], self.dsm_datelength)
        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self. dsm_attributes:
            if attr!='Name':
                self. dsm_attributes[attr][0]=data[self. dsm_attributes[attr][1]]
            else:
                name=''
                for c in data[self. dsm_attributes[attr][1]:self. dsm_attributes[attr][1]+12]:
                    name+=chr(c)
                self. dsm_attributes[attr][0]=name
        return('OK')
    def push_modify_data(self):
        return

class Digital_Synth_Partial():
    attributes={}
    deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
    baseaddress=[0x19,0x00,0x00]
    offset=[0x00,0x20]
    address=[baseaddress[0],baseaddress[1]+offset[0],baseaddress[2]+offset[1]]
    datelength=[0x00,0x00,0x00,0x3D]
    sysexsetlist=deviceID+[0x12]+address
    sysexgetlist=deviceID+[0x11]+address+datelength

    def __init__(self, *args, **kwargs):
        pass

class Digital_Synth1(Digital_Synth, Digital_Synth_Modify):
    def __init__(self, *args, **kwargs):
        self.attributes={}
        super().__init__(self, *args, **kwargs)
        mro_list=__class__.mro()
        mro_list[2]()
        self.id=1
        self.baseaddress=[0x19,0x00,0x00]
        self.offset=[0x01,0x00]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.dsm_address=[self.address[0],self.address[1]+self.dsm_offset[0],self.address[2]+self.dsm_offset[1]]
        self.datelength=[0x00,0x00,0x00,0x40]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength

class Digital_Synth2(Digital_Synth, Digital_Synth_Modify):
    def __init__(self, *args, **kwargs):
        self.attributes={}
        super().__init__(self, *args, **kwargs)
        mro_list=__class__.mro()
        mro_list[2]()
        self.id=2
        self.baseaddress=[0x19,0x20,0x00]
        self.offset=[0x01,0x00]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.dsm_address=[self.address[0],self.address[1]+self.dsm_offset[0],self.address[2]+self.dsm_offset[1]]
        self.datelength=[0x00,0x00,0x00,0x40]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength

    
class Analog_Synth():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT TONE   ',0,12]
        self.attributes['LFOShape']=[0,13,1]
        self.attributes['LFORate']=[53,14,1]
        self.attributes['LFOFade']=[0,15,1]
        self.attributes['LFOTempoSynSw']=[0,16,1]
        self.attributes['LFOTempoSynNote']=[17,17,1]
        self.attributes['LFOPitchDepth']=[64,18,1]
        self.attributes['LFOFilterDepth']=[64,19,1]
        self.attributes['LFOAmpDepth']=[64,20,1]
        self.attributes['LFOKeyTrigger']=[1,21,1]
        self.attributes['OSCWaveform']=[0,22,1]
        self.attributes['OSCPitchCoarse']=[64,23,1]
        self.attributes['OSCPitchFine']=[64,24,1]
        self.attributes['OSCPulseWidth']=[0,25,1]
        self.attributes['OSCPulseWidthModDepth']=[0,26,1]
        self.attributes['OSCPEVelocitySens']=[64,27,1]
        self.attributes['OSCPEAttackTime']=[0,28,1]
        self.attributes['OSCPEDecay']=[0,29,1]
        self.attributes['OSCPEDepth']=[64,30,1]
        self.attributes['SubOscType']=[0,31,1]
        self.attributes['FilterSwitch']=[1,32,1]
        self.attributes['FilterCutoff']=[127,33,1]
        self.attributes['FilterCutoffKeyfollow']=[64,34,1]
        self.attributes['FilterResonance']=[0,35,1]
        self.attributes['FilterEVelocitySens']=[64,36,1]
        self.attributes['FilterEAttackTime']=[0,37,1]
        self.attributes['FilterEDecayTime']=[0,38,1]
        self.attributes['FilterESustainLevel']=[127,39,1]
        self.attributes['FilterEReleaseTime']=[0,40,1]
        self.attributes['FilterEDepth']=[64,41,1]
        self.attributes['AMPLevel']=[127,42,1]
        self.attributes['AMPLevelKeyfollow']=[64,43,1]
        self.attributes['AMPLevelVelocitySens']=[64,44,1]
        self.attributes['AMPEAttackTime']=[0,45,1]
        self.attributes['AMPEDecayTime']=[0,46,1]
        self.attributes['AMPESustainLevel']=[127,47,1]
        self.attributes['AMPEReleaseTime']=[0,48,1]
        self.attributes['PortamentoSw']=[0,49,1]
        self.attributes['PortamentoTime']=[20,50,1]
        self.attributes['LegatoSw']=[0,51,1]
        self.attributes['OctaveShift']=[64,52,1]
        self.attributes['PitchBendRangeUp']=[2,53,1]
        self.attributes['PitchBendRangeDown']=[2,54,1]
        self.attributes['LFOPitchMC']=[80,56,1]
        self.attributes['LFOFilterMC']=[64,57,1]
        self.attributes['LFOAmpMC']=[64,58,1]
        self.attributes['LFORateMC']=[82,59,1]
        self.baseaddress=[0x19,0x40,0x00]
        self.offset=[0x02,0x00]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x40]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
# required for SysEx Data set 1 (DT1=0x12) 
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datelength)
        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr!='Name':
                self.attributes[attr][0]=data[self.attributes[attr][1]]
            else:
                name=''
                for c in data[self.attributes[attr][1]:self.attributes[attr][1]+12]:
                    name+=chr(c)
                self.attributes[attr][0]=name
        return('OK')
    def push_data():
        return

class Drum_Kit_Common():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0]
        self.baseaddress=[0x19,0x60,0x00]
        self.offset=[0x10,0x00]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datelength=[0x00,0x00,0x00,0x12]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        return
    def push_data(self):
        return

class Drum_Kit_Partial():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['PartialName']=['INIT',0]
        self.attributes['AssignType']=[0,12,1]
        self.baseaddress=[0x19,0x60]
        self.offset=[0x10]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0]]
        self.datelength=[0x00,0x00,0x01,0x43]
        self.deviceID=[0x41,0x10,0x00,0x00,0x00,0x0e]
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datelength
        self.devicestatus='unknown'
    def get_data(self):
        return
    def push_data(self):
        return


onoff2 = b'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'
onoff4 = b'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'
onoff3 = b'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'
onoff1 = b'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'
onoff_data=(onoff3,onoff4,onoff1,onoff2)

OFF0 = b'iVBORw0KGgoAAAANSUhEUgAAAHgAAABQCAYAAADSm7GJAAAABmJLR0QADACAAADdhk3+AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5wodFiYdlyUmRgAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAADOklEQVR42u3cOWgUURzH8a9JTGLiCTYRhAQRUYR4ayN4BRGPQkTQwsZKEAsJghYiiojYqp2gRUQstPBAUBEJosG7EAk2Hqgp1EKyOURdi3npZt68mZ3Ne4m/D2z13/3P7vzmeDP7dkFERERERERERERERERERERERESKMiHA91QL/Cnw8zUU1GvIQ/8xrwHYAXQBvcAAUAaGgffANWAvMC1n/1bTr4jHTA/9x7RdwEfHD/8D6ARqFHD4aoELOVfCPWCqAg5bV4Ur4jEwSQG7qRnlcDuB3RX2WAWc0/g4PHPMSLGoLX6j9uCwXE35gBeBdqDJbAwnUjaINw6Xea0py6tUtfuPGbOB35aVcSzhdVvNNXHS6zoUcBjn4H1m9BznFXA8oXbDjLiT7NeZL4yAd1pqp4C/lvpJs0fE2QRMVox+A24z59Q4JeBmyus/AE8SahOBNYrRb8AbLLUeotuTaR5Yah2K0W/Aiyy15449nllq7YrRb8BzLbVexx5vc/b/79V5DviLY4+vltosoNmcz7OoBRoTaiPfaFWi2v2DMWi5Vlycoc+ApU9bjutU28P1u9lq9w/+EF1j2YrJuNfZBmO6VPIUcNqKz3KYsm31zYrST8Bp01l+Zehle26jovQT8GBKvT5Dr/oKlqOAq6RE8m1Glz3cdS8tKUo/AZdTVn6Wc2eTpdaf471dIvq6Me5RxCG/2v2DudHxyVJrcewxneRpOmWgT/uqv4B7U25SuGhJ2YCGFGWYAc9z7DHfUnunGP0G3GOpLXXsscxSe6kY/QZ8n2i6TpyVjgOtdZbaXcXoN+CfRHOZk0bG21Je32Y2hDjDQLdi9BvwyCVDkiMkz9cCOGqpXUc3OYIIuAv4nlBbSDRFNs52YI+l71lFGEbAQ9h/jXAYuAwsB2YAC4DTwBXLe3wKPFKE4WgGPlPcLwFWOyyzFc2LHjUlot/6lgvodV6Dq/ACBrhjDseVeAgcVHRhBow5tx4i39803AY2M47mM43HgAHOAGuB147P/wYcALagrwYzqfO47G5gCbCe6H86VphByxSi+Vd9wAvglrne7VdcIiIiIiIiIiIiIiIiIiIiIiIiIiKSzz/Jqt+98U3Y2wAAAABJRU5ErkJggg=='
OFF1 = b'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'
TRI0 = b'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'
TRI1 = b'iVBORw0KGgoAAAANSUhEUgAAAHgAAABQCAYAAADSm7GJAAAABmJLR0QADACAAADdhk3+AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5wodCzIrYs9UqQAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAAaTUlEQVR42sVd7a9l1Vl/njOXgbnsMzMwAolf538w6Qcw9i061ikZrYAWWltssE2QaCqJ0QSkSm2aWqQqYkUbpNQWRzKBqSZFDV/9B+wHPto40mllzmEQKuvnh71efs+z1tr7zOxLuUnLnXP32Xut9bz/npet63//SYiIQERUVMYfSO9nvK78l6/W7rfGb1TXxZv4e2njmZLXh+ozCCae3V/z+Fn6f6UV8jp18jxa+2ztWcwaNK4BnX3bfbbWrO77Ihr/DnPdyh4nqgP0pNO8bW0QV+lO2ti824TWjKHut7TYtCF+nlaHpG4XYti2JttIVmYcrRgMzXtOE7cWGW3ckf+qkUBCbIGKZZRIifydcj+YHapAVmI+TIfUlmUYboFZXG/pzDhqjg95qfYA1W3TEsofY/2kmtXQOWR1O+trEW2uwK6ZWVGb9y13sEIEJ1haSbwVGC+GSqwJt6c9BBFVaciAl1NUCmj8bzDqYfxOsBKYVwrHKag5XCHA+B0VEdC1WeKN3uLP0RSudB9VNYrd6ymYv7EMgg67p9vapg2OJbT5xJYaZwMkTQaw16OpW/YUlmfQvBAiiLdSVmlqyO6Jnz4diaSZvkWxRjWjkTjJIAsEIL7V8fO8UmSKjbcL5feRYeN6lXROWn9luZjZ7DXqpEvdCbPV065JHteWmBLoMIcirrFQLd1Xy7GUs9WyHtW23zFKcJKC9GUjprWC1hAfnO6eN6xSU6FWgy1rLbBqWR0TAChWCuVAgbJoBUlIOo2ggnhwEIiCLZfaE3PeXiKIuTY9D6yaWnuMz4FYqubljp+BXMTGURdNAo1MG3eokanT6mClGPEZKiJ7GmA9vsz5SpLCAhMXAxS6hFEtQxMRrB+ZZYEWWnYEY5HV+YUwB8zOhBYBkbKWbAXiHxVJOiLBgHwi+XC0qPdisiASpMF4rHfpQFEkTaWcj/feRx6FsdTWE3E85wivUkyYoGWhyXSJyF55aiSeRs5nXk83DLRZknQFBJErsyonLkpSmokrOh6klENPBELlCdYWTA3rxPXAOhhJaouZJj0XP9S4Zt4nM7UR9KwnmRYoth0gvlVzXuNZaVES4H2i4ZTWkgz6XTPlo7+jce9xL5mhRWWPRb0sOF0QzOYrLiZ1apRs4uYQVWmSED5gtaq5qM9sMcYnK/lS6uNKuIDK+/LWUy2+nlrzAJKiuODRLNBlqKWjejaIicz1RQOp0TTImobNHBrxtPr4AWyH6fwVoqHsb5VNS4i/AIL8e1Jz0Q4i+Vnlb9kehdEuaIjXB5SHB75d2SwwMsHN9wznJGi8b1Rf6fpQGEVCPJgQ/2jWLPk5+WGh/E/z5/nBIiHacYSy13hP5X1BRBFG6Yl/U5b4MKpzDeMCQMfHDJGYn+mvSHtKa5F4hmWvCOUZ6XnsOyXGGuk43gdxHbp++RbAC1RlM6awmoad6cSbybynzza3XTDXDi/f4oAQGKFJVkDZPqm1uz5+TZI//p40Chk3jcFIUtlNh0lM5NAKgmAAFLirysYZeYP6oCg5kUl7FdWb1b54DREdSTZlKNfq+t9uAZ8Q1Hj3Tn2Q6mSbYpwpyxRaUXu8cvvTF5pg3/rlW8gZt+FUIwYjh0kzOGZCCiV1RqGKCT3Ual91XN6ETzvhiUzCuFo7bD74aKBixecZiSk2ULF7dM9djepNo/gXFZ3UJbKaijogsHpGVCEgFZhUUbSrYLU0etI94kqSalaRiDbTqN2k4qNDiFG9a0imJHraaX2SVK/ktSJI3mNS8aMpIB0KZBWPQPtL64ufpdtkVU1rl+S083ny/0JhRuS/w0gqmxfN63HmUaKZjSpao8nS4V9uhnd4sjoASSa77EphAatJZQkngCJy1uZn/huTOQknCOt/vclHok0TIULShBoI4JBDO4kV8Kay00d4XtIUtBBW7eN/a/hDHULRTqb4tIc0cgJKHrlUISmnGQwMNbx0E2TiAGU2C5M2XdumFE9CVLbvvSLipp+wfunmFeukbOvQOjTeJKrPk91TSDc4qdUn4mE6VZ/cJg5+KfRK9lMb6SReo2Qkr4owp3V/Fzl0/tHwnZugLljnNJ7MUAWdXAr/e/v+V2XJz/qlmyzzQYixEsZM4IVfe8VaOuFK9ZKGkSXYXxGYGLjGsclZhCOF9tSMI2JyElMYSV4qjAGvddJog5N7HhjnLeGQkt0F2xu2RfRZdu/j95cSV0Rk875XR/sayCalsEkgEkIJE9Kzo40FxaUIBcgA+RA59EmhBWrbl78XCMCgkE3Zdma7G88sFGolnwTB3juFQpC4z2DXkmP1GOMi04fAJrLhiQ6rgqWjLCD9HjQuTrPhTnEaaFPKDyPHZfOB78tB/Ww+8P3R2cqHQE5Q/Lwo9sjDQaNzlRCr6EyBYkop8Xg+fKhBtfK+OWY1zOKdUBjnUr1zxohZKA5fFjTYczYOFcipDR6XYDqMt1+lgF+TFxnKF4vnCvPQdKPMzREoQPTibv6NY+c2Hzw44mYif/DV8ZADgQfgRAgdbAJcEjBAGiZDrklDMXAR4n3IWy+oTPpP9MqD87aRUDBmfgZlyBtmsChBuU2tUbQlgvXwIQkI0QxySPakI2Cy/vYJdGy4BQ7QK+vRDLklT3rzsxflnfxZ/9NP2JIX4yGrAVbYDkMpIVoMuBjcPuHYSv/1nnFVcMO+fh0jw5Uh9JxYdNJ/TV+InJzKDyJHUIfzN0Lt8irk0zhQPkSijzenLl6Np3xVP8O3TzQR294nmfhKmR40nFTjt5TsQAFHlHwklCRHSpo0gLjxWRbGK7h7YrIWyk6MM+n4turAYsmOZtvAdoOcEFIXSjipGMw2Zzt+LMQVEdn+3EVjg4xzFM2Gslom+wUyQ+w0SsaEIy2CtaUSiuMJAnISyGJyvoG8YHD6UTNYgyQhgXyJDODA2G4IgU6h2H0QeILsb2hco4quX7gRcEVovkoBjQCDRXXzoR/Iu/WzfuEEhR3M7JoLBYSxaPX7TBoJVa1XPokcO7fh0yKc5Xmg9CRfJ5w7TiAJHaiSnjZySWlNMZm2DoKS1jucu9EoKlVXTpNzp9JU3ZtfePeIa1T2CzfacNOVt5ikuU7g5Q0wx+IDFk9GJwnTqopslfly4sMU8HKInGJtB4ik+B9kF3JiJcfB4tNoMeQIWtKGUrBWxnAPirgnT548t1hlf+gHxWQkM5I8ZU4ZCnu0JV7NIQvYmw6FOiaW5e9xmpJib2capOFZA3YtJuyizw2eD1b/yOFa9p9y2jaa1OH5G6Bi6t0MVAb6N6uHzYf/Z7nUPX+DkYzNh5czzPrcjVR/xXh5qemyUJg4DBek+bSUBAl/RU2JTuUWwUJoKnCZJG24sr0CXl/UrLX+yEV9trpFRUTX/3gcdfUuKgCcL9ne/sODIW7D0m9vX8446+dvqKo76mK/BsZuQo9SDVlFEDJdAe5DllYVJWAjEmnl1sE542lTQGkRU860yum44FQH/Z48x9uefM+ZAyBuGM4ez0hZundSZ8PZ44tV9ub2H8qtT77nDDLKplSZ4lUeqc9AlRAQSj+Wfye1n82ZuZ/DbTnFSV58qVpBUbVc1REKgJOhYka4DDrGaBZyNUeujhmeOwbjjXWchHD3WxcvX758YrHk/sPxKu3d6sTZ/uIBSPLZ452uIpsUMFLEyYuJ/qKmVLIEuRyDUrKA064KcrSSxlBYZwzFNOQsGnlc8AVzOZ0posNzx9ECBIQC8M0vvbZcJT93fEKRaSlRoZjhlgdPnHvllVdOL2eqY6Z0QlXFnpOvWqnzSRbF8+W0HqHyoVULoGhYb60LOv1CQMQT1KVLtpNERIdvHoO/MeNm21++tJy43zpWlaz0E3I1C2w+sozB1t86Zu1sjImlVS+WS5aojkr7JTroyLZW/Vu+WKeXaK3bV8CFCDlVySlMqjpFycOLyIhkseuuBJwfBHHX3zxKJSuhqoxUtoUBDlka7cmpU6fOLLLJH3ltZBIuzUEJNXL4I5QSTEgYZwGrxIJNUKhBw0qoIqYqNSGASsiYuLMoSQtTaRlKClLF+hHKWa1QbLoO3ziKigdVZXvHMqnZ39+/eOipvRNcMDZGF5B27WItz1SnJ1CR7R3LGG7990cn6jjcv+KaVV2ttwipeWqdEVfMxx0e6soIoMaMZqSN0xFUYFeX7bWlHU7Nj8mGZ49WZ7y96wDU8rNHCzIGClFIjZiCet+m4XqE0sEeyNq+cdTxlJZEgdomSIMGoraT5RaF4EpOUcpOpZsarCGV6whXiZRERoVWUS8UnLNlEbJi11c+X6lh8fmF4evrEpYENeoWoQD5rBZN8lpK3rnkbcf9rJ9dL09U3Hmprgylc4BDuUxyInCXBuG+IVCuWXITgDiUjCtnRrMU8v0hlMgIrtKS7mnz2OPZbO54zaFj4zUrk9gOkFufuXWRvRueWa+sLbHJa41tIc0SWCnZFS5D9Zmg9dcPgMh3XRqb5lxFBMetgM3oCJW+lvUlG+r2RfYTHn4MXAVD6iGUmimImPupq1hBDJk2d16SzZ2XMuNqzDwlRlnlcQDRcH/3u//x8auW3KeHqhJBuA0DIqA0nrQO1tUVZwCAJTqIrP9uWE7kX70kb9/79kUxLSjxH6l+GkKtLcwA7OQEU7pkUozsvDqsGuwgSamS0VCcKjH16aDyHcjmrk3TrdfUIxVi0V0B0q/6rDA8PawEWspGXG0QF8zBFbKJyX/CIDPF64wcn4vNVdZPr2V/f39R+cjly5dP3PrMbWdMMoKBqTBKmTKaJF4DKSFhrn/qbTEaAAFGO6jrq1Lf20TrYkHZ/sqmTYgwmotU6LfiZDGuwv6ePHny3PC161VCnUkxkBnbtyCulqnUGhkoMdiQRBoh1OqJ1Yml0Ob58y+e3d69ibVWUprQqBsCrtMhFfFJljzHsBmKhM0YCZslJirDnzCNcBxCbj66wfajmwlRE1OcsWfbFa7Q3v7t9XJBLpxOnlwa1QDqN4YWB4LDhOxHAiUDI8goE3gQBxrKhUKUC7//X6cHHWT7se0ylX33VoavDaZXiJzX0umh0XmkwvWSdrWFYMp1NiaZVUZFWH8t5LAB6kFQzBOKOxkz0BEs5+1G3H2bR3YlnEocr9QSmv9NXmYK3LMqFxTHgrSAUePiepYAWf/N9cvt8se2ZPdob4GGoQSqvyLfAS6fC3IeEagaU0CACrJZUwI1vA3f3LOVzT3zDKyuNn0FeqDuSOD1U9ePBdiufrjZXIUSXnjnImdugpie5FSHzBWrOTblrBfZ9WQe1k8dAJE//rozDShlqMEjWmiUudo6LoTCGL5YoEQQsY477xu58EKuxHRmczue017xvHbzsYa/3i+EoGR6C2lWM2WjHk4k3ZqvqH6DzVAXlc2TAdgkjP9ZP7Uvm09cXkbkT7w+onGP6wkoTLpdRBoz6nzRAJkdocZ3saMgNPUxxelA2Q+KKn77a69fmbeLMpVBgsheLv+YI+xXjxTbkCCdEGu1UiG5+i65YEhb7KafCcNT24KxW7bTLg2EgcvnlCK29Jjhq/tjouLeqyf05cuXTwyyL3nsF2BWCjdfDFz+4ibutIZJmKvg0ojh6vyicbJQMSF7DNEJRC48+L3T8qnWF4VmZIlVx0qdBQl3NYNVaKlBSlpQYaYStaowqsI1cL4TdQVllRFbqK4/OTLI+q/2jXbK6GNyCOFZsTH/EkVdKmsiDeI7zjb3vnG1EWvpFxaRPcA+XF1ObHjyiKWAYwij+1lK4chlZkyh3jOPQhLbkoLO9IRWko0rISEq6yePCERk+6k3FhE6j3+Q4lxljRUMwGx6ngrOTZtL87sM0yLj89tfX7DWYMtr90xxkFj1NzxxJA/cKvbOuuMm4yx2nJsSq4PF2VBJqRU0ZVGCeZb2+CarzVRH7HsbQszrHoAkRwYZ/vKIBfylnj7kywZ8dimXQ6nNSb/9m7q8agYuS73+i+vQqpwUaTcWV9VpfYe9GroppnKBJrxmnuBSBBjXH2pbvAVqEt5Zu6TZV+kZZuCIyPa+N5bSGsMTR2ybEGfI4AoVW3pGlWaIxLEW972xuO3n5MmT5y78zvdOM3VWpmONOgcVtu6W2y1zq0YQ03koVCdsQHmgTpAzlpviwYj5pkIz5fiSe2aDmDkWKSxIuLGS2k/YckKmlhYPiIhu73vDhEdp/Qi2aNEmMdRme6S0i0amW0Tc/f39ixc++5+nxfQIQ3T9Z9cBvovMFIWVVgylwaJmjA1sN1ruem9JutMAftaziM1tNkdmq60EULXrapX6Cuz3t5/+3+XVKn9+bb3uSg6nB00dzDquK7lst9VVydKQl+uGc4EbnsSB7dxAJTZwtxX9DOb7tBpzvFKaTUwCwjdZ5yk3BkWj9FsGC+rvD1+5dvHBbj79pp08FFCKFHjdZohZ+fuBERd+iF155kocHCdVva1YOJKzRWJzuuXg+UE2k6I8Tc4RG1QDbJLkPLXOjZjgbBO4Mb2HLtEz148vJ/L2M2+69hXYCQIgZRf3f+uL7zuz/cyby4n7letyfZmK1I37gOjw2GG0XSRpB+TtC21jrZjOENcuYstxYDAvKn2RVh0POWhVc681G5qnvWrn7Qdl8dv731rs4Ax/etjWRUlrRvT4wfb+5cQdHj8s/ba5YjJ0+PJhmPG46lrHdbdXb5h2DibS5AhA4ybbIiwKOcCGJXfe11hnVfbruwrp755pb/vn9585f/782cUe9mOHNbOrW8f2/rfkIH6Gx66lc3LjltUegA5/chg2rHDEhR+l7+JNTyvXZc4U8N1PrVdOJADAhFGtsIMaekxhn5Zp8dYncwOmDCNRGPXAYiJg+PI12uqkXnrv4bHDNeN3ZCb9rKzNDc52BJsOk5LB4UI0DbYOCS7DJCZ95np54GqH3djA7AD7NGHgiTYqPBmorq2SUgQXaueHp8YOXzq8lMC6feBHxv5vH3jrIBjHOIzwTqSwL1SKFnT44h5s25yaZHWFwqhtawFLn5uEnmC6MrTLQqL1XGftcGKvjbJhf9xUV/6e5oSIv21UZ5zoV5Htb/1omcR96ZqRwL99APfx4auIByEre6kqssfQVp5Enp2D1hw+1wngk4Rm5CkogQSH0yLzCryhDGKYrQwlLzg4gEYTcxPLtNSs6olLxQk8lLfUw17IICb95ENUHjHrMQJqENfhC4fQlQapS0bgrWxuGJMOsMDdUh3s1MGJ3Wv8PzDvw0330+5IqM/+n7wbP8MXrzFMLZUQtca0Wt9lz7/DqNdhDuce2ZyDw40rq0TvhICrz1L7VpKuYxUaCBH8CFyS0OAn5DZefoPWq2b8EeHdIe4X9ka/xZOCXjJSsnfu5UY8jGb4/CHr0Go9c6cQ1jW+XGGmpmsupsalumsUjQSWiO21FbLD6gd9YuJlif69CDbe3j749o+HuH98KDN+am9xr4ipD03d5PNIm72Sn1VbFVhV+4nJZ1ohb+lIqaapgqlEE+MrdW7i1mgbgxdyEKAx/h32jR62fMXUwjhIsyupLc3xDhP384dMzhwKW5MF+9YYmJStScwTVMkuNtx0MLgJ6GZ2o8OJgxtbYGqCyUkL/h7ctoq6BrpaW8HN4SBSfq7S/EzxBelc8O/gUa50NPj1o4dkeHT1jhD21KmfPzM8eshBq+5MzTmPBe7jPoI9u0C4+PA5xdSUp86LYeu0hXeu+H1I7CVoYyCyqGnNrK5xQmVmcM9E+tNWtP8cbbxLARRObn83HCR9w/BHq5V3orTRLN/dmC3eLh8Pjyja3/b4XusSbThwNo1YDxGSGg41zpar8Kigxxp9Eudc7Pbm34Y3UD1TayiVbrz9veVEHv5wJY2pSDFc1YlX2WAGix5/XfkuP/s+Iqnqg/17knLBs0mbSYW42JmPjXsHjq9h0o+md4qGs2UUJ7jEOs+CNOhV63oxvUXlHuqK+slmxIT98MgydT18blWbvjzFp/0ikoJaTdCF9rqyL/B1h4GOrfUzj/2Lm9Cwmd4JCHCzEdwafPqL04WhVEUYQhVc0xhxM8ne57OD6wgM4t4uI83W0nTd8AdXSdxH1O4VaOzPQrTVWTYEyndsruwNXOLfl+u4t4nBS59fBDyB6jyp4UwjQR3GYjStWpfPW6vJR/fWYKfHE5MEaTuSwZ7P8PDoJO1E2IdFhod1+nx9OyufkzTOz2s6crhWlSnChOGaUvvcVllJVcf+tRaMGawp+HV6T19qjqf3LNRmCDa0kJYmcr83nvnyT714dqcuRz/SH16j9Vph1DEpaq3l9xMgOjzUcJLnRqi2/rbTO14m0sot2BEz35965Usrx9/7XaT3xrrd3HF3r+3DDcl9SHYbRysT5z0naI2zWs3CTto4zB4k1bpu6kDmiKvSr1dDZ8ONgnxz/9Y70luNUvx8bfxb+gw9PLQDnOfXLBP1FDpB/MmRO/n9wf3IYfagJxI3VwXnzhR/dCVr7ntTRJ5iEnSYdUbCKiLPnZ02zJruqDmkw6SSJNhzps7YYZm4Xme4rid9mGGYK/ELelzeOzRMrLMF9mPiXNB49twr5VqS6JlRJ7QfOucPKe2jkzYHE+pRZ3JxmCG2TDDJHD4xp7Z3eZ7O3B87qtGenUeDAaRD2CnfYteJqO7ve80bYMLOTDk3soNK1CtQ6TpxODJx315U0Hu2ziKX08Sck3rZUavpDgLWMpk9Jmw6WbrDQuc4WmdU5S4mYM5jnHKkZEaNehODCUmbMkGeiXsFCFOO3Fz0sYum1CkbPOfJtfT/lCd4JU7BlO2cHmjZ9uB7Utpjtl3XP6dm59T+lO3Whh2VGSbFhHZz9151VY3saMx77rrMxHG7hE67MAk6tndK4nQH4s1lcNAJnbTjLOkVRAm72NjWtQ3GW00ePHZUM9qRSEzEbFMe5dwLm9z9oTtI8y6ap2cX5zTaLszRA1e0YzJ2iQx2iKdXzQuxI0ihDRWDiThaJsCTHkPpjIbh19dMSe4cQ2FCPe/qEcuMgzcXLmJHDaYzJoR+/38re1s0IaSDcwAAAABJRU5ErkJggg=='
SIN0 = b'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'
SIN1 = b'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'
SAW0 = b'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'
SAW1 = b'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'
SQR0 = b'iVBORw0KGgoAAAANSUhEUgAAAHgAAABQCAYAAADSm7GJAAAABmJLR0QADACAAADdhk3+AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5wodDgQBNqPO4QAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAABY0lEQVR42u3dwWrCMBzA4f5rpHgQ92Z9/8dYwR7ENDu5sQ6HimBtvh940INoPhNrKhqllEbrrTUEgAVYgAVYgAVYgAFrLaX5DTnnJqVU3fbWOI6x2+0W97g+h6H5OBxu9pimKSLi+3rMtypPp1PTdV2V+5ellFjaY4qIuyzO53NsNpvrS3TO2br23i/S/9+Dc56M0pqB5ShagAVYgAVYgAELsN619Kw7iog8DENayhPb7/e+D/xM4OPxmLquM6LrncFt07ZWfO/BAqwFAkcYTDNYgAVYgAUYsAALsAALsAALMGABFmAB1hsCO+NvBguwAOsVwL50ZwYLsAALsAADFmABFmAB1uMlQ/DTvT++XdkMthltiRZgAdYrgJ0PNoMFWIAFuOZidjAEuLYZvN0+tnu5tF+a7fu+rxJ05vDnzylLKb8utywJlzuNBX1Wuuc5rGl5vlyuAstBlgALsAALsADX3RePsVDp3q2d4wAAAABJRU5ErkJggg=='
SQR1 = b'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'
PW_SQR0 = b'iVBORw0KGgoAAAANSUhEUgAAAHgAAABQCAYAAADSm7GJAAAABmJLR0QAAAAAAAD5Q7t/AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5woTFTQJF5JLggAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAABsElEQVR42u3dzW6CQBRAYa5giAtj3/9V+lQl0YVxnK5sWoxGKhpgvpOwkAWBOd57h/nRyDlXWC4rTUAwCAbBIBgEg2AQTDCWQtM/kVKqmqYpbnjrcDjEZrOZ3H19dV31sds97ON8PkdE/HyO/lDl8Xis2rYtcvwy5xxTu6eIGOTidDpFXde3U3RKSV6b95f0fg1O6ayVliwYetEgGASDYBAMggkGwZgrzVgXiojoum4yD7bdbq0HHlPwfr+v2ra9Ol/X9aCGTikFLZOM4FW1Wj2f8ce4Bl4geMRUf3XO7gudLLxacKicInjMtA0pGgQTDK9J9/m9UlEtFcGYWwT3olmLi2DMKoKHrsyf4u4CEQyCQTDm3ot+sGbreYtgEAyCCR5WPbVmiZ2s/sCFCQcpGgTj7YJl3kJrsMkGKRoEg2AQTDAIBsEgGO/i7ZMNWJjgOTF01K2wFC1Q1WAsL0U/M9lgokIE412CzQeLYBAMgkFwyfSXJRNcWgSv1/97NZ7ar8Q2TfNZpNCeh6s/p8w5/zkeSQmXi05p18KQZ1hSer4cNwVDJwsEg2AQDIJBcNl8A9shdYhMIIqZAAAAAElFTkSuQmCC'
PW_SQR1 = b'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'
S_H0 = b'iVBORw0KGgoAAAANSUhEUgAAAHgAAABQCAYAAADSm7GJAAAABmJLR0QADACAAADdhk3+AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5wodDgUykGietgAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAABjklEQVR42u3dMUrDYACG4U8bFcFCHVy8i15B0MXN+7i7indx8AI6OqiDkyCCg5WqQzppLLY2bdI+D2QJkib/m/ylJY0JAAAwH/dJPmtcDhp2vIc1H+/DtHZ0dUrb6TvHm2lagTcN5WIHRmAERmAERmCB63CcZD3JSsVyNeE2L2r+wuH8H8d7m2S/4liLJEcTbnP7D/v8Pq/AN99ffME9JrmsWD9IcrdsU/RgyWbON+/BCIzAAhsCgRG40U6TdCo+j24lORO4/Z6SfFSsf015J4rACIzAzDtwL8lLRn+R3TNk7Q38HDfPmaIRGIERGIERWGBDIDACIzCtCNytWNdxotTSpahYvzPuhoox//7e2M/Ebqb0IwFXnikagREYgREYgRn5OXitofvZ++Xk7LZ03K9T/rrCFTx0kZ93eA5SPjMSU7TACIzACIzACMxfFQ3Zjz0pXMEIjMACIzACI3AbDARebL/dANGapw0VGo50kvJ/TfRTPtsymdGdGALPzsZwMUUjMAIjMAIjMAAATOYLfr13Aq+RR30AAAAASUVORK5CYII='
S_H1 = b'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'
OCT_10 = b'iVBORw0KGgoAAAANSUhEUgAAAHgAAABQCAYAAADSm7GJAAAABmJLR0QADACAAADdhk3+AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5wodFiEd2GSwgQAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAAE40lEQVR42u2cXYhWRRzGf+7a7ta6tUJfBlGLRR8Y9mEbUhaVIlEZWBR2twjeSNHGEtVFFIZg1J10EWhBbUVFEWRtbFJpmJZmIRGLgWtSLhip2277UbpdnAmWt3P+M/O+8+7n84Nzse+cmWfnPGdm/jPvzAtCCCGEEEIIIYQQQgghhBBCCCGEEEIIIVIxp0rl1gKnJrAeNcDpyDz1Var/31Woew1Ql/P5KadXVeqBB4BOoAf4CxgDRoBe4H1gLXBOQs1bgc3AXqDfmTsMHAbeBdqAszxl9Lr/M/X1WBWe8eYCrfeqbe4a4JfAiv8BdLi3sVxagd2Ben3AeqOVTheDL3Mv8YQaXAtsKfMBfAacXYbmetcdxep9BMyfpga3Aj8bWlUzuLPCh/A1cGaE3iMV6u0DmqaRwWuALjfGjk20wR2JHsTWQL3bgH8S6HWXdNdT2eAvArW8BseOhwuB5xO9KG3AyoAAbosbEiplObBOEyebdzxv1GvAYhfBLgQ2uOi26P4fPVOVxz16O4Db3Zh+AdAODHgCveaAep7rGdOrTbIWHMPFnq7y2YJ893rGkhVG73LI86DPyMm3BBg08j0qg/PZaAjt93T3rxh5PyzIs8rI0+9abBFPe3oNGZyDFa4/6Ml7iVuMyMs7CszLyfOGofeSR6/ZMzS0THGDnwHedtcPE2FwiyEyELBqBLDLKOOenCXUPuP+JQF6nxj526a4weN5shKD50ZEoEXsccuTPj4HlhakrSh5cIuMLvikm9f62ABsK0g7OFui4lCDrzXS9gWWsddIWxyh9517e0N6jF2zfdoTOg++3EjrCSzjp4jyU+iJiBZsPfDfAss4aqRdBDS66U0qvcmmtmAal0c1vmKMasEXGml9gWWcBIaM9PMT60027a6+IVf7ZHbRNUCDkT4YoWcFY+OnSo2J9GY9IQbP86SPROgNG2mNgZojsi2twfWe9NEIPevehkDNUdmW1uAhT3pdhF5doM5QIj1F0QH3/LdwP6fMFl7USq2xdaCCHmWq8KK7pnwLHvMENo0RetaS5nhT/0ykpy468L4jRtqCwDKaKd6mM1Yy/UmhJyIM7vEsUoSwwPMCDSfWE4kMviKwjKuMtIMRelfKtvQG7zHSbggsw/qKb3+E3vVU70TGrDV4O9l2nTxuCgx87jDSukv+PgocKLi3CbhR1qU1uJ9sL3NRZLzKk7/FvQh5jAA7cz7vMsp72KN3HfCVcS2V9f9nLcU7Cw5gb2191cj7VkGeRdi7SKygbasnr2/T/YzZ0RFDA/C7IbaxIN9q7F2VN3uGhqJ8XeSvai336L0eUNdZaTDAc9i7/N504+N84GpgE9nacdH933j07sJ/BGYlcB7ZIa0O7H3Rp13PIIONVaRfSXfMY1mA5qcJ9ToD6zljDI49ujI4biyulJcLgqtS1gHHE+gdITvEpijaQxfwVIW6X5IdSwnhMPAQlX0PfBy4n+zoigwOYBPwBOXtI/oYuDvSsG7gPuBEGXqHyH4R4FtNhOJZBnwfOP4dc11kJatQl5IddQnRGwBeIGxT/owdg+dWKL6TbOnwTrLf6Wh1JjSR7b/qI9vHvA34APt73hB6XUu+huyQ9C1ka9PNLlo/5vS2u4j+hNqgEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhIB/AaEmaIn14+bFAAAAAElFTkSuQmCC'
OCT_11 = b'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'
OCT_20 = b'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'
OCT_21 = b'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'
RND0 = b'iVBORw0KGgoAAAANSUhEUgAAAHgAAABQCAYAAADSm7GJAAAABmJLR0QADACAAADdhk3+AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5wodDggJlM0J3wAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAAEUUlEQVR42u2bbYgVVRjHf2s3FdHELDBDRFkp0mj9kJZQS6jpB1cyEYSCTGqpPgS9SPkSWZatICKIie8lqX1z00AKdrMgjC1Jkoja2JTCfGWlTL2u2/XDOReWy505c/fO7Jy5/H9wvtznzDkz8587z/Oc8wwIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCFHz1PXjmHqgs8JjrgOXbTsJ/Ap0AIeAswnMf9r2uxphvAbgxxB7E/B5FefyP9BjWx64BHQD54A/gN/tvThm7alTDxRiar3AZ8B9Ccy/LOJ4DY5x5g3QvfgP2As01pLAxXYdWBzz/BeA2zIkcN/WDtwTh1iDPHEVt9qn95EYxxwNvJZR1/kYcBxYUisCF89lS8xjvgLckVGRhwK7geW1IjDAZOCBGMcbUe0N8oC1wPM+Cfy1jc6LbTAwFpgPfBPx9RQnLwF3pyRO33sxCBgFTLSReQtwKuI4m2J+8KsKco6EHJsDvnMcvy6BIG9rSkHWEce13AI8bdMm1zV8m4VX9A3g4wiv1bhZasXwjV7gE2CqXR8IYwYwNws++IzDfimGh6jcm+Ndj/3sSevCrjj6vZgFgcc67CeqHH9XwO+Lgfs9FvlEhCxiDjDcZ4FzwDMh9jzwZZVzfAW0lfm9Dnjf84h5g/W3QQwBpvkmcA4YYyPHNuDBkL5bgYsxzLki4Pcm4CGPBT4N/OLo05C2wI0l0V8P8DdwEHg05LgfgJUxnUMH0BqSV/pMh8M+PosLHQeA2ZjdprhYhdnJKZdnz/JY4PMO+6isCNwLHAYeB56MIXou5WdgX4DNZ1/8j8M+JCsCF2xacDbBOd62LqKUacATngo80mG/lhWBc8BC4CiwIKE5uoCdAbY1+LcWD3Cnw96dNR88DPg0weh2DeUrO6YAT3ko8HSH/VTaAvddYL/dpkXbKb/CVGQwsKdS/1JB6rE5wLYasxftC+OAex19jvv0D+626U8zsCggqi0yCXg5ofNoCQheJgLPeSTw6w57PkIaldoruhWzUhPGG1S4FBeRiyFzL/VE3Kn2jxDGF5jaLW998DuOPG808EJCc2/A1GmVC/bSph5TfDjU0a/iipeBFvgysN7R59WEfPG/wAeeBVQ5TN3VMet/wzhq/8FeC1x8CsMWNe4Cnk1o7g+Bv1ISs87muBMwRQQtNo3bjbv6M4/ZKiwM1OukmioGgPccY3Rhqh36M7+r/LaZyqpB0iibLW3N/RUrrTx4I+Gb2xOIXiddKbswXxNkhRXAtqwJfAHY4ejzJv37tMbFDcwSpu9cta6qqrghzZWs9ZRfJy4yBVPGkgT7gZ88Frcds+/7UbUDpSnwn5iCszCSqmkuAG95JuoV++A1AjOB3+IK09NkHaaEJ+hBm24vti2BuQ/a1OPhhK+xYN1CD2YnqPTrwk7ge8yKXx4hhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQoia4SZJJJnQ3iF34wAAAABJRU5ErkJggg=='
RND1 = b'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'

images={}
images['OFF']=[OFF0,OFF1]
images['TRI']=[TRI0,TRI1]
images['SIN']=[SIN0,SIN1]
images['SAW']=[SAW0,SAW1]
images['SQR']=[SQR0,SQR1]
images['PW_SQR']=[PW_SQR0,PW_SQR1]
images['S_H']=[S_H0,S_H1]
images['OCT_1']=[OCT_10,OCT_11]
images['OCT_2']=[OCT_20,OCT_21]
images['RND']=[RND0,RND1]

IMAGE_SUBSAMPLE=4
TEXT_SIZE=26

def make_analog_synth_window(AS,theme,loc,siz):
    prefix='-ANALOG_SYNTH-'
    group={}
    column={}
    frames={}
    ADSR_Frame_number=0
    ADSR_Frame=[[]]
    psg.theme(theme)
    ANALOG_JSON_FILE='analog.json'
    with open(ANALOG_JSON_FILE) as json_file:
        analog_parameters = json.load(json_file)
        if 'Skeleton' in analog_parameters:
            column_names=analog_parameters['Skeleton']
            layout=[]
        else:
            layout=[[psg.Text('Cannot create layout for'+prefix)]]
            column_names=None
        if 'data' in analog_parameters and column_names:
            
            name_index=0 if 'Name' not in column_names else column_names.index('Name')
            short_name_index=0 if 'ShortName' not in column_names else column_names.index('ShortName')
            address_index=0 if 'Address' not in column_names else column_names.index('Address')
            length_index=0 if 'Length' not in column_names else column_names.index('Length')
            group_index=0 if 'Group' not in column_names else column_names.index('Group')
            label_index=0 if 'Label' not in column_names else column_names.index('Label')
            column_index=0 if 'Column' not in column_names else column_names.index('Column')
            frame_index=0 if 'Frame' not in column_names else column_names.index('Frame')
            verticalgroup_index=0 if 'VerticalGroup' not in column_names else column_names.index('VerticalGroup')
            orientation_index=0 if 'Orientation' not in column_names else column_names.index('Orientation')
            type_index=0 if 'Type' not in column_names else column_names.index('Type')
            valuefrom_index=0 if 'ValueFrom' not in column_names else column_names.index('ValueFrom')
            valueto_index=0 if 'ValueTo' not in column_names else column_names.index('ValueTo')
            rangefrom_index=0 if 'RangeFrom' not in column_names else column_names.index('RangeFrom')
            rangeto_index=0 if 'RangeTo' not in column_names else column_names.index('RangeTo')
            default_index=0 if 'Default' not in column_names else column_names.index('Default')
            list_index=0 if 'List' not in column_names else column_names.index('List')
            description_index=0 if 'Description' not in column_names else column_names.index('Description')
           
            for row in analog_parameters['data']:
                
                if row[group_index] not in group and row[group_index] !='N/A':
                    if row[label_index]!='N/A':
                        group[row[group_index]]=[[psg.Text(row[label_index],expand_x=True,justification='center',
                                                           background_color='yellow',relief='raised',text_color='black',
                                                           font=('Arial',12,'bold'))]]
                        column[row[group_index]]=row[column_index]
                    else:
                        group[row[group_index]]=[]
                        column[row[group_index]]=row[column_index]
                    if row[frame_index]=='':
                        tempframe=None
                    if row[frame_index]!='' and row[frame_index] not in frames:
                        tempframe=psg.Frame(row[frame_index],[],key='-AS_FRAME-'+row[frame_index]+'-')
                        frames[row[frame_index]]=[psg.Frame(row[frame_index],[],key='-AS_FRAME-'+row[frame_index]+'-')]
                        group[row[group_index]]+=[[tempframe]]
#                if row[verticalgroup_index]!=''and ADSR_Frame[-1]==None:
#                    ADSR_Frame[-1]=[]
                if row[type_index]=='SLIDER':
                    key_value='-AS_SLIDER-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    text_key_value='-AS_TEXT_SLIDER-'+row[short_name_index]+'-value'
                    text_key_value.replace(' ','_')
                    orient='horizontal' if row[orientation_index]=='horizontal' else 'vertical'
                    if orient=='horizontal':
                        if tempframe:
                            tempframe.add_row(psg.Text(row[name_index],size=TEXT_SIZE))
                            tempframe.Rows[-1].append(psg.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                       default_value=AS.attributes[row[short_name_index]][0], orientation='horizontal',
                                       size=(20,10),enable_events=True,key=key_value,disable_number_display=True))
                            tempframe.Rows[-1].append(psg.Text(int(row[default_index]), enable_events=True, key=text_key_value))
                            # tempframe.add_row([psg.Text(row[name_index],size=28),
                            # psg.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                            #            default_value=int(row[default_index]), orientation='horizontal',
                            #            size=(20,10),enable_events=True,key=key_value,disable_number_display=True),
                            # psg.Text(int(row[default_index]), enable_events=True, key=text_key_value)])
                        else:
                            group[row[group_index]]+=[[psg.Text(row[name_index],size=TEXT_SIZE),
                            psg.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                       default_value=AS.attributes[row[short_name_index]][0], orientation='horizontal',
                                       size=(20,10),enable_events=True,key=key_value,disable_number_display=True),
                            psg.Text(int(row[default_index]), enable_events=True, key=text_key_value)]]
                    else:
                        if row[verticalgroup_index]=='':
                            group[row[group_index]]+=[[psg.Text(row[name_index],size=TEXT_SIZE),
                                psg.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                           default_value=AS.attributes[row[short_name_index]][0], orientation='vertical',
                                           size=(5,None),enable_events=True,key=key_value,disable_number_display=True),
                                psg.Text(int(row[default_index]), enable_events=True, key=text_key_value)]]
                        else:
                            ADSR_Frame[-1].extend([psg.Column(
                                [[psg.Text(row[label_index],k=text_key_value+'top')],
                                 [psg.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                           default_value=AS.attributes[row[short_name_index]][0], orientation='vertical',
                                           size=(5,10),enable_events=True,key=key_value,disable_number_display=True)],
                                 [psg.Text(int(row[default_index]), enable_events=True, key=text_key_value)]
                                ]
                                 )])
                            if row[verticalgroup_index]=='END':
                                group[row[group_index]]+=[[psg.Frame(row[frame_index],[ADSR_Frame[-1]],k='-AS_FRAME-'+row[frame_index]+'vert')]]
                                ADSR_Frame.append([])
  
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='TEXT':
                    key_value='-AS_NAME-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[psg.Text(row[name_index],size=TEXT_SIZE),
                                               psg.Text(AS.attributes[row[short_name_index]][0],size=TEXT_SIZE)]]
                elif row[type_index]=='ONOFF':
                    key_value='-AS_ONOFF-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[psg.Text(row[name_index],size=TEXT_SIZE),
                              psg.Button(image_data=onoff_data[0],metadata=[0,0],auto_size_button=True,border_width=0,
                                         button_color=(psg.theme_element_background_color(),psg.theme_element_background_color() ),
                                         key=key_value, image_subsample=IMAGE_SUBSAMPLE)]]
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='LISTBUTTON':
                     key_value='-AS_LISTBUTTON-'+row[short_name_index]+'-'
                     key_value.replace(' ','_')
                     tmp_layout=[psg.Text(row[name_index],size=TEXT_SIZE)]
                     for part in range(int(row[valuefrom_index]),int(row[valueto_index])+1):
                         tmp_layout+=[psg.Button('',auto_size_button=True,border_width=0,
                                    image_data=images[row[list_index][part]][1 if int(row[default_index])==part else 0], 
                                    image_subsample=IMAGE_SUBSAMPLE, mouseover_colors=(psg.YELLOWS[0],psg.YELLOWS[0]),
                                    button_color=(psg.theme_element_background_color(),psg.theme_element_background_color()),
                                    metadata=[1 if int(row[default_index])==part else 0,
                                              [ i for i in range(int(row[valuefrom_index]),int(row[valueto_index])+1) if i!=part ],
                                              row[list_index][part]], key=key_value+' '+str(part))]
                     group[row[group_index]]+=[tmp_layout]
                     #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='LIST':
                    key_value='-AS_LIST-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[
                        psg.Text(row[name_index],size=TEXT_SIZE),
                        psg.Combo(row[list_index], default_value=row[list_index][AS.attributes[row[short_name_index]][0]], key=key_value,
                                  readonly=True,enable_events=True,size=10)]]
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
    layout = [[psg.Button('Fake buttton'), psg.Button('Popup'), psg.Button('Exit')]]
    current_column=0
    col=[[],[]]
    for line in group:
#        if column[line]!=current_column:
        col[int(column[line])]+=group[line]
#    for ccc in col:
    layout+=[[psg.Frame('',col[0],border_width=0),psg.VerticalSeparator(),psg.Frame('',col[1],border_width=0,vertical_alignment='top')]]
    return psg.Window('Analog Synth', layout, location=loc, resizable=True, size=siz, finalize=True, 
                      icon= music,return_keyboard_events=True)

def make_digital_synth_window(DS,theme,loc,siz):
    prefix='-DIGITAL_SYNTH_'+str(DS.id)+'-'
    short_prefix='-DS_'+str(DS.id)
    group={}
    column={}
    frames={}
    ADSR_Frame_number=0
    ADSR_Frame=[[]]
    psg.theme(theme)
    DIGITAL_JSON_FILE='digital.json'
    with open(DIGITAL_JSON_FILE) as json_file:
        digital_parameters = json.load(json_file)
        if 'Skeleton' in digital_parameters:
            column_names=digital_parameters['Skeleton']
            layout=[]
        else:
            layout=[[psg.Text('Cannot create layout for'+prefix)]]
            column_names=None
        if 'data' in digital_parameters and column_names:
     
            name_index=0 if 'Name' not in column_names else column_names.index('Name')
            short_name_index=0 if 'ShortName' not in column_names else column_names.index('ShortName')
            address_index=0 if 'Address' not in column_names else column_names.index('Address')
            length_index=0 if 'Length' not in column_names else column_names.index('Length')
            group_index=0 if 'Group' not in column_names else column_names.index('Group')
            label_index=0 if 'Label' not in column_names else column_names.index('Label')
            column_index=0 if 'Column' not in column_names else column_names.index('Column')
            frame_index=0 if 'Frame' not in column_names else column_names.index('Frame')
            verticalgroup_index=0 if 'VerticalGroup' not in column_names else column_names.index('VerticalGroup')
            orientation_index=0 if 'Orientation' not in column_names else column_names.index('Orientation')
            type_index=0 if 'Type' not in column_names else column_names.index('Type')
            valuefrom_index=0 if 'ValueFrom' not in column_names else column_names.index('ValueFrom')
            valueto_index=0 if 'ValueTo' not in column_names else column_names.index('ValueTo')
            rangefrom_index=0 if 'RangeFrom' not in column_names else column_names.index('RangeFrom')
            rangeto_index=0 if 'RangeTo' not in column_names else column_names.index('RangeTo')
            default_index=0 if 'Default' not in column_names else column_names.index('Default')
            list_index=0 if 'List' not in column_names else column_names.index('List')
            description_index=0 if 'Description' not in column_names else column_names.index('Description')
           
            for row in digital_parameters['data']:
                
                if row[group_index] not in group and row[group_index] !='N/A':
                    if row[label_index]!='N/A':
                        group[row[group_index]]=[[psg.Text(row[label_index],expand_x=True,justification='center',
                                                           background_color='yellow',relief='raised',text_color='black',
                                                           font=('Arial',12,'bold'))]]
                        column[row[group_index]]=row[column_index]
                    else:
                        group[row[group_index]]=[]
                        column[row[group_index]]=row[column_index]
                    if row[frame_index]=='':
                        tempframe=None
                    if row[frame_index]!='' and row[frame_index] not in frames:
                        tempframe=psg.Frame(row[frame_index],[],key='-AS_FRAME-'+row[frame_index]+'-')
                        frames[row[frame_index]]=[psg.Frame(row[frame_index],[],key='-AS_FRAME-'+row[frame_index]+'-')]
                        group[row[group_index]]+=[[tempframe]]
#                if row[verticalgroup_index]!=''and ADSR_Frame[-1]==None:
#                    ADSR_Frame[-1]=[]
                if row[type_index]=='SLIDER':
                    key_value=short_prefix+'_SLIDER-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    text_key_value=short_prefix+'_TEXT_SLIDER-'+row[short_name_index]+'-value'
                    text_key_value.replace(' ','_')
                    orient='horizontal' if row[orientation_index]=='horizontal' else 'vertical'
                    if orient=='horizontal':
                        if tempframe:
                            tempframe.add_row(psg.Text(row[name_index],size=TEXT_SIZE))
                            tempframe.Rows[-1].append(psg.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                       default_value=DS.attributes[row[short_name_index]][0], orientation='horizontal',
                                       size=(20,10),enable_events=True,key=key_value,disable_number_display=True))
                            tempframe.Rows[-1].append(psg.Text(int(row[default_index]), enable_events=True, key=text_key_value))
                            # tempframe.add_row([psg.Text(row[name_index],size=28),
                            # psg.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                            #            default_value=int(row[default_index]), orientation='horizontal',
                            #            size=(20,10),enable_events=True,key=key_value,disable_number_display=True),
                            # psg.Text(int(row[default_index]), enable_events=True, key=text_key_value)])
                        else:
                            group[row[group_index]]+=[[psg.Text(row[name_index],size=TEXT_SIZE),
                            psg.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                       default_value=DS.attributes[row[short_name_index]][0], orientation='horizontal',
                                       size=(20,10),enable_events=True,key=key_value,disable_number_display=True),
                            psg.Text(int(row[default_index]), enable_events=True, key=text_key_value)]]
                    else:
                        if row[verticalgroup_index]=='':
                            group[row[group_index]]+=[[psg.Text(row[name_index],size=TEXT_SIZE),
                                psg.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                           default_value=DS.attributes[row[short_name_index]][0], orientation='vertical',
                                           size=(5,None),enable_events=True,key=key_value,disable_number_display=True),
                                psg.Text(int(row[default_index]), enable_events=True, key=text_key_value)]]
                        else:
                            ADSR_Frame[-1].extend([psg.Column(
                                [[psg.Text(row[label_index],k=text_key_value+'top')],
                                 [psg.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                           default_value=DS.attributes[row[short_name_index]][0], orientation='vertical',
                                           size=(5,10),enable_events=True,key=key_value,disable_number_display=True)],
                                 [psg.Text(int(row[default_index]), enable_events=True, key=text_key_value)]
                                ]
                                 )])
                            if row[verticalgroup_index]=='END':
                                group[row[group_index]]+=[[psg.Frame(row[frame_index],[ADSR_Frame[-1]],k=short_prefix+'_FRAME-'+row[frame_index]+'vert')]]
                                ADSR_Frame.append([])
  
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='TEXT':
                    key_value=short_prefix+'_NAME-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[psg.Text(row[name_index],size=TEXT_SIZE),
                                               psg.Text(DS.attributes[row[short_name_index]][0],size=TEXT_SIZE)]]
                elif row[type_index]=='ONOFF':
                    key_value=short_prefix+'_ONOFF-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[psg.Text(row[name_index],size=TEXT_SIZE),
                              psg.Button(image_data=onoff_data[0],metadata=[0,0],auto_size_button=True,border_width=0,
                                         button_color=(psg.theme_element_background_color(),psg.theme_element_background_color() ),
                                         key=key_value, image_subsample=IMAGE_SUBSAMPLE)]]
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='LISTBUTTON':
                     key_value=short_prefix+'_LISTBUTTON-'+row[short_name_index]+'-'
                     key_value.replace(' ','_')
                     tmp_layout=[psg.Text(row[name_index],size=TEXT_SIZE)]
                     for part in range(int(row[valuefrom_index]),int(row[valueto_index])+1):
                         tmp_layout+=[psg.Button('',auto_size_button=True,border_width=0,
                                    image_data=images[row[list_index][part]][1 if int(row[default_index])==part else 0], 
                                    image_subsample=IMAGE_SUBSAMPLE, mouseover_colors=(psg.YELLOWS[0],psg.YELLOWS[0]),
                                    button_color=(psg.theme_element_background_color(),psg.theme_element_background_color()),
                                    metadata=[1 if int(row[default_index])==part else 0,
                                              [ i for i in range(int(row[valuefrom_index]),int(row[valueto_index])+1) if i!=part ],
                                              row[list_index][part]], key=key_value+' '+str(part))]
                     group[row[group_index]]+=[tmp_layout]
                     #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='LIST':
                    key_value=short_prefix+'_LIST-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[
                        psg.Text(row[name_index],size=TEXT_SIZE),
                        psg.Combo(row[list_index], default_value=row[list_index][DS.attributes[row[short_name_index]][0]], key=key_value,
                                  readonly=True,enable_events=True,size=10)]]
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
    layout = [[psg.Button('DS'+str(DS.id)+' Fake buttton'), psg.Button('DS'+str(DS.id)+' Popup'), psg.Button('Exit')]]
    current_column=0
    col=[[],[]]
    for line in group:
#        if column[line]!=current_column:
        col[int(column[line])]+=group[line]
#    for ccc in col:
    layout+=[[psg.Frame('',col[0],border_width=0),psg.VerticalSeparator(),psg.Frame('',col[1],border_width=0,vertical_alignment='top')]]
    return psg.Window('Digital Synth '+str(DS.id), layout, location=loc, resizable=True, size=siz, finalize=True, 
                      icon= music,return_keyboard_events=True)



def make_main_window(theme, loc, siz):
  global notesstring, defaultinstrument, instrumentlist
  psg.theme(theme)
  menu_def = [['&Application', ['&Properties','E&xit']], ['&Help', ['&About']] ]
  right_click_menu_def = [[], ['Version', 'Nothing','Exit']]
  graph_right_click_menu_def = [[], ['Erase','Draw Line', 'Draw',['Circle', 'Rectangle', 'Image'], 'Exit']]
  l_list_column = [[
  psg.Image(filename='jd-xi-small.png', tooltip='JD-Xi Keyboard'),
             psg.Push(),
            
   psg.Text('Prog Rx/Tx Ch',size=14, tooltip='Specifies the channel used to\ntransmit and receive MIDI messages for the program.'),
   psg.Combo(list(i for i in range(1,17)), default_value=16, key='-MAIN_COMBO-PC-', 
             readonly=True,enable_events=True,
             tooltip='Specifies the channel used to\ntransmit and receive MIDI messages for the program.'),
   psg.Text('                              ',key='-MAIN-ALERT-'),
   psg.Button('Exit', button_color=( 'red2','green2'),s=(8,1),font=('Arial',14,'bold'))
   ]]

  settings_layout= [[psg.Checkbox('Debug', default=True,enable_events=True, k='-DEBUG-')]]

  theme_layout = [[psg.Text("Choose theme")], [psg.Listbox(values = psg.theme_list(), size =(20, 12), 
                      key ='-THEME LISTBOX-',enable_events = True)], [psg.Button("Set Theme")]]
    
  log_layout =  [[psg.Text("All messages printed will go here.")],
              [psg.Multiline(size=(60,15), font='Courier 8', expand_x=True, expand_y=True, 
               write_only=True, 
               reroute_stdout=True, reroute_stderr=True, echo_stdout_stderr=True, 
               autoscroll=True, auto_refresh=True,key='-LOGMultiLine-')]
                      # [sg.Output(size=(60,15), font='Courier 8', expand_x=True, expand_y=True)]
                      ]
  tabs=[[psg.TabGroup(
       [[ psg.Tab('Settings', settings_layout),
          psg.Tab('Theme', theme_layout),
          psg.Tab('Output', log_layout,)]], key='-TAB GROUP-', expand_x=True, expand_y=True,enable_events=True),
     ]]

  layout = [
    [psg.MenubarCustom(menu_def, key='-MENU-',tearoff=True)],
    [psg.Column(l_list_column)],
    [psg.Text('MIDI in ',size=7), 
     psg.Combo(input_ports, default_value=input_ports[0], key='-MAIN_COMBO-INPUT-', 
             readonly=True,enable_events=True,size=30), 
     psg.Button('Reload',size=(0,2)),# button_color=(psg.YELLOWS[0], psg.BLUES[0])),
     psg.Button('Panic',size=(0,2)), #button_color=(psg.YELLOWS[0], psg.BLUES[0])),
     psg.Button('Open',size=(0,2)), #button_color=(psg.YELLOWS[0], psg.BLUES[0])),
     psg.Button('Close',size=(0,2)) #button_color=(psg.YELLOWS[0], psg.BLUES[0]))
    ],
    [psg.Text('MIDI out',size=7),psg.Combo(output_ports, default_value=output_ports[0], key='-MAIN_COMBO-OUTPUT-', 
            readonly=True,enable_events=True,size=30)],
    [psg.Text('Channel',size=7), 
     psg.Combo(digitalsynth+analogsynth+drums,default_value=drums[0], key='-MAIN_COMBO-channel-',  
             readonly=True,enable_events=True,size=20),
     psg.Text('Instrument',size=9),
     psg.Combo(instrumentlist, default_value=defaultinstrument, key='-MAIN_COMBO-instrument-', 
             readonly=True,enable_events=True,size=29)],
#  [psg.Combo([i for i in range(0,256)], default_value=1, key='-MAIN_COMBO-BANK-', readonly=True,enable_events=True)],

    [psg.Button('Play', size=(10,2), key='Play'),
     psg.B('Polytouch',size=(8,2),key='Poly'),
     psg.Slider(range=(36, 72), default_value=40, expand_x=True, enable_events=True, #param_tooltip=defaultinstrument,
     orientation='horizontal', key='-MAIN_SLpitch-',size=(20,8)),
     psg.Button('Test Sound',size=(10,2))],
    
    
    [psg.Button('Analog'),psg.Button('Digital 1'),psg.Button('Digital 2'),
     psg.Button('Voice'),psg.Button('Effects'),
     psg.Button('Arpeggio'),psg.Button('Program')]
  ]
  
  layout +=tabs
 
  window = psg.Window(Manufacturer+' '+ devicename+" - "+PROCESS_NAME, layout, icon= music, #"jdxi.png", 
                    scaling=.5, resizable=True, size=siz,# (715, 850), 
                    finalize=True,
                    location=loc, #(10, 10), 
                    return_keyboard_events=True)
  #,enable_window_config_events=True)
# bind keyboard letters for playing
  for c in notesstring:
      window.bind("<KeyPress-"+c+">",c+"KeyPressed")
      window.bind("<KeyPress-"+c.upper()+">",c+"KeyPressed")
      window.bind("<KeyRelease-"+c+">",c+"KeyReleased")
      window.bind("<KeyRelease-"+c.upper()+">",c+"KeyReleased")
#for Croatian keyboard
  window.bind("<KeyPress-scaron>", "šKeyPressed")
  window.bind("<KeyRelease-scaron>", "šKeyReleased")
  window.bind("<KeyPress-ccaron>", "čKeyPressed")
  window.bind("<KeyRelease-ccaron>", "čKeyReleased")
  window.bind("<KeyPress-cacute>", "ćKeyPressed")
  window.bind("<KeyRelease-cacute>", "ćKeyReleased")
  window.bind("<KeyPress-zcaron>", "žKeyPressed")
  window.bind("<KeyRelease-zcaron>", "žKeyReleased")
  window.bind("<KeyPress-dstroke>", "đKeyPressed")
  window.bind("<KeyRelease-dstroke>", "đKeyReleased")
# sample for key binding
# window.bind("<Control-KeyPress-b>", "CTRL-B")
# window.bind("<Control-KeyPress-B>", "CTRL-B")
# window.bind("<Control-KeyRelease-b>", "Release-B")
# window.bind("<Control-KeyRelease-B>", "Release-B")
  playbutton = window['Play']
  playbutton.bind('<ButtonPress>', " Press", propagate=False)
  playbutton.bind('<ButtonRelease>', " Release", propagate=False)
  return window

def main():
    global DEBUG, CONFIG_FILE, ManufacturerSysExIDsFile
    global notesstring, testingnote, testingch, testingvolume, testingduration
    global input_ports, current_inport, current_outport, inport, outport
    global tonelistDS, tonelistAS, drumkitDR, presetprogramlist,presetprogramall
    global defaultinstrument, instrumentlist
    global Manufacturer, devicename
    
    # start time
    timestart=time.time()
    # first, try to get config file form arguments
    parser = argparse.ArgumentParser(description='This is a controller for synthesizer.')
    parser.add_argument('--config','-c', dest='conf_file', type=str, default=CONFIG_FILE, help='Config JSON file.' )
    # try to parse arguments
    try:
      args = parser.parse_args()
      pass
    except:
    # many things are not defined yet... So, exit...
        start_logger()
        logger.error('Cannot parse args, exiting.')
        stop_logger()
        sys.exit(2)
    # now start logger if parsing passed
    start_logger()
    # check if parsed vars are ok
    if 'args' not in locals():
        logger.error('Parsing arguments failure, exiting.')
        stop_logger()
        sys.exit(3)  
    printdebug(sys._getframe().f_lineno, "Called with: "+ str(args))
    # check if CONFIG_FILE is OK
    if(args.conf_file):
        CONFIG_FILE=args.conf_file
    if not os.path.exists(CONFIG_FILE):
        logger.error('Cannot open config file:'+CONFIG_FILE+'.')
        stop_logger()
        sys.exit(4)  
    else:
        logger.info('Using config file:'+CONFIG_FILE+'.')
    printdebug(sys._getframe().f_lineno, str("CONFIG_FILE="+CONFIG_FILE))
    # change dir to location of file
    currdir=os.path.dirname(os.path.realpath(__file__))
    os.chdir(currdir)
    # collect all config data
    with open(CONFIG_FILE) as json_file:
        data = json.load(json_file)
        # get logpath. default is "."
        if 'logpath' in data:
            logpath=data['logpath']
        printdebug(sys._getframe().f_lineno, str("Path is:"+logpath))
        # get logfile
        if 'logfile' in data:
            logfile=data['logfile']
        printdebug(sys._getframe().f_lineno, str("Log file is:"+logfile))
        # get loglevel. default is DEBUG
        if 'loglevel' in data:
            loglevel=data['loglevel'].upper()
            change_log_level(loglevel)
        printdebug(sys._getframe().f_lineno, str("Log level is:"+loglevel))
        # get device type
        if 'devicename' in data:
            devicename=data['devicename']
        else:
            devicename='JD-Xi'
        if devicename in ['JD-Xi']:
            printdebug(sys._getframe().f_lineno, str(devicename+" is used device."))
            logger.info( devicename+" is used device.")
        else:
            printdebug(sys._getframe().f_lineno, str("Don't know how to use "+  devicename+" device."))
            logger.error("Don't know how to use "+  devicename+" device.")
            stop_logger()
            sys.exit(5)
    
    if 'devicefamiliycode' in data:
      devicefamiliycode=data['DeviceFamilyCode']
    if 'DeviceFamilyNumberCode' in data:
      DeviceFamilyNumberCode=data['DeviceFamilyNumberCode']
    if 'Manufacturer' in data:
      Manufacturer=data['Manufacturer']
    if 'ManufacturerID' in data:
      ManufacturerID=data['ManufacturerID']
    if 'ManufacturerSysExIDsFile' in data:
        ManufacturerSysExIDsFile=data['ManufacturerSysExIDsFile']
    else:
      ManufacturerSysExIDsFile='ManufacturerSysExIDs.json'

    if 'MIDIch' in data:
      midich=data['MIDIch']
      for ch in midich:
        chtype=ch['Type']
        if chtype=='DS':
          add_digital_synth(ch['ID'],ch['Desc'])
        elif chtype=='AS':
          add_analog_synth(ch['ID'],ch['Desc']);
        elif chtype=='DR':
          add_drums(ch['ID'],ch['Desc']);
        elif chtype=='PC':
          setup_program_control(ch['ID'],ch['Desc'])
    
        if 'TONES_FILE' in data:
            TONES_FILE=data['TONES_FILE']
            # now, collect all tones data from file
            with open(TONES_FILE) as json_file:
                tonesdata = json.load(json_file)
                if 'PresetDrumKitList' in tonesdata:
                    drumkitDR=tonesdata['PresetDrumKitList']
                else:
                    drumkitDR=[dict(No=i,Name='Name_'+str(i)) for i in range(33)]
                if 'PresetToneListDS' in tonesdata:
                    tonelistDS=tonesdata['PresetToneListDS']
                else:
                    tonelistDS=[dict(No=i,Name='Name_'+str(i)) for i in range(128)]
                if 'PresetToneListAS' in tonesdata:
                    tonelistAS=tonesdata['PresetToneListAS']
                else:
                    tonelistAS=[dict(No=i,Name='Name_'+str(i)) for i in range(128)]
                if 'PresetProgram' in tonesdata:
                    presetprogram=tonesdata['PresetProgram']
                else:
                    presetprogram=[dict(No=i,Name='Name_'+str(i)) for i in range(128)]
     
    # prepare lists, leave only 'No' and 'Name'
    # old one: drumkitDR=[dict(No=i['No'],Name=i['Name']) for i in drumkitDR]
    drumkitDR=[[i['No'],i['Name']] for i in drumkitDR]
    tonelistDS=[[i['No'],i['Name']] for i in tonelistDS]
    tonelistAS=[[i['No'],i['Name']] for i in tonelistAS]
    presetprogramlist=[[i['No'],i['Name']] for i in presetprogram]
    presetprogramall=[[i['No'],i['Program'],i['Name'],i['D1'],i['D2'],i['DR'],i['AN'],i['MSB'],i['LSB'],
                       i['PC'],i['Genre'],i['Tempo']] for i in presetprogram]
    
    instrumentlist=drumkitDR
    defaultinstrument=instrumentlist[0] 
    printdebug(sys._getframe().f_lineno, str("Current file:"+str(__file__)))
    # get MIDI ports
    ret=get_ports()
    
    psg.theme('DarkBlue12')
    main_window=make_main_window(psg.theme(),(10,1),(565, 575))
    AnalogSynth=Analog_Synth()
    ret=AnalogSynth.get_data()
    if ret=='7OF9':
        c_thread = threading.Thread(target=delayed_event, args=(main_window, 2.0,'-NO_DEVICE-','on'), daemon=True)
        c_thread.start()
    DigitalSynth1=Digital_Synth1()
    print("DS1 attr",DigitalSynth1.attributes)
    print("DS1 dsm_attr",DigitalSynth1.dsm_attributes)
    print("addr",DigitalSynth1.address)
    print("dsm_addr",DigitalSynth1.dsm_address)
    
    ret=DigitalSynth1.get_data()
    if ret=='7OF9':
        printdebug(sys._getframe().f_lineno, str("Cannot create digital synth 1 window."))
    # else:
    #     print(ret)

    DigitalSynth2=Digital_Synth2()
    ret=DigitalSynth2.get_data()
    if ret=='7OF9':
        printdebug(sys._getframe().f_lineno, str("Cannot create digital synth 2 window."))
    # else:
    #     print(ret)
    print("DS2 attr",DigitalSynth2.attributes)
    print("DS2 dsm_attr",DigitalSynth2.dsm_attributes)
    print("addr",DigitalSynth2.address)
    print("dsm_addr",DigitalSynth2.dsm_address)
    



    SystemSetup=System_Setup()
    SystemSetup.get_data()
    print(SystemSetup.attributes)
    SystemCommon=System_Common()
    SystemCommon.get_data()
    print(SystemCommon.attributes)
    SystemController=System_Controller()
    SystemController.get_data()
    print(SystemController.attributes)
    ProgramCommon=Program_Common()
    ProgramCommon.get_data()
    print(ProgramCommon.attributes)
    ProgramVocalEffect=Program_Vocal_Effect()
    ProgramVocalEffect.get_data()
    print(ProgramVocalEffect.attributes)
    ProgramEffect1=Program_Effect1()
    ProgramEffect1.get_data()
    print(ProgramEffect1.attributes)
    ProgramDelay=Program_Delay()
    ProgramDelay.get_data()
    print(ProgramDelay.attributes)
    
    analog_window=make_analog_synth_window(AnalogSynth,psg.theme(),(585,10),(940, 975))
    digital1_window=make_digital_synth_window(DigitalSynth1,psg.theme(),(595,10),(940, 975))
    digital2_window=make_digital_synth_window(DigitalSynth2,psg.theme(),(595,10),(940, 975))
    
    effects_window=make_effects_window(psg.theme(),(1535,10),(350, 120))
    vocalFX_window=make_vocalFX_window(psg.theme(),(1535,165),(350, 120))
    arpeggio_window= make_arpeggio_window(psg.theme(),(1535,320),(350, 120))
    program_window=make_program_window(psg.theme(),(1535,475),(350, 280))
    
    for element in analog_window.element_list():
        if str(element.key).startswith('-AS_ONOFF-'):
            element.bind('<Enter>', ' Enter')
            element.bind('<Leave>', ' Leave')
        elif str(element.key).startswith('-AS_THREETEXT-'):
            element.bind('<Enter>', ' Enter')
            element.bind('<Leave>', ' Leave')
                
    while True:
        win, event, values = psg.read_all_windows(timeout=50)
#        event, values = main_window.read(timeout=50)
        if event == psg.WIN_CLOSED or event == 'Exit':
            if win==analog_window:
                analog_window.hide()
            elif win==effects_window:
                effects_window.hide()
            elif win==vocalFX_window:
                vocalFX_window.hide()
            elif win==arpeggio_window:
                arpeggio_window.hide()
            elif win==program_window:
                program_window.hide()
            else:
                analog_window.close()
                effects_window.close()
                vocalFX_window.close()
                arpeggio_window.close()
                program_window.close()
                break
            continue
        if event is psg.TIMEOUT_KEY:
          continue
        printdebug(sys._getframe().f_lineno, str(win)+str(event)+str(values))
        if event[1:] == 'KeyPressed':
            test_tone_on(int(notesstring.find(event[0].lower())+60))
        elif event[1:] == 'KeyReleased':
            test_tone_off(int(notesstring.find(event[0].lower())+60))
      
        elif event in ('Play Press', 'Play Release'):
            if event == 'Play Press':
                main_window['Play'].update(text='Play Pressed')
#      playbutton.update(text='Play Pressed')
                test_tone_on(testingnote)
            else:
                test_tone_off(testingnote)
                main_window['Play'].update(text='Play')

        elif event == 'Reload':
            port_panic()
            port_close()
            get_io_ports()
            main_window['-MAIN_COMBO-INPUT-'].update(values=input_ports, 
                  value=(current_inport if (current_inport in input_ports) else input_ports[0]))
            main_window['-MAIN_COMBO-OUTPUT-'].update(values=output_ports, 
                  value=(current_outport if (current_outport in output_ports) else output_ports[0]))
            port_open()
        elif event == 'Test Sound':
            test_tone(testingnote)
            test_tone(testingnote+4)
            test_tone(testingnote+7)
        elif event == 'Panic':
            port_panic()
        elif event == 'Open':
            port_open()
        elif event == 'Close':
            port_close()
        elif event.startswith('-AS_SLIDER-'):
            analog_window[event.replace('-AS_SLIDER-','-AS_TEXT_SLIDER-')+'value'].update(int(values[event]))
            attr=event[len('-AS_SLIDER-'):-1]
            AnalogSynth.attributes[attr][0]=int(values[event])
            send_sysex_DT1(AnalogSynth,AnalogSynth.attributes[attr][1],[int(values[event])])
        elif event.startswith('-AS_ONOFF-'):
            #analog_window[event].update(int(values[event]))
            #attr=event[len('-AS_ONOFF-'):]
            action = event.split(' ')
            attr=action[0][len('-AS_ONOFF-'):-1]
            if len(action)>1:
                #action=action[1]
                index = 0 if action[1] == 'Leave' else 1
                analog_window[action[0]].metadata[0] = index
            else:
                index=analog_window[action[0]].metadata[0]
                if analog_window[action[0]].metadata[1]:
                    analog_window[action[0]].metadata[1]=0
                else:
                    analog_window[action[0]].metadata[1]=1
                send_sysex_DT1(AnalogSynth,int(AnalogSynth.attributes[attr][1]),[int(analog_window[action[0]].metadata[1])])
                AnalogSynth.attributes[attr][0]=analog_window[action[0]].metadata[1]
            analog_window[action[0]].update(image_data=onoff_data[index+2*analog_window[action[0]].metadata[1]],image_subsample=IMAGE_SUBSAMPLE)
        elif event.startswith('-AS_LISTBUTTON-'):
            splited=event.split(' ')
            attr=splited[0]
            attr_value=splited[1]
            if len(splited)>2:  
                continue
            attr=attr[len('-AS_LISTBUTTON-'):-1]
            attr_value=int(attr_value)
            AnalogSynth.attributes[attr][0]=attr_value
            current_button=analog_window['-AS_LISTBUTTON-'+attr+'- '+str(attr_value)]
            if current_button.metadata[0]!=0:
                continue
            send_sysex_DT1(AnalogSynth,int(AnalogSynth.attributes[attr][1]),[attr_value])
            for others in current_button.metadata[1]:
                tmp_button=analog_window['-AS_LISTBUTTON-'+attr+'- '+str(others)]
                tmp_button.update(image_data=images[tmp_button.metadata[2]][0],image_subsample=IMAGE_SUBSAMPLE)
                tmp_button.metadata[0]=0
            current_button.update(image_data=images[current_button.metadata[2]][1],image_subsample=IMAGE_SUBSAMPLE)
            current_button.metadata[0]=1
        elif event.startswith('-AS_LIST-'):
            attr=event[len('-AS_LIST-'):-1]
            attr_value=analog_window[event].widget.current()
            AnalogSynth.attributes[attr][0]=attr_value
            send_sysex_DT1(AnalogSynth,int(AnalogSynth.attributes[attr][1]),[attr_value])
            
        elif event == '-MAIN_COMBO-INPUT-':
            printdebug(sys._getframe().f_lineno, "Combo for:"+str(values['-MAIN_COMBO-INPUT-']))
            current_inport=str(values['-MAIN_COMBO-INPUT-'])
        elif event == '-MAIN_COMBO-OUTPUT-':
            printdebug(sys._getframe().f_lineno, "Combo for:"+str(values['-MAIN_COMBO-OUTPUT-']))
            current_outport=str(values['-MAIN_COMBO-OUTPUT-'])
        elif event == '-MAIN_COMBO-PC-':
            printdebug(sys._getframe().f_lineno, "Prog Rx/Tx ch:"+str(values['-MAIN_COMBO-PC-']))
            current_outportx=str(values['-MAIN_COMBO-pc-'])
        elif event == '-MAIN_SLpitch-':
            printdebug(sys._getframe().f_lineno, str(values['-MAIN_SLpitch-'])+str(type(values['-MAIN_SLpitch-'])))
            testingnote=int(values['-MAIN_SLpitch-'])
        elif event == '-MAIN_COMBO-channel-':
            printdebug(sys._getframe().f_lineno, "Combo for:"+str(values['-MAIN_COMBO-channel-']))
            testingch=values['-MAIN_COMBO-channel-'][1]
            instrumenttype=values['-MAIN_COMBO-channel-'][0][:2]
            if instrumenttype=='DS':
                main_window['-MAIN_COMBO-instrument-'].update(values=tonelistDS, value=tonelistDS[0])
            elif instrumenttype=='AS':
                main_window['-MAIN_COMBO-instrument-'].update(values=tonelistAS, value=tonelistAS[0])   
            elif instrumenttype=='DR':
                main_window['-MAIN_COMBO-instrument-'].update(values=drumkitDR, value=drumkitDR[0])
            printdebug(sys._getframe().f_lineno, "Instrument type:"+instrumenttype)
    
        # elif event == '-MAIN_COMBO-BANK-':
        #     printdebug(sys._getframe().f_lineno, "Combo for:"+str(values['-MAIN_COMBO-BANK-']))
        #     control_change(testingch,'Bank Select',int(values['-MAIN_COMBO-BANK-']))
        elif event == '-MAIN_COMBO-instrument-':
            printdebug(sys._getframe().f_lineno, str(values['-MAIN_COMBO-instrument-']))
#     control_change(testingch,'Bank Select',int(values['-MAIN_COMBO-instrument-']['No']-1))
            control_change(testingch,'Bank Select',int(values['-MAIN_COMBO-instrument-'][0]-1))
            #new 202311106
            AnalogSynth.get_data()
            if ret=='7OF9':
                c_thread = threading.Thread(target=delayed_event, args=(main_window, 2.0,'-NO_DEVICE-','on'), daemon=True)
                c_thread.start()
            else:
                main_window.write_event_value('-NO_DEVICE-','inactive')
            analog_window.close()
            analog_window=make_analog_synth_window(AnalogSynth,psg.theme(),(585,10),(940, 975))
        elif event=='Poly':
            tone_on(testingch, testingnote, testingvolume, testingduration)
            msg=mido.Message('polytouch', channel=testingch, note=testingnote, 
                         value=122, time=.1)
            #time.sleep(.3)
            printdebug(sys._getframe().f_lineno, str(msg))
            outport.send(msg)
            time.sleep(1)
            tone_off(testingch, testingnote, 80, .1)
        elif event=='-PROGRAM-LIST-':
            attr_value=program_window['-PROGRAM-LIST-'].widget.current()
            program_window['-PROGRAM-'+'Program'].update(presetprogramall[attr_value][1])
            program_window['-PROGRAM-'+'Name'].update(presetprogramall[attr_value][2])
            program_window['-PROGRAM-'+'Genre'].update(presetprogramall[attr_value][10])
            program_window['-PROGRAM-'+'D1'].update(presetprogramall[attr_value][3])
            program_window['-PROGRAM-'+'D2'].update(presetprogramall[attr_value][4])
            program_window['-PROGRAM-'+'DR'].update(presetprogramall[attr_value][5])
            program_window['-PROGRAM-'+'AN'].update(presetprogramall[attr_value][6])
            program_window['-PROGRAM-'+'MSB'].update(presetprogramall[attr_value][7])
            program_window['-PROGRAM-'+'LSB'].update(presetprogramall[attr_value][8])
            program_window['-PROGRAM-'+'PC'].update(presetprogramall[attr_value][9])
            program_window['-PROGRAM-'+'Tempo'].update(presetprogramall[attr_value][11])
            pass
        elif event=='PopupARPEGGIO':
            AnalogSynth.get_data()
            print(AnalogSynth.attributes['Name'])
#            send_sysex_DT1(AnalogSynth,AnalogSynth.attributes['LegatoSw'][1],[1,66])
            pass
        elif event=='-NO_DEVICE-':
            if values['-NO_DEVICE-']=='on' and AnalogSynth.devicestatus!='OK':
                main_window['-MAIN-ALERT-'].update('JD-Xi not recognized',background_color='red')
                main_window.refresh()
                c_thread = threading.Thread(target=delayed_event, 
                                            args=(main_window, 2.0,'-NO_DEVICE-','off'), daemon=True)
                c_thread.start()

            elif values['-NO_DEVICE-']=='off' and AnalogSynth.devicestatus!='OK':
                main_window['-MAIN-ALERT-'].update('                              ', 
                                                   background_color=psg.theme_element_background_color())
                main_window.refresh()
                c_thread = threading.Thread(target=delayed_event, 
                                            args=(main_window, 2.0,'-NO_DEVICE-','on'), daemon=True)
                c_thread.start()
            elif values['-NO_DEVICE-']=='inactive':
                main_window['-MAIN-ALERT-'].update('                              ', 
                                                   background_color=psg.theme_element_background_color())
             
        elif event=='Activate program':
            attr_value=program_window['-PROGRAM-LIST-'].widget.current()
#            control_change(15,'Bank Select',int(values['-PROGRAM-LIST-']))
            control_change(15,'Bank Select',int(attr_value))
        elif event=='Program start':
            msg=mido.Message('start')
            outport.send(msg)
        elif event=='Program stop':
            msg=mido.Message('stop')
            outport.send(msg)
        elif event == "Set Theme":
            new_theme = values['-THEME LISTBOX-'][0]
            printdebug(sys._getframe().f_lineno, "New theme: " + str(new_theme))
            siz=main_window.current_size_accurate()
            loc=main_window.current_location()
            main_window.close()
            main_window = make_main_window(new_theme,loc,siz)
        elif event == '-TAB GROUP-':
            printdebug(sys._getframe().f_lineno, str(main_window['-TAB GROUP-']))
        elif event == 'Analog':
            analog_window.hide()
            analog_window.un_hide()
            continue
        elif event == 'Voice':
            vocalFX_window.hide()
            vocalFX_window.un_hide()
            continue
        elif event == 'Effects':
            effects_window.hide()
            effects_window.un_hide()
            continue
        elif event == 'Arpeggio':
            arpeggio_window.hide()
            arpeggio_window.un_hide()
            continue
        elif event == 'Program':
            program_window.hide()
            program_window.un_hide()
            continue
        
        elif event == '-DEBUG-':
            DEBUG=True if values['-DEBUG-']==True else False
        else: 
            printdebug(sys._getframe().f_lineno, 
                       str("Unhandled event (type:{}, {}, len:({}) vith values:{}"
                           .format(type(event), event,len(event),values)))

    main_window.close()
    port_panic()
    port_close()
    stop_logger()
    sys.exit(0)    
if __name__ == '__main__':
    main()


    
