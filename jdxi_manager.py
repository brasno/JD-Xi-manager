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
#import pandas as pd
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.constants import *
from tkinter import messagebox

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
CONFIG_FILE='./jdxi_manager.json'
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

DeviceFamiliyCode=''
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
JDXi_device=[0x41,0x10,0x00,0x00,0x00,0x0e]

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

def delay_event(widget, delay, event):
    i=0.001
    delta=.1
    print("delay",delay)
    while i<=delay:
        time.sleep(delta)
        i+=delta
    print("delay",i)
    print("widget",widget)
    widget.event_generate(event, when="tail")

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
    global ManufacturerID, Manufacturer, devicename, ManufacturerSysExIDsFile
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
            logger.warning("Waiting too log for status identification.")
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
  
def control_change(chid,func, value, **kwargs):
    printdebug(sys._getframe().f_lineno, str("in CC:"+str(chid)+" "+func+" "+str(value)))
    if func in ('Bank Select','Modulation','Portamento Time','Data Entry','Volume','Panpot', 
                'Expression','Hold 1','Portamento','Resonance','Release Time','Attack time',
                'Cutoff','Decay Time','Vibrato Rate','Vibrato Depth','Vibrato Delay'):
        printdebug(sys._getframe().f_lineno, "Control change: "+ func)
        # specific for JD-Xi
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
               if 'user' in kwargs: # User program
                   if kwargs['user']==1:
                       LSB=LSB-64
                
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

def send_sysex_DT1(sysexsetlist, address, values):
    """
    This message sends data to the other device. The address and size indicate the type and amount of data that is requested.
    instrument : List   of data for specific instrument
    address : base address where to save data (last byte,base address will be defined in the instrument)
    values : list of values
    Returns: None.
    """
    sysexdata=sysexsetlist+[address]+values+[0] #zero is checksum, i. e. not needed to calculate
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

def make_effects_window(theme,loc,siz):
    prefix='-EFFECTS-'
    tk.theme(theme)
    layout = [[tk.Text('This is the Effects window'), tk.Text('      ', k=prefix+'OUTPUT-')],
              [tk.Button('FAKE'), tk.Button('PopupEFFECTS'), tk.Button('Exit')]]
    return tk.Window('Effects', layout, location=loc, resizable=True, size=siz, finalize=True, icon= music)


def make_vocalFX_window(theme,loc,siz):
    prefix='-VOCAL_FX-'
    tk.theme(theme)
    layout = [[tk.Text('This is the VocalFX window'), tk.Text('      ', k=prefix+'OUTPUT-')],
              [tk.Button('FAKE'), tk.Button('PopupVOCAL_FX'), tk.Button('Exit')]]
    return tk.Window('Vocal FX', layout, location=loc, resizable=True, size=siz, finalize=True, icon= music)


def make_arpeggio_window(theme,loc,siz):
    prefix='-ARPEGGIO-'
    tk.theme(theme)
    layout = [[tk.Text('This is the Arpeggio window'), tk.Text('      ', k=prefix+'OUTPUT-')],
              [tk.Button('FAKE'), tk.Button('PopupARPEGGIO'), tk.Button('Exit')]]
    return tk.Window('Arpeggio', layout, location=loc, resizable=True, size=siz, finalize=True, icon= music)

def make_drums_window(theme,loc,siz):
    prefix='-DRUMS-'
    tk.theme(theme)
    layout = [[tk.Text('This is the Drums window'), tk.Text('      ', k=prefix+'OUTPUT-')],
              [tk.Button('FAKE'), tk.Button('PopupDrums'), tk.Button('Exit')]]
    return tk.Window('Drums', layout, location=loc, resizable=True, size=siz, finalize=True, icon= music)

def make_program_window(theme,loc,siz):
    global presetprogramlist, presetprogramall
    prefix='-PROGRAM-'
    key_value=prefix
    key_value.replace(' ','_')
    tk.theme(theme)
    layout = [
              [[tk.Text('User Program',size=TEXT_SIZE),
                  tk.Button(image_data=onoff_data[0],metadata=[0,0,0,1],auto_size_button=True,border_width=0,
                             button_color=(tk.theme_element_background_color(),tk.theme_element_background_color() ),
                             key=key_value+'ONOFF-user-', image_subsample=IMAGE_SUBSAMPLE),
                  tk.Button('Exit')]],
              [tk.Combo(presetprogramlist, default_value=presetprogramlist[0], key=key_value+'LIST-',
                                  readonly=True,enable_events=True,size=20),
               tk.Button('Activate program')],
              [tk.Frame('',[[tk.Text('Program:',size=(8),font=('Arial',10,'bold'),text_color='black',background_color='yellow'),
               tk.Text(presetprogramall[0][1],k=key_value+'Program',text_color='black',background_color='yellow'),
              tk.Text('Name:',size=(8),font=('Arial',10,'bold'),text_color='black',background_color='yellow'),
              tk.Text(presetprogramall[0][2],k=key_value+'Name',text_color='black',background_color='yellow')]],
                         background_color='yellow',border_width=0,expand_x=True)],
              [tk.Text('Genre:',size=(8),font=('Arial',10,'bold')),
               tk.Text(presetprogramall[0][10],k=key_value+'Genre')],
              [tk.Column(
              [
               
               [tk.Text('D1:',size=(4),font=('Arial',10,'bold')),tk.Text(presetprogramall[0][3],k=key_value+'D1')],
               [tk.Text('D2:',size=(4),font=('Arial',10,'bold')),tk.Text(presetprogramall[0][4],k=key_value+'D2')],
               [tk.Text('DR:',size=(4),font=('Arial',10,'bold')),tk.Text(presetprogramall[0][5],k=key_value+'DR')],
               [tk.Text('AN:',size=(4),font=('Arial',10,'bold')),tk.Text(presetprogramall[0][6],k=key_value+'AN')]]),
               tk.Column(
               [[tk.Text('MSB:',size=(7),font=('Arial',10,'bold')),tk.Text(presetprogramall[0][7],k=key_value+'MSB')],
                [tk.Text('LSB:',size=(7),font=('Arial',10,'bold')),tk.Text(presetprogramall[0][8],k=key_value+'LSB')],
                [tk.Text('PC:',size=(7),font=('Arial',10,'bold')),tk.Text(presetprogramall[0][9],k=key_value+'PC')],
                [tk.Text('Tempo:',size=(7),font=('Arial',10,'bold')),tk.Text(presetprogramall[0][11],k=key_value+'Tempo')]])],
              [tk.Button('Program start'),tk.Button('Program stop')]
              ]
    return tk.Window('Program', layout, location=loc, resizable=True, size=siz, finalize=True, icon= music)


class System_Setup():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['ProgramBSMSB']=[40,4,1]
        self.attributes['ProgramBSLSB']=[127,5,1]
        self.attributes['ProgramPC']=[15,6,1]

        self.baseaddress=[0x01,0x00,0x00]
        self.offset=[0x00,0x00]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x3B]
        self.deviceID=JDXi_device
# required for SysEx Data set 1 (DT1=0x12). Last byte must be added at the end
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]
        self.devicestatus='unknown'
    

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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
        self.datalength=[0x00,0x00,0x00,0x2B]
        self.deviceID=JDXi_device
# required for SysEx Data set 1 (DT1=0x12) 
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]
        self.devicestatus='unknown'
    

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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
        self.attributes['KeyboardVelocityCurve']=[1,3,1]
        self.attributes['KeyboardVelocityCurveOffset']=[64,4,1]

        self.baseaddress=[0x02,0x00,0x00]
        self.offset=[0x00,0x03]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x11]
        self.deviceID=JDXi_device
# required for SysEx Data set 1 (DT1=0x12) 
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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
        self.attributes['ProgramName']=['INIT',0,12]
        self.attributes['ProgramLevel']=[127,16,1]
        self.attributes['ProgramTempo']=[[2,14,14,0],17,4]
        self.attributes['VocalEffect']=[0,22,1]
        self.attributes['VocalEffectNumber']=[0,28,1]
        self.attributes['VocalEffectPart']=[1,29,1]
        self.attributes['AutoNoteSwitch']=[0,30,1]

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x00]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x1f]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self.attributes:
            if attr=='ProgramName':
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
        self.datalength=[0x00,0x00,0x00,0x18]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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
        self.attributes['EFX1Distorsion_FuzzLevel']=[[8,0,5,0],17,4]
        self.attributes['EFX1Distorsion_FuzzDrive']=[[8,0,5,0],21,4]
        self.attributes['EFX1Distorsion_FuzzType']=[[8,0,0,0],25,4]
        self.attributes['EFX1Distorsion_FuzzPresence']=[[8,0,7,15],29,4]
        self.attributes['EFX1CompressorLevel']=[[8,0,0,0],33,4]
        self.attributes['EFX1CompressorSideChainSwitch']=[[8,0,0,0],37,4]
        self.attributes['EFX1CompressorSideLevel']=[[8,0,0,0],41,4]
        self.attributes['EFX1CompressorSideNote']=[[8,0,0,0],45,4]
        self.attributes['EFX1CompressorSideTime']=[[8,0,0,0],49,4]
        self.attributes['EFX1CompressorSideRelease']=[[8,0,0,0],53,4]
        self.attributes['EFX1CompressorSideSyncSwitch']=[[8,0,0,0],57,4]
       
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
        self.datalength=[0x00,0x00,0x01,0x11]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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

        self.attributes['EFX2Type']=[0,0,1]
        self.attributes['EFX2Level']=[127,1,1]
        self.attributes['EFX2DelaySendLevel']=[50,2,1]
        self.attributes['EFX2ReverbSendLevel']=[50,3,1]
        self.attributes['EFX2Parameter1']=[[8,0,0,0],17,4]
        self.attributes['EFX2Parameter2']=[[8,0,0,0],21,4]
        self.attributes['EFX2Parameter3']=[[8,0,0,0],25,4]
        self.attributes['EFX2Parameter4']=[[8,0,0,0],29,4]
        self.attributes['EFX2Parameter5']=[[8,0,0,0],33,4]
        self.attributes['EFX2Parameter6']=[[8,0,0,0],37,4]
        self.attributes['EFX2Parameter7']=[[8,0,0,0],41,4]
        self.attributes['EFX2Parameter8']=[[8,0,0,0],45,4]
        self.attributes['EFX2Parameter9']=[[8,0,0,0],49,4]
        self.attributes['EFX2Parameter10']=[[8,0,0,0],53,4]
        self.attributes['EFX2Parameter11']=[[8,0,0,0],57,4]
        self.attributes['EFX2Parameter12']=[[8,0,0,0],61,4]
        self.attributes['EFX2Parameter13']=[[8,0,0,0],65,4]
        self.attributes['EFX2Parameter14']=[[8,0,0,0],69,4]
        self.attributes['EFX2Parameter15']=[[8,0,0,0],73,4]
        self.attributes['EFX2Parameter16']=[[8,0,0,0],77,4]
        self.attributes['EFX2Parameter17']=[[8,0,0,0],81,4]
        self.attributes['EFX2Parameter18']=[[8,0,0,0],85,4]
        self.attributes['EFX2Parameter19']=[[8,0,0,0],89,4]
        self.attributes['EFX2Parameter20']=[[8,0,0,0],93,4]
        self.attributes['EFX2Parameter21']=[[8,0,0,0],97,4]
        self.attributes['EFX2Parameter22']=[[8,0,0,0],101,4]
        self.attributes['EFX2Parameter23']=[[8,0,0,0],105,4]
        self.attributes['EFX2Parameter24']=[[8,0,0,0],109,4]
        self.attributes['EFX2Parameter25']=[[8,0,0,0],113,4]
        self.attributes['EFX2Parameter26']=[[8,0,0,0],117,4]
        self.attributes['EFX2Parameter27']=[[8,0,0,0],121,4]
        self.attributes['EFX2Parameter28']=[[8,0,0,0],125,4]
        self.attributes['EFX2Parameter29']=[[8,0,0,0],129,4]
        self.attributes['EFX2Parameter30']=[[8,0,0,0],133,4]
        self.attributes['EFX2Parameter31']=[[8,0,0,0],137,4]
        self.attributes['EFX2Parameter32']=[[8,0,0,0],141,4]

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x04]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x01,0x11]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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

    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['DelayEnable']=[1,0,1]
        self.attributes['DelayReverbSendLevel']=[50,3,1]
        self.attributes['DelayType']=[[8,0,0,0],4,4]
        self.attributes['DelayUnits']=[[8,0,0,0],8,4]
        self.attributes['Delayms']=[[8,0,0,0],12,4]
        self.attributes['Delaynote']=[[8,0,0,0],16,4]
        self.attributes['DelayTapTime']=[[8,0,0,0],20,4]
        self.attributes['DelayFeedback']=[[8,0,0,0],24,4]
        self.attributes['DelayHFDamp']=[[8,0,0,0],28,4]
        self.attributes['DelayLevel']=[[8,0,0,0],32,4]
        self.attributes['DelayParameter9']=[[8,0,0,0],36,4]
        self.attributes['DelayParameter10']=[[8,0,0,0],40,4]
        self.attributes['DelayParameter11']=[[8,0,0,0],44,4]
        self.attributes['DelayParameter12']=[[8,0,0,0],48,4]
        self.attributes['DelayParameter13']=[[8,0,0,0],52,4]
        self.attributes['DelayParameter14']=[[8,0,0,0],56,4]
        self.attributes['DelayParameter15']=[[8,0,0,0],60,4]
        self.attributes['DelayParameter16']=[[8,0,0,0],64,4]
        self.attributes['DelayParameter17']=[[8,0,0,0],68,4]
        self.attributes['DelayParameter18']=[[8,0,0,0],72,4]
        self.attributes['DelayParameter19']=[[8,0,0,0],76,4]
        self.attributes['DelayParameter20']=[[8,0,0,0],80,4]
        self.attributes['DelayParameter21']=[[8,0,0,0],84,4]
        self.attributes['DelayParameter22']=[[8,0,0,0],88,4]
        self.attributes['DelayParameter23']=[[8,0,0,0],92,4]
        self.attributes['DelayParameter24']=[[8,0,0,0],96,4]

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x06]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x64]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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
        self.attributes['ReverbEnable']=[1,0,1]
        self.attributes['ReverbLevel']=[127,1,1]
        self.attributes['ReverbType']=[[8,0,0,0],3,4]
        self.attributes['ReverbTime']=[[8,0,7,15],7,4]
        self.attributes['ReverbHFDamp']=[[8,0,0,0],11,4]
        self.attributes['ReverbLevel2']=[[8,0,0,0],15,4]
        self.attributes['ReverbParameter5']=[[8,0,0,0],19,4]
        self.attributes['ReverbParameter6']=[[8,0,0,0],23,4]
        self.attributes['ReverbParameter7']=[[8,0,0,0],27,4]
        self.attributes['ReverbParameter8']=[[8,0,0,0],31,4]
        self.attributes['ReverbParameter9']=[[8,0,0,0],35,4]
        self.attributes['ReverbParameter10']=[[8,0,0,0],39,4]
        self.attributes['ReverbParameter11']=[[8,0,0,0],43,4]
        self.attributes['ReverbParameter12']=[[8,0,0,0],47,4]
        self.attributes['ReverbParameter13']=[[8,0,0,0],51,4]
        self.attributes['ReverbParameter14']=[[8,0,0,0],55,4]
        self.attributes['ReverbParameter15']=[[8,0,0,0],59,4]
        self.attributes['ReverbParameter16']=[[8,0,0,0],63,4]
        self.attributes['ReverbParameter17']=[[8,0,0,0],67,4]
        self.attributes['ReverbParameter18']=[[8,0,0,0],71,4]
        self.attributes['ReverbParameter19']=[[8,0,0,0],75,4]
        self.attributes['ReverbParameter20']=[[8,0,0,0],79,4]
        self.attributes['ReverbParameter21']=[[8,0,0,0],83,4]
        self.attributes['ReverbParameter22']=[[8,0,0,0],87,4]
        self.attributes['ReverbParameter23']=[[8,0,0,0],91,4]
        self.attributes['ReverbParameter24']=[[8,0,0,0],95,4]

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x08]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x63]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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

class Program_Part():
    attributes={}
    deviceID=JDXi_device
    baseaddress=[0x18,0x00,0x00]
    offset=[0x00,0x20]
    address=[baseaddress[0],baseaddress[1]+offset[0],baseaddress[2]+offset[1]]
    datalength=[0x00,0x00,0x00,0x3D]
    sysexsetlist=deviceID+[0x12]+address
    sysexgetlist=deviceID+[0x11]+address+datalength

    def __init__(self, *args, **kwargs):
        self.attributes['ReceiveChannel']=[32,0,1]
        self.attributes['PartSwitch']=[0,1,1]
        self.attributes['ToneBankSelectMSB']=[[2,14,14,0],6,1]
        self.attributes['ToneBankSelectLSB']=[0,7,1]
        self.attributes['ToneProgramNumber']=[0,8,1]
        self.attributes['PartLevel']=[0,9,1]
        self.attributes['PartPan']=[0,10,1]
        self.attributes['PartCoarseTune']=[0,11,1]
        self.attributes['PartFineTune']=[0,12,1]
        self.attributes['PartMono/Poly']=[0,13,1]
        self.attributes['PartLegatoSwitch']=[0,14,1]
        self.attributes['PartPitchBendRange']=[0,15,1]
        self.attributes['PartPortamentoSwitch']=[0,16,1]
        self.attributes['PartPortamentoTime']=[128,17,2]
        self.attributes['PartCutoffOffset']=[64,19,1]
        self.attributes['PartResonanceOffset']=[64,20,1]
        self.attributes['PartAttackTimeOffset']=[64,21,1]
        self.attributes['PartDecayTimeOffset']=[64,22,1]
        self.attributes['PartReleaseTimeOffset']=[64,23,1]
        self.attributes['PartVibratoRate']=[64,24,1]
        self.attributes['PartVibratoDepth']=[64,25,1]
        self.attributes['PartVibratoDelay']=[64,26,1]
        self.attributes['PartOctaveShift']=[64,27,1]
        self.attributes['PartVelocitySensOffset']=[64,28,1]
        self.attributes['VelocityRangeLower']=[1,33,1]
        self.attributes['VelocityRangeUpper']=[127,34,1]
        self.attributes['VelocityFadeWidthLower']=[0,35,1]
        self.attributes['VelocityFadeWidthUpper']=[0,36,1]
        self.attributes['MuteSwitch']=[1,37,1]
        self.attributes['PartDelaySendLevel']=[127,43,1]
        self.attributes['PartReverbSendLevel']=[127,44,1]
        self.attributes['PartOutputAssign']=[0,45,1]
        self.attributes['PartScaleTuneType']=[2,47,1]
        self.attributes['PartScaleTuneKey']=[0,48,1]
        self.attributes['PartScaleTuneforC']=[64,49,1]
        self.attributes['PartScaleTuneforC#']=[64,50,1]
        self.attributes['PartScaleTuneforD']=[64,51,1]
        self.attributes['PartScaleTuneforD#']=[64,52,1]
        self.attributes['PartScaleTuneforE']=[64,53,1]
        self.attributes['PartScaleTuneforF']=[64,54,1]
        self.attributes['PartScaleTuneforF#']=[64,55,1]
        self.attributes['PartScaleTuneforG']=[64,56,1]
        self.attributes['PartScaleTuneforG#']=[64,57,1]
        self.attributes['PartScaleTuneforA']=[64,58,1]
        self.attributes['PartScaleTuneforA#']=[64,59,1]
        self.attributes['PartScaleTuneforB']=[64,60,1]
        self.attributes['ReceiveProgramChange']=[1,61,1]
        self.attributes['ReceiveBankSelect']=[1,62,1]
        self.attributes['ReceivePitchBend']=[1,63,1]
        self.attributes['ReceivePolyphonicKeyPressure']=[1,64,1]
        self.attributes['ReceiveChannelPressure']=[1,65,1]
        self.attributes['ReceiveModulation']=[1,66,1]
        self.attributes['ReceiveVolume']=[1,67,1]
        self.attributes['ReceivePan']=[1,68,1]
        self.attributes['ReceiveExpression']=[1,69,1]
        self.attributes['ReceiveHold-1']=[1,70,1]


class Program_Part_DS1(Program_Part):
    def __init__(self, *args, **kwargs):
        self.attributes={}
        
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x20]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x4C]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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


class Program_Part_DS2(Program_Part):
    def __init__(self, *args, **kwargs):
        self.attributes={}

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x21]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x4C]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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


class Program_Part_AS(Program_Part):
    def __init__(self, *args, **kwargs):
        self.attributes={}

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x22]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x4C]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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


class Program_Part_DR(Program_Part):
    def __init__(self, *args, **kwargs):
        self.attributes={}

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x23]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x4C]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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

class Program_Zone():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['ArpeggioSwitch']=[0,3,1]
        self.attributes['ZoneOctaveShift']=[64,25,1]


class Program_Zone_DS1(Program_Zone):
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x30]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x23]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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

class Program_Zone_DS2(Program_Zone):
    def __init__(self, *args, **kwargs):
        self.attributes={}

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x31]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x23]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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

    
class Program_Zone_AS(Program_Zone):
    def __init__(self, *args, **kwargs):
        self.attributes={}

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x32]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x23]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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

class Program_Zone_DR(Program_Zone):
    def __init__(self, *args, **kwargs):
        self.attributes={}

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x33]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x23]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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

class Program_Controller(): #arpeggio
    def __init__(self, *args, **kwargs):
        self.attributes={}  
        
        self.attributes['ArpeggioGrid']=[0,1,1]
        self.attributes['ArpeggioDuration']=[0,2,1]
        self.attributes['ArpeggioSwitch']=[0,3,1]
        self.attributes['ArpeggioStyle']=[0,5,1]
        self.attributes['ArpeggioMotif']=[0,6,1]
        self.attributes['ArpeggioOctaveRange']=[64,7,1]
        self.attributes['ArpeggioAccentRate']=[0,9,1]
        self.attributes['ArpeggioVelocity']=[0,10,1]

        self.baseaddress=[0x18,0x00,0x00]
        self.offset=[0x00,0x40]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x0c]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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

class Digital_Synth_Tone_Common():

    def __init__(self, *args, **kwargs):
        self.baseaddress=kwargs['baseaddress']
        self.offset=kwargs['offset']

        self.attributes={}
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
        self.deviceID=JDXi_device
        self.id=0
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x40]
        self.devicestatus='unknown'

    def get_data(self):
        printdebug(sys._getframe().f_lineno, "DS tone common, get_data")
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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

    def __init__(self, *args, **kwargs):
        self.baseaddress=kwargs['baseaddress']
        self.offset=kwargs['offset']
        self.attributes={}
        self.attributes['AttTimIntSens']=[0,1,1]
        self.attributes['RelTimIntSens']=[0,2,1]
        self.attributes['PortTimIntSens']=[0,3,1]
        self.attributes['EnvLooMod']=[0,4,1]
        self.attributes['EnvLooSynNot']=[11,5,1]
        self.attributes['ChrPort']=[0,6,1]

        self.deviceID=JDXi_device
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x25]
        self.devicestatus='unknown'

#        super().__init__(self, *args, **kwargs)
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        pass

    def get_data(self):
        printdebug(sys._getframe().f_lineno, "DS modify, get_data")
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self. attributes:
            if attr!='Name':
                self. attributes[attr][0]=data[self. attributes[attr][1]]
            else:
                name=''
                for c in data[self. attributes[attr][1]:self. attributes[attr][1]+12]:
                    name+=chr(c)
                self. attributes[attr][0]=name
        return('OK')

    def set__attr(self,attribute,value):
        self.attributes[attribute][0]=value
        send_data=self.attributes[attribute][1]
        send_sysex_DT1(self.sysexsetlist,send_data,value)
 
    def push_data(self):
        return

class Digital_Synth_Partial():

    def __init__(self, *args, **kwargs):
        self.baseaddress=kwargs['baseaddress']
        self.offset=kwargs['offset']
        
        self.attributes={}
        self.attributes['OSCWave']=[0,0,1]
        self.attributes['OSCWaveVariation']=[0,1,1]
        self.attributes['OSCPitch']=[64,3,1]
        self.attributes['OSCDetune']=[74,4,1]
        self.attributes['OSCPulseWidthModDepth']=[1,5,1]
        self.attributes['OSCPulseWidth']=[0,6,1]
        self.attributes['OSCPitchEnvAttackTime']=[0,7,1]
        self.attributes['OSCPitchEnvDecay']=[0,8,1]
        self.attributes['OSCPitchEnvDepth']=[64,9,1]
        self.attributes['FILTERMode']=[0,10,1]
        self.attributes['FILTERSlope']=[0,11,1]
        self.attributes['FILTERCutoff']=[127,12,1]
        self.attributes['FILTERCutoffKeyfollow']=[64,13,1]
        self.attributes['FILTEREnvVelocitySens']=[64,14,1]
        self.attributes['FILTERResonance']=[0,15,1]
        self.attributes['FILTEREnvAttackTime']=[0,16,1]
        self.attributes['FILTEREnvDecayTime']=[0,17,1]
        self.attributes['FILTEREnvSustainLevel']=[127,18,1]
        self.attributes['FILTEREnvReleaseTime']=[0,19,1]
        self.attributes['FILTEREnvDepth']=[64,20,1]
        self.attributes['AMPLevel']=[100,21,1]
        self.attributes['AMPLevelVelocitySens']=[64,22,1]
        self.attributes['AMPEnvAttackTime']=[0,23,1]
        self.attributes['AMPEnvDecayTime']=[36,24,1]
        self.attributes['AMPEnvSustainLevel']=[0,25,1]
        self.attributes['AMPEnvReleaseTime']=[0,26,1]
        self.attributes['AMPPan']=[64,27,1]
        self.attributes['LFOShape']=[0,28,1]
        self.attributes['LFORate']=[81,29,1]
        self.attributes['LFOTempoSyncSwitch']=[0,30,1]
        self.attributes['LFOTempoSyncNote']=[17,31,1]
        self.attributes['LFOFadeTime']=[0,32,1]
        self.attributes['LFOKeyTrigger']=[0,33,1]
        self.attributes['LFOPitchDepth']=[64,34,1]
        self.attributes['LFOFilterDepth']=[64,35,1]
        self.attributes['LFOAmpDepth']=[64,36,1]
        self.attributes['LFOPanDepth']=[64,37,1]
        self.attributes['ModulationLFOShape']=[0,38,1]
        self.attributes['ModulationLFORate']=[88,39,1]
        self.attributes['ModulationLFOTempoSyncSwitch']=[0,40,1]
        self.attributes['ModulationLFOTempoSyncNote']=[17,41,1]
        self.attributes['OSCPulseWidthShift']=[127,42,1]
        self.attributes['ModulationLFOPitchDepth']=[80,44,1]
        self.attributes['ModulationLFOFilterDepth']=[64,45,1]
        self.attributes['ModulationLFOAmpDepth']=[64,46,1]
        self.attributes['ModulationLFOPanDepth']=[64,47,1]
        self.attributes['CutoffAftertouchSens']=[64,48,1]
        self.attributes['LevelAftertouchSens']=[74,49,1]
        self.attributes['WaveGain']=[1,52,1]
        self.attributes['WaveNumber']=[14,53,4]
        self.attributes['HPFCutoff']=[0,57,1]
        self.attributes['SuperSawDetune']=[1,58,1]
        self.attributes['ModulationLFORateControl']=[84,59,1]
        self.attributes['AMPLevelKeyfollow']=[64,60,1]

        self.deviceID=JDXi_device
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x3D]

        sysexsetlist=self.deviceID+[0x12]+self.address
        sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        
    def get_data(self):
        printdebug(sys._getframe().f_lineno, "DS partial, get_data")
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
        printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        if data=='unknown':
            self.devicestatus='unknown'
            return('7OF9')
        else:
            self.devicestatus='OK'
        for attr in self. attributes:
            if attr!='Name':
                self. attributes[attr][0]=data[self. attributes[attr][1]]
            else:
                name=''
                for c in data[self. attributes[attr][1]:self. attributes[attr][1]+12]:
                    name+=chr(c)
                self. attributes[attr][0]=name
        return('OK')

    def set__attr(self,attribute,value):
        self.attributes[attribute][0]=value
        send_data=self.attributes[attribute][1]
        send_sysex_DT1(self.sysexsetlist,send_data,value)
 
    def push_data(self):
        return
class Digital_Synth():

    def __init__(self,*args, **kwargs):
        #self.attributes={}
        self.baseaddress=kwargs['baseaddress']
        self.id=kwargs['id']
        self.attributes={}
        self.common=Digital_Synth_Tone_Common(baseaddress=self.baseaddress,offset=[0x00,0x00])
        self.part1=Digital_Synth_Partial(baseaddress=self.baseaddress,offset=[0x00,0x20])
        self.part2=Digital_Synth_Partial(baseaddress=self.baseaddress,offset=[0x00,0x21])
        self.part3=Digital_Synth_Partial(baseaddress=self.baseaddress,offset=[0x00,0x22])
        self.modify=Digital_Synth_Modify(baseaddress=self.baseaddress,offset=[0x00,0x50])
    

        # self.deviceID=JDXi_device
        # self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        # self.datalength=[0x00,0x00,0x00,0x40]
        # self.sysexsetlist=self.deviceID+[0x12]+self.address
        # self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        # print("u DigitalSynth",self)
        # super().__init__(self, *args, **kwargs)
        # mro_list=__class__.mro()
        # mro_list[2]()
        self.devicestatus='unknown'

    def get_data(self):
        printdebug(sys._getframe().f_lineno, "DS"+self.id+ ", get  data")
        if(self.common.get_data())!='OK':
            printdebug(sys._getframe().f_lineno, 'Cannot get common data for DS'+self.id)
            logger.error('Cannot get common datafor DS'+self.id)
        if(self.part1.get_data())!='OK':
            printdebug(sys._getframe().f_lineno, 'Cannot get partial1 data for DS'+self.id)
            logger.error('Cannot get partial1 data for DS'+self.id)
        if(self.part2.get_data())!='OK':
            printdebug(sys._getframe().f_lineno,  'Cannot get partial2 data for DS'+self.id)
            logger.error('Cannot get partial2 data for DS'+self.id)
        if(self.part3.get_data())!='OK':
            printdebug(sys._getframe().f_lineno,  'Cannot get partial3 data for DS'+self.id)
            logger.error( 'Cannot get partial3 data for DS'+self.id)
        if(self.modify.get_data())!='OK':
            printdebug(sys._getframe().f_lineno,  'Cannot get modify data for DS'+self.id)
            logger.error( 'Cannot get modify data for DS'+self.id)

        # printdebug(sys._getframe().f_lineno, "DS, get_data")
        # data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
        # printdebug(sys._getframe().f_lineno, "Data received: "+ str(data))
        # if data=='unknown':
        #     self.devicestatus='unknown'
        #     return('7OF9')
        # else:
        #     self.devicestatus='OK'
        # for attr in self.attributes:
        #     if attr!='Name':
        #         self.attributes[attr][0]=data[self.attributes[attr][1]]
        #     else:
        #         name=''
        #         for c in data[self.attributes[attr][1]:self.attributes[attr][1]+12]:
        #             name+=chr(c)
        #         self.attributes[attr][0]=name
                
        # self.get_modify_data()
        return('OK')

    def set_attr(self,attribute,value):
        if attribute in self.attributes:
            self.attributes[attribute][0]=value
            send_data=self.attributes[attribute][1]
            send_sysex_DT1(self.sysexsetlist,send_data,value)
            pass
        elif attribute in self.dsm_attributes:
            self.set_modify_attr(attribute, value)
        else:
            pass

    def push_data(self):
        return

    def get_addresses(self):
        printdebug(sys._getframe().f_lineno, "Base Address: "+ str(self.baseaddress))
        printdebug(sys._getframe().f_lineno, "Address: "+ str(self.address))
        printdebug(sys._getframe().f_lineno, "Dsm Address: "+ str(self.dsm_address))
        printdebug(sys._getframe().f_lineno, "Offset: "+ str(self.offset))
    
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
        self.datalength=[0x00,0x00,0x00,0x40]
        self.deviceID=JDXi_device
# required for SysEx Data set 1 (DT1=0x12) 
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]
        self.devicestatus='unknown'

    def get_data(self):
        data=send_sysex_RQ1(self.deviceID, self.address+[0x00], self.datalength)
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
        length=((self.datalength[0]*256+self.datalength[1])*256+self.datalength[2])*256+self.datalength[3]
        data=[0]*length
        for attr in self.attributes:
            if attr != "Name":
                data[self.attributes[attr][1]] = self.attributes[attr][0]
            else:
                name=self.attributes[attr][0]
                name=name+' '*(self.attributes[attr][2] - len(name))
                nameascii=[ord(c) for c in name]
                data[self.attributes[attr][1] : self.attributes[attr][1]+self.attributes[attr][2]] = nameascii
                self.attributes[attr][0] = name
        send_sysex_DT1(self.sysexsetlist, 0, data)  # 0 because of all chunk
        return

class Drum_Kit_Common():
    def __init__(self, *args, **kwargs):
        self.attributes={}
        self.attributes['Name']=['INIT',0]
        self.baseaddress=[0x19,0x60,0x00]
        self.offset=[0x10,0x00]
        self.address=[self.baseaddress[0],self.baseaddress[1]+self.offset[0],self.baseaddress[2]+self.offset[1]]
        self.datalength=[0x00,0x00,0x00,0x12]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
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
        self.datalength=[0x00,0x00,0x01,0x43]
        self.deviceID=JDXi_device
        self.sysexsetlist=self.deviceID+[0x12]+self.address
        self.sysexgetlist=self.deviceID+[0x11]+self.address+self.datalength
        self.devicestatus='unknown'

    def get_data(self):
        return

    def push_data(self):
        return

onoff3=''
onoff4=''
onoff1=''
onoff2=''
onoff_data=(onoff3,onoff4,onoff1,onoff2)

OFF0 = ''
OFF1 = ''
TRI0 = ''
TRI1 = ''
SIN0 = ''
SIN1 = ''
SAW0 = ''
SAW1 = ''
SQR0 = ''
SQR1 = ''
PW_SQR0 = ''
PW_SQR1 = ''
S_H0 = ''
S_H1 = ''
OCT_10 = ''
OCT_11 = ''
OCT_20 = ''
OCT_21 = ''
RND0 = ''
RND1 = ''
FREE_RUN0 = ''
FREE_RUN1 = ''
TEMPO_SYNC0 = ''
TEMPO_SYNC1 = ''
POLY0 = ''
POLY1 = ''
MONO0 = ''
MONO1 = ''
NORMAL0 = ''
NORMAL1 = ''
LEGATO0 = ''
LEGATO1 = ''

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

images['FREE_RUN']=[FREE_RUN0,FREE_RUN1]
images['TEMPO_SYNC']=[TEMPO_SYNC0,TEMPO_SYNC1]
images['POLY']=[POLY0,POLY1]
images['MONO']=[MONO0,MONO1]
images['NORMAL']=[NORMAL0,NORMAL1]
images['LEGATO']=[LEGATO0,LEGATO1]
       
IMAGE_SUBSAMPLE=4
TEXT_SIZE=26

def make_analog_synth_window(AS,theme,loc,siz):
    prefix='-ANALOG_SYNTH-'
    short_prefix='-AS'
    group={}
    column={}
    frames={}
    ADSR_Frame_number=0
    ADSR_Frame=[[]]
    tk.theme(theme)
    ANALOG_JSON_FILE='analog.json'
    with open(ANALOG_JSON_FILE) as json_file:
        analog_parameters = json.load(json_file)
        if 'Skeleton' in analog_parameters:
            column_names=analog_parameters['Skeleton']
            layout=[]
        else:
            layout=[[tk.Text('Cannot create layout for'+prefix)]]
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
                        group[row[group_index]]=[[tk.Text(row[label_index],expand_x=True,justification='center',
                                                           background_color='yellow',relief='raised',text_color='black',
                                                           font=('Arial',12,'bold'))]]
                        column[row[group_index]]=row[column_index]
                    else:
                        group[row[group_index]]=[]
                        column[row[group_index]]=row[column_index]
                    if row[frame_index]=='':
                        tempframe=None
                    if row[frame_index]!='' and row[frame_index] not in frames:
                        tempframe=tk.Frame(row[frame_index],[],key=short_prefix+'FRAME-'+row[frame_index]+'-')
                        frames[row[frame_index]]=[tk.Frame(row[frame_index],[],key=short_prefix+'_FRAME-'+row[frame_index]+'-')]
                        group[row[group_index]]+=[[tempframe]]

                if row[short_name_index] in AS.attributes:
                    default_val=AS.attributes[row[short_name_index]][0]
#                elif row[short_name_index] in AS.dsm_attributes:
#                    default_val=AS.dsm_attributes[row[short_name_index]][0]
                else:
                    default_val=0

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
                            tempframe.add_row(tk.Text(row[name_index],size=TEXT_SIZE))
                            tempframe.Rows[-1].append(tk.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                       default_value=default_val, orientation='horizontal',
                                       size=(20,10),enable_events=True,key=key_value,disable_number_display=True))
                            tempframe.Rows[-1].append(tk.Text(int(row[default_index]), enable_events=True, key=text_key_value))
                            # tempframe.add_row([tk.Text(row[name_index],size=28),
                            # tk.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                            #            default_value=int(row[default_index]), orientation='horizontal',
                            #            size=(20,10),enable_events=True,key=key_value,disable_number_display=True),
                            # tk.Text(int(row[default_index]), enable_events=True, key=text_key_value)])
                        else:
                            group[row[group_index]]+=[[tk.Text(row[name_index],size=TEXT_SIZE),
                            tk.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                       default_value=default_val, orientation='horizontal',
                                       size=(20,10),enable_events=True,key=key_value,disable_number_display=True),
                            tk.Text(int(row[default_index]), enable_events=True, key=text_key_value)]]
                    else:
                        if row[verticalgroup_index]=='':
                            group[row[group_index]]+=[[tk.Text(row[name_index],size=TEXT_SIZE),
                                tk.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                           default_value=default_val, orientation='vertical',
                                           size=(5,None),enable_events=True,key=key_value,disable_number_display=True),
                                tk.Text(int(row[default_index]), enable_events=True, key=text_key_value)]]
                        else:
                            ADSR_Frame[-1].extend([tk.Column(
                                [[tk.Text(row[label_index],k=text_key_value+'top')],
                                 [tk.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                           default_value=default_val, orientation='vertical',
                                           size=(5,10),enable_events=True,key=key_value,disable_number_display=True)],
                                 [tk.Text(int(row[default_index]), enable_events=True, key=text_key_value)]
                                ]
                                 )])
                            if row[verticalgroup_index]=='END':
                                group[row[group_index]]+=[[tk.Frame(row[frame_index],[ADSR_Frame[-1]],k=short_prefix+'_FRAME-'+row[frame_index]+'vert')]]
                                ADSR_Frame.append([])

  
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='TEXT':
                    key_value=short_prefix+'_NAME-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[tk.Text(row[name_index],size=TEXT_SIZE),
                                               tk.Text(default_val,size=TEXT_SIZE)]]
                elif row[type_index]=='ONOFF':
                    key_value=short_prefix+'_ONOFF-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[tk.Text(row[name_index],size=TEXT_SIZE),
                              tk.Button(image_data=onoff_data[0],metadata=[0,0,int(row[valuefrom_index]),int(row[valueto_index])],auto_size_button=True,border_width=0,
                                         button_color=(tk.theme_element_background_color(),tk.theme_element_background_color() ),
                                         key=key_value, image_subsample=IMAGE_SUBSAMPLE)]]
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='LISTBUTTON':
                     key_value=short_prefix+'_LISTBUTTON-'+row[short_name_index]+'-'
                     key_value.replace(' ','_')
                     tmp_layout=[tk.Text(row[name_index],size=TEXT_SIZE)]
                     for part in range(int(row[valuefrom_index]),int(row[valueto_index])+1):
                         tmp_layout+=[tk.Button('',auto_size_button=True,border_width=0,
                                    image_data=images[row[list_index][part]][1 if int(row[default_index])==part else 0], 
                                    image_subsample=IMAGE_SUBSAMPLE, mouseover_colors=(tk.YELLOWS[0],tk.YELLOWS[0]),
                                    button_color=(tk.theme_element_background_color(),tk.theme_element_background_color()),
                                    metadata=[1 if int(row[default_index])==part else 0,
                                              [ i for i in range(int(row[valuefrom_index]),int(row[valueto_index])+1) if i!=part ],
                                              row[list_index][part]], key=key_value+' '+str(part))]
                     group[row[group_index]]+=[tmp_layout]
                     #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='LIST':
                    key_value=short_prefix+'_LIST-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[
                        tk.Text(row[name_index],size=TEXT_SIZE),
                        tk.Combo(row[list_index], default_value=row[list_index][default_val], key=key_value,
                                  readonly=True,enable_events=True,size=10)]]
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
    layout = [[tk.Button('Fake buttton'), tk.Button('Popup'), tk.Button('Exit')]]
    current_column=0
    col=[[],[]]
    for line in group:
#        if column[line]!=current_column:
        col[int(column[line])]+=group[line]
#    for ccc in col:
    layout+=[[tk.Frame('',col[0],border_width=0),tk.VerticalSeparator(),tk.Frame('',col[1],border_width=0,vertical_alignment='top')]]
    return tk.Window('Analog Synth', layout, location=loc, resizable=True, size=siz, finalize=True, 
                      icon= music,return_keyboard_events=True)

def update_analog_synth_window(AS, AW):
    prefix='-ANALOG_SYNTH-'
    short_prefix='-AS'
    ADSR_Frame_number=0
    ADSR_Frame=[[]]
    ANALOG_JSON_FILE='analog.json'
    for element in AW.element_list():
        key=str(element.key)
        if key.startswith('-AS_ONOFF-'):
            attr=key[len('-AS_ONOFF-'):-1]
            AW[key].metadata[1]=AS.attributes[attr][0]
            AW[key].update(image_data=onoff_data[0+2*AW[key].metadata[1]],image_subsample=IMAGE_SUBSAMPLE)
#            print(key,str(AS.attributes[attr][0]))
        elif key.startswith('-AS_LISTBUTTON-'):
            splited=key.split()
            attr=splited[0][len('-AS_LISTBUTTON-'):-1]
            attr_value=int(AS.attributes[attr][0])
            current_button=AW['-AS_LISTBUTTON-'+attr+'- '+str(attr_value)]
            if current_button.metadata[0]!=0:
                continue
            for others in current_button.metadata[1]:
                tmp_button=AW['-AS_LISTBUTTON-'+attr+'- '+str(others)]
                tmp_button.update(image_data=images[tmp_button.metadata[2]][0],image_subsample=IMAGE_SUBSAMPLE)
                tmp_button.metadata[0]=0
            current_button.update(image_data=images[current_button.metadata[2]][1],image_subsample=IMAGE_SUBSAMPLE)
            current_button.metadata[0]=1
#            print(key,str(AS.attributes[attr][0]))
        elif key.startswith('-AS_SLIDER-'):
            attr=key[len('-AS_SLIDER-'):-1]
            AW[key].update(int(AS.attributes[attr][0]))
            AW[key.replace('-AS_SLIDER-','-AS_TEXT_SLIDER-')+'value'].update(int(AS.attributes[attr][0]))
#            print(key,str(AS.attributes[attr][0]))

def make_digital_synth_window(DS,theme,loc,siz):
    prefix='-DIGITAL_SYNTH_'+str(DS.id)+'-'
    short_prefix='-DS_'+str(DS.id)
    group={}
    column={}
    frames={}
    ADSR_Frame_number=0
    ADSR_Frame=[[]]
    tk.theme(theme)
    DIGITAL_JSON_FILE='digital.json'
    with open(DIGITAL_JSON_FILE) as json_file:
        digital_parameters = json.load(json_file)
        if 'Skeleton' in digital_parameters:
            column_names=digital_parameters['Skeleton']
            layout=[]
        else:
            layout=[[tk.Text('Cannot create layout for'+prefix)]]
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
                        group[row[group_index]]=[[tk.Text(row[label_index],expand_x=True,justification='center',
                                                           background_color='yellow',relief='raised',text_color='black',
                                                           font=('Arial',12,'bold'))]]
                        column[row[group_index]]=row[column_index]
                    else:
                        group[row[group_index]]=[]
                        column[row[group_index]]=row[column_index]
                    if row[frame_index]=='':
                        tempframe=None
                    if row[frame_index]!='' and row[frame_index] not in frames:
                        tempframe=tk.Frame(row[frame_index],[],key=short_prefix+'_FRAME-'+row[frame_index]+'-')
                        frames[row[frame_index]]=[tk.Frame(row[frame_index],[],key=short_prefix+'_FRAME-'+row[frame_index]+'-')]
                        group[row[group_index]]+=[[tempframe]]
#                if row[verticalgroup_index]!=''and ADSR_Frame[-1]==None:
#                    ADSR_Frame[-1]=[]
                if row[short_name_index] in DS.attributes:
                    default_val=DS.attributes[row[short_name_index]][0]
                elif row[short_name_index] in DS.dsm_attributes:
                    default_val=DS.dsm_attributes[row[short_name_index]][0]
                else:
                    default_val=0
 
                if row[type_index]=='SLIDER':
                    key_value=short_prefix+'_SLIDER-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    text_key_value=short_prefix+'_TEXT_SLIDER-'+row[short_name_index]+'-value'
                    text_key_value.replace(' ','_')
                    orient='horizontal' if row[orientation_index]=='horizontal' else 'vertical'
                    if orient=='horizontal':
                        if tempframe:
                            tempframe.add_row(tk.Text(row[name_index],size=TEXT_SIZE))
                            tempframe.Rows[-1].append(tk.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                       default_value=default_val, orientation='horizontal',
                                       size=(20,10),enable_events=True,key=key_value,disable_number_display=True))
                            tempframe.Rows[-1].append(tk.Text(int(row[default_index]), enable_events=True, key=text_key_value))
                            # tempframe.add_row([tk.Text(row[name_index],size=28),
                            # tk.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                            #            default_value=int(row[default_index]), orientation='horizontal',
                            #            size=(20,10),enable_events=True,key=key_value,disable_number_display=True),
                            # tk.Text(int(row[default_index]), enable_events=True, key=text_key_value)])
                        else:
                            group[row[group_index]]+=[[tk.Text(row[name_index],size=TEXT_SIZE),
                            tk.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                       default_value=default_val, orientation='horizontal',
                                       size=(20,10),enable_events=True,key=key_value,disable_number_display=True),
                            tk.Text(int(row[default_index]), enable_events=True, key=text_key_value)]]
                    else:
                        if row[verticalgroup_index]=='':
                            group[row[group_index]]+=[[tk.Text(row[name_index],size=TEXT_SIZE),
                                tk.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                           default_value=default_val, orientation='vertical',
                                           size=(5,None),enable_events=True,key=key_value,disable_number_display=True),
                                tk.Text(int(row[default_index]), enable_events=True, key=text_key_value)]]
                        else:
                            ADSR_Frame[-1].extend([tk.Column(
                                [[tk.Text(row[label_index],k=text_key_value+'top')],
                                 [tk.Slider(range=(int(row[valuefrom_index]),int(row[valueto_index])),
                                           default_value=default_val, orientation='vertical',
                                           size=(5,10),enable_events=True,key=key_value,disable_number_display=True)],
                                 [tk.Text(int(row[default_index]), enable_events=True, key=text_key_value)]
                                ]
                                 )])
                            if row[verticalgroup_index]=='END':
                                group[row[group_index]]+=[[tk.Frame(row[frame_index],[ADSR_Frame[-1]],k=short_prefix+'_FRAME-'+row[frame_index]+'vert')]]
                                ADSR_Frame.append([])

  
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='TEXT':
                    key_value=short_prefix+'_NAME-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[tk.Text(row[name_index],size=TEXT_SIZE),
                                               tk.Text(default_val,size=TEXT_SIZE)]]
                elif row[type_index]=='ONOFF':
                    key_value=short_prefix+'_ONOFF-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[tk.Text(row[name_index],size=TEXT_SIZE),
                              tk.Button(image_data=onoff_data[0],metadata=[0,0,int(row[valuefrom_index]),int(row[valueto_index])],auto_size_button=True,border_width=0,
                                         button_color=(tk.theme_element_background_color(),tk.theme_element_background_color() ),
                                         key=key_value, image_subsample=IMAGE_SUBSAMPLE)]]
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='LISTBUTTON':
                     key_value=short_prefix+'_LISTBUTTON-'+row[short_name_index]+'-'
                     key_value.replace(' ','_')
                     tmp_layout=[tk.Text(row[name_index],size=TEXT_SIZE)]
                     for part in range(int(row[valuefrom_index]),int(row[valueto_index])+1):
                         tmp_layout+=[tk.Button('',auto_size_button=True,border_width=0,
                                    image_data=images[row[list_index][part]][1 if int(row[default_index])==part else 0], 
                                    image_subsample=IMAGE_SUBSAMPLE, mouseover_colors=(tk.YELLOWS[0],tk.YELLOWS[0]),
                                    button_color=(tk.theme_element_background_color(),tk.theme_element_background_color()),
                                    metadata=[1 if int(row[default_index])==part else 0,
                                              [ i for i in range(int(row[valuefrom_index]),int(row[valueto_index])+1) if i!=part ],
                                              row[list_index][part]], key=key_value+' '+str(part))]
                     group[row[group_index]]+=[tmp_layout]
                     #AS.attributes[row[short_name_index]][0]=int(row[default_index])
                elif row[type_index]=='LIST':
                    key_value=short_prefix+'_LIST-'+row[short_name_index]+'-'
                    key_value.replace(' ','_')
                    group[row[group_index]]+=[[
                        tk.Text(row[name_index],size=TEXT_SIZE),
                        tk.Combo(row[list_index], default_value=row[list_index][default_val], key=key_value,
                                  readonly=True,enable_events=True,size=10)]]
                    #AS.attributes[row[short_name_index]][0]=int(row[default_index])
    layout = [[tk.Button('DS'+str(DS.id)+' Fake buttton'), tk.Button('DS'+str(DS.id)+' Popup'), tk.Button('Exit')]]
    current_column=0
    col=[[],[]]
    for line in group:
#        if column[line]!=current_column:
        col[int(column[line])]+=group[line]
#    for ccc in col:
    layout+=[[tk.Frame('',col[0],border_width=0),tk.VerticalSeparator(),tk.Frame('',col[1],border_width=0,vertical_alignment='top')]]
    return tk.Window('Digital Synth '+str(DS.id), layout, location=loc, resizable=True, size=siz, finalize=True, 
                      icon= music,return_keyboard_events=True)

style_set = 0

def set_style():
    global style
    global style_set
    if style_set: return        
    try: root.tk.call('source',
                os.path.join(_location, 'themes', 'default.tcl'))
    except: pass
    style = ttk.Style()
    style.theme_use('default')
    style.configure('.', font = "TkDefaultFont")
    style.configure('TRadioButton', indicatoron=False)
    if sys.platform == "win32":
       style.theme_use('winnative')    
    style.layout("ListButton.TRadiobutton", [('Radiobutton.padding', {'sticky': '', 'children': 
                 [ ('Radiobutton.focus', {'side': 'left', 'sticky': '', 'children': 
                 [('Radiobutton.label', {'sticky': ''})]})]})] )
    style.configure("ListButton.TRadiobutton", background='yellow',foreground="red",
                    activeforeground="green",highlightbackground="white")
    style.map("ListButton.TRadiobutton",
              background=[#('disabled', 'magenta'),
                ('active', "yellow"),
                ('selected', "#61e339"),
                #('pressed', '!focus', 'cyan'),
                ('!focus', '#010101'), ##304f85"),
                ('focus', "#304f85"),
                ('pressed', 'red'),
                #('pressed', "#10fff5"),
                #('!pressed', "#f0fff5"),
               
                #('active', "#304f85"),('!active', "#304f85")
                ],
                highlightcolor=[('focus', 'pink'),
                                ('!focus', 'red')],
            )

    style_set = 1

global  w1, w2, w3, w4, w5, w6, w7, w8, w9, top, top_Analog, top_Digital1, top_Digital2, top_Voice, top_Effects, top_Arpeggio, top_Program, top_Drums

def on_AnalogClick(*args):
    if DEBUG:
        print('on_AnalogClick')
        print(top_Analog.state())
        sys.stdout.flush()
    if 'normal' == top_Analog.state():
        top_Analog.withdraw() 
    else:
        top_Analog.deiconify()

def on_Digital1Click(*args):
    if DEBUG:
        print('on_Digital1Click')
        print(top_Digital1.state())
        sys.stdout.flush()
    if 'normal' == top_Digital1.state():
        top_Digital1.withdraw() 
    else:
        top_Digital1.deiconify()
   
def on_Digital2Click(*args):
    if DEBUG:
        print('on_Digital2Click')
        print(top_Digital2.state())
        sys.stdout.flush()
    if 'normal' == top_Digital2.state():
        top_Digital2.withdraw() 
    else:
        top_Digital2.deiconify()

def on_VoiceClick(*args):
    if DEBUG:
        print('on_VoiceClick')
        print(top_Voice.state())
        sys.stdout.flush()
    if 'normal' == top_Voice.state():
        top_Voice.withdraw() 
    else:
        top_Voice.deiconify()

def on_EffectsClick(*args):
    if DEBUG:
        print('on_EffectsClick')
        print(top_Effects.state())
        sys.stdout.flush()
    if 'normal' == top_Effects.state():
        top_Effects.withdraw() 
    else:
        top_Effects.deiconify()

def on_ArpeggioClick(*args):
    if DEBUG:
        print('on_ArpeggioClick')
        print(top_ProgramController.state())
        sys.stdout.flush()
    if 'normal' == top_ProgramController.state():
        top_ProgramController.withdraw() 
    else:
        top_Arpeggio.deiconify()

def on_DrumsClick(*args):
    if DEBUG:
        print('on_DrumsClick')
        print(top_Drums.state())
        sys.stdout.flush()
    if 'normal' == top_Drums.state():
        top_Drums.withdraw() 
    else:
        top_Drums.deiconify()

def on_ProgramClick(*args):
    if DEBUG:
        print('on_ProgramClick')
        print(top_Program.state())
        sys.stdout.flush()
    if 'normal' == top_Program.state():
        top_Program.withdraw() 
    else:
        top_Program.deiconify()

def on_OpenClick(*args):
    if DEBUG:
        print('on_OpenClick')
        for arg in args:
            print ('arg:', arg)
        sys.stdout.flush()

def on_TestSoundClick(*args):   
    if DEBUG:
        print('on_TestSoundClick')
        for arg in args:
            print ('arg:', arg)
        sys.stdout.flush()

def on_ReloadClick(*args):
    if DEBUG:
        print('on_ReloadClick')
        for arg in args:
            print ('arg:', arg)
        sys.stdout.flush()

def on_PanicClick(*args):
    if DEBUG:
        print('on_PanicClick')
        for arg in args:
            print ('arg:', arg)
        sys.stdout.flush()

def on_PlayClick(*args):
    if DEBUG:
        print('on_PlayClick')
        for arg in args:
            print ('arg:', arg)
        sys.stdout.flush()

def on_PolytouchClick(*args):
    if DEBUG:
        print('on_PolytouchClick')
        for arg in args:
            print ('arg:', arg)

def on_CloseClick(*args):
    if DEBUG:
        print('on_CloseClick')
        for arg in args:
            print ('arg:', arg)
        sys.stdout.flush()

   
def do_exit(*args):
    if DEBUG:
        print('on_VoiceClick')
        for arg in args:
            print ('arg:', arg)
        sys.stdout.flush()
    if messagebox.askokcancel("Quit JD-Xi manager", "Are you sure you want to quit JD-Xi manager?"):
        root.destroy()


class JDXi_manager():
    def __init__(self, top=None,loc=None,siz=None ):
        '''This class configures and populates the toplevel window.
           top is the toplevel containing window.'''
        set_style()
        top.geometry("762x300+187+88")
        top.geometry(f"{siz[0]}x{siz[1]}+{loc[0]}+{loc[1]}")

        top.minsize(400, 200)
        top.maxsize(1905, 1050)
        top.resizable(1,  1)
        top.title("JD-Xi manager")
        # top.configure(background="#304f83")
        # top.configure(highlightbackground="#304f83")
        # top.configure(highlightcolor="#f0f0f0")

        self.top = top
        self.ProgRxTxCh = tk.StringVar()
        self.MIDIout = tk.StringVar()
        self.Channel = tk.StringVar()
        self.Instrument = tk.StringVar()
        self.MIDIin = tk.StringVar()
        self.TestNote = tk.DoubleVar()

        self.Top_Digital2 = ttk.Button(self.top)
        self.Top_Digital2.place(relx=0.136, rely=0.587, height=28, width=83)
        self.Top_Digital2.configure(command=on_Digital2Click)
        self.Top_Digital2.configure(text='''Digital 2''')
        self.Top_Digital2.configure(compound='left')

        self.Top_TestSound = ttk.Button(self.top)
        self.Top_TestSound.place(relx=0.642, rely=0.423, height=28, width=83)
        self.Top_TestSound.configure(command=on_TestSoundClick)
        self.Top_TestSound.configure(text='''Test Sound''')
        self.Top_TestSound.configure(compound='left')

        self.Top_MIDIout = ttk.Label(self.top)
        self.Top_MIDIout.place(relx=0.014, rely=0.13, height=23, width=74)
        self.Top_MIDIout.configure(font="-family {DejaVu Sans} -size 10")
        self.Top_MIDIout.configure(relief="flat")
        self.Top_MIDIout.configure(anchor='w')
        self.Top_MIDIout.configure(justify='left')
        self.Top_MIDIout.configure(text='''MIDI out''')
        self.Top_MIDIout.configure(compound='left')

        self.Top_Channel = ttk.Label(self.top)
        self.Top_Channel.place(relx=0.014, rely=0.227, height=24, width=74)
        self.Top_Channel.configure(font="-family {DejaVu Sans} -size 10")
        self.Top_Channel.configure(relief="flat")
        self.Top_Channel.configure(anchor='w')
        self.Top_Channel.configure(justify='left')
        self.Top_Channel.configure(text='''Channel''')
        self.Top_Channel.configure(compound='left')

        self.Top_RxTxVals = ttk.Combobox(self.top)
        self.Top_RxTxVals.place(relx=0.601, rely=0.033, relheight=0.067
                , relwidth=0.064)
        self.value_list = ['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16',]
        self.Top_RxTxVals.configure(values=self.value_list)
        self.Top_RxTxVals.configure(font="-family {DejaVu Sans} -size 10")
        self.Top_RxTxVals.configure(textvariable=self.ProgRxTxCh)

        self.Top_MIDIoutVals = ttk.Combobox(self.top)
        self.Top_MIDIoutVals.place(relx=0.136, rely=0.13, relheight=0.067
                , relwidth=0.243)
        self.Top_MIDIoutVals.configure(font="-family {DejaVu Sans} -size 10")
        self.Top_MIDIoutVals.configure(textvariable=self.MIDIout)

        self.Top_ChannelVals = ttk.Combobox(self.top)
        self.Top_ChannelVals.place(relx=0.136, rely=0.227, relheight=0.07
                , relwidth=0.243)
        self.Top_ChannelVals.configure(font="-family {DejaVu Sans} -size 10")
        self.Top_ChannelVals.configure(textvariable=self.Channel)

        self.Top_Instrument = ttk.Label(self.top)
        self.Top_Instrument.place(relx=0.014, rely=0.327, height=23, width=85)
        self.Top_Instrument.configure(font="-family {DejaVu Sans} -size 10")
        self.Top_Instrument.configure(relief="flat")
        self.Top_Instrument.configure(anchor='w')
        self.Top_Instrument.configure(justify='left')
        self.Top_Instrument.configure(text='''Instrument''')
        self.Top_Instrument.configure(compound='left')

        self.Top_InstrumentVals = ttk.Combobox(self.top)
        self.Top_InstrumentVals.place(relx=0.136, rely=0.327, relheight=0.067
                , relwidth=0.243)
        self.Top_InstrumentVals.configure(font="-family {DejaVu Sans} -size 10")
        self.Top_InstrumentVals.configure(textvariable=self.Instrument)

        self.Top_ProgRxTxCh = ttk.Label(self.top)
        self.Top_ProgRxTxCh.place(relx=0.437, rely=0.033, height=23, width=105)
        self.Top_ProgRxTxCh.configure(font="-family {DejaVu Sans} -size 10")
        self.Top_ProgRxTxCh.configure(relief="flat")
        self.Top_ProgRxTxCh.configure(anchor='w')
        self.Top_ProgRxTxCh.configure(justify='left')
        self.Top_ProgRxTxCh.configure(text='''Prog Rx/Tx Ch''')
        self.Top_ProgRxTxCh.configure(compound='left')

        self.Top_Reload = ttk.Button(self.top)
        self.Top_Reload.place(relx=0.437, rely=0.13, height=28, width=63)
        self.Top_Reload.configure(command=on_ReloadClick)
        self.Top_Reload.configure(text='''Reload''')
        self.Top_Reload.configure(compound='left')

        self.Top_Panic = ttk.Button(self.top)
        self.Top_Panic.place(relx=0.533, rely=0.13, height=28, width=63)
        self.Top_Panic.configure(command=on_PanicClick)
        self.Top_Panic.configure(text='''Panic''')
        self.Top_Panic.configure(compound='left')

        self.Top_Open = ttk.Button(self.top)
        self.Top_Open.place(relx=0.629, rely=0.13, height=28, width=63)
        self.Top_Open.configure(command=on_OpenClick)
        self.Top_Open.configure(text='''Open''')
        self.Top_Open.configure(compound='left')

        self.Top_Digital1 = ttk.Button(self.top)
        self.Top_Digital1.place(relx=0.014, rely=0.587, height=28, width=83)
        self.Top_Digital1.configure(command=on_Digital1Click)
        self.Top_Digital1.configure(text='''Digital 1''')
        self.Top_Digital1.configure(compound='left')

        self.Top_MIDIin = ttk.Label(self.top)
        self.Top_MIDIin.place(relx=0.014, rely=0.033, height=23, width=64)
        self.Top_MIDIin.configure(font="-family {DejaVu Sans} -size 10")
        self.Top_MIDIin.configure(relief="flat")
        self.Top_MIDIin.configure(anchor='w')
        self.Top_MIDIin.configure(justify='left')
        self.Top_MIDIin.configure(text='''MIDI in''')
        self.Top_MIDIin.configure(compound='left')

        self.Top_Play = ttk.Button(self.top)
        self.Top_Play.place(relx=0.014, rely=0.457, height=28, width=83)
        self.Top_Play.configure(command=on_PlayClick)
        self.Top_Play.configure(text='''Play''')
        self.Top_Play.configure(compound='left')

        self.Top_Polytouch = ttk.Button(self.top)
        self.Top_Polytouch.place(relx=0.136, rely=0.457, height=28, width=83)
        self.Top_Polytouch.configure(command=on_PolytouchClick)
        self.Top_Polytouch.configure(text='''Polytouch''')
        self.Top_Polytouch.configure(compound='left')

        self.Top_Drums = ttk.Button(self.top)
        self.Top_Drums.place(relx=0.26, rely=0.587, height=28, width=85)
        self.Top_Drums.configure(command=on_DrumsClick)
        self.Top_Drums.configure(text='''Drums''')
        self.Top_Drums.configure(compound='left')

        self.Top_Analog = ttk.Button(self.top)
        self.Top_Analog.place(relx=0.383, rely=0.587, height=28, width=83)
        self.Top_Analog.configure(command=on_AnalogClick)
        self.Top_Analog.configure(text='''Analog''')
        self.Top_Analog.configure(compound='left')

        self.Top_Effects = ttk.Button(self.top)
        self.Top_Effects.place(relx=0.629, rely=0.587, height=28, width=83)
        self.Top_Effects.configure(command=on_EffectsClick)
        self.Top_Effects.configure(text='''Effects''')
        self.Top_Effects.configure(compound='left')

        self.Top_Arpeggio = ttk.Button(self.top)
        self.Top_Arpeggio.place(relx=0.751, rely=0.587, height=28, width=83)
        self.Top_Arpeggio.configure(command=on_ArpeggioClick)
        self.Top_Arpeggio.configure(text='''Arpeggio''')
        self.Top_Arpeggio.configure(compound='left')

        self.Top_Program = ttk.Button(self.top)
        self.Top_Program.place(relx=0.874, rely=0.587, height=28, width=83)
        self.Top_Program.configure(command=on_ProgramClick)
        self.Top_Program.configure(text='''Program''')
        self.Top_Program.configure(compound='left')

        self.Top_TExit = ttk.Button(self.top)
        self.Top_TExit.place(relx=0.874, rely=0.033, height=28, width=83)
        self.Top_TExit.configure(command=do_exit)
        self.Top_TExit.configure(text='''Exit''')
        self.Top_TExit.configure(compound='left')
        self.Top_TExit.configure(cursor="cross")

        self.Top_Close = ttk.Button(self.top)
        self.Top_Close.place(relx=0.724, rely=0.13, height=28, width=63)
        self.Top_Close.configure(command=on_CloseClick)
        self.Top_Close.configure(text='''Close''')
        self.Top_Close.configure(compound='left')

        self.Top_MIDIinVals = ttk.Combobox(self.top)
        self.Top_MIDIinVals.place(relx=0.136, rely=0.033, relheight=0.067
                , relwidth=0.243)
        self.Top_MIDIinVals.configure(font="-family {DejaVu Sans} -size 10")
        self.Top_MIDIinVals.configure(textvariable=self.MIDIin)
        self.Top_MIDIinVals.configure(cursor="xterm")

        self.mainSNote = ttk.Scale(self.top, from_=1, to=100)
        self.mainSNote.place(relx=0.262, rely=0.467, relheight=0.053
                , relwidth=0.357)
        self.mainSNote.configure(variable=self.TestNote)
        self.TestNote.set(40)
        self.mainSNote.configure(length="261")

        self.Top_Voice = ttk.Button(self.top)
        self.Top_Voice.place(relx=0.505, rely=0.587, height=28, width=83)
        self.Top_Voice.configure(command=on_VoiceClick)
        self.Top_Voice.configure(text='''Voice''')
        self.Top_Voice.configure(compound='left')

class Analog():
    def __init__(self, top=None):
        top.geometry("762x300+187+88")
        top.minsize(400, 200)
        top.maxsize(1905, 1050)
        top.resizable(1,  1)
        top.title("JD-Xi Analog")
        self.top = top
        self.Top_TExit = ttk.Button(self.top)
        self.Top_TExit.place(relx=0.874, rely=0.033, height=28, width=83)
        self.Top_TExit.configure(command=do_exit)
        self.Top_TExit.configure(text='''Exit''')
        self.Top_TExit.configure(compound='left')
        self.Top_TExit.configure(cursor="cross")



class Digital1():
    def __init__(self, top=None):
        top.geometry("762x300+187+88")
        top.minsize(400, 200)
        top.maxsize(1905, 1050)
        top.resizable(1,  1)
        top.title("JD-Xi Digital1")
        self.top = top
        self.Top_TExit = ttk.Button(self.top)
        self.Top_TExit.place(relx=0.874, rely=0.033, height=28, width=83)
        self.Top_TExit.configure(command=do_exit)
        self.Top_TExit.configure(text='''Exit''')
        self.Top_TExit.configure(compound='left')
        self.Top_TExit.configure(cursor="cross")

class Digital2():
    def __init__(self, top=None):
        top.geometry("762x300+187+88")
        top.minsize(400, 200)
        top.maxsize(1905, 1050)
        top.resizable(1,  1)
        top.title("JD-Xi Digital2")
        self.top = top
        self.Top_TExit = ttk.Button(self.top)
        self.Top_TExit.place(relx=0.874, rely=0.033, height=28, width=83)
        self.Top_TExit.configure(command=do_exit)
        self.Top_TExit.configure(text='''Exit''')
        self.Top_TExit.configure(compound='left')
        self.Top_TExit.configure(cursor="cross")

class Voice():
    def __init__(self, top=None):
        top.geometry("762x300+187+88")
        top.minsize(400, 200)
        top.maxsize(1905, 1050)
        top.resizable(1,  1)
        top.title("JD-Xi Voice")
        self.top = top
        self.Top_TExit = ttk.Button(self.top)
        self.Top_TExit.place(relx=0.874, rely=0.033, height=28, width=83)
        self.Top_TExit.configure(command=do_exit)
        self.Top_TExit.configure(text='''Exit''')
        self.Top_TExit.configure(compound='left')
        self.Top_TExit.configure(cursor="cross")


class Effects():
    def __init__(self, top=None):
        top.geometry("762x300+187+88")
        top.minsize(400, 200)
        top.maxsize(1905, 1050)
        top.resizable(1,  1)
        top.title("JD-Xi Effects")
        self.top = top
        self.Top_TExit = ttk.Button(self.top)
        self.Top_TExit.place(relx=0.874, rely=0.033, height=28, width=83)
        self.Top_TExit.configure(command=do_exit)
        self.Top_TExit.configure(text='''Exit''')
        self.Top_TExit.configure(compound='left')
        self.Top_TExit.configure(cursor="cross")

class ProgramController():
    def __init__(self, top=None):
        top.geometry("762x300+187+88")
        top.minsize(400, 200)
        top.maxsize(1905, 1050)
        top.resizable(1,  1)
        top.title("JD-Xi Arpeggio")
        self.top = top
        self.Top_TExit = ttk.Button(self.top)
        self.Top_TExit.place(relx=0.874, rely=0.033, height=28, width=83)
        self.Top_TExit.configure(command=do_exit)
        self.Top_TExit.configure(text='''Exit''')
        self.Top_TExit.configure(compound='left')
        self.Top_TExit.configure(cursor="cross")

class Program():
    def __init__(self, top=None):
        top.geometry("762x300+187+88")
        top.minsize(400, 200)
        top.maxsize(1905, 1050)
        top.resizable(1,  1)
        top.title("JD-Xi Program")
        self.top = top
        self.Top_TExit = ttk.Button(self.top)
        self.Top_TExit.place(relx=0.874, rely=0.033, height=28, width=83)
        self.Top_TExit.configure(command=do_exit)
        self.Top_TExit.configure(text='''Exit''')
        self.Top_TExit.configure(compound='left')
        self.Top_TExit.configure(cursor="cross")

class Drums():
    def __init__(self, top=None):
        top.geometry("762x300+187+88")
        top.minsize(400, 200)
        top.maxsize(1905, 1050)
        top.resizable(1,  1)
        top.title("JD-Xi Drums")
        self.top = top
        self.Top_TExit = ttk.Button(self.top)
        self.Top_TExit.place(relx=0.874, rely=0.033, height=28, width=83)
        self.Top_TExit.configure(command=do_exit)
        self.Top_TExit.configure(text='''Exit''')
        self.Top_TExit.configure(compound='left')
        self.Top_TExit.configure(cursor="cross")

        

def close_or_hide(*args, **kwargs):
    window=kwargs['window']
    if DEBUG:
        print('close_or_hide')
        print("Window:",window, "Title:", window.title())
        sys.stdout.flush()
#    print("event",event.widget)
    # check 
    if window!=root:
        window.withdraw()
    else:
        if messagebox.askokcancel("Quit JD-Xi manager", "Are you sure you want to quit JD-Xi manager?"):
            window.destroy()


def make_root_windows():
  global notesstring, defaultinstrument, instrumentlist
  global  w1, w2, w3, w4, w5, w6, w7, w8, w9, top, top_Analog, top_Digital1, top_Digital2, top_Voice, top_Effects, top_Arpeggio, top_Program, top_Drums

  # TODO!!! tk.theme(theme)

  top = root
  root.protocol( 'WM_DELETE_WINDOW' , lambda :close_or_hide(window=root))

  w1 = JDXi_manager(top=root,loc=(10,1),siz=(740, 350))
  # Creates a toplevel widget.
  top_Analog = tk.Toplevel(root)
  w2 = Analog(top_Analog)
  top_Analog.protocol( 'WM_DELETE_WINDOW' , lambda :close_or_hide(window=top_Analog))
  top_Digital1 = tk.Toplevel(root)
  w3 = Digital1(top_Digital1)
  top_Digital1.protocol( 'WM_DELETE_WINDOW' , lambda :close_or_hide(window=top_Digital1))
  top_Digital2 = tk.Toplevel(root)
  w4 = Digital2(top_Digital2)
  top_Digital2.protocol( 'WM_DELETE_WINDOW' , lambda :close_or_hide(window=top_Digital2))
  top_Voice = tk.Toplevel(root)
  w5 = Voice(top_Voice)
  top_Voice.protocol( 'WM_DELETE_WINDOW' , lambda :close_or_hide(window=top_Voice))
  top_Effects = tk.Toplevel(root)
  w6 = Effects(top_Effects)
  top_Effects.protocol( 'WM_DELETE_WINDOW' , lambda :close_or_hide(window=top_Effects))
  top_ProgramController = tk.Toplevel(root)
  w7 = ProgramController(top_ProgramController)
  top_ProgramController.protocol( 'WM_DELETE_WINDOW' , lambda :close_or_hide(window=top_ProgramController))
  top_Program = tk.Toplevel(root)
  w8 = Program(top_Program)
  top_Program.protocol( 'WM_DELETE_WINDOW' , lambda :close_or_hide(window=top_Program))
  top_Drums = tk.Toplevel(root)
  w9 = Drums(top_Drums)
  top_Drums.protocol( 'WM_DELETE_WINDOW' , lambda :close_or_hide(window=top_Drums))

  return 

def make_main_window(root, theme, loc, siz):
  global notesstring, defaultinstrument, instrumentlist
  # TODO!!! tk.theme(theme)
  
  menu_def = [['&Application', ['&Properties','E&xit']], ['&Help', ['&About']] ]
  right_click_menu_def = [[], ['Version', 'Nothing','Exit']]
  graph_right_click_menu_def = [[], ['Erase','Draw Line', 'Draw',['Circle', 'Rectangle', 'Image'], 'Exit']]
  l_list_column = [[
   tk.Image('png',filename='jd-xi-small.png', tooltip='JD-Xi Keyboard'),
             tk.Pusgh(),
   tk.Text('Prog Rx/Tx Ch',size=14, tooltip='Specifies the channel used to\ntransmit and receive MIDI messages for the program.'),
   tk.Combo(list(i for i in range(1,17)), default_value=16, key='-MAIN_COMBO-PC-', 
             readonly=True,enable_events=True,
             tooltip='Specifies the channel used to\ntransmit and receive MIDI messages for the program.'),
   tk.Text('                              ',key='-MAIN-ALERT-'),
   tk.Button('Exit', button_color=( 'red2','green2'),s=(8,1),font=('Arial',14,'bold'))
   ]]

  settings_layout= [[tk.Checkbox('Debug', default=True,enable_events=True, k='-DEBUG-')]]

  theme_layout = [[tk.Text("Choose theme")], [tk.Listbox(values = tk.theme_list(), size =(20, 12), 
                      key ='-THEME LISTBOX-',enable_events = True)], [tk.Button("Set Theme")]]
    
  log_layout =  [[tk.Text("All messages printed will go here.")],
              [tk.Multiline(size=(60,15), font='Courier 8', expand_x=True, expand_y=True, 
               write_only=True, 
               reroute_stdout=True, reroute_stderr=True, echo_stdout_stderr=True, 
               autoscroll=True, auto_refresh=True,key='-LOGMultiLine-')]
                      # [sg.Output(size=(60,15), font='Courier 8', expand_x=True, expand_y=True)]
                      ]
  tabs=[[tk.TabGroup(
       [[ tk.Tab('Settings', settings_layout),
          tk.Tab('Theme', theme_layout),
          tk.Tab('Output', log_layout,)]], key='-TAB GROUP-', expand_x=True, expand_y=True,enable_events=True),
     ]]

  layout = [
    [tk.MenubarCustom(menu_def, key='-MENU-',tearoff=True)],
    [tk.Column(l_list_column)],
    [tk.Text('MIDI in ',size=7), 
     tk.Combo(input_ports, default_value=input_ports[0], key='-MAIN_COMBO-INPUT-', 
             readonly=True,enable_events=True,size=30), 
     tk.Button('Reload',size=(0,2)),# button_color=(tk.YELLOWS[0], tk.BLUES[0])),
     tk.Button('Panic',size=(0,2)), #button_color=(tk.YELLOWS[0], tk.BLUES[0])),
     tk.Button('Open',size=(0,2)), #button_color=(tk.YELLOWS[0], tk.BLUES[0])),
     tk.Button('Close',size=(0,2)) #button_color=(tk.YELLOWS[0], tk.BLUES[0]))
    ],
    [tk.Text('MIDI out',size=7),tk.Combo(output_ports, default_value=output_ports[0], key='-MAIN_COMBO-OUTPUT-', 
            readonly=True,enable_events=True,size=30)],
    [tk.Text('Channel',size=7), 
     tk.Combo(digitalsynth+analogsynth+drums,default_value=drums[0], key='-MAIN_COMBO-channel-',  
             readonly=True,enable_events=True,size=20),
     tk.Text('Instrument',size=9),
     tk.Combo(instrumentlist, default_value=defaultinstrument, key='-MAIN_COMBO-instrument-', 
             readonly=True,enable_events=True,size=29)],
#  [tk.Combo([i for i in range(0,256)], default_value=1, key='-MAIN_COMBO-BANK-', readonly=True,enable_events=True)],

    [tk.Button('Play', size=(10,2), key='Play'),
     tk.B('Polytouch',size=(8,2),key='Poly'),
     tk.Slider(range=(36, 72), default_value=40, expand_x=True, enable_events=True, #param_tooltip=defaultinstrument,
     orientation='horizontal', key='-MAIN_SLpitch-',size=(20,8)),
     tk.Button('Test Sound',size=(10,2))],
    
    
    [tk.Button('Digital 1'),tk.Button('Digital 2'),tk.Button('Drums'),tk.Button('Analog'),
     tk.Button('Voice'),tk.Button('Effects'), tk.Button('Arpeggio'),tk.Button('Program')]
  ]
  
  layout +=tabs
 
  window = tk.Window(Manufacturer+' '+ devicename+" - "+PROCESS_NAME, layout, icon= music, #"jdxi.png", 
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


def main(*args):
    global DEBUG, CONFIG_FILE, ManufacturerSysExIDsFile
    global notesstring, testingnote, testingch, testingvolume, testingduration
    global input_ports, current_inport, current_outport, inport, outport
    global tonelistDS, tonelistAS, drumkitDR, presetprogramlist,presetprogramall
    global defaultinstrument, instrumentlist
    global Manufacturer, devicename
    global root

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
    # many things are not defined yet... So, call 7OF9...
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
        try:
            data = json.load(json_file)
        except:
            error_str=str("Don't know how to decode '"+  CONFIG_FILE+"' JSON file.")
            printdebug(sys._getframe().f_lineno, error_str)
            logger.error(error_str)
            stop_logger()
            sys.exit(6)  
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
        if 'DevName' in data:
            devicename=data['DevName']
        else:
            devicename='JD-Xi'
        if devicename in ['JD-Xi']:
            printdebug(sys._getframe().f_lineno, str(devicename+" is used device."))
            logger.info( devicename+" is used device.")
        else:
            error_str=str("Don't know how to use "+  devicename+" device.")
            printdebug(sys._getframe().f_lineno, error_str)
            logger.error(error_str)
            stop_logger()
            sys.exit(5)    

    if 'DeviceFamilyCode' in data:
      DeviceFamiliyCode=data['DeviceFamilyCode']
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
    else:
        error_str=str("Don't know how to configure MIDI channels.")
        printdebug(sys._getframe().f_lineno, error_str)
        logger.error(error_str)
        stop_logger()
        sys.exit(9)  
        
    if 'TONES_FILE' in data:
        TONES_FILE=data['TONES_FILE']
        # now, collect all tones data from file
        with open(TONES_FILE) as json_file:
            try:
                tonesdata = json.load(json_file)
            except:
                error_str=str("Don't know how to decode '"+  TONES_FILE+"' JSON file.")
                printdebug(sys._getframe().f_lineno, error_str)
                logger.error(error_str)
                stop_logger()
                sys.exit(7)  
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
    root = tk.Tk()
    # TODO!!! tk.theme('DarkBlue12')
    # TODO!!! 
    root.option_add('*tearOff', False)
    # TODO menu_help = Menu(menubar, name='help')
    # TODO menubar.add_cascade(menu=menu_help, label='Help')
    #main_window=make_main_window(tk.theme(),(10,1),(565, 575))
####    main_window=make_main_window(root, 'default',(10,1),(565, 575))
    make_root_windows()
    AnalogSynth=Analog_Synth()
    ret=AnalogSynth.get_data()
    ret=1
    if ret=='7OF9':
        c_thread = threading.Thread(target=delay_event, args=(w1.Top_Digital2, 15.0,'<ButtonPress>'), daemon=True)
        c_thread.start()
#    DigitalSynth1=Digital_Synth1()
    DigitalSynth1=Digital_Synth(baseaddress=[0x19,0x01,0x00],id='1')
    
    ret=DigitalSynth1.get_data()
    if ret=='7OF9':
        printdebug(sys._getframe().f_lineno, str("Cannot create digital synth 1 window."))
    # else:
    #     print(ret)

#    DigitalSynth2=Digital_Synth2()
    DigitalSynth2=Digital_Synth(baseaddress=[0x19,0x21,0x00],id='2')
    ret=DigitalSynth2.get_data()
    if ret=='7OF9':
        printdebug(sys._getframe().f_lineno, str("Cannot create digital synth 2 window."))

    SystemSetup=System_Setup()
    SystemSetup.get_data()
    printdebug(sys._getframe().f_lineno, str(SystemSetup.attributes))
    SystemCommon=System_Common()
    SystemCommon.get_data()
    printdebug(sys._getframe().f_lineno, str(SystemCommon.attributes))
    SystemController=System_Controller()
    SystemController.get_data()
    printdebug(sys._getframe().f_lineno, str(SystemController.attributes))
    ProgramCommon=Program_Common()
    ProgramCommon.get_data()
    printdebug(sys._getframe().f_lineno, str(ProgramCommon.attributes))
    ProgramVocalEffect=Program_Vocal_Effect()
    ProgramVocalEffect.get_data()
    printdebug(sys._getframe().f_lineno, str(ProgramVocalEffect.attributes))
    ProgramEffect1=Program_Effect1()
    ProgramEffect1.get_data()
    printdebug(sys._getframe().f_lineno, str(ProgramEffect1.attributes))
    ProgramDelay=Program_Delay()
    ProgramDelay.get_data()
    printdebug(sys._getframe().f_lineno, str(ProgramDelay.attributes))


    c_thread = threading.Thread(target=delay_event, args=(w1.Top_Digital2, 2.0,'<Button-1>'), daemon=True)
    c_thread.start()
    c_thread = threading.Thread(target=delay_event, args=(w1.Top_Digital2, 5.0,'<ButtonRelease-1>'), daemon=True)
    c_thread.start()


    c_thread = threading.Thread(target=delay_event, args=(w1.Top_Digital2, 10.0,'<Button-1>'), daemon=True)
    c_thread.start()
    c_thread = threading.Thread(target=delay_event, args=(w1.Top_Digital2, 15.0,'<ButtonRelease-1>'), daemon=True)
    c_thread.start()
    
    root.mainloop()
    port_panic()
#    port_close()
    stop_logger()
    sys.exit(0)    

    windows=[] #without main_window

    analog_window=make_analog_synth_window(AnalogSynth,tk.theme(),(585,10),(940, 975))
    windows.append(analog_window)
    digital1_window=make_digital_synth_window(DigitalSynth1,tk.theme(),(595,10),(940, 975))
    windows.append(digital1_window)
    digital2_window=make_digital_synth_window(DigitalSynth2,tk.theme(),(595,10),(940, 975))
    windows.append(digital2_window)
    
    effects_window=make_effects_window(tk.theme(),(1535,10),(350, 120))
    windows.append(effects_window)
    vocalFX_window=make_vocalFX_window(tk.theme(),(1535,165),(350, 120))
    windows.append(vocalFX_window)
    arpeggio_window= make_arpeggio_window(tk.theme(),(1535,320),(350, 120))
    windows.append(arpeggio_window)
    program_window=make_program_window(tk.theme(),(1535,475),(350, 280))
    windows.append(program_window)
    drums_window=make_drums_window(tk.theme(),(1535,765),(350, 280))
    windows.append(drums_window)

    for element in analog_window.element_list():
        if str(element.key).startswith('-AS_ONOFF-'):
            element.bind('<Enter>', ' Enter')
            element.bind('<Leave>', ' Leave')
        elif str(element.key).startswith('-AS_THREETEXT-'):
            element.bind('<Enter>', ' Enter')
            element.bind('<Leave>', ' Leave')

    for element in digital1_window.element_list():
        if str(element.key).startswith('-DS_1_ONOFF-'):
            element.bind('<Enter>', ' Enter')
            element.bind('<Leave>', ' Leave')

    for element in digital2_window.element_list():
        if str(element.key).startswith('-DS_2_ONOFF-'):
            element.bind('<Enter>', ' Enter')
            element.bind('<Leave>', ' Leave')

    for element in program_window.element_list():
        if str(element.key).startswith('-PROGRAM-ONOFF-'):
            element.bind('<Enter>', ' Enter')
            element.bind('<Leave>', ' Leave')

    while True:
        win, event, values = tk.read_all_windows(timeout=50)
#        event, values = main_window.read(timeout=50)
        if event == tk.WIN_CLOSED or event == 'Exit':
            if win in windows:
                       win.hide()
            else:
                for w in windows:
                    w.close()
                break
            continue
        if event is tk.TIMEOUT_KEY:
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
            send_sysex_DT1(AnalogSynth.sysexsetlist,AnalogSynth.attributes[attr][1],[int(values[event])])
        elif event.startswith('-DS_1_SLIDER-'):
            digital1_window[event.replace('-DS_1_SLIDER-','-DS_1_TEXT_SLIDER-')+'value'].update(int(values[event]))
            attr=event[len('-DS_1_SLIDER-'):-1]
            DigitalSynth1.set_attr(attr,[int(values[event])])
#            send_sysex_DT1(DigitalSynth1.sysexsetlist,send_data,[int(values[event])])
        elif event.startswith('-DS_2_SLIDER-'):
            digital2_window[event.replace('-DS_2_SLIDER-','-DS_2_TEXT_SLIDER-')+'value'].update(int(values[event]))
            attr=event[len('-DS_2_SLIDER-'):-1]
            DigitalSynth2.set_attr(attr,[int(values[event])])
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
                    value=analog_window[action[0]].metadata[2]
                else:
                    analog_window[action[0]].metadata[1]=1
                    value=analog_window[action[0]].metadata[3]
                send_sysex_DT1(AnalogSynth.sysexsetlist,int(AnalogSynth.attributes[attr][1]),[int(analog_window[action[0]].metadata[1])])
                AnalogSynth.attributes[attr][0]=analog_window[action[0]].metadata[1]
            analog_window[action[0]].update(image_data=onoff_data[index+2*analog_window[action[0]].metadata[1]],image_subsample=IMAGE_SUBSAMPLE)
        elif event.startswith('-DS_1_ONOFF-'):
            action = event.split(' ')
            attr=action[0][len('-DS_1_ONOFF-'):-1]
            if len(action)>1:
                index = 0 if action[1] == 'Leave' else 1
                digital1_window[action[0]].metadata[0] = index
            else:
                index=digital1_window[action[0]].metadata[0]
                if digital1_window[action[0]].metadata[1]:
                    digital1_window[action[0]].metadata[1]=0
                    value=digital1_window[action[0]].metadata[2]
                else:
                    digital1_window[action[0]].metadata[1]=1
                    value=digital1_window[action[0]].metadata[3]
                DigitalSynth1.set_attr(attr,[value])
#                send_sysex_DT1(AnalogSynth.sysexsetlist,int(AnalogSynth.attributes[attr][1]),[int(digital1_window[action[0]].metadata[1])])
#                DigitalSynth1.attributes[attr][0]=digital1_window[action[0]].metadata[1]
            digital1_window[action[0]].update(image_data=onoff_data[index+2*digital1_window[action[0]].metadata[1]],image_subsample=IMAGE_SUBSAMPLE)
        elif event.startswith('-DS_2_ONOFF-'):
            action = event.split(' ')
            attr=action[0][len('-DS_2_ONOFF-'):-1]
            if len(action)>1:
                index = 0 if action[1] == 'Leave' else 1
                digital2_window[action[0]].metadata[0] = index
            else:
                index=digital2_window[action[0]].metadata[0]
                if digital2_window[action[0]].metadata[1]:
                    digital2_window[action[0]].metadata[1]=0
                    value=digital2_window[action[0]].metadata[2]
                else:
                    digital2_window[action[0]].metadata[1]=1
                    value=digital2_window[action[0]].metadata[3]
                DigitalSynth2.set_attr(attr,[value])
#                send_sysex_DT1(AnalogSynth.sysexsetlist,int(AnalogSynth.attributes[attr][1]),[int(digital2_window[action[0]].metadata[1])])
#                DigitalSynth2.attributes[attr][0]=analog_window[action[0]].metadata[1]
            digital2_window[action[0]].update(image_data=onoff_data[index+2*digital2_window[action[0]].metadata[1]],image_subsample=IMAGE_SUBSAMPLE)
        elif event.startswith('-PROGRAM-ONOFF-'):
            action = event.split(' ')
            attr=action[0][len('-PROGRAM-ONOFF-'):-1]
            if len(action)>1:
                index = 0 if action[1] == 'Leave' else 1
                program_window[action[0]].metadata[0] = index
            else:
                index=program_window[action[0]].metadata[0]
                if program_window[action[0]].metadata[1]:
                    program_window[action[0]].metadata[1]=0
                else:
                    program_window[action[0]].metadata[1]=1
                    value=program_window[action[0]].metadata[3] #check this
            program_window[action[0]].update(image_data=onoff_data[index+2*program_window[action[0]].metadata[1]],image_subsample=IMAGE_SUBSAMPLE)
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
            send_sysex_DT1(AnalogSynth.sysexsetlist,int(AnalogSynth.attributes[attr][1]),[attr_value])
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
            send_sysex_DT1(AnalogSynth.sysexsetlist,int(AnalogSynth.attributes[attr][1]),[attr_value])
            
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
            analog_window=make_analog_synth_window(AnalogSynth,tk.theme(),(585,10),(940, 975))
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
        elif event=="PopupARPEGGIO":
#            AnalogSynth.push_data()
            #            print(AnalogSynth.attributes['Name'])
            print(AnalogSynth.attributes)
            print('AnalogSynthV portamento:',int(AnalogSynth.attributes['PortamentoTime'][0]))
#            print('AnalogWindow portamento:',int(analog_window['-AS_SLIDER-PortamentoTime-']))
            print(values)
            analog_window['-AS_TEXT_SLIDER-PortamentoTime-value'].update(
                int(AnalogSynth.attributes['PortamentoTime'][0]))
            AnalogSynth.get_data()
            update_analog_synth_window(AnalogSynth, analog_window)
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
                                                   background_color=tk.theme_element_background_color())
                main_window.refresh()
                c_thread = threading.Thread(target=delayed_event, 
                                            args=(main_window, 2.0,'-NO_DEVICE-','on'), daemon=True)
                c_thread.start()
            elif values['-NO_DEVICE-']=='inactive':
                main_window['-MAIN-ALERT-'].update('                              ', 
                                                   background_color=tk.theme_element_background_color())
             
        elif event=='Activate program':
            attr_value=program_window['-PROGRAM-LIST-'].widget.current()
#            control_change(15,'Bank Select',int(values['-PROGRAM-LIST-']))

            control_change(15,'Bank Select',int(attr_value),user=program_window['-PROGRAM-ONOFF-user-'].metadata[1])
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
        elif event == 'Digital 1':
            digital1_window.hide()
            digital1_window.un_hide()
            continue
        elif event == 'Digital 2':
            digital2_window.hide()
            digital2_window.un_hide()
            continue
        elif event == 'Drums':
            drums_window.hide()
            drums_window.un_hide()
            continue
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
