#!/usr/bin/python

# $Id: jxrfile.py,v 1.15 2021/05/27 16:05:57 thor Exp $

import getopt
import sys
from jp2utils import *
from icc import *

def lordw(buffer):
    return (ord(buffer[1]) << 8) + \
           (ord(buffer[0]) << 0)

def lordl(buffer):
    return (ord(buffer[3]) << 24) + \
           (ord(buffer[2]) << 16) + \
           (ord(buffer[1]) <<  8) + \
           (ord(buffer[0]) <<  0)

def lordq(buffer):
    return (ord(buffer[7]) << 56) + \
           (ord(buffer[6]) << 48) + \
           (ord(buffer[5]) << 40) + \
           (ord(buffer[4]) << 32) + \
           (ord(buffer[3]) << 24) + \
           (ord(buffer[2]) << 16) + \
           (ord(buffer[1]) <<  8) + \
           (ord(buffer[0]) <<  0)

class JXRCodestream:
    def __init__(self,file,indent):
        self.infile = file
        self.indent = indent
        self.alpha_present = False
        self.index_table_present = False
        self.bitpos = 0
        self.bitbuffer = 0
        self.frequency_mode = False
        self.tiles_wide = 0
        self.tiles_high = 0
        self.num_bands = 0
        self.tile_offsets = None
        self.trim_flexbits = False
        self.dc_variable = False
        self.lp_variable = False
        self.hp_variable = False
        self.num_components = 0

    def get_bits(self,bits):
        result = 0
        while bits > 0:
            avail = self.bitpos
            if avail == 0:
                self.bitbuffer = ord(self.infile.read(1))
                self.bitpos    = 8
                avail          = 8
            if avail > bits:
                avail = bits
            result = (result << avail) | ((self.bitbuffer >> (self.bitpos - avail)) & ((1 << avail) - 1))
            bits  -= avail
            self.bitpos -= avail
        return result

    def align_to_byte(self):
        self.bitpos = 0
        
    def print_indent(self, buffer, nl = 1):
        print_indent(buffer, self.indent, nl)

    def print_position(self):
        print("%i:" % self.infile.tell())
            
    def parse_image_header(self):
        self.print_indent("Image Header Contents:")
        self.indent += 1
        gdi=self.infile.read(8)
        self.print_indent("GDI Signature     : %s" % gdi[0:7])
        flags=ord(self.infile.read(1))
        self.print_indent("Reserved B        : 0x%01x" % (flags >> 4))
        if flags & 0x08 != 0:
            hard_tiling="Enabled"
        else:
            hard_tiling="Disabled"
        self.print_indent("Hard Tiling       : %s" % hard_tiling)
        self.print_indent("Reserved C        : 0x%01x" % (flags & 0x07))
        flags=ord(self.infile.read(1))
        if flags & 0x80 != 0:
            tiling="Enabled"
            tiles=True
        else:
            tiling="Disabled"
            tiles=False
        self.print_indent("Tiling            : %s" % tiling)
        if flags & 0x40 != 0:
            mode = "Frequency"
            self.frequency_mode = True
        else:
            mode = "Spatial"
        self.print_indent("Progression       : %s" % mode)
        xfrm=(flags >> 3) & 0x07
        rot = ""
        if xfrm == 0:
            rot = "Upright"
        if xfrm & 1 != 0:
            rot += "Flip Vertical "
        if xfrm & 2 != 0:
            rot += "Flip Horizontal "
        if xfrm & 4 != 0:
            rot += "Rotate Clockwise "
        self.print_indent("Orientation       : %s" % rot)
        if flags & 0x04:
            self.index_table_present = True
            idx="Yes"
        else:
            idx="No"
        self.print_indent("Index Table       : %s" % idx)
        self.print_indent("Overlap Mode      : %d" % (flags & 0x03))
        flags = ord(self.infile.read(1))
        if flags & 0x80 != 0:
            shdr = "Short Headers"
            short = True
        else:
            shdr = "Long Headers"
            short = False
        self.print_indent("Header Format     : %s" % shdr)
        if flags & 0x40 != 0:
            lflg = "32 bit integers required"
        else:
            lflg = "16 bit integers sufficient"
        self.print_indent("Arithmetics       : %s" % lflg)
        if flags & 0x20 != 0:
            windowing = True
            win = "Present"
        else:
            windowing = False
            win = "Not Present (full image)"
        self.print_indent("View Window       : %s" % win)
        if flags & 0x10 != 0:
            trim="Enabled"
            self.trim_flexbits = True
        else:
            trim="Disabled"
        self.print_indent("Trim Flexbits     : %s" % trim)
        self.print_indent("Reserved D        : 0x%01x" % ((flags >> 3) & 0x01))
        if flags & 0x04 != 0:
            rgb="Not Swapped"
        else:
            rgb="Swapped"
        self.print_indent("RGB order         : %s" % rgb)
        if flags & 0x02 != 0:
            pre="Premultiplied"
        else:
            pre="Not Premultiplied"
        self.print_indent("Alpha Plane       : %s" % pre)
        if flags & 0x01 != 0:
            alpha="Present"
            self.alpha_present = True
        else:
            alpha="Not Present"
        self.print_indent("Alpha Plane       : %s" % alpha)
        flags = ord(self.infile.read(1))
        color = (flags >> 4)
        bits  = flags & 0x0f
        self.output_bitdepth = bits
        if color == 0:
            cmode = "YOnly"
        elif color == 1:
            cmode = "YUV420"
        elif color == 2:
            cmode = "YUV422"
        elif color == 3:
            cmode = "YUV444"
        elif color == 4:
            cmode = "CMYK"
        elif color == 5:
            cmode = "CMYK Direct"
        elif color == 6:
            cmode = "N Component"
        elif color == 7:
            cmode = "RGB"
        elif color == 8:
            cmode = "RGBE"
        else:
            cmode = "Reserved (%d)" % color
        self.print_indent("Color Format      : %s" % cmode)
        if bits == 0:
            bmode = "Min is Black"
        elif bits == 1:
            bmode = "8bpp"
        elif bits == 2:
            bmode = "16bpp"
        elif bits == 3:
            bmode = "16bpp Signed"
        elif bits == 4:
            bmode = "Half Float"
        elif bits == 5:
            bmode = "Reserved (5)"
        elif bits == 6:
            bmode = "32bpp Signed"
        elif bits == 7:
            bmode = "Float"
        elif bits == 8:
            bmode = "5bpp"
        elif bits == 9:
            bmode = "10bpp"
        elif bits == 10:
            bmode = "5:6:5 Packed"
        elif bits == 15:
            bmode = "Min is White"
        else:
            bmode = "Reserved (%d)" % bits
        self.print_indent("Bit Depths        : %s" % bmode)
        if short:
            width  = ordw(self.infile.read(2)) + 1
            height = ordw(self.infile.read(2)) + 1
        else:
            width  = ordl(self.infile.read(4)) + 1
            height = ordl(self.infile.read(4)) + 1
        self.print_indent("Image Width       : %d" % width)
        self.print_indent("Image Height      : %d" % height)
        if tiles:
            t1 = ord(self.infile.read(1))
            t2 = ord(self.infile.read(1))
            t3 = ord(self.infile.read(1))
            tilew = ((t1 << 4) | ((t2 & 0xf0) >> 4)) + 1
            tileh = (((t2 & 0x0f) << 8) | t3) + 1
            self.print_indent("Tiles Left-Right  : %d" % tilew)
            self.print_indent("Tiles Top-Bottom  : %d" % tileh)
        else:
            tilew = 1
            tileh = 1
        totw = width
        self.tiles_wide = tilew
        self.tiles_high = tileh
        for x in range(0,tilew-1):
            if short:
                tw = ord(self.infile.read(1))
            else:
                tw = ordw(self.infile.read(2))
            self.print_indent("Width of Tile  %d : %d MBs" % (x,tw))
            totw -= tw << 4
        if tiles:
            self.print_indent("Width of Tile  %d : %d MBs (computed)" % (tilew-1,(totw + 15) >> 4))
        toth = height
        for y in range(0,tileh-1):
            if short:
                th = ord(self.infile.read(1))
            else:
                th = ord(self.infile.read(2))
            self.print_indent("Height of Tile %d : %d MBs" % (y,th))
            toth -= th << 4
        if tiles:
            self.print_indent("Height of Tile %d : %d MBs (computed)" % (tileh-1,(toth + 15) >> 4))
        if windowing:
            t1 = ord(self.infile.read(1))
            t2 = ord(self.infile.read(1))
            t3 = ord(self.infile.read(1))
            top   = t1 >> 2
            left  = ((t1 & 0x03) << 4) | ((t2 & 0xf0) >> 4)
            bot   = ((t2 & 0x0f) << 2) | ((t3 & 0xc0) >> 6)
            right = t3 & 0x3f
            self.print_indent("Top    Border     : %d" % top)
            self.print_indent("Left   Border     : %d" % left)
            self.print_indent("Bottom Border     : %d" % bot)
            self.print_indent("Right  Border     : %d" % right)
        self.indent -= 1

    def parse_quantizer(self,comps,band):
        self.indent += 1
        if comps != 1:
            mode = self.get_bits(2)
            if mode == 0:
                qmod = "Uniform"
            elif mode == 1:
                qmod = "Separate"
            elif mode == 2:
                qmod = "Independent"
            elif mode == 3:
                qmod = "Reserved"
            self.print_indent("Quantizer %s Mode      : %s" % (band,qmod))
        else:
            mode = 0
        if mode == 0:
            qp = self.get_bits(8)
            self.print_indent("Quantizer %s QP        : %s" % (band,qp))
        elif mode == 1:
            qp = self.get_bits(8)
            self.print_indent("Quantizer %s QP Luma   : %s" % (band,qp))
            qp = self.get_bits(8)
            self.print_indent("Quantizer %s QP Chroma : %s" % (band,qp))
        elif mode == 2:
            for i in range(0,comps):
                qp = self.get_bits(8)
                self.print_indent("Quantizer %s QP %2d     : %s" % (band,i,qp))
        self.indent -= 1

    def parse_image_plane_header(self,alpha):
        if alpha:
            self.print_indent("Image Plane Header Contents (for Alpha Plane):")
        else:
            self.print_indent("Image Plane Header Contents:")
        self.indent += 1
        flags=ord(self.infile.read(1))
        cfmt = (flags & 0xe0) >> 5
        if cfmt == 0:
            cformat = "YOnly"
            comps   = 1
        elif cfmt == 1:
            cformat = "YUV420"
            comps   = 3
        elif cfmt == 2:
            cformat = "YUV422"
            comps   = 3
        elif cfmt == 3:
            cformat = "YUV444"
            comps   = 3
        elif cfmt == 4:
            cformat = "YUVK"
            comps   = 4
        elif cfmt == 5:
            cformat = "Reserved (5)"
            comps   = 0
        elif cfmt == 6:
            cformat = "N Component"
            comps   = 0 # later
        elif cfmt == 7:
            cformat = "Reserved (7)"
            comps   = 0
        self.print_indent("Internal Color Fmt: %s" % cformat)  
        if flags & 0x10 != 0:
            scaled = "Enabled"
        else:
            scaled = "Disabled"
        self.print_indent("Output Scaling    : %s" % scaled)
        bands = flags & 0x0f
        self.num_bands = bands
        if bands == 0:
            bd = "All Subbands Present"
            self.num_bands = 4
        elif bands == 1:
            bd = "No Flexbits"
            self.num_bands = 3
        elif bands == 2:
            bd = "Flexbits and Highpasses not Present"
            self.num_bands = 2
        elif bands == 3:
            bd = "Only DC Band Present"
            self.num_bands = 1
        else:
            bd = "Reserved (%d)" % bands
            self.num_bands = 0
        self.print_indent("Included Bands    : %s" % bd)
        if cfmt == 1 or cfmt == 2 or cfmt == 3:
            flags = ord(self.infile.read(1))
            self.print_indent("Chroma Centering X: %d" % (flags >> 4))
            self.print_indent("Chroma Centering Y: %d" % (flags & 0x0f))
        elif cfmt == 6:
            comps = ord(self.infile.read(1))
            if (comps >> 4) == 15:
                comps = ((comps & 0x0f) | (ord(self.infile.read(1)))) + 16
            else:
                self.print_indent("Reserved H        : %d" % (comps & 0x0f))
                comps = ((comps >> 4) + 1)
        self.print_indent("Components        : %d" % comps)
        self.num_components = comps
        if self.output_bitdepth == 2 or self.output_bitdepth == 3 or self.output_bitdepth == 6:
            flags=ord(self.infile.read(1))
            self.print_indent("Output Upshift    : %d" % flags)
        elif self.output_bitdepth == 7:
            flags=ord(self.infile.read(1))
            self.print_indent("Mantissa Length   : %d" % flags)
            flags=ord(self.infile.read(1))
            self.print_indent("Exponent Bias     : %d" % flags)
        dcuniform = self.get_bits(1)
        if dcuniform == 1:
            uni = "Uniform"
        else:
            uni = "Variable"
            self.dc_variable = True
        self.print_indent("DC Quantization   : %s" % uni)
        if dcuniform:
            self.parse_quantizer(comps,"DC    ")
        if bands != 3:
            self.print_indent("Reserved I        : %d" % self.get_bits(1))
            lpuniform = self.get_bits(1)
            if lpuniform == 1:
                uni = "Uniform"
            else:
                uni = "Variable"
                self.lp_variable = True
            self.print_indent("LP Quantization   : %s" % uni)
            if lpuniform:
                self.parse_quantizer(comps,"LP    ")
            if bands != 2:
                self.print_indent("Reserved J        : %d" % self.get_bits(1))
                hpuniform = self.get_bits(1)
                if hpuniform == 1:
                    uni = "Uniform"
                else:
                    uni = "Variable"
                    self.hp_variable = True
                self.print_indent("HP Quantization   : %s" % uni)
                if hpuniform:
                    self.parse_quantizer(comps,"HP    ")
        self.align_to_byte()
        self.indent -= 1

    def vlw_esc(self):
        first = ord(self.infile.read(1))
        if first < 0xfb:
            second = ord(self.infile.read(1))
            return (first << 8) | second
        elif first == 0xfb:
            return ordl(self.infile.read(4))
        elif first == 0xfc:
            return ordq(self.infile.read(8))
        else:
            return 0
        
    def parse_table_tiles(self):
        self.print_indent("Index Table Tiles Contents:")
        self.indent += 1
        if self.frequency_mode:
            entries = self.num_bands * self.tiles_wide * self.tiles_high
        else:
            entries = self.tiles_wide * self.tiles_high
        startcode = ordw(self.infile.read(2))
        self.print_indent("Start Code        : 0x%04lx" % startcode)
        self.print_indent("Number of Entries : %d" % entries)
        self.tile_offsets = []
        for i in range(0,entries):
            offset = self.vlw_esc()
            self.tile_offsets.append(offset)
            self.print_indent("Tile %4d Offset: 0x%08lx" % (i,offset))

    def tile_header_DC(self,alpha):
        if alpha:
            plane = "DC    (alpha)"
            comps = 1
            self.print_indent("Tile Header DC (alpha)")
        else:
            plane = "DC           "
            comps = self.num_components
            self.print_indent("Tile Header DC")
        if self.dc_variable:
            self.parse_quantizer(comps,plane)

    def tile_header_LP(self,alpha):
        if alpha:
            plane = "LP %2d (alpha)"
            comps = 1
            self.print_indent("Tile Header LP (alpha)")
        else:
            plane = "LP %2d        "
            comps = self.num_components
            self.print_indent("Tile Header LP")
        if self.lp_variable:
            quant = self.get_bits(1)
            if quant == 0:
                var = "Enabled"
            else:
                var = "Disabled"
            self.print_indent("Variable LP Quant     : %s" % var)
            if quant == 0:
                numqp = self.get_bits(4) + 1
                self.print_indent("Number of Quantizers  : %d" % numqp)
                for i in range(0,numqp):
                    self.parse_quantizer(comps,plane % i)

    def tile_header_HP(self,alpha):
        if alpha:
            plane = "HP %2d (alpha)"
            comps = 1 
            self.print_indent("Tile Header HP (alpha)")
        else:
            plane = "HP %2d        "
            comps = self.num_components
            self.print_indent("Tile Header HP")
        if self.hp_variable:
            quant = self.get_bits(1)
            if quant == 0:
                var = "Enabled"
            else:
                var = "Disabled"
            self.print_indent("Variable HP Quant     : %s" % var)
            if quant == 0:
                numqp = self.get_bits(4) + 1
                self.print_indent("Number of Quantizers  : %d" % numqp)
                for i in range(0,numqp):
                    self.parse_quantizer(comps,plane % i)

    def tile_DC(self,tile):
        self.print_indent("Tile %d (DC)          :" % tile)
        self.indent += 1
        startcode = ordl(self.infile.read(4))
        self.print_indent("Start code            : 0x%08lx" % startcode)
        if self.num_bands > 1:
            self.tile_header_DC(False)
            if self.alpha_present:
                self.tile_header_DC(True)
        self.align_to_byte()
        self.indent -= 1

    def tile_LP(self,tile):
        self.print_indent("Tile %d (LP)          :" % tile)
        self.indent += 1
        startcode = ordl(self.infile.read(4))
        self.print_indent("Start code            : 0x%08lx" % startcode)
        self.tile_header_LP(False)
        if self.alpha_present:
            self.tile_header_LP(True)
        self.align_to_byte()
        self.indent -= 1
        
    def tile_HP(self,tile):
        self.print_indent("Tile %d (HP)          :" % tile)
        self.indent += 1
        startcode = ordl(self.infile.read(4))
        self.print_indent("Start code            : 0x%08lx" % startcode)
        if self.num_bands > 2:
            self.tile_header_HP(False)
            if self.alpha_present:
                self.tile_header_HP(True)
        self.align_to_byte()
        self.indent -= 1        

    def tile_FlexBits(self,tile):
        self.print_indent("Tile %d (FlexBits)    :" % tile)
        self.indent += 1
        startcode = ordl(self.infile.read(4))
        self.print_indent("Start code            : 0x%08lx" % startcode)
        if self.trim_flexbits:
            self.print_indent("Trim Flexbits         : %d" % self.get_bits(4))
        self.align_to_byte()
        self.indent -= 1

    def tile_Spatial(self,tile):
        self.print_indent("Tile %d (spatial mode):" % tile)
        self.indent += 1
        startcode = ordl(self.infile.read(4))
        self.print_indent("Start code            : 0x%08lx" % startcode)
        if self.trim_flexbits:
            self.print_indent("Trim Flexbits         : %d" % self.get_bits(4))
        self.tile_header_DC(False)
        if self.num_bands > 1:
            self.tile_header_LP(False)
        if self.num_bands > 2:
            self.tile_header_HP(False)
        if self.alpha_present:
            self.tile_header_DC(True)
            if self.num_bands > 1:
                self.tile_header_LP(True)
            if self.num_bands > 2:
                self.tile_header_HP(True)
        self.align_to_byte()
        self.indent -= 1

    def parse_profile_info(self):
        self.print_indent("Profile Information")
        last = False
        while last == False:
            profile = self.get_bits(8)
            level   = self.get_bits(8)
            if profile <= 44:
                prof = "Subbaseline"
            elif profile <= 55:
                prof = "Baseline"
            elif profile <= 66:
                prof = "Main"
            elif profile <= 111:
                prof = "Advanced"
            else: 
                prof = "Unknown"
            self.print_indent("Profile               : %s (%d)" % (prof,profile))
            self.print_indent("Level                 : 0x%02x" % level)
            self.print_indent("Reserved L            : 0x%04lx" % self.get_bits(15))
            if self.get_bits(1) == 1:
                last = True
            
    def parse(self):
        self.indent += 1
        self.parse_image_header()
        print()
        self.print_position()
        self.parse_image_plane_header(False)
        if self.alpha_present == True:
            print()
            self.print_position()
            self.parse_image_plane_header(True)
        if self.index_table_present == True:
            print()
            self.print_position()
            self.parse_table_tiles()
        subseqnt  = self.vlw_esc()
        if subseqnt > 0:
            current = self.infile.tell()
            print()
            self.print_position()
            self.parse_profile_info()
            self.infile.seek(current + subseqnt)
        print()
        num_tiles = self.tiles_wide * self.tiles_high
        base      = self.infile.tell()
        if self.frequency_mode:
            for i in range(0,num_tiles):
                self.infile.seek(base + self.tile_offsets[i * self.num_bands])
                self.print_position()
                self.tile_DC(i)
            if self.num_bands > 1:
                for i in range(0,num_tiles):
                    self.infile.seek(base + self.tile_offsets[i * self.num_bands + 1])
                    self.print_position()
                    self.tile_LP(i)
            if self.num_bands > 2:
                for i in range(0,num_tiles):
                    self.infile.seek(base + self.tile_offsets[i * self.num_bands + 2])
                    self.print_position()
                    self.tile_HP(i)
            if self.num_bands > 3:
                for i in range(0,num_tiles):
                    self.infile.seek(base + self.tile_offsets[i * self.num_bands + 3])
                    self.print_position()
                    self.tile_FlexBits(i)
        elif num_tiles > 1:
            for i in range(0,num_tiles):
                self.infile.seek(base + self.tile_offsets[i])
                self.print_position()
                self.tile_Spatial(i)
        else:
            self.print_position()
            self.tile_Spatial(0)
        
class JXRFile:
    def __init__(self,file,endian = 0):
        self.infile = file
        self.indent = 0
        self.offset = 0
        self.endian = endian
        self.coffset = NotImplemented
        self.csize   = NotImplemented
        self.aoffset = NotImplemented
        self.asize   = NotImplemented
        
    def readshort(self):
        if self.endian == 0:
            return lordw(self.infile.read(2))
        else:
            return ordw(self.infile.read(2))

    def readlong(self):
        if self.endian == 0:
            return lordl(self.infile.read(4))
        else:
            return ordl(self.infile.read(4))

    def readquad(file):
        if self.endian == 0:
            return lordq(self.infile.read(8))
        else:
            return ordq(self.infile.read(8))
        
    def print_hex(self, buffer):
        print_hex(buffer,self.indent)
        
    def print_indent(self, buffer, nl = 1):
        print_indent(buffer, self.indent, nl)
        
    def print_position(self):
        print("0x%08lx:" % self.infile.tell())

    def pxFormatToString(self,values):
        uuid = 0
        for i in range(0,16):
            uuid = (uuid << 8) | values[i]
        if uuid   == 0x24C3DD6F034EFE4BB1853D77768DC90D:
            return "24bppRGB"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC90C:
            return "24bppBGR"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC90E:
            return "32bppBGR"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC915:
            return "48bppRGB"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC912:
            return "48bppRGBFixedPoint"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC93B:
            return "48bppRGBHalf"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC918:
            return "96bppRGBFixedPoint"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC940:
            return "64bppRGBFixedPoint"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC942:
            return "64bppRGBHalf"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC941:
            return "128bppRGBFixedPoint"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC91B:
            return "128bppRGBFloat"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC90F:
            return "32bppBGRA"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC916:
            return "64bppRGBA"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC91D:
            return "64bppRGBAFixedPoint"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC93A:
            return "64bppRGBAHalf"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC91E:
            return "128bppRGBAFixedPoint"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC919:
            return "128bppRGBAFloat"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC910:
            return "32bppPBGRA"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC917:
            return "64bppPRGBA"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC91A:
            return "128bppPRGBAFloat"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC91C:
            return "32bppCMYK"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC92C:
            return "40bppCMYKAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC91F:
            return "64bppCMYK"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC92D:
            return "80bppCMYKAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC920:
            return "24bpp3Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC921:
            return "32bpp4Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC922:
            return "40bpp5Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC923:
            return "48bpp6Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC924:
            return "56bpp7Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC925:
            return "64bpp8Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC92E:
            return "32bpp3ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC92F:
            return "40bpp4ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC930:
            return "48bpp5ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC931:
            return "56bpp6ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC932:
            return "64bpp7ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC933:
            return "72bpp8ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC926:
            return "48bpp3Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC927:
            return "64bpp4Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC928:
            return "80bpp5Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC929:
            return "96bpp6Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC92A:
            return "112bpp7Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC92B:
            return "128bpp8Channels"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC934:
            return "64bpp3ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC935:
            return "80bpp4ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC936:
            return "96bpp5ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC937:
            return "112bpp6ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC938:
            return "128bpp7ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC939:
            return "144bpp8ChannelsAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC908:
            return "8bppGray"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC90B:
            return "16bppGray"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC913:
            return "16bppGrayFixedPoint"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC93E:
            return "16bppGrayHalf"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC93F:
            return "32bppGrayFixedPoint"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC911:
            return "32bppGrayFloat"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC905:
            return "BlackWhite"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC909:
            return "16bppBGR555"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC90A:
            return "16bppBGR565"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC914:
            return "32bppBGR101010"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC93D:
            return "32bppRGBE"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC954:
            return "32bppCMYKDIRECT"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC955:
            return "64bppCMYKDIRECT"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC956:
            return "40bppCMYKDIRECTAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC943:
            return "80bppCMYKDIRECTAlpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC944:
            return "12bppYCC420"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC945:
            return "16bppYCC422"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC946:
            return "20bppYCC422"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC947:
            return "32bppYCC422"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC948:
            return "24bppYCC444"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC949:
            return "30bppYCC444"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC94A:
            return "48bppYCC444"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC94B:
            return "48bppYCC444FixedPoint"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC94C:
            return "20bppYCC420Alpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC94D:
            return "24bppYCC422Alpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC94E:
            return "30bppYCC422Alpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC94F:
            return "48bppYCC422Alpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC950:
            return "32bppYCC444Alpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC951:
            return "40bppYCC444Alpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC952:
            return "64bppYCC444Alpha"
        elif uuid == 0x24C3DD6F034EFE4BB1853D77768DC953:
            return "64bppYCC444AlphaFixedPoint"
        else:
            return "Unknown (0x%016x)" % uuid
            
    def print_rotation(self,values):
        rot = ""
        if values[0] == 0:
            rot = "Upright"
        if values[0] & 1 != 0:
            rot += "Flip Vertical "
        if values[0] & 2 != 0:
            rot += "Flip Horizontal "
        if values[0] & 4 != 0:
            rot += "Rotate Clockwise "
        self.print_indent("Orientation       : %s" % rot)

    def print_colorspace(self,values):
        if values[0] == 1:
            cspace = "sRGB"
        elif values[0] == 0xffff:
            cspace = "sRGB not preferred"
        else:
            cspace = "Reserved (%d)" % values[0]
        self.print_indent("Colorspace        : %s" % cspace)

    def print_imagetype(self,values):
        itype = ""
        if values[0] == 0:
            itype = "Standard"
        if values[0] & 1:
            itype += "Preview "
        if values[0] & 2:
            itype += "Page "
        self.print_indent("Image Type        : %s" % itype)

    def print_colorinfo(self,values):
        if values[0] == 1:
            primaries = "Rec 709"
        elif values[0] == 2:
            primaries = "Application Specific"
        elif values[0] == 4:
            primaries = "Rec 470-6"
        elif values[0] == 5:
            primaries = "Rec 601 (625)"
        elif values[0] == 6:
            primaries = "Rec 601 (525)"
        elif values[0] == 7:
            primaries = "SMTPE 240M"
        else:
            primaries = "Reserved (%d)" % values[0]
        if values[1] == 1:
            transfer = "Rec 709"
        elif values[1] == 2:
            transfer = "Application Specific"
        elif values[1] == 4:
            transfer = "Gamma 2.2"
        elif values[1] == 5:
            transfer = "Gamma 2.8"
        elif values[1] == 6:
            transfer = "Rec 601 (525)"
        elif values[1] == 7:
            transfer = "SMTPE 240M"
        elif values[1] == 8:
            transfer = "Linear"
        elif values[1] == 11:
            transfer = "xvYCC"
        elif values[1] == 12:
            transfer = "Rec 361"
        elif values[1] == 13:
            transfer = "sRGB"
        else:
            transfer = "Reserved (%d)" % values[1]
        if values[2] == 0:
            matrix = "None"
        elif values[2] == 1:
            matrix = "Rec 709"
        elif values[2] == 2:
            matrix = "Application Specific"
        elif values[2] == 4:
            matrix = "US Title 47"
        elif values[2] == 5:
            matrix = "Rec 601 (625)"
        elif values[2] == 6:
            matrix = "Rec 601 (525)"
        elif values[2] == 7:
            matrix = "SMTPE 240M"
        elif values[2] == 8:
            matrix = "YCgCo"
        else:
            matrix = "Reserved (%d)" % values[2]
        flags = values[3] >> 1
        if values[3] & 1:
            crange = "Full Range"
        else:
            crange = "Reduced Range"
        self.print_indent("Primaries         : %s" % primaries)
        self.print_indent("Transfer Function : %s" % transfer)
        self.print_indent("Matrix            : %s" % matrix)
        self.print_indent("Reserved K        : 0x%02x" % flags)
        self.print_indent("Range             : %s" % crange)
        
    def print_profileinfo(self,values):
        last = False
        idx  = 0
        while last == False:
            profile = values[idx]
            level   = values[idx+1]
            flags   = (values[idx+2] << 8) | values[idx+3]
            if profile <= 44:
                prof = "Subbaseline"
            elif profile <= 55:
                prof = "Baseline"
            elif profile <= 66:
                prof = "Main"
            elif profile <= 111:
                prof = "Advanced"
            else: 
                prof = "Unknown"
            self.print_indent("Profile           : %s (%d)" % (prof,profile))
            self.print_indent("Level             : 0x%02x" % level)
            self.print_indent("Reserved L        : 0x%04lx" % (flags >> 1))
            if flags & 1:
                last = True
            idx += 3

    def parse_exif(self,offset):
        current = self.infile.tell()
        self.infile.seek(offset)
        count = self.readshort()
        for i in range(0,count):
            self.parse_ifd_entry()
        self.infile.seek(current)

    def print_componentsconfig(self,buffer):
        self.print_indent("Components Config :")
        px = ""
        for i in range(0,len(buffer)):
            c = ord(buffer[i])
            if c == 0:
                px += "not present "
            elif c == 1:
                px += "Y "
            elif c == 2:
                px += "Cb "
            elif c == 3:
                px += "Cr "
            elif c == 4:
                px += "R "
            elif c == 5:
                px += "G "
            elif c == 6:
                px += "B "
            else:
                px += "reserved (%d) " % c
            self.print_indent("Pixel %2d Config   : %s" % (i+1,px))

    def print_usercomment(self,buffer):
        ctype = ordq(buffer[0:8])
        if ctype == 0x4153424949000000:
            comment = buffer[8:]
            coding  = "ASCII"
        elif ctype == 0x4a49530000000000:
            comment = "???"
            coding  = "JIS"
        elif ctype == 0x554e49434f444500:
            comment = buffer[8:]
            coding  = "UNICODE"
        else:
            comment = "???"
            coding  = "unknown"
        self.print_indent("User Comment      : %s (%s)" % (comment,coding))

    def parse_exposureprog(self,ep):
        if ep == 0:
            prog = "Undefined"
        elif ep == 1:
            prog = "Manual"
        elif ep == 2:
            prog = "Normal"
        elif ep == 3:
            prog = "Aperture Priority"
        elif ep == 4:
            prog = "Shutter Priority"
        elif ep == 5:
            prog = "Creative"
        elif ep == 6:
            prog = "Action"
        elif ep == 7:
            prog = "Portrait"
        elif ep == 8:
            prog = "Landscape"
        else:
            prog = "Reserved (%d)" % ep
        self.print_indent("Exposure Program  : %s" % prog)

    def parse_ifd_entry(self):
        tag   = self.readshort()
        type  = self.readshort()
        count = self.readlong()
        offset = 0
        values = []
        content = ""
        if type == 1 or type == 6:
            typename="Byte"
            if count > 4:
                offset = self.readlong()
                current = self.infile.tell()
                self.infile.seek(offset)
                for i in range(0,count):
                    v = ord(self.infile.read(1))
                    content += "%02x " % v
                    values.append(v)
                self.infile.seek(current)
            else:
                buffer = self.infile.read(4)
                if count > 0:
                    v = ord(buffer[0:1])
                    content += "%02x " % v
                    values.append(v)
                if count > 1:
                    v = ord(buffer[1:2])
                    content += "%02x " % v
                    values.append(v)
                if count > 2:
                    v = ord(buffer[2:3])
                    content += "%02x " % v
                    values.append(v)
                if count > 3:
                    v = ord(buffer[3:4])
                    content += "%02x " % v
                    values.append(v)
        elif type == 2:
            typename="UTF-8"
            if count > 4:
                offset = self.readlong()
                current = self.infile.tell()
                self.infile.seek(offset)
                buffer = self.infile.read(count)
                for i in range(0,len(buffer)):
                    content += "%02x " % ord(buffer[i])
                if buffer[len(buffer)-1] == '\0':
                    buffer = buffer[0:len(buffer)-1]
                values.append(buffer)
                self.infile.seek(current)
            else:
                buffer = self.infile.read(4)
                buffer = buffer[0:count]
                for i in range(0,len(buffer)):
                    content += "%02x " % ord(buffer[i])
                if buffer[len(buffer)-1] == '\0':
                    buffer = buffer[0:len(buffer)-1]
                values.append(buffer)
        elif type == 3 or type == 8:
            typename="Short"
            if count > 2:
                offset = self.readlong()
                current = self.infile.tell()
                self.infile.seek(offset)
                for i in range(0,count):
                    v = self.readshort()
                    values.append(v)
                    content += "%04x " % v
                self.infile.seek(current)
            else:
                if count > 0:
                    v = self.readshort()
                    values.append(v)
                    content += "%04x " % v
                else:
                    self.infile.read(2)
                if count > 1:
                    v = self.readshort()
                    values.append(v)
                    content += "%04x " % v
                else:
                    self.infile.read(2)
        elif type == 4 or type == 9:
            typename="Long"
            if count > 1:
                offset = self.readlong()
                current = self.infile.tell()
                self.infile.seek(offset)
                for i in range(0,count):
                    v = self.readlong()
                    values.append(v)
                    content += "%08x " % v
                self.infile.seek(current)
            else:
                if count > 0:
                    v = self.readlong()
                    values.append(v)
                    content += "%08x " % v
                else:
                    self.infile.read(4)
        elif type == 5 or type == 10:
            typename="Rational"
            offset = self.readlong()
            current = self.infile.tell()
            self.infile.seek(offset)
            for i in range(0,count):
                num = self.readlong()
                den = self.readlong()
                content += "%d/%d " % (num,den)
                values.append([num,den])
            self.infile.seek(current)
        elif type == 11:
            typename="Float"
            if count > 1:
                offset = self.readlong()
                current = self.infile.tell()
                self.infile.seek(offset)
                for i in range(0,count):
                    v = ieee_float_to_float(self.readlong())
                    values.append(v)
                    content += "%g " % v
                self.infile.seek(current)
            else:
                if count > 0:
                    v = ieee_float_to_float(self.readlong())
                    values.append(v)
                    content += "%g " % v
                else:
                    self.infile.read(4)
        elif type == 12:
            typename="Double"
            offset = self.readlong()
            current = self.infile.tell()
            self.infile.seek(offset)
            for i in range(0,count):
                v = ieee_double_to_float(self.readquad())
                values.append(v)
                content += "%g " % v
            self.infile.seek(current)
        elif type == 7:
            typename="Undefined"
            if count > 4:
                offset = self.readlong()
                current = self.infile.tell()
                self.infile.seek(offset)
                buffer = self.infile.read(count)
                self.infile.seek(offset)
                for i in range(0,count):
                    content += "0x%02x " % ord(self.infile.read(1))
                self.infile.seek(current)
            else:
                current = self.infile.tell()
                buffer = self.infile.read(count)
                self.infile.seek(current)
                for i in range(0,count):
                    content += "0x%02x " % ord(self.infile.read(1))
                self.infile.seek(current + 4)
        else:
            typename="Unknown"
            values.append(self.readlong())
            self.infile.seek(self.infile.tell() - 4)
            for i in range(0,4):
                content += "0x%02x " % ord(self.infile.read(1))
        if count <= 16:
            self.print_indent("0x%04x(%8s[%2d]): %s" % (tag,typename,count,content))
        else:
            self.print_indent("0x%04x(%8s[%2d]): ..." % (tag,typename,count))
        self.indent += 1
        if tag == 0xbc01:
            self.print_indent("Pixel Format      : %s" % self.pxFormatToString(values))
        elif tag == 0xbc80:
            self.print_indent("Image Width       : %d" % values[0])
        elif tag == 0xbc81:
            self.print_indent("Image Height      : %d" % values[0])
        elif tag == 0xbc82:
            self.print_indent("Width Resolution  : %g" % values[0])
        elif tag == 0xbc83:
            self.print_indent("Height Resolution : %g" % values[0])
        elif tag == 0xbcc0:
            self.print_indent("Image Offset      : 0x%08lx" % values[0])
            self.coffset = values[0]
        elif tag == 0xbcc1:
            self.print_indent("Image Bytecount   : 0x%08lx" % values[0])
            self.csize = values[0]
        elif tag == 0x010d:
            self.print_indent("Document Name     : %s" % values[0])
        elif tag == 0x010e:
            self.print_indent("Image Description : %s" % values[0])
        elif tag == 0x010f:
            self.print_indent("Equipment Make    : %s" % values[0])
        elif tag == 0x0110:
            self.print_indent("Equipment Model   : %s" % values[0])
        elif tag == 0x011d:
            self.print_indent("Page Name         : %s" % values[0])
        elif tag == 0x0129:
            self.print_indent("Page Number       : %d-%d" % (values[0],values[1]))
        elif tag == 0x0131:
            self.print_indent("Software Version  : %s" % values[0])
        elif tag == 0x0132:
            self.print_indent("Date and Time     : %s" % values[0])
        elif tag == 0x013b:
            self.print_indent("Artist Name       : %s" % values[0])
        elif tag == 0x013c:
            self.print_indent("Host Computer     : %s" % values[0])
        elif tag == 0x8222:
            self.print_exposureprog(values[0])
        elif tag == 0x8298:
            self.print_indent("Copyright Notice  : %s" % values[0])
        elif tag == 0x829a:
            self.print_indent("Exposure Time     : %s" % content)
        elif tag == 0x829d:
            self.print_indent("F-Stops           : %s" % content)
        elif tag == 0x8824:
            self.print_indent("Spectral Sens.    : %s" % values[0])
        elif tag == 0x8827:
            self.print_indent("ISO Speed Rating  : %d" % values[0]) 
        elif tag == 0x9000:
            self.print_indent("EXIF Version      : %s" % content)
        elif tag == 0x9003:
            self.print_indent("Date & Time (Org) : %s" % values[0])
        elif tag == 0x9004:
            self.print_indent("Date & Time (Dgt) : %s" % values[0])
        elif tag == 0x9101:
            self.print_componentsconfig(buffer)
        elif tag == 0x9102:
            self.print_indent("Compressed BPP    : %s" % content)
        elif tag == 0x9201:
            self.print_indent("Shutter Speed     : %s" % content)
        elif tag == 0x9202:
            self.print_indent("Aperture          : %s" % content)
        elif tag == 0x9203:
            self.print_indent("Brightness        : %s" % content)
        elif tag == 0x9204:
            self.print_indent("Exposure Bias     : %s" % content)
        elif tag == 0x9205:
            self.print_indent("Max. Aperture     : %s" % content)
        elif tag == 0x9206:
            self.print_indent("Subject Distance  : %s" % content)
        elif tag == 0x9290:
            self.print_indent("Sub-Seconds       : %s" % values[0])
        elif tag == 0x9291:
            self.print_indent("Sub-Seconds (Org) : %s" % values[0])
        elif tag == 0x9292:
            self.print_indent("Sub-Seconds (Dgt) : %s" % values[0])
        elif tag == 0x927c:
            self.print_indent("Marker Note       : %s" % content)
        elif tag == 0x9286:
            self.print_usercomment(buffer)
        elif tag == 0xa000:
            self.print_indent("FlashPix Version  : %s" % content)
        elif tag == 0xa001:
            self.print_colorspace(values)
        elif tag == 0xa002:
            self.print_indent("PixelXDimension   : %s" % values[0])
        elif tag == 0xa003:
            self.print_indent("PixelYDimension   : %s" % values[0])
        elif tag == 0xa004:
            self.print_indent("Sound File        : %s" % values[0])
        elif tag == 0xa20b:
            self.print_indent("Flash Energy      : %s" % content)
        elif tag == 0xa20e:
            self.print_indent("Focal Plane X Res : %s" % content)
        elif tag == 0xa20f:
            self.print_indent("Focal Plane Y Res : %s" % content)
        elif tag == 0xa214:
            self.print_indent("Subject Location  : %d,%d" % (values[0],values[1]))
        elif tag == 0xa215:
            self.print_indent("Exposure Index    : %s" % content)
        elif tag == 0xa404:
            self.print_indent("Digital Zoom Ratio: %s" % content)
        elif tag == 0xa405:
            self.print_indent("Focal Len for 35mm: %d" % values[0])
        elif tag == 0xa420:
            self.print_indent("Unique ID         : %s" % values[0])
        elif tag == 0xbc02:
            self.print_rotation(values)
        elif tag == 0xbc04:
            self.print_imagetype(values)
        elif tag == 0xbc05:
            self.print_colorinfo(values)
        elif tag == 0xbc06:
            self.print_profileinfo(values)
        elif tag == 0xbcc2:
            self.print_indent("Alpha Offset      : 0x%08lx" % values[0])
            self.aoffset = values[0]
        elif tag == 0xbcc3:
            self.print_indent("Alpha Bytecount   : 0x%08lx" % values[0])
            self.asize = values[0]
        elif tag == 0xbcc4:
            self.print_indent("Image Bands       : %d" % values[0])
        elif tag == 0xbcc5:
            self.print_indent("Alpha Presence    : %d" % values[0])
        elif tag == 0x02bc:
            self.print_indent("Adobe XMP data:");
            self.indent += 1
            string = ""
            for i in values:
                string += chr(i)
            print(string)
        elif tag == 0x8769:
            self.print_indent("EXIF 2.2 data:");
            self.parse_exif(values[0])
        elif tag == 0x8773:
            self.print_indent("ICC Profile:");
            parse_icc(self.indent+1,buffer)
        elif tag == 0xea1c:
            self.print_indent("Padding Data");
        self.indent -= 1

        
    def parse(self):
        type = self.infile.read(2)
        id = self.readshort()
        if id != 0x01bc:
            raise JP2Error("not a valid JXR file, identifier is invalid")
        ifdoffset = self.readlong()
        self.print_indent("IFD at offset:         0x%04lx" % ifdoffset)
        self.infile.seek(ifdoffset)
        count = self.readshort()
        self.print_indent("Number of IFD entries: %d" % count)
        self.indent+=1
        for i in range(0,count):
            self.parse_ifd_entry()
        if self.coffset != NotImplemented:
            self.infile.seek(self.coffset)
            jxrc = JXRCodestream(self.file,self.indent)
            print()
            self.print_position()
            self.print_indent("Codestream Contents:")
            jxrc.parse()
        if self.aoffset != NotImplemented and self.aoffset != 0:
            self.infile.seek(self.aoffset)
            jxrc = JXRCodestream(self.file,self.indent)
            print()
            self.print_position()
            self.print_indent("Codestream Alpha Plane Contents:")
            jxrc.parse()

ignore_codestream = 0
if __name__ == "__main__":
    
    # Read Arguments
    (args, files) = getopt.getopt(sys.argv[1:], "C", "ignore-codestream")
    for (o, a) in args:
        if o in ("-C", "--ignore-codestream"):
            ignore_codestream = 1

    if len(files) != 1:
        print("Usage: [OPTIONS] %s FILE" % (sys.argv[0]))
        sys.exit(1)

    print("###############################################################")
    print("# JXR file format log file generated by jxrfile.py            #")
    print("###############################################################")
    print()

    # Parse Files
    file = open(files[0],"rb")
    type = file.read(2)
    file.seek(0)
    try:
        if ord(type[0]) == 0x57 and ord(type[1]) == 0x4d:
            jxr = JXRCodestream(file,0)
            jxr.parse()
        elif ord(type[0]) == 0x49 and ord(type[1]) == 0x49:
            jxr = JXRFile(file,0)
            jxr.parse()
        elif ord(type[0]) == 0x4d and ord(type[1]) == 0x4d:
            jxr = JXRFile(file,1)
            jxr.parse()
        else:
            print('Input file is neither a JXR codestream nor a JXR file')
            
    except JP2Error as e:
        print('***', str(e))
