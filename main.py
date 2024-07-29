#!/bin/env python
# we'll need liblo
# and some yaml parsing

# lets just get it done and not make it perfect


# uses python-pyyaml
# and python-oscpy

import yaml
import oscpy
from time import sleep

from enum import Enum
MidiStatus = Enum('MidiStatus',['ControlChange','NoteOnOff'])

# validate
def validateChannel(x):
    if not isinstance(x,int):
        raise TypeError(f"expected int, got {type(x)}")
    if x > 15 or x < 0:
        raise ValueError(f"channel must be in the range [0..15], got {x}")
    return x
def validateUint7(x):
    if not isinstance(x,int):
        raise TypeError(f"expected int, got {type(x)}")
    if x > 127 or x < 0:
        raise ValueError(f"channel must be in the range [0..127], got {x}")
    return x

def validateOscAddress(x):
    if not isinstance(x,str):
        raise TypeError(f"expected str, got {type(x)}")
    #todo make sure it parses as an address
    return x

class Input:
    def __init__(self, inp):
        self.channel = validateChannel(inp["channel"])
        if "cc" in inp:
            if "note" in inp:
                raise TypeError(f"only one of {cc,note} can be specified")
            self.kind = MidiStatus.ControlChange
            self.cc = validateUint7(inp["cc"])
            return
        if "note" in inp:
            self.kind = MidiStatus.NoteOnOff
            self.note = validateUint7(inp["note"])
class Output:
    def __init__(self,inp):
        self.path = validateOscAddress(inp["path"])

class Mapping:
    def __init__(self, inp):
        self.input = Input(inp["input"])
        self.output = Output(inp["output"])

#=============================================================
# we keep track of all the values of interest
# its a list of osc messages
valuesOfInterest = {}

#=============================================================
# osc server for control
# commands:
#   /reloadConfig
#       re-reads mapping.yaml
#   /load [i]
#       load all values saved in data/save{i}.yaml and sends them as osc messages
#   /save [i]
#       saves all current values to data/save{i}.yaml

# the address of the machine running badness
address = "127.0.0.1"
port = 8000

osc = OSCThreadServer()
osc.listen(default=True,encoding='ascii')

@osc.address(b'/load')
def loadValues(pageNumber):
    print(f"loading {pageNumber}.yaml")
    with open(f"{pageNumber}.yaml",'r') as file:
        data = yaml.safe_load(file)
        osc.send_bundle(data.items(),address,port)#takes a list of (address,[values...])
        # unclear what we do if the set of values we just loaded is different from the set we have in memory
        # safest is probably add all the new values to the set
        for address,values in data:
            valuesOfInterest[address] = values

@osc.address(b'/save')
    print(f"saving current values to {pageNumber}.yaml")
    with open(f"{pageNumber}.yaml",'w') as file:
        yaml.dump(valuesOfInterest)

# global config is a list of Mappings from input to output
yamlFilePath = "../mapping.yaml"
# map from Input to Output
input2output = {}
# map from Output to Input
output2input = {}

@osc.address(u'/reloadConfig')
def reloadConfig():
    with open(yamlFilePath, 'r') as file:
        parsed_data = yaml.safe_load(file)
    for item in parsed_data:
        inout = Mapping(item)
        input2output[inout.input] = inout.output
        output2input[inout.output] = inout.input

#===========================================================

#our midi input section
import rtmidi
import rtmidi.midiconstants

midiIn = rtmidi.midiIn()
#midiOut = rtmidi.midiOut()
available_ports = midiIn.get_ports()
# we cant just claim all of them because maybe theres routing going on
# so it has to be configurable somehow
# TODO

midiInputPorts = available_ports

#at the moment, we dont differentiate between midi devices, but that could be passed in
def midiCallback(event):
    message, deltatime = event

    if message[0] & 0xF0 == NOTE_ON:
        channel = message[0] & 0x0F
        note = message[1] & 0x7F
        velocity = message[2] & 0x7F
        inp = Input({"channel":channel,"note":note})
        if inp in input2output:
            output = input2output[inp]
            osc.send_message(output.path,velocity)
            valuesOfInterest[output.path] = velocity
    else if message[0] & 0xF0 == NOTE_OFF:
        channel = message[0] & 0x0F
        note = message[1] & 0x7F
        velocity = message[2] & 0x7F
        inp = Input({"channel":channel,"note":note})
        if inp in input2output:
            output = input2output[inp]
            osc.send_message(output.path,velocity)
            valuesOfInterest[output.path] = velocity
    else if message[0] & 0xF0 == CONTROL_CHANGE:
        channel = message[0] & 0x0F
        cc = message[1] & 0x7F
        value = message[2] & 0x7F
        inp = Input({"channel":channel,"cc":cc})
        if inp in input2output:
            output = input2output[inp]
            osc.send_message(output.path,value)
            valuesOfInterest[output.path] = velocity
    # get channel #wtf do we really need to do this crap?
    # yikes
    else:
        raise NotImplementedError(f"midi status type {message[0] >> 4} not implemented")

#=============================================================

midiInputs = [open_midiinput(port)[0] for port in midiInputPorts]
for midiIn in midiInputs:
  midiIn.set_callback(midiCallback)

# this thread has nothing to do
while True:
    sleep(1)
