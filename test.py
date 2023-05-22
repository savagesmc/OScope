#!/usr/bin/env python3

import vxi11
import argparse
from time import sleep
import numpy as np

debug = False

def hexdump( src, length=16, sep='.' ):
    '''
    @brief Return {src} in hex dump.
    @param[in] length	{Int} Nb Bytes by row.
    @param[in] sep		{Char} For the text part, {sep} will be used for non ASCII char.
    @return {Str} The hexdump
    @note Full support for python2 and python3 !
    '''
    result = []

    # Python3 support
    try:
        xrange(0,1);
    except NameError:
        xrange = range;

    for i in xrange(0, len(src), length):
        subSrc = src[i:i+length];
        hexa = '';
        isMiddle = False;
        for h in xrange(0,len(subSrc)):
            if h == length/2:
                hexa += ' ';
            h = subSrc[h];
            if not isinstance(h, int):
                h = ord(h);
            h = hex(h).replace('0x','');
            if len(h) == 1:
                h = '0'+h;
            hexa += h+' ';
        hexa = hexa.strip(' ');
        text = '';
        for c in subSrc:
            if not isinstance(c, int):
                c = ord(c);
            if 0x20 <= c < 0x7F:
                text += chr(c);
            else:
                text += sep;
        result.append(('%08X:  %-'+str(length*(2+1)+1)+'s  |%s|') % (i, hexa, text));

    return '\n'.join(result);

def decodeSkew(v):
    return float(v[:-2])

class Scope:

    devNumChanMap = {
        "SDS1102X-E" : 2,
        "SDS1104X-E" : 4,
        "SDS1202X-E" : 2,
        "SDS1204X-E" : 4,
    }

    chFieldTypeMap = {
        "ATTN" : float,
        "BWL" : str,
        "CPL" : str,
        "OFST" : float,
        "SKEW" : decodeSkew,
        "TRA" : str,
        "UNIT" : str,
        "VDIV" : float,
        "INVS" : str
    }

    acqFieldTypeMap = {
        "SAST" : str,
        "SARA" : str,
    }

    trFieldTypeMap = {
        "TRCP" : str,
        "TRDL" : str,
        "TRLV" : str,
        "TRMD" : str,
        "TRSE" : str,
        "TRWI" : str,
        "TRPA" : str
    }

    inrFlags = [
        "NewSigAcq",
        "ScrDumpTerm",
        "RtnToLocal",
        "DataTimeout",
        "SegAcquired",
        "N/A",
        "MemCardFull",
        "MemCardSwapped",
        "WFA_ProcComplete",
        "WFB_ProcComplete",
        "WFC_ProcComplete",
        "WFD_ProcComplete",
        "Pass/Fail Test",
        "TrigReady",
        "N/A",
        "N/A"
    ]

    def queryValue(self, vIdentifier, dtype=str):
        chdr = self.instr.ask("CHDR?")
        self.instr.write("CHDR OFF")
        v = dtype(self.instr.ask(f"{vIdentifier}?"))
        self.instr.write(chdr)
        return v

    def setValue(self, vIdentifier, value):
        chdr = self.instr.ask("CHDR?")
        self.instr.write("CHDR OFF")
        self.instr.write(f"{vIdentifier} {value}")
        self.instr.write(chdr)

    def cmdComplete(self):
        v = self.queryValue("*OPC")
        return v

    def __init__(self, ip):
        self.instr =  vxi11.Instrument(args.ip)
        self.idn = self.getIdn()
        self.instrname = self.idn.split(',')[1]
        self.numChannels = Scope.devNumChanMap[self.instrname] \
                if self.instrname in Scope.devNumChanMap.keys() else 1

    def reset(self):
        self.instr.write("*RST")
        sleep(20)
        return self.cmdComplete()

    '''
    Scope level control functions
    '''
    def getIdn(self):
        return self.queryValue("*IDN")

    def getInr(self):
        inr = self.queryValue("INR", dtype=int)
        r = []
        for i in range(16):
            if inr & (1<<i):
                r.append(Scope.inrFlags[i])
        return r

    def getTimeDiv(self):
        return self.queryValue("TDIV", dtype=float)

    def setTimeDiv(self, val):
        self.setValue("TDIV", val)
        return self.cmdComplete()

    def getSampRate(self):
        return self.queryValue("SARA", dtype=float)

    '''
    Acquisition control functions
    '''
    def getAcqConfig(self):
        print("getAcqConfig")
        result = {
            key:self.queryValue(iden) \
                for key in self.acqFieldMap.keys()
        }
        return result

    '''
    Triggering control functions
    '''
    def getTriggerConfig(self):
        result = {
            key:self.queryValue(key) \
                for key in Scope.trFieldTypeMap.keys()
        }
        return result

    def getTriggerChannel(self):
        trse = self.queryValue("TRSE").split(',')
        chan = trse[2].replace('C', '')
        return chan

    def setTriggerLevel(self, lvl):
        chan = self.getTriggerChannel()
        self.instr.write(f"TRLV {lvl}")

    def setTriggerChannel(self, ch):
        self.instr.write(f"TRSE EDGE,SR,C{ch},HT,OFF")

    def setTriggerMode(self, mode):
        self.instr.write(f"TRMD {mode}")

    def stopTrigger(self):
        self.setTriggerMode("STOP")

    def armTrigger(self, mode='SINGLE'):
        self.setTriggerMode(mode)

    '''
    Channel control functions
    '''
    def queryChannelValue(self, chan, vIdentifier):
        qstr = f"C{chan}:{vIdentifier}"
        r = self.queryValue(qstr,
                dtype = Scope.chFieldTypeMap[vIdentifier])
        return r

    def setChannelValue(self, chan, vIdentifier, val):
        vstr = f"C{chan}:{vIdentifier} {val}"
        self.instr.write(vstr)

    def activeChannels(self):
        return [scope.queryChannelValue(ch+1, 'TRA') for ch in range(self.numChannels)]

    def activateChannel(self, chan):
        scope.setChannelValue(chan, 'TRA', 'ON')

    def deactivateChannel(self, chan):
        scope.setChannelValue(chan, 'TRA', 'OFF')

    def getChannelConfig(self, idx):
        result = {
            iden:self.queryChannelValue(idx, iden) \
                for iden in Scope.chFieldTypeMap.keys()
        }
        return result

    def setChannelConfig(self, values):
        for key,val in values.items():
            self.setChannelValue(key, val)

    '''
    sparsing == 0:
                1:

    wfType   == 0: points on screen
                1: points from memory
    '''
    def setupWaveform(self, firstPoint=0, numPoints=0, sparsing=0, wfType=0):
        setupStr = f"WFSU SP,{sparsing},NP,{numPoints},FP,{firstPoint}"
        self.instr.write(setupStr)
        if debug:
            print(f"sent {setupStr}")
        #self.instr.write(f"WFSU TYPE,{wfType}")
        #if debug:
        #    print(f"sent WFSU TYPE,{wfType}")

    def getWaveform(self, chan):
        self.instr.write(f"C{chan}:WF? DAT2")
        r = self.instr.read_raw()
        idx1=r.index(b',')
        st=r.index(b'#9')+2
        en=st+9
        l = int(r[st:en].decode("utf-8"))
        if 'DAT2' not in str(r[:idx1]):
            print("Error, did not receive DAT2 waveform.")
            return
        chanCfg = self.getChannelConfig(chan)
        st = len(r) - l - 2
        vdiv = chanCfg['VDIV']
        offset = chanCfg['OFST']
        tdiv = self.getTimeDiv()
        srate = self.getSampRate()
        def toVolts(b):
            i = int(b) if b < 127 else int(b)-256
            return float(i)*(vdiv/25)-offset
        def toTime(i):
            return
        samps = np.array([toVolts(v) for v in r[st:-2]])
        times = np.array([-tdiv * 7 + i * (1/srate) for i in range(len(samps))])
        return samps, times

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--ip", required=True,
            help="ip of instrument")
    parser.add_argument("-r", "--reset", action='store_true',
            help="reset all scope settings")
    parser.add_argument("--configure", action='store_true',
            help="configure scope settings")
    parser.add_argument("--capture", action='store_true',
            help="capture samples")
    parser.add_argument("-d", "--debug", default=False,
            action='store_true', help="increase output verbosity")
    args = parser.parse_args()

    debug = args.debug
    scope = Scope(args.ip)

    if args.reset:
        if debug:
            print(f"Resetting Scope to Clean Settings")
        scope.reset()
        sleep(30)
        if debug:
            print(f"Reset complete")

    def printInr():
        m = scope.getInr()
        found = False
        s = "INR: "
        for i in range(len(m)):
            s += m[i]
            if i < (len(m)-1):
                found = True
                s += ','
        if found and debug:
            print(s)
        return m

    def printStats():
        print(f"IDN:           {scope.idn}")
        print(f"Instrument:    {scope.instrname}")
        print(f"Channels:      {scope.numChannels} | {scope.activeChannels()} ")
        print(f"Time Div:      {scope.getTimeDiv()}")
        print(f"Samp Rate:     {scope.getSampRate()}")
        print(f"ACQUIRE_WAY:   {scope.queryValue('ACQUIRE_WAY')}")
        print(f"Trig Config:   {scope.getTriggerConfig()}")
        for c in range(scope.numChannels):
            print(f"Chan {c+1}:        {scope.getChannelConfig(c+1)}")
        printInr()
        print(f"Cmd Complete:  {scope.cmdComplete()}")

    if debug:
        printStats()

    if args.configure:
        # Disable trace #4
        scope.deactivateChannel(4)
        if debug:
            print(f"Deactivate Channel 4")

        scope.setTimeDiv(10e-6)

        for chan in range(3):
            scope.setChannelValue(chan+1, 'ATTN', '10')
            scope.setChannelValue(chan+1, 'VDIV', '1')
            scope.setChannelValue(chan+1, 'OFST', '-3')

        trigChan = 1
        scope.setTriggerChannel(trigChan)
        scope.setTriggerLevel(0.15)
        scope.setTriggerMode("SINGLE")
        for m in scope.getInr():
            print(f"{m}")

        scope.setupWaveform()

        if debug:
            printStats()

    if args.capture:

        def risingEdgeTime(samps, times, lvl):
            idx = np.argmax(samps > lvl)
            return times[idx]

        def writeData(fname, data):
            np.savetxt(fname, data)

        num = 0
        de1 = []
        de2 = []
        lastLog = 0

        while True:
            scope.armTrigger()
            m = printInr()
            while "NewSigAcq" not in m:
                sleep(0.05)
                m = printInr()
            sleep(1.5)
            num += 1
            wf1, t1 = scope.getWaveform(1)
            wf2, t2 = scope.getWaveform(2)
            wf3, t3 = scope.getWaveform(3)
            re1 = risingEdgeTime(wf1, t1, 1.5)
            re2 = risingEdgeTime(wf2, t2, 1.5)
            re3 = risingEdgeTime(wf3, t3, 1.5)
            de1.append(re2)
            a = np.array(de1)
            avg = np.mean(a)
            st = np.std(a)
            de2.append(re3)
            b = np.array(de2)
            avg_pps = np.mean(b)
            st_pps = np.std(b)
            print(f"{num:7}  ublox: {re1:15.10f} pps: {re3:15.10f} avg: {avg_pps:15.10f} std: {st_pps:15.10f} ptp: {re2:15.10f} avg: {avg:15.10f} std: {st:15.10f}")
            if (num-lastLog) > 60:
                writeData("ptp.txt", a)
                writeData("chil.txt", b)
                lastLog = num
