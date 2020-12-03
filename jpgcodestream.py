# -*- coding: utf-8 -*-
"""
JPEG codestream-parser (All-JPEG Codestream/File Format Parser Tools)
See LICENCE.txt for copyright and licensing conditions.
"""

import sys

from jp2utils import *
from jpgxtbox import *
from jp2box import *
from jp2file import *

#
# Some Exceptions
#

class InvalidMarker(JP2Error):
    def __init__(self, marker):
        JP2Error.__init__(self, 'marker 0xff%s can\'t appear here' % (marker))
        self.marker = marker

class InvalidSizedMarker(JP2Error):
    def __init__(self, marker):
        JP2Error.__init__(self, 'invalid sized marker %s' % (marker))
        self.marker = marker

class InvalidMarkerField(JP2Error):
    def __init__(self, marker, field):
        JP2Error.__init__(self, 'invalid field %s in marker %s' % (field, marker))
        self.marker = marker
        self.field  = field

class RequiredMarkerMissing(JP2Error):
    def __init__(self, marker):
        JP2Error.__init__(self, 'required marker 0xff%s missing' % (marker))
        self.marker = marker

class UnexpectedEOC(JP2Error):
    def __init__(self):
        JP2Error.__init__(self, 'unexpected end of codestream')

class MisplacedData(JP2Error):
    def __init__(self):
        JP2Error.__init__(self, 'marker expected')

#
# The Codestream Class
#

class JPGCodestream:
    def __init__(self, indent = 0, hook = None, offset = 0):
        self.indent = indent
        self.datacount = 0
        self.bytecount = 0
        self.offset    = offset
        self.markerpos = 0
        self.frametype = 0
        self.c0        = 0
        self.c1        = 0
        self.boxlist   = BoxList()
        if hook == None:
            self.superhook = superbox_hook
        else:
            self.superhook = hook

    def print_indent(self, buffer, nl = 1):
        print_indent(buffer, self.indent, nl)

    def new_marker(self, name, description):
        self.print_indent("%-8s: New marker: %s (%s)" % \
                          (str(self.markerpos),name, description))
        print
        self.indent = self.indent + 1
        self.headers = []

    def end_marker(self):
        self.flush_marker()
        self.indent = self.indent - 1
        print

    def flush_marker(self):
        if len(self.headers) > 0:
            maxlen = 0
            for header in self.headers:
                maxlen = max(maxlen, len(header[0]))
            for header in self.headers:
                s = ""
                for i in range(maxlen - len(header[0])):
                    s = s + " "
                self.print_indent("%s%s : %s" % (header[0], s, header[1]))
            print
            self.headers = []

    def load_marker(self, file, marker):
        mrk    = ordw(marker)
        if (mrk >= 0xffd0 and mrk <= 0xffd9):
            self.buffer = marker
        elif mrk >= 0xffc0 or mrk == 0xffb1 or mrk == 0xffb2 or mrk == 0xffb3 or mrk == 0xffb9 or mrk == 0xffba or mrk == 0xffbb:
            size   = file.read(2)
            ln     = ordw(size)
            if (ln < 2):
                raise InvalidSizedMarker("Marker too short")
            self.buffer = marker + size + file.read(ln-2)
            if len(self.buffer) != ln + 2:
                raise UnexpectedEOC()
        else:
            raise MisplacedData()
        self.bytecount  = self.bytecount + len(self.buffer)
        self.pos        = 0
        
    def load_buffer(self, file):
        self.markerpos = self.offset
        marker = file.read(2)
        while len(marker) == 2 and ordw(marker) == 0xffff:
            self.offset    = self.offset + 1
            self.markerpos = self.markerpos + 1
            marker         = chr(0xff) + file.read(1)
        if len(marker) == 0:
            self.buffer = []
        else:  
            if len(marker) < 2:
                raise UnexpectedEOC()
            self.load_marker(file,marker)
            self.offset = self.offset + len(self.buffer)

    def parse_DQT(self):
        self.new_marker("DQT", "Define quantization table")
        self.pos = 4
        while self.pos < len(self.buffer):
            tq = ord(self.buffer[self.pos:self.pos + 1])
            self.pos = self.pos + 1
            pq = tq >> 4
            tq = tq & 15
            if pq == 0:
                ntry = "byte"
            elif pq == 1:
                ntry = "word"
            else:
                ntry = "invalid"
            self.print_indent("Entry size          : %s" % ntry)
            self.print_indent("Table destination   : %d" % tq)
            q = []
            for i in range(64):
                if pq == 0:
                    q = q + [ord(self.buffer[self.pos:self.pos + 1])]
                    self.pos = self.pos + 1
                elif pq == 1:
                    q = q + [ordw(self.buffer[self.pos:self.pos + 2])]
                    self.pos = self.pos + 2
                else:
                    q = q + [0]
            scanorder =  [0,  1,  5,  6, 14, 15, 27, 28,
                          2,  4,  7, 13, 16, 26, 29, 42,
                          3,  8, 12, 17, 25, 30, 41, 43,
                          9, 11, 18, 24, 31, 40, 44, 53,
                          10, 19, 23, 32, 39, 45, 52, 54,
                          20, 22, 33, 38, 46, 51, 55, 60,
                          21, 34, 37, 47, 50, 56, 59, 61,
                          35, 36, 48, 49, 57, 58, 62, 63]
            self.print_indent("Quantization Matrix : ")
            for y in range(8):
                line = ""
                for x in range(8):
                    line = "%s %5d" % (line,q[scanorder[x + y * 8]])
                self.print_indent(line)
        self.end_marker()

    def parse_DAC(self):
        self.new_marker("DAC", "Define arithmetic coding conditioning")
        self.pos = 4
        while self.pos < len(self.buffer):
            tc = ord(self.buffer[self.pos:self.pos+1])
            if (tc >> 4) == 0:
                hclass = "dc"
            elif (tc >> 4) == 1:
                hclass = "ac"
            else:
                hclass = "invalid"
            self.print_indent("AC coding table class     : %s" % hclass)
            self.print_indent("AC coding destination     : %d" % (tc & 0x0f))
            self.pos = self.pos + 1
            cond = ord(self.buffer[self.pos:self.pos+1])
            self.pos = self.pos + 1
            if (tc >> 4) == 0:
                self.print_indent("   Lower Amplitude DC     : %d" % (cond & 0x0f))
                self.print_indent("   Upper Amplitude DC     : %d" % (cond >> 4  ))
            elif (tc >> 4) == 1:
                self.print_indent("   Block End AC           : %d" % cond)
        self.end_marker()
        
    def parse_DHT(self):
        self.new_marker("DHT", "Define huffman table")
        self.pos = 4
        while self.pos < len(self.buffer):
            tc = ord(self.buffer[self.pos:self.pos+1])
            if (tc >> 4) == 0:
                hclass = "dc"
            elif (tc >> 4) == 1:
                hclass = "ac"
            else:
                hclass = "invalid"
            self.print_indent("Huffman table class       : %s" % hclass)
            self.print_indent("Huffman table destination : %d" % (tc & 0x0f))
            self.pos = self.pos + 1
            ln = []
            for i in range(16):
                ln = ln + [ord(self.buffer[self.pos:self.pos + 1])]
                self.pos = self.pos + 1
            for i in range(16):
                v = []
                for j in range(ln[i]):
                    v = v + [ord(self.buffer[self.pos:self.pos + 1])]
                    self.pos = self.pos + 1
                if ln[i] > 0:
                    self.print_indent("%d symbols of size %2d        : %s" % (len(v),i+1,str(v)))
            print
        self.end_marker()

    def parse_scan(self,file):
        self.new_marker("SOS", "Start of Scan")
        if len(self.buffer) < 2+2+1+1:
            raise InvalidSizedMarker("SOS")
        ns = ord(self.buffer[4:5])
        if len(self.buffer) != 2 + 6 + 2*ns:
            raise InvalidSizedMarker("SOS")
        self.print_indent("Number of Components : %d" % ns)
        self.pos = 5
        for i in range(ns):
            self.print_indent("Component % d : %d" % (i,ord(self.buffer[self.pos:self.pos + 1])))
            self.pos = self.pos + 1
            table = ord(self.buffer[self.pos:self.pos + 1])
            if self.frametype == 0xfff7:
                self.print_indent("Mapping %d    : %d" % (i,table))
            else:
                dc    = table >> 4
                ac    = table & 0x0f
                self.print_indent("DC table %d   : %d" % (i,dc))
                if self.frametype == 0xffc3 or self.frametype == 0xffc7 or self.frametype == 0xffcb or self.frametype == 0xffcf:
                    self.print_indent("Reserved %d   : %d" % (i,ac))
                else:
                    self.print_indent("AC table %d   : %d" % (i,ac))
            self.pos = self.pos + 1
        sstart = ord(self.buffer[self.pos:self.pos + 1])
        sstop  = ord(self.buffer[self.pos+1:self.pos + 2])
        self.pos = self.pos + 2
        if self.frametype == 0xfff7:
            self.print_indent("Near         : %d" % sstart)
            if sstop == 0:
                scantype = "plane interleaved"
            elif sstop == 1:
                scantype = "line interleaved"
            elif sstop == 2:
                scantype = "sample interleaved"
            else:
                scantype = "invalid, type %d" % sstop
            self.print_indent("Scan type    : %s" % scantype)
        elif self.frametype == 0xffc3 or self.frametype == 0xffc7 or self.frametype == 0xffcb or self.frametype == 0xffcf:
            self.print_indent("Predictor    : %d" % sstart)
            self.print_indent("Reserved     : %d" % sstop)
        else:
            self.print_indent("Scan start   : %d" % sstart)
            self.print_indent("Scan stop    : %d" % sstop)
        ah = ord(self.buffer[self.pos:self.pos + 1])
        al = ah & 0x0f
        ah = ah >> 4
        self.print_indent("Shift high   : %d" % ah)
        self.print_indent("Shift low    : %d" % al)
        marker = self.parse_data(file,self.frametype == 0xfff7)
        self.end_marker()
        return marker

    def parse_frame(self,file,process):
        if ordw(self.buffer) == 0xffde:
            self.new_marker("DHP","Define hierarchical process")
        else:
            self.new_marker("SOF","Start of frame, type: %s" % process)

        prec = ord(self.buffer[4:5])
        self.print_indent("Frame bit precision : %d" % prec)
        hei  = ordw(self.buffer[5:7])
        wid  = ordw(self.buffer[7:9])
        self.print_indent("Frame width         : %d" % wid)
        self.print_indent("Frame height        : %d" % hei)
        dep  = ord(self.buffer[9:10])
        self.print_indent("Depth               : %d" % dep)
        self.pos = 10
        for i in range(dep):
            ci = ord(self.buffer[self.pos:self.pos+1])
            self.print_indent("Component Id        : %d" % ci)
            mcu = ord(self.buffer[self.pos+1:self.pos+2])
            self.print_indent("MCU Width           : %d" % (mcu & 0x0f))
            self.print_indent("MCU Height          : %d" % (mcu >> 4))
            qnt = ord(self.buffer[self.pos+2:self.pos+3])
            self.print_indent("Quantization Table  : %d" % qnt)
            self.pos = self.pos + 3
        if ordw(self.buffer) != 0xffde:
            print
            self.frametype = ordw(self.buffer)
            self.load_buffer(file)
            marker = ordw(self.buffer)
            while marker == 0xffc4 or marker == 0xffcc or marker >= 0xffd0:
                if marker == 0xffda:
                    marker = self.parse_scan(file)
                    if marker == 0xffdc:
                        self.load_buffer(file)
                        self.parse_DNL()
                        marker = ordw(file.read(2))
                        file.seek(self.offset)
                    if marker == 0xffdf or marker == 0xffd9:
                        break
                else:
                    self.parse_table()
                self.load_buffer(file)
                marker = ordw(self.buffer)
        self.end_marker()

    def parse_APP(self,idx):
        if idx == 11 and self.buffer[4:6] == "JP":
            self.new_marker("APP11","JPEG XT Extension Marker")
            segment=BoxSegment(self.buffer,self.offset)
            self.boxlist.addBoxSegment(segment)
            if self.boxlist.isComplete(segment):
                box=self.boxlist.toBox(segment,self.indent + 1)
                box.parse(self.superhook)
        else:
            self.new_marker(("APP%x" % idx),("Application marker #%d" % idx))
            if len(self.buffer) < 256:
                print_hex(self.buffer)
        self.end_marker()
        
    def parse_COM(self):
        self.new_marker("COM","Comment marker")
        if len(self.buffer) < 256:
            print_hex(self.buffer)
        self.end_marker()
        
    def parse_EXP(self):
        self.new_marker("EXP","Frame Expansion marker")
        ehv = ord(self.buffer[4:5])
        self.print_indent("Horizontal expansion : %d" % (ehv >> 4))
        self.print_indent("Vertical   expansion : %d" % (ehv & 0x0f))
        self.end_marker()

    def parse_DRI(self):
        self.new_marker("DRI","Define restart interval")
        ri = ordw(self.buffer[4:6])
        self.print_indent("Restart interval     : %d" % ri)
        self.end_marker()

    def parse_DNL(self):
        self.new_marker("DNL","Define number of lines")
        nl = ordw(self.buffer[4:6])
        self.print_indent("Image height         : %d" % nl)
        self.end_marker()
         
    def parse_table(self):
        marker = ordw(self.buffer)
        if marker == 0xffc4:
            self.parse_DHT()
        elif marker == 0xffcc:
            self.parse_DAC()
        elif marker == 0xffdb:
            self.parse_DQT()
        elif marker == 0xffdd:
            self.parse_DRI()
        elif marker == 0xffdf:
            self.parse_EXP()
        elif marker == 0xffdc:
            self.parse_DNL()
        elif marker >= 0xffe0 and marker <= 0xffef:
            self.parse_APP(ordw(self.buffer) - 0xffe0)
        elif marker == 0xfffe:
            self.parse_COM()
        elif marker == 0xffd8:
            self.new_marker("SOI","Start of image")
            self.end_marker()
        elif marker == 0xffd9:
            self.new_marker("EOI","End of image")
            self.end_marker()
        elif marker >= 0xff01:
            self.new_marker("???","Unknown marker %04x" % marker)
            if len(self.buffer) < 256:
                print_hex(self.buffer)
            self.end_marker()

    def stream_parse(self, file, startpos):
        self.pos       = 0
        self.datacount = 0
        self.bytecount = 0
        self.offset    = startpos

        self.load_buffer(file)
        if ordw(self.buffer) != 0xffd8:
            raise RequiredMarkerMissing("SOI marker missing")

        while ordw(self.buffer) != 0xffd9:
            if ordw(self.buffer) == 0xffc0:
                self.parse_frame(file,"baseline")
            elif ordw(self.buffer) == 0xffc1:
                self.parse_frame(file,"sequential")
            elif ordw(self.buffer) == 0xffc2:
                self.parse_frame(file,"progressive")
            elif ordw(self.buffer) == 0xffc3:
                self.parse_frame(file,"lossless")
            elif ordw(self.buffer) == 0xffc5:
                self.parse_frame(file,"differential sequential")
            elif ordw(self.buffer) == 0xffc6:
                self.parse_frame(file,"differential progressive")
            elif ordw(self.buffer) == 0xffc7:
                self.parse_frame(file,"differential lossless")
            elif ordw(self.buffer) == 0xffc9:
                self.parse_frame(file,"AC sequential")
            elif ordw(self.buffer) == 0xffca:
                self.parse_frame(file,"AC progressive")
            elif ordw(self.buffer) == 0xffcb:
                self.parse_frame(file,"AC lossless")
            elif ordw(self.buffer) == 0xffcd:
                self.parse_frame(file,"AC differential sequential")
            elif ordw(self.buffer) == 0xffce:
                self.parse_frame(file,"AC differential progressive")
            elif ordw(self.buffer) == 0xffcf:
                self.parse_frame(file,"AC differential lossless")
            elif ordw(self.buffer) == 0xffde:
                self.parse_frame(file,"define hierarchical process")
            elif ordw(self.buffer) == 0xfff7:
                self.parse_frame(file,"JPEG LS")
            elif ordw(self.buffer) == 0xffb1:
                self.parse_frame(file,"residual sequential")
            elif ordw(self.buffer) == 0xffb2:
                self.parse_frame(file,"residual progressive")
            elif ordw(self.buffer) == 0xffb3:
                self.parse_frame(file,"residual large DCT")
            elif ordw(self.buffer) == 0xffb9:
                self.parse_frame(file,"AC residual sequential")
            elif ordw(self.buffer) == 0xffba:
                self.parse_frame(file,"AC residual progressive")
            elif ordw(self.buffer) == 0xffbb:
                self.parse_frame(file,"AC residual large DCT")
            else:
                self.parse_table()
            self.load_buffer(file)

        self.new_marker("EOI","End of image")
        self.end_marker()
        oh = self.bytecount - self.datacount
        checksum = self.c0 + 256 * self.c1
        self.print_indent("Checksum  : 0x%04x" % checksum)
        self.print_indent("Size      : %d bytes" % (self.bytecount))
        self.print_indent("Data Size : %d bytes" % (self.datacount))
        self.print_indent("Overhead  : %d bytes (%d%%)" % (oh, 100 * oh / self.bytecount))

    def update_checksum(self,byte):
        self.c0 = self.c0 + byte
        while self.c0 >= 255:
            self.c0 = self.c0 - 255
        self.c1 = self.c1 + self.c0
        while self.c1 >= 255:
            self.c1 = self.c1 - 255
            
    def parse_data(self, file, bitstuff):
        byte = 0
        cnt  = 0

        while 1:
            last_byte = byte
            dta       = file.read(1)
            if len(dta) != 1:
                raise UnexpectedEOC()
            self.offset    = self.offset + 1
            self.datacount = self.datacount + 1
            self.bytecount = self.bytecount + 1
            cnt            = cnt + 1
            byte           = ord(dta)
            if last_byte == 0xff:
                if ((byte > 0x00 and not bitstuff) or (byte >= 0x80 and bitstuff)):
                    marker = (last_byte << 8) | byte
                    if marker >= 0xffd0 and marker <= 0xffd7:
                        self.markerpos = self.offset - 2
                        self.datacount = self.datacount - 2
                        self.new_marker("RST","Restart marker #%d" % (marker - 0xffd0))
                        self.end_marker()
                    elif marker != 0xffff: #Skip filler bytes.
                        print
                        self.print_indent("%d bytes of entropy coded data" % (cnt - 2))
                        self.offset = self.offset - 2
                        file.seek(self.offset)
                        return marker
                else:
                    self.update_checksum(0xff)
                    self.update_checksum(byte)
            elif byte != 0xff:
                self.update_checksum(byte)

#
# Main Function for Codestream Parsing
#

if __name__ == "__main__":
    # Read Arguments
    if len(sys.argv) != 2:
        print "Usage: %s FILE" % (sys.argv[0])
        sys.exit(1)

    print "###############################################################"
    print "# JPG codestream log file generated by jpgcodestream.py       #"
    print "###############################################################"
    print

    # Parse Files
    filename  = sys.argv[1]
    file = open(filename,"rb")
    jpg  = JPGCodestream()
    try:
        jpg.stream_parse(file,0)        
    except JP2Error, e:
        print '***', str(e)
