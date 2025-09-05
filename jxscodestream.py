#!/usr/bin/python

# $Id: jxscodestream.py,v 1.22 2024/05/14 11:21:46 thor Exp $

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

def decode_Profile(profile):
    if profile == 0x0000:
        return "unrestricted"
    elif profile == 0x1500:
        return "light 422.10"
    elif profile == 0x1a00:
        return "light 444.12"
    elif profile == 0x2500:
        return "light-subline"
    elif profile == 0x3240:
        return "main 420"
    elif profile == 0x3540:
        return "main 422.10"
    elif profile == 0x3a40:
        return "main 444.12"
    elif profile == 0x3e40:
        return "main 4444.12"
    elif profile == 0x4240:
        return "high 420.12"
    elif profile == 0x4a40:
        return "high 444.12"
    elif profile == 0x4a44:
        return "chigh 444.12"
    elif profile == 0x4a45:
        return "tdc 444.12"
    elif profile == 0x4a4c:
        return "ehigh 444.12"
    elif profile == 0x4e40:
        return "high 4444.12"
    elif profile == 0x6a45:
        return "tdc mls 444.12"
    elif profile == 0x6EC0:
        return "mls 12"
    elif profile == 0x9300:
        return "light bayer"
    elif profile == 0xb340:
        return "main bayer"
    elif profile == 0xc340:
        return "high bayer"
    else:
        return "invalid (0x%x)" % profile

def decode_Level(level):
    lvl = (level >> 8) & 0xfc
    sub = level & 0x9f
    fbl = (level & 0x360) >> 5
    if lvl == 0x00:
        lstr = "unrestricted"
    elif lvl == 0x04:
        lstr = "1k-1"
    elif lvl == 0x10:
        lstr = "2k-1"
    elif lvl == 0x20:
        lstr = "4k-1"
    elif lvl == 0x24:
        lstr = "4k-2"
    elif lvl == 0x28:
        lstr = "4k-3"
    elif lvl == 0x30:
        lstr = "8k-1"
    elif lvl == 0x34:
        lstr = "8k-2"
    elif lvl == 0x38:
        lstr = "8k-3"
    elif lvl == 0x40:
        lstr = "10k-1"
    else:
        lstr = "invalid (0x%x)" % lvl
    if sub == 0x00:
        sstr = "unrestricted"
    elif sub == 0x80:
        sstr = "full"
    elif sub == 0x10:
        sstr = "12bpp"
    elif sub == 0x0c:
        sstr = "9bpp"
    elif sub == 0x08:
        sstr = "6bpp"
    elif sub == 0x06:
        sstr = "4bpp"
    elif sub == 0x04:
        sstr = "3bpp"
    elif sub == 0x03:
        sstr = "2bpp"
    else:
        sstr = "invalid (0x%x)" % sub
    if fbl == 0x00:
        fstr = ""
    elif fbl == 0x1b:
        fstr = "full"
    elif fbl == 0x18:
        fstr = "fblev12bpp"
    elif fbl == 0x08:
        fstr = "fblev4.5bpp"
    elif fbl == 0x03:
        fstr = "fblev3bpp"
    else:
        fstr = "invalid fbb (0x%x)" % fbl
    return "%s@%s %s" % (lstr,sstr,fstr)
#
# The Codestream Class
#

class JXSCodestream:
    def __init__(self, indent = 0, offset = 0):
        self.indent = indent
        self.datacount   = 0
        self.bytecount   = 0
        self.offset      = offset
        self.markerpos   = 0
        self.frametype   = 0
        self.c0          = 0
        self.c1          = 0
        self.sliceheight = 0
        self.ypos        = 0
        self.precheight  = 0
        self.precwidth   = 0
        self.columnsize  = 0
        self.width       = 0
        self.height      = 0
        self.hlevels     = 0
        self.vlevels     = 0
        self.bandcount   = 0
        self.precision   = 0
        self.depth       = 0
        self.profile     = 0
        self.level       = 0
        self.nbpp        = 0
        self.longhdr     = 0
        self.rawbyline   = 0
        self.excluded    = 0
        self.inter       = False
        self.sampling    = ""
        self.quant       = ""
        self.colortrafo  = ""
        self.fractional  = 8
        self.nlt         = "None"
        self.extent      = "Unspecified"
        self.boxlist     = BoxList()

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
        if (mrk >= 0xff10 and mrk <= 0xff11):
            self.buffer = marker
        elif (mrk >= 0xff12 and mrk <= 0xff1b) or mrk == 0xff20 or mrk == 0xff21 or mrk == 0xff50:
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

        if len(marker) == 0:
            self.buffer = []
        else:  
            if len(marker) < 2:
                raise UnexpectedEOC()
            self.load_marker(file,marker)
            self.offset = self.offset + len(self.buffer)

    def check_profile(self):
        sliceheight = self.sliceheight << self.vlevels # this is in image lines (grid points)
        if self.profile == 0x1500: #light 422.10
            if self.precision != 8 and self.precision != 10:
                raise JP2Error("Light422.10 only supports 8 and 10 bit sample precision")
            if self.sampling != "400" and self.sampling != "422":
                raise JP2Error("Light422.20 only suppors 400 and 422 subsampling")
            if self.vlevels > 1:
                raise JP2Error("Light422.10 only supports up to 1 vertical decomposition level")
            if self.quant != "deadzone":
                raise JP2Error("Light422.10 only supports the deadzone quantizer")
            if self.columnsize != 0:
                raise JP2Error("Light422.10 does not support columns")
            if sliceheight != 16:
                raise JP2Error("Light422.10 only supports slices of 16 grid points")
            if self.colortrafo != "None":
                raise JP2Error("Light422.10 does not support any color decorrelation transformation")
            if self.longhdr != 0:
                raise JP2Error("Light422.10 does not support the long header mode switch")
            if self.rawbyline != 0:
                raise JP2Error("Light422.10 does not support the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("Light422.10 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("Light422.10 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("Light422.10 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("Light422.10 does not support the CDT marker")
            self.nbpp = 20
        elif self.profile == 0x1a00: #light 444.12
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("Light444.12 only supports 8,10 and 12 bit sample precision")
            if self.sampling != "400" and self.sampling != "422" and self.sampling != "444":
                raise JP2Error("Light444.12 only supports 400, 422 and 444 subsampling")
            if self.vlevels > 1:
                raise JP2Error("Light444.12 only supports up to 1 vertical decomposition level")
            if self.quant != "deadzone":
                raise JP2Error("Light444.12 only supports the deadzone quantizer")
            if self.columnsize != 0:
                raise JP2Error("Light444.12 does not support columns")
            if sliceheight != 16:
                raise JP2Error("Light444.12 only supports slices of 16 grid points")
            if self.colortrafo != "None" and self.colortrafo != "RCT":
                raise JP2Error("Light444.12 only supports the RCT or no color transformation")
            if self.longhdr != 0:
                raise JP2Error("Light444.12 does not support the long header mode switch")
            if self.rawbyline != 0:
                raise JP2Error("Light444.12 does not support the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("Light444.12 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("Light444.12 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("Light444.12 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("Light422.12 does not support the CDT marker")
            self.nbpp = 36
        elif self.profile == 0x2500: #light subline 422.10
            if self.precision != 8 and self.precision != 10:
                raise JP2Error("Light subline 422.10 only supports 8 and 10 bit sample precision")
            if self.sampling != "400" and self.sampling != "422":
                raise JP2Error("Light subline 422.10 only supports 400 and 444 subsampling")
            if self.vlevels > 0:
                raise JP2Error("Light subline 422.10 only supports 0 vertical decomposition levels")
            if self.precwidth > 2048:
                raise JP2Error("Light subline 422.10 allows precincts to be at most 2048 grid points large")
            if self.colortrafo != "None":
                raise JP2Error("Light subline 422.10 does not support any color decorrelation transformation")
            if self.longhdr != 0:
                raise JP2Error("Light subline 422.10 does not support the long header mode switch")
            if self.rawbyline != 0:
                raise JP2Error("Light subline 422.10 does not support the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("Light subline 422.10 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("Light subline 422.10 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("Light subline 422.10 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("Light subline 422.10 does not support the CDT marker")
            self.nbpp = 20
        elif self.profile == 0x3240: #main 420.12
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("Main420.10 only supports 8 and 10 bit sample precision")
            if self.sampling != "420":
                raise JP2Error("Main420.10 only supports 420 subsampling")
            if self.vlevels > 1:
                raise JP2Error("Main420.10 only supports up to 1 vertical decomposition level")
            if self.columnsize != 0 and self.vlevels > 0:
                raise JP2Error("Main420.10 only supports columns for 0 vertical levels")
            if sliceheight != 16:
                raise JP2Error("Main420.10 only supports slices of 16 grid points")
            if self.colortrafo != "None":
                raise JP2Error("Main420.10 does not support any color decorrelation transformation")
            if self.longhdr != 0:
                raise JP2Error("Main420.10 does not support the long header mode switch")
            if self.rawbyline != 0:
                raise JP2Error("Main420.10 does not support the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("Main420.10 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("Main420.10 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("Main420.10 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("Main420.10 does not support the CDT marker")
            self.nbpp = 20
        elif self.profile == 0x3540: #main 422.10
            if self.precision != 8 and self.precision != 10:
                raise JP2Error("Main 422.10 only supports 8 and 10 bit sample precision")
            if self.sampling != "400" and self.sampling != "422":
                raise JP2Error("Main422.10 only supports 400 and 444 subsampling")
            if self.vlevels > 1:
                raise JP2Error("Main422.10 only supports up to 1 vertical decomposition level")
            if self.columnsize != 0 and self.vlevels > 0:
                raise JP2Error("Main422.10 only supports columns for 0 vertical levels")
            if sliceheight != 16:
                raise JP2Error("Main422.10 only supports slices of 16 grid points")
            if self.colortrafo != "None":
                raise JP2Error("Main422.10 does not support any color decorrelation transformation")
            if self.longhdr != 0:
                raise JP2Error("Main422.10 does not support the long header mode switch")
            if self.rawbyline != 0:
                raise JP2Error("Main422.10 does not support the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("Main422.10 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("Main422.10 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("Main422.10 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("Main422.10 does not support the CDT marker")
            self.nbpp = 20
        elif self.profile == 0x3a40: #main 444.12
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("Main444.12 only supports 8,10 and 12 bit sample precision")
            if self.sampling != "400" and self.sampling != "422" and self.sampling != "444":
                raise JP2Error("Main444.12 only supports 400, 422 and 444 subsampling")
            if self.vlevels > 1:
                raise JP2Error("Main444.12 only supports up to 1 vertical decomposition level")
            if self.columnsize != 0 and self.vlevels > 0:
                raise JP2Error("Main444.10 only supports columns for 0 vertical levels")
            if sliceheight != 16:
                raise JP2Error("Main444.12 only supports slices of 16 grid points")
            if self.colortrafo != "None" and self.colortrafo != "RCT":
                raise JP2Error("Main444.12 only supports RCT or no color transformation")
            if self.longhdr != 0:
                raise JP2Error("Main444.12 does not support the long header mode switch")
            if self.rawbyline != 0:
                raise JP2Error("Main444.12 does not support the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("Main444.12 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("Main444.12 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("Main444.12 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("Main444.12 does not support the CDT marker")
            self.nbpp = 36
        elif self.profile == 0x3e40: #main 4444.12
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("Main4444.12 only supports 8,10 and 12 bit sample precision")
            if self.sampling != "400" and self.sampling != "422" and self.sampling != "444" and self.sampling != "4224" and self.sampling != "4444":
                raise JP2Error("Main4444.12 only supports 400, 422, 444, 4224 and 4444 subsampling")
            if self.vlevels > 1:
                raise JP2Error("Main4444.12 only supports up to 1 vertical decomposition level")
            if self.columnsize != 0 and self.vlevels > 0:
                raise JP2Error("Main4444.12 only supports columns for 0 vertical levels")
            if sliceheight != 16:
                raise JP2Error("Main4444.12 only supports slices of 16 grid points")
            if self.colortrafo != "None" and self.colortrafo != "RCT":
                raise JP2Error("Main4444.12 only supports RCT or no color transformation")
            if self.longhdr != 0:
                raise JP2Error("Main4444.12 does not support the long header mode switch")
            if self.rawbyline != 0:
                raise JP2Error("Main4444.12 does not support the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("Main4444.12 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("Main4444.12 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("Main4444.12 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("Main4444.12 does not support the CDT marker")
            self.nbpp = 48
        elif self.profile == 0x4240: #high 420.12
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("High420.12 only supports 8,10 and 12 bit sample precision")
            if self.sampling != "420":
                raise JP2Error("High420.12 only supports 420 subsampling")
            if self.vlevels > 2:
                raise JP2Error("High420.12 only supports up to 2 vertical decomposition levels")
            if self.vlevels == 0:
                raise JP2Error("High420.12 does not support 0 vertical levels")
            if sliceheight != 16:
                raise JP2Error("High420.12 only supports slices of 16 grid points")
            if self.colortrafo != "None":
                raise JP2Error("High420.12 does not allow any color transformation")
            if self.longhdr != 0:
                raise JP2Error("High420.12 does not support the long header mode switch")
            if self.rawbyline != 0:
                raise JP2Error("High420.12 does not support the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("High420.12 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("High420.12 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("High420.12 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("High420.12 does not support the CDT marker")
            self.nbpp = 18
        elif self.profile == 0x4a40: #high 444.12
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("High444.12 only supports 8,10 and 12 bit sample precision")
            if self.sampling != "400" and self.sampling != "422" and self.sampling != "444":
                raise JP2Error("High444.12 only supports 400, 422 and 444 subsampling")
            if self.vlevels > 2:
                raise JP2Error("High444.12 only supports up to 2 vertical decomposition levels")
            if self.columnsize != 0 and self.vlevels > 0:
                raise JP2Error("High444.12 only supports columns for 0 vertical levels")
            if sliceheight != 16:
                raise JP2Error("High444.12 only supports slices of 16 grid points")
            if self.colortrafo != "None" and self.colortrafo != "RCT":
                raise JP2Error("High444.12 only supports RCT or no color transformation")
            if self.longhdr != 0:
                raise JP2Error("High444.12 does not support the long header mode switch")
            if self.rawbyline != 0:
                raise JP2Error("High444.12 does not support the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("High444.12 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("High444.12 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("High444.12 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("High444.12 does not support the CDT marker")
            self.nbpp = 36
        elif self.profile == 0x4e40: #high 4444.12
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("High4444.12 only supports 8,10 and 12 bit sample precision")
            if self.sampling != "400" and self.sampling != "422" and self.sampling != "444" and self.sampling != "4224" and self.sampling != "4444":
                raise JP2Error("High4444.12 only supports 400, 422, 444, 4224 and 4444 subsampling")
            if self.vlevels > 2:
                raise JP2Error("High4444.12 only supports up to 2 vertical decomposition levels")
            if self.columnsize != 0 and self.vlevels > 0:
                raise JP2Error("High4444.12 only supports columns for 0 vertical levels")
            if sliceheight != 16:
                raise JP2Error("High4444.12 only supports slices of 16 grid points")
            if self.colortrafo != "None" and self.colortrafo != "RCT":
                raise JP2Error("High4444.12 only supports RCT or no color transformation")
            if self.longhdr != 0:
                raise JP2Error("High4444.12 does not support the long header mode switch")
            if self.rawbyline != 0:
                raise JP2Error("High4444.12 does not support the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("High4444.12 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("High4444.12 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("High4444.12 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("High4444.12 does not support the CDT marker")
            self.nbpp = 48
        elif self.profile == 0x6ec0: #MLS 12
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("MLS.12 only supports 8,10 and 12 bit sample precision")
            if self.sampling != "400" and self.sampling != "420" and self.sampling != "422" and self.sampling != "444" and self.sampling != "4224" and self.sampling != "4444":
                raise JP2Error("MLS.12 only supports 400, 420, 422, 444, 4224 and 4444 subsampling")
            if self.vlevels > 2:
                raise JP2Error("MLS.12 only supports up to 2 vertical decomposition levels")
            if self.columnsize != 0 and self.vlevels > 0:
                raise JP2Error("MLS.12 only supports columns for 0 vertical levels")
            if sliceheight != 16:
                raise JP2Error("MLS.12 only supports slices of 16 grid points")
            if self.colortrafo != "None" and self.colortrafo != "RCT":
                raise JP2Error("MLS.12 only supports RCT or no color transformation")
            if self.longhdr != 0:
                raise JP2Error("MLS.12 does not support the long header mode switch")
            if self.rawbyline != 0:
                raise JP2Error("MLS.12 does not support the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("MLS.12 does not support excluding components from the transformation")
            if self.fractional != 0:
                raise JP2Error("MLS.12 requires 0 fractional bits")
            if self.nlt != "None":
                raise JP2Error("MLS.12 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("MLS.12 does not support the CDT marker")
            self.nbpp = 64 # there is not really a limit
        elif self.profile == 0x9300: #LightBayer
            if self.precision != 10 and self.precision != 12 and self.precision != 14 and self.precision != 16:
                raise JP2Error("LightBayer only supports 10,12,14 and 16 bit sample precision")
            if self.sampling != "4444":
                raise JP2Error("LightBayer only supports 4444 subsampling")
            if self.vlevels > 0:
                raise JP2Error("LightBayer does not support vertical decomposition")
            if self.columnsize != 0:
                raise JP2Error("LightBayer does not support colums")
            if sliceheight != 16:
                raise JP2Error("LightBayer only supports slices of 16 grid points")
            if self.colortrafo != "Star-Tetrix":
                raise JP2Error("LightBayer only supports the Star-Tetrix color transformation")
            if self.excluded != 1:
                raise JP2Error("LightBayer requires one component to be excluded from the transformation")
            if self.rawbyline != 1:
                raise JP2Error("LightBayer requires the raw-mode per packet switch")
            if self.fractional != 6 and self.nlt != "None":
                raise JP2Error("LightBayer requires 6 fractional bits if a non-linear transform is present")
            if self.fractional != 8 and self.nlt == "None":
                raise JP2Error("LightBayer requires 8 fractional bits without a non-linear transform")
            if self.extent != "in-line":
                raise JP2Error("LightBayer only supports the in-line Star-Tetrix transformation")
            self.nbpp = 64
        elif self.profile == 0xb340: #MainBayer
            if self.precision != 10 and self.precision != 12 and self.precision != 14 and self.precision != 16:
                raise JP2Error("MainBayer only supports 10,12,14 and 16 bit sample precision")
            if self.sampling != "4444":
                raise JP2Error("MainBayer only supports 4444 subsampling")
            if self.vlevels > 1:
                raise JP2Error("MainBayer only supports 0 or 1 vertical decompositions")
            if self.columnsize != 0:
                raise JP2Error("MainBayer does not support colums")
            if sliceheight != 16:
                raise JP2Error("MainBayer only supports slices of 16 grid points")
            if self.colortrafo != "Star-Tetrix":
                raise JP2Error("MainBayer only supports the Star-Tetrix color transformation")
            if self.excluded != 1:
                raise JP2Error("MainBayer requires one component to be excluded from the transformation")
            if self.rawbyline != 1:
                raise JP2Error("MainBayer requires the raw-mode per packet switch")
            if self.fractional != 6 and self.nlt != "None":
                raise JP2Error("MainBayer requires 6 fractional bits if a non-linear transform is present")
            if self.fractional != 8 and self.nlt == "None":
                raise JP2Error("MainBayer requires 8 fractional bits without a non-linear transform")
            self.nbpp = 64
        elif self.profile == 0xc340: #HighBayer
            if self.precision != 10 and self.precision != 12 and self.precision != 14 and self.precision != 16:
                raise JP2Error("HighBayer only supports 10,12,14 and 16 bit sample precision")
            if self.sampling != "4444":
                raise JP2Error("HighBayer only supports 4444 subsampling")
            if self.vlevels > 2:
                raise JP2Error("HighBayer does not support more than 2 vertical decompositions")
            if self.columnsize != 0:
                raise JP2Error("HighBayer does not support colums")
            if sliceheight != 16:
                raise JP2Error("HighBayer only supports slices of 16 grid points")
            if self.colortrafo != "Star-Tetrix":
                raise JP2Error("HighBayer only supports the Star-Tetrix color transformation")
            if self.excluded != 1:
                raise JP2Error("HighBayer requires one component to be excluded from the transformation")
            if self.rawbyline != 1:
                raise JP2Error("HighBayer requires the raw-mode per packet switch")
            if self.fractional != 6 and self.nlt != "None":
                raise JP2Error("HighBayer requires 6 fractional bits if a non-linear transform is present")
            if self.fractional != 8 and self.nlt == "None":
                raise JP2Error("HighBayer requires 8 fractional bits without a non-linear transform")
            self.nbpp = 64
        elif self.profile == 0x4a44: # CHigh
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("CHigh only supports 8,10 and 12 bit sample precision")
            if self.sampling != "400" and self.sampling != "422" and self.sampling != "444":
                raise JP2Error("CHigh only supports 400, 422 and 444 subsampling")
            if self.vlevels > 2:
                raise JP2Error("CHigh only supports up to 2 vertical decomposition levels")
            if self.vlevels == 0 and self.hlevels != 3 and self.hlevels != 4:
                raise JP2Error("CHigh only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.vlevels == 0 and self.sampling == "420":
                raise JP2Error("CHigh does not support 0 vertical levels for 420 subsampling")
            if self.vlevels == 1 and self.hlevels != 4 and self.hlevels != 5:
                raise JP2Error("CHigh only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.vlevels == 2 and self.hlevels != 5:
                raise JP2Error("CHigh only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.columnsize != 0:
                raise JP2Error("CHigh does not support columns")
            if sliceheight != 16:
                raise JP2Error("CHigh only supports slices of 16 grid points")
            if self.colortrafo != "None" and self.colortrafo != "RCT":
                raise JP2Error("CHigh only supports RCT or no color transformation")
            if self.colortrafo == "RCT" and self.sampling != "444":
                raise JP2Error("CHigh only supports RCT for 444 sampling")
            if self.longhdr != 0:
                raise JP2Error("CHigh does not support the long header mode switch")
            if self.rawbyline != 1:
                raise JP2Error("CHigh requires the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("CHigh does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("CHigh requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("CHigh does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("CHigh does not support the CDT marker")
            self.nbpp = 36
        elif self.profile == 0x4a4c: # EHigh
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("EHigh only supports 8,10 and 12 bit sample precision")
            if self.sampling != "400" and self.sampling != "422" and self.sampling != "444":
                raise JP2Error("EHigh only supports 400, 422 and 444 subsampling")
            if self.vlevels > 2:
                raise JP2Error("EHigh only supports up to 2 vertical decomposition levels")
            if self.vlevels == 0 and self.hlevels != 3 and self.hlevels != 4:
                raise JP2Error("EHigh only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.vlevels == 0 and self.sampling == "420":
                raise JP2Error("EHigh does not support 0 vertical levels for 420 subsampling")
            if self.vlevels == 1 and self.hlevels != 4 and self.hlevels != 5:
                raise JP2Error("EHigh only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.vlevels == 2 and self.hlevels != 5:
                raise JP2Error("EHigh only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.columnsize != 0:
                raise JP2Error("EHigh does not support columns")
            if sliceheight != 16:
                raise JP2Error("EHigh only supports slices of 16 grid points")
            if self.colortrafo != "None" and self.colortrafo != "RCT":
                raise JP2Error("EHigh only supports RCT or no color transformation")
            if self.colortrafo == "RCT" and self.sampling != "444":
                raise JP2Error("EHigh only supports RCT for 444 sampling")
            if self.longhdr != 0:
                raise JP2Error("EHigh does not support the long header mode switch")
            if self.rawbyline != 1:
                raise JP2Error("EHigh requires the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("EHigh does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("EHigh requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("EHigh does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("EHigh does not support the CDT marker")
            self.nbpp = 36
        elif self.profile == 0x4a45: # TDC 444.12
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("TDC444.12 only supports 8,10 and 12 bit sample precision")
            if self.sampling != "400" and self.sampling != "422" and self.sampling != "444":
                raise JP2Error("TDC444.12 only supports 400, 422 and 444 subsampling")
            if self.vlevels > 2:
                raise JP2Error("TDC444.12 only supports up to 2 vertical decomposition levels")
            if self.vlevels == 0 and self.hlevels != 3 and self.hlevels != 4:
                raise JP2Error("TDC444.12 only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.vlevels == 0 and self.sampling == "420":
                raise JP2Error("TDC444.12 does not support 0 vertical levels for 420 subsampling")
            if self.vlevels == 1 and self.hlevels != 4 and self.hlevels != 5:
                raise JP2Error("TDC444.12 only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.vlevels == 2 and self.hlevels != 5:
                raise JP2Error("TDC444.12 only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.columnsize != 0:
                raise JP2Error("TDC444.12 does not support columns")
            if sliceheight != 16:
                raise JP2Error("TDC444.12 only supports slices of 16 grid points")
            if self.colortrafo != "None" and self.colortrafo != "RCT":
                raise JP2Error("TDC444.12 only supports RCT or no color transformation")
            if self.colortrafo == "RCT" and self.sampling != "444":
                raise JP2Error("TDC444.12 only supports RCT for 444 sampling")
            if self.longhdr != 0:
                raise JP2Error("TDC444.12 does not support the long header mode switch")
            if self.rawbyline != 1:
                raise JP2Error("TDC444.12 requires the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("TDC444.12 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("TDC444.12 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("TDC444.12 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("TDC444.12 does not support the CDT marker")
            self.nbpp = 36
        elif self.profile == 0x6a45: # TDC MLS 444.12
            if self.precision != 8 and self.precision != 10 and self.precision != 12:
                raise JP2Error("TDC MLS 444.12 only supports 8,10 and 12 bit sample precision")
            if self.sampling != "400" and self.sampling != "422" and self.sampling != "444":
                raise JP2Error("TDC MLS 444.12 only supports 400, 422 and 444 subsampling")
            if self.vlevels > 2:
                raise JP2Error("TDC MLS 444.12 only supports up to 2 vertical decomposition levels")
            if self.vlevels == 0 and self.hlevels != 3 and self.hlevels != 4:
                raise JP2Error("TDC MLS 444.12 only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.vlevels == 0 and self.sampling == "420":
                raise JP2Error("TDC MLS 444.12 does not support 0 vertical levels for 420 subsampling")
            if self.vlevels == 1 and self.hlevels != 4 and self.hlevels != 5:
                raise JP2Error("TDC MLS 444.12 only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.vlevels == 2 and self.hlevels != 5:
                raise JP2Error("TDC MLS 444.12 only supports (3,0),(4,0),(4,1),(5,1),(5,2) as wavelet decompositions")
            if self.columnsize != 0:
                raise JP2Error("TDC MLS 444.12 does not support columns")
            if sliceheight != 16:
                raise JP2Error("TDC MLS 444.12 only supports slices of 16 grid points")
            if self.colortrafo != "None" and self.colortrafo != "RCT":
                raise JP2Error("TDC MLS 444.12 only supports RCT or no color transformation")
            if self.colortrafo == "RCT" and self.sampling != "444":
                raise JP2Error("TDC MLS 444.12 only supports RCT for 444 sampling")
            if self.longhdr != 0:
                raise JP2Error("TDC MLS 444.12 does not support the long header mode switch")
            if self.rawbyline != 1:
                raise JP2Error("TDC MLS 444.12 requires the raw mode by line switch")
            if self.excluded != 0:
                raise JP2Error("TDC MLS 444.12 does not support excluding components from the transformation")
            if self.fractional != 8:
                raise JP2Error("TDC MLS 444.12 requires 8 fractional bits")
            if self.nlt != "None":
                raise JP2Error("TDC MLS 444.12 does not support non-linear transforms")
            if self.extent != "Unspecified":
                raise JP2Error("TDC MLS 444.12 does not support the CDT marker")
            self.nbpp = 36
        elif self.profile != 0x0000:
            raise JP2Error("invalid profile indicator %s" % self.profile)
            
    def check_level(self):
        level = (self.level >> 8) & 0xfc # the rest is the sublevel and frame buffer level
        if level == 0x04: #1k-1 level
            if self.width > 1280 or self.height > 5120 or self.width * self.height > 2621440:
                raise JP2Error("image is too large for 2k-1 level")
        elif level == 0x10: #2k-1 level
            if self.width > 2048 or self.height > 8192 or self.width * self.height > 4194304:
                raise JP2Error("image is too large for 2K-1 level")
        elif level == 0x20: #4k-1
            if self.width > 4096 or self.height > 16384 or self.width * self.height > 8912896:
                raise JP2Error("image is too large for 4K-1 level")
        elif level == 0x24: #4k-2
            if self.width > 4096 or self.height > 16384 or self.width * self.height > 16777216:
                raise JP2Error("image is too large for 4K-2 level")
        elif level == 0x28: #4k-3
            if self.width > 4096 or self.height > 16384 or self.width * self.height > 16777216:
                raise JP2Error("image is too large for 4K-3 level")
        elif level == 0x30: #8k-1
            if self.width > 8192 or self.height > 32768 or self.width * self.height > 35651584:
                raise JP2Error("image is too large for 8K-1 level")
        elif level == 0x34:
            if self.width > 8192 or self.height > 32768 or self.width * self.height > 67108864:
                raise JP2Error("image is too large for 8K-2 level")
        elif level == 0x38:
            if self.width > 8192 or self.height > 32768 or self.width * self.height > 67108864:
                raise JP2Error("image is too large for 8K-3 level")
        elif level == 0x40:
            if self.width > 10240 or self.height > 40960 or self.width * self.height > 104857600:
                raise JP2Error("image is too large for 10K-1 level")
        elif level != 0x00:
            raise JP2Error("invalid level specification")

    def check_sublevel(self,bytecount):
        sublevel = self.level & 0xff
        bpp      = 8.0 * bytecount / (self.width * self.height)
        if self.colortrafo == "Star-Tetrix":
            bpp = bpp / 4.0
        if sublevel == 0x80: # full
            if bpp > self.nbpp:
                raise JP2Error("bitrate exceeds maximum permissible bitrate of %d for full sublevel" % self.nbpp)
        elif sublevel == 0x10: # 12bpp
            if bpp > 12.0:
                raise JP2Error("bitrate exceeds 12bpp for 12bpp sublevel")
        elif sublevel == 0x0c: # 9bpp
            if bpp > 9.0:
                raise JP2Error("bitrate exceeds 9bpp for 9bpp sublevel")
        elif sublevel == 0x08: #6bpp
            if bpp > 6.0:
                raise JP2Error("bitrate exceeds 6bpp for 6bpp sublevel")
        elif sublevel == 0x06: #4bpp
            if bpp > 4.0:
                raise JP2Error("bitrate exceeds 4bpp for 4bpp sublevel")
        elif sublevel == 0x04: #3bpp
            if bpp > 3.0:
                raise JP2Error("bitrate exceeds 3bpp for 3bpp sublevel")
        elif sublevel == 0x03: #2bpp
            if bpp > 2.0:
                raise JP2Error("bitrate exceeds 2bpp for 2bpp sublevel")
        elif sublevel != 0x00:
                raise JP2Error("invalid sublevel specification")
        
    def parse_PIH(self):
        self.new_marker("PIH", "Picture header")
        self.pos = 4
        if len(self.buffer) != 2 + 26:
            raise InvalidSizedMarker("Size of the PIH marker shall be 26 bytes")
        lcod = ordl(self.buffer[self.pos + 0:self.pos + 4])
        ppih = ordw(self.buffer[self.pos + 4:self.pos + 6])
        plev = ordw(self.buffer[self.pos + 6:self.pos + 8])
        wf   = ordw(self.buffer[self.pos + 8:self.pos +10])
        hf   = ordw(self.buffer[self.pos +10:self.pos +12])
        cw   = ordw(self.buffer[self.pos +12:self.pos +14])
        hsl  = ordw(self.buffer[self.pos +14:self.pos +16])
        nc   = ord(self.buffer[self.pos +16:self.pos +17])
        ng   = ord(self.buffer[self.pos +17:self.pos +18])
        ss   = ord(self.buffer[self.pos +18:self.pos +19])
        bw   = ord(self.buffer[self.pos +19:self.pos +20])
        fqbr = ord(self.buffer[self.pos +20:self.pos +21])
        fq   = fqbr >> 4
        br   = fqbr & 15
        misc = ord(self.buffer[self.pos +21:self.pos +22])
        fslc = misc >> 7
        ppoc = (misc >> 4) & 7
        cpih = misc & 15
        wavl = ord(self.buffer[self.pos +22:self.pos + 23])
        nlx  = wavl >> 4
        nly  = wavl & 15
        cod  = ord(self.buffer[self.pos +23:self.pos + 24])
        lhdr = (cod >> 7) & 1
        lraw = (cod >> 6) & 1
        qpih = (cod >> 4) & 3
        fs   = (cod >> 2) & 1
        rm   = cod & 3
        self.sliceheight = hsl
        self.precheight  = 1 << nly
        self.width       = wf
        self.height      = hf
        self.depth       = nc
        self.columnsize  = cw
        self.hlevels     = nlx
        self.vlevels     = nly
        self.profile     = ppih
        self.level       = plev
        self.longhdr     = lhdr
        self.rawbyline   = lraw
        self.fractional  = fq
        self.colortrafo  = self.decode_cpih(cpih)
        if cw == 0:
            pwidthstr = "full width"
        else:
            pwidthstr = "%s 8*LL samples of max(sx)" % cw
        if fslc == 0:
            slicemode = "regular (in the DWT domain)"
        else:
            slicemode = "invalid (%s)" % fslc
        if ppoc == 0:
            progression = "resolution-line-band-component"
        else:
            progression = "invalid (%s)" % ppoc
        self.print_indent("Size of the codestream    : %s" % lcod)
        self.print_indent("Profile                   : %s" % decode_Profile(ppih))
        self.print_indent("Level                     : %s" % decode_Level(plev))
        self.print_indent("Width  of the frame       : %s" % wf)
        self.print_indent("Height of the frame       : %s" % hf)
        self.print_indent("Precinct width            : %s " % pwidthstr)
        self.print_indent("Slice height              : %s lines"       % (hsl << nly))
        self.print_indent("Number of components      : %s" % nc)
        self.print_indent("Code group size           : %s" % ng)
        self.print_indent("Significance group size   : %s code groups" % ss)
        self.print_indent("Wavelet bit precision     : %s bits" % bw)
        self.print_indent("Fractional bits           : %s bits" % fq)
        self.print_indent("Raw bits per code group   : %s bits" % br)
        self.print_indent("Slice coding mode         : %s" % slicemode)
        self.print_indent("Progression mode          : %s" % progression)
        self.print_indent("Colour decorrelation      : %s" % self.colortrafo)
        self.print_indent("Horizontal wavelet levels : %s" % nlx)
        self.print_indent("Vertical wavelet levels   : %s" % nly)
        self.print_indent("Forced long headers       : %s" % lhdr)
        self.print_indent("Raw mode switch per line  : %s" % lraw)
        self.print_indent("Quantizer type            : %s" % self.decode_qpih(qpih))
        self.print_indent("Sign handling             : %s" % self.decode_fs(fs))
        self.print_indent("Run mode                  : %s" % self.decode_rm(rm))
        self.end_marker()

    def decode_qpih(self,qpih):
        if qpih == 0:
            self.quant = "deadzone"
            return "deadzone"
        elif qpih == 1:
            self.quant = "uniform"
            return "uniform"
        else:
            return "invalid (%s)" % qpih

    def decode_cpih(self,cpih):
        if cpih == 0:
            return "None"
        elif cpih == 1:
            return "RCT"
        elif cpih == 3:
            return "Star-Tetrix"
        else:
            return "invalid (%s)" % cpih

    def decode_fs(self,fs):
        if fs == 0:
            return "encoded jointly"
        elif fs == 1:
            return "encoded separately"
        else:
            return "invalid (%s)" % fs

    def decode_rm(self,rm):
        if rm == 0:
            return "zero prediction"
        elif rm == 1:
            return "zero coefficients"
        else:
            return "invalid (%s)" % rm

    def parse_CDT(self):
        self.new_marker("CDT", "Component Table")
        self.pos = 4
        c = 0
        maxsx = 0
        self.sampling = "400"
        while self.pos < len(self.buffer):
            bc = ord(self.buffer[self.pos:self.pos+1])
            xy = ord(self.buffer[self.pos+1:self.pos+2])
            sx = xy >> 4
            sy = xy & 15
            if c == 0:
                self.precision = bc
            elif self.precision != bc:
                self.precision = 0
            if sx > maxsx:
                maxsx = sx
            if c == 0 or c == 3:
                if sx != 1 or sy != 1:
                    self.sampling == "unknown"
                if c == 3:
                    self.sampling = self.sampling + "4"
            elif c > 3:
                self.sampling = "unknown"
            else:
                if self.sampling == "400":
                    if sx == 1 and sy == 1:
                        self.sampling = "444"
                    elif sx == 2 and sy == 1:
                        self.sampling = "422"
                    elif sx == 2 and sy == 2:
                        self.sampling = "420"
                    else:
                        self.sampling = "unknown"
                elif self.sampling == "444":
                    if sx != 1 or sy != 1:
                        self.sampling = "unknown"
                elif self.sampling == "422":
                    if sx != 2 or sy != 1:
                        self.sampling = "unknown"
                elif self.sampling == "420":
                    if sx != 2 or sy != 2:
                        self.sampling = "unknown"
            self.print_indent("Component %s precision              : %s bits" % (c,bc))
            self.print_indent("Component %s horizontal subsampling : %s" % (c, sx))
            self.print_indent("Component %s vertical   subsampling : %s" % (c, sy))
            c = c + 1
            self.pos = self.pos + 2
        if self.columnsize == 0:
            self.precwidth = self.width
        else:
            self.precwidth = self.columnsize * 8 * maxsx * (1 << self.hlevels)
        if c != self.depth:
            raise JP2Error("Number of components in CDT marker is different from NC in picture header")
        self.print_indent("Sampling format                    : %s" % self.sampling)
        self.end_marker()
            
    def parse_COM(self):
        self.new_marker("COM","Extensions Marker")
        tcom = ordw(self.buffer[4:6])
        data = self.buffer[6:]
        if tcom == 0:
            if ord(data[len(data)-1:]) != 0:
                raise JP2Error("Vendor information is not zero-terminated");
            self.print_indent("Vendor                   : %s" % data[0:len(data)-1])
        elif tcom == 1:
            if ord(data[len(data)-1:]) != 0:
                raise JP2Error("Copyright information is not zero-terminated");
            self.print_indent("Copyright                : %s" % data[0:len(data)-1])
        elif tcom >= 0x8000:
            self.print_indent("Vendor 0x%4x information :" % tcom)
            print_hex(data)
        else:
            self.print_indent("Invalid 0x%4x data       :" % tcom)
            print_hex(data)
        self.end_marker()

    def parse_CAP(self):
        self.new_marker("CAP","Capabilities Marker")
        self.pos = 4
        while self.pos < len(self.buffer):
            for bit in range(8):
                cap = ((ord(self.buffer[self.pos:self.pos + 1])) >> (7 - bit)) & 1
                if cap == 0:
                    required = "not required"
                else:
                    required = "is required"
                self.print_indent("Capability %3s : %s" % (((self.pos << 3) + bit - 32,required)))
            self.pos = self.pos + 1
        self.end_marker()

    def parse_WGT(self):
        self.new_marker("WGT","Weights Table")
        self.pos = 4
        b = 0
        while self.pos < len(self.buffer):
            gb = ord(self.buffer[self.pos:self.pos + 1])
            pb = ord(self.buffer[self.pos + 1:self.pos + 2])
            self.print_indent("Band %3s gain,priority : %2s %2s" % (b,gb,pb))
            self.pos = self.pos + 2
            b = b + 1
        self.bandcount = b
        self.end_marker()
        
    def parse_WGI(self):
        self.new_marker("WGI","Refresh Weights Table")
        self.pos = 4
        b = 0
        while self.pos < len(self.buffer):
            gb = ord(self.buffer[self.pos:self.pos + 1])
            pb = ord(self.buffer[self.pos + 1:self.pos + 2])
            self.print_indent("Band %3s gain,priority : %2s %2s" % (b,gb,pb))
            self.pos = self.pos + 2
            b = b + 1
        self.bandcount = b
        self.end_marker()

    def parse_NLT(self):
        self.new_marker("NLT","Nonlinearity Marker")
        tnlt = ord(self.buffer[4:5])
        if tnlt == 1:
            self.nlt = "quadratic"
            self.print_indent("NLT Type       : quadratic")
            if len(self.buffer) != 2 + 2 + 1 + 2:
                raise InvalidSizedMarker("Size of the NLT marker shall be 5 bytes")
            t1 = ordw(self.buffer[5:7])
            self.print_indent("DC Offset      : %s" % t1)
        elif tnlt == 2:
            self.nlt = "extended"
            self.print_indent("NLT Type       : extended")
            if len(self.buffer) != 2 + 12:
                raise InvalidSizedMarker("Size of NLT marker shall be 12 bytes")
            t1 = ordl(self.buffer[5:9])
            t2 = ordl(self.buffer[9:13])
            e  = ord(self.buffer[13:14])
            self.print_indent("Threshold t1   : %s" % t1)
            self.print_indent("Threshold t2   : %s" % t2)
            self.print_indent("Slope exponent : %s" % e)
        self.end_marker()

    def parse_CWD(self):
        self.new_marker("CWD","Component Dependent Wavelet Decomposition Marker")
        if len(self.buffer) != 2 + 2 + 1:
            raise InvalidSizedMarker("Size of the CWD marker shall be 3 bytes")
        sd = ord(self.buffer[4:5])
        self.excluded = sd
        self.print_indent("Components excluded from DWT : %s" % sd)
        self.end_marker()

    def parse_CTS(self):
        self.new_marker("CTS","Colour Transformation Specification Marker")
        if len(self.buffer) != 2 + 4:
            raise InvalidSizedMarker("Size of the CTS marker shall be 4 bytes")
        cf = ord(self.buffer[4:5])
        ex = ord(self.buffer[5:6])
        if cf == 0:
            xfo = "full"
        elif cf == 3:
            xfo = "in-line"
        else:
            xfo = "invalid (%d)" % cf
        self.extent = xfo
        self.print_indent("Transformation type : %s" % xfo)
        self.print_indent("Red exponent        : %s" % (ex >> 4))
        self.print_indent("Blue exponent       : %s" % (ex & 0x0f))
        self.end_marker()

    def parse_CRG(self):
        self.new_marker("CRG","Component Registration Marker")
        self.pos = 4
        c = 0
        while self.pos < len(self.buffer):
            xc = ordw(self.buffer[self.pos:self.pos + 2])
            yc = ordw(self.buffer[self.pos + 2:self.pos + 4])
            self.print_indent("Component %s position : (0x%04x,0x%04x) = (%3d%%,%3d%%)" % (c,xc,yc,xc * 100 / 65536,yc * 100 / 65536))
            self.pos = self.pos + 4
            c = c + 1
        self.end_marker()

    def parse_TPC(self):
        self.new_marker("TPC","Temporal Prediction Control Marker")
        if len(self.buffer) < 2 + 3:
            raise InvalidSizedMarker("Size of the TPC marker is too small")
        self.pos = 6
        si = ord(self.buffer[4:5])
        bo = ord(self.buffer[5:6])
        qbi = bo >> 4
        qbr = bo & 15
        if qbi >= 8:
            qbi = qbi-16
        if qbr >= 8:
            qbr = qbr-16
        self.print_indent("Size of a TDC selection group  : %d code groups" % si)
        self.print_indent("Quantization boost for intra   : %d" % qbi)
        self.print_indent("Quantization boost for refresh : %d" % qbr)
        band = 0
        while self.pos < len(self.buffer):
            yh = ord(self.buffer[self.pos:self.pos+1])
            sh = ord(self.buffer[self.pos+1:self.pos+2])
            self.print_indent("Refresh position      for band %d : %d" % (band,yh))
            self.print_indent("Refresh hash exponent for band %d : %d" % (band,sh))
            self.pos = self.pos + 2
            band = band + 1
        self.end_marker()
        
    def parse_SLC(self):
        self.new_marker("SLC","Slice Header")
        if len(self.buffer) != 2 + 4:
            raise InvalidSizedMarker("Size of the SLC marker shall be 4 bytes")
        self.print_indent("Slice index : %s" % ordw(self.buffer[4:6]))
        self.inter = False
        self.check_profile()
        self.check_level()
        self.end_marker()

    def parse_SLI(self):
        self.new_marker("SLI","TDC enabled Slice Header")
        if len(self.buffer) != 2 + 4:
            raise InvalidSizedMarker("Size of the SLI marker shall be 4 bytes")
        self.print_indent("Slice index : %s" % ordw(self.buffer[4:6]))
        self.inter = True
        self.check_profile()
        self.check_level()
        self.end_marker()

    def parse_Precinct(self,file,px,py):
        if self.inter:
            bytesize = (24 + 8 + 8 + 8 + 8 + 4 * self.bandcount + 7) >> 3
            title    = "Precinct (inter)"
        else:
            bytesize = (24 + 8 + 8 + 2 * self.bandcount + 7) >> 3
            title    = "Precinct"
        self.print_indent("%-8s: %s (%s,%s)" % (self.offset,title,px,py))
        self.indent  = self.indent + 1
        header       = file.read(bytesize)
        self.offset  = self.offset + bytesize
        psize        = (ord(header[0:1]) << 16) + (ord(header[1:2]) << 8) + (ord(header[2:3]) << 0)
        qp           = ord(header[3:4])
        rp           = ord(header[4:5])
        self.print_indent("Data length   : %s bytes" %  psize)
        self.print_indent("Quantization  : %s" % qp)
        self.print_indent("Refinement    : %s" % rp)
        self.pos     = 5
        if self.inter:
            fbqp     = ord(header[5:6])
            fbrp     = ord(header[6:7])
            self.pos = 7
            self.print_indent("Frame Buffer Quantization  : %s" % fbqp)
            self.print_indent("Frame Buffer Refinement    : %s" % fbrp)
        for b in range(self.bandcount):
            offset = (b >> 2) + self.pos
            mode = (ord(header[offset:offset + 1]) >> (6 - ((b & 0x03) << 1))) & 0x03
            if mode == 0:
                modestr = "no prediction, no sigflags"
            elif mode == 1:
                modestr = "vertical prediction, no sigflags"
            elif mode == 2:
                modestr = "no prediction, sigflags"
            elif mode == 3:
                modestr = "vertical prediction, sigflags"
            self.print_indent("Band %3s mode : %s" % (b,modestr))
        if self.inter:
            for b in range(self.bandcount):
                bi = b + self.bandcount
                offset = (bi >> 2) + self.pos
                mode = (ord(header[offset:offset + 1]) >> (6 - ((bi & 0x03) << 1))) & 0x03
                if mode == 0:
                    modestr = "intra"
                elif mode == 2:
                    modestr = "inter band"
                elif mode == 3:
                    modestr = "inter flags"
                elif mode == 1:
                    modestr = "refresh band"
                self.print_indent("Band %3s temporal mode : %s" % (b,modestr))
        file.read(psize)
        print
        self.offset    = self.offset + psize
        self.datacount = self.datacount + psize
        self.bytecount = self.bytecount + psize + bytesize
        self.indent    = self.indent - 1
        
    def parse_Slice(self,file):
        for py in range(self.sliceheight):
            if self.ypos < self.height:
                for px in range(0,self.width,self.precwidth):
                    self.parse_Precinct(file,px,self.ypos / self.precheight)
            self.ypos = self.ypos + self.precheight

    def stream_parse(self, file, startpos):
        self.pos       = 0
        self.datacount = 0
        self.bytecount = 0
        self.offset    = startpos

        self.load_buffer(file)
        if ordw(self.buffer) != 0xff10:
            raise RequiredMarkerMissing("SOI marker missing")

                
        while len(self.buffer) >= 2 and ordw(self.buffer) != 0xff11:
            if ordw(self.buffer) == 0xff10:
                self.new_marker("SOC","Start of Codestream");
                self.end_marker()
            elif ordw(self.buffer) == 0xff12:
                self.parse_PIH()
            elif ordw(self.buffer) == 0xff13:
                self.parse_CDT()
            elif ordw(self.buffer) == 0xff14:
                self.parse_WGT()
            elif ordw(self.buffer) == 0xff1b:
                self.parse_WGI()
            elif ordw(self.buffer) == 0xff15:
                self.parse_COM()
            elif ordw(self.buffer) == 0xff16:
                self.parse_NLT()
            elif ordw(self.buffer) == 0xff17:
                self.parse_CWD()
            elif ordw(self.buffer) == 0xff18:
                self.parse_CTS()
            elif ordw(self.buffer) == 0xff19:
                self.parse_CRG()
            elif ordw(self.buffer) == 0xff1a:
                self.parse_TPC()
            elif ordw(self.buffer) == 0xff20:
                self.parse_SLC()
                self.parse_Slice(file)
            elif ordw(self.buffer) == 0xff21:
                self.parse_SLI()
                self.parse_Slice(file)
            elif ordw(self.buffer) == 0xff50:
                self.parse_CAP()
            else:
                self.new_marker("???","Unknown marker %04x" % marker)
                if len(self.buffer) < 256:
                    print_hex(self.buffer)
                self.end_marker()
            self.load_buffer(file)

        if len(self.buffer) >= 2:
            self.new_marker("EOI","End of image")
        self.end_marker()
        oh = self.bytecount - self.datacount
        self.check_sublevel(self.bytecount)
        self.print_indent("Size      : %d bytes" % (self.bytecount))
        self.print_indent("Data Size : %d bytes" % (self.datacount))
        self.print_indent("Overhead  : %d bytes (%d%%)" % (oh, 100 * oh / self.bytecount))


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
    jxs  = JXSCodestream()
    try:
        jxs.stream_parse(file,0)        
    except JP2Error, e:
        print '***', str(e)
