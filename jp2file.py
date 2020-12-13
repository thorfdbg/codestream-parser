#!/usr/bin/python

# $Id: jp2file.py,v 1.75 2020/10/15 12:14:27 thor Exp $

import getopt
import sys

from jp2box import *
from jp2codestream import *
from jp2utils import *
from icc import *
from jxrfile import *
from jpgcodestream import *
from jxscodestream import *

def parse_resolution_box(box,buffer):
    if len(buffer) != 10:
        box.print_ident("invalid box")
        return
    vrn = ordw(buffer[0:2])
    vrd = ordw(buffer[2:4])
    hrn = ordw(buffer[4:6])
    hrd = ordw(buffer[6:8])
    vre = ord(buffer[8])
    hre = ord(buffer[9])
    box.print_indent("Resolution: %d/%d*10^%d x %d/%d*10^%d" % \
          (hrn, hrd, hre, vrn, vrd, vre))

def parse_placeholder_box(box,buffer):
    print("Placeholder box")
    if len(buffer) < 6+8:
        box.print_indent("invalid box")
        return
    flags = ord(buffer[3])
    hdr   = "Access to original box"
    if flags & 1:
        box.print_indent("%s : yes" % hdr)
    else:
        box.print_indent("%s : no " % hdr)
    hdr  =  "Stream equivalent box "
    if flags & 2:
        box.print_indent("%s : yes" % hdr)
    else:
        box.print_indent("%s : no " % hdr)
    hdr  =  "Incremental codestream"
    if flags & 4:
        if flags & 8:
                box.print_indent("%s : yes (many)" % hdr)
        else:
                box.print_indent("%s : yes (one)" % hdr)
    else:
        box.print_indent("%s : no" % hdr)
    binid = ordq(buffer[4:12])
    box.print_indent("Contents in bin        : %d" % binid)
    hdr = box.parse_string_header(buffer[12:len(buffer)])
    buffer = hdr[0]
    box.print_indent("Original box length    : %d" % hdr[1])
    box.print_indent("Original box type      : %s" % hdr[2])
    if flags & 6:
        binid = ordq(buffer[0:8])
        box.print_indent("Stream equiv. in bin   : %d" % binid)
        hdr = box.parse_string_header(buffer[8:len(buffer)])
        buffer = hdr[0]
        box.print_indent("Stream equiv. box len  : %d" % hdr[1])
        box.print_indent("Stream equiv. box type : %s" % hdr[2])
        if flags & 4:
            csn   = ordq(buffer[0:8])
            box.print_indent("Codestream index       : %d" % csn)
            if flags & 8:
                num = ordl(buffer[0:4])
                box.print_indent("Number of codestreams  : %d" % num)

def parse_rreq_box(box,buffer):
    print("Reader Requirements Box")
    if len(buffer) < 5:
        box.print_indent("invalid box")
    ml  = ord(buffer[0])
    box.print_indent("Mask length %d" % ord(buffer[0]))
    off = 1
    box.print_indent("Fully Understand Mask :",0)
    for i in range(ml):
        print("0x%02x " % ord(buffer[off]), end=' ')
        off += 1
    print()
    box.print_indent("Display Contents Mask :",0)
    for i in range(ml):
        print("0x%02x " % ord(buffer[off]), end=' ')
        off += 1
    print()
    nsf = ordw(buffer[off:off+2])
    box.print_indent("Number of standard flags: %d" % nsf)
    off += 2
    for i in range(nsf):
        sf = ordw(buffer[off:off+2])
        off += 2
        box.print_indent(" Standard flag :",0)
        if sf == 0:
            print("writer could not fully understand file")
        elif sf == 1:
            print("no extensions (dep)")
        elif sf == 2:
            print("multiple composition layers")
        elif sf == 3:
            print("profile 0 (dep)")
        elif sf == 4:
            print("profile 1")
        elif sf == 5:
            print("full profile")
        elif sf == 6:
            print("JPEG 2000-2")
        elif sf == 7:
            print("DCT")
        elif sf == 8:
            print("no opacity (dep)")
        elif sf == 9:
            print("non-premultiplied opacity")
        elif sf == 10:
            print("premultiplied opacity")
        elif sf == 11:
            print("chroma-key opacity")
        elif sf == 12:
            print("contigous codestream (dep)")
        elif sf == 13:
            print("fragmented in-order codestream")
        elif sf == 14:
            print("fragmented out-of-order codestream")
        elif sf == 15:
            print("fragments in multiple local files")
        elif sf == 16:
            print("fragments accross the internet")
        elif sf == 17:
            print("using composition")
        elif sf == 18:
            print("compositing layer support not required (dep)")
        elif sf == 19:
            print("contains multiple layers (dep)")
        elif sf == 20:
            print("each layer contains only a single codestream (dep)")
        elif sf == 21:
            print("layers contain multiple codestreams (dep)")
        elif sf == 22:
            print("all layers in the same colorspace")
        elif sf == 23:
            print("layers in multiple colorspaces")
        elif sf == 24:
            print("animation not required (dep)")
        elif sf == 25:
            print("animated, but first layer covers entire area and is opaque")
        elif sf == 26:
            print("animated, but first layer does not cover entire area")
        elif sf == 27:
            print("animated, and no layer reused (dep)")
        elif sf == 28:
            print("animated, but layers are reused")
        elif sf == 29:
            print("animated with persistent frames only (dep)")
        elif sf == 30:
            print("animated without persistent frames only")
        elif sf == 31:
            print("no scaling required (dep)")
        elif sf == 32:
            print("scaling within a layer required")
        elif sf == 33:
            print("scaling between layer required")
        elif sf == 34:
            print("contains ROI metadata")
        elif sf == 35:
            print("contains IPR metadata")
        elif sf == 36:
            print("contains content metadata")
        elif sf == 37:
            print("contains history metadata")
        elif sf == 38:
            print("contains creation metadata")
        elif sf == 39:
            print("digitally signed")
        elif sf == 40:
            print("is checksummed")
        elif sf == 41:
            print("desired Graphic Arts reproduction specified")
        elif sf == 42:
            print("palettized colors (dep)")
        elif sf == 43:
            print("Restricted ICC color profiles (dep)")
        elif sf == 44:
            print("Any ICC color profiles")
        elif sf == 45:
            print("sRGB (dep)")
        elif sf == 46:
            print("sRGB-grey (dep)")
        elif sf == 47:
            print("BiLevel 1")
        elif sf == 48:
            print("BiLevel 2")
        elif sf == 49:
            print("YCbCr 1")
        elif sf == 50:
            print("YCbCr 2")
        elif sf == 51:
            print("YCbCr 3")
        elif sf == 52:
            print("PhotoYCC")
        elif sf == 53:
            print("YCCK")
        elif sf == 54:
            print("CMY")
        elif sf == 55:
            print("CMYK")
        elif sf == 56:
            print("CIELab (default)")
        elif sf == 57:
            print("CIELab with parameters")
        elif sf == 58:
            print("CIEJab (default)")
        elif sf == 59:
            print("CIEJab with parameters")
        elif sf == 60:
            print("e-sRGB")
        elif sf == 61:
            print("ROMM-RGB")
        elif sf == 62:
            print("non-square samples")
        elif sf == 63:
            print("layers have labels (dep)")
        elif sf == 64:
            print("codestreams have labels (dep)")
        elif sf == 66:
            print("layers have different metadata (dep)")
        elif sf == 67:
            print("GIS metadata XML box")
        elif sf == 68:
            print("JPSEC extensions")
        elif sf == 69:
            print("JP3D extensions")
        elif sf == 71:
            print("e-sYCC")
        elif sf == 72:
            print("JPX baseline")
        elif sf == 73:
            print("YPbPr(1125/60)")
        elif sf == 74:
            print("YPbPr(1250/50)")
        elif sf == 75:
            print("JPEG XR Codestream")
        elif sf == 76:
            print("JPEG XR Sub Baseline")
        elif sf == 77:
            print("JPEG XR Baseline")
        elif sf == 78:
            print("JPEG XR Main Profile")
        elif sf == 79:
            print("JPEG XR Advanced")
        elif sf == 80:
            print("Fix point data format")
        elif sf == 81:
            print("Floating point data format")
        elif sf == 82:
            print("Mantissa Exponent data format")
        elif sf == 83:
            print("scRGB color space")
        else:
            print("unknown standard flag %d " % sf)

        box.print_indent(" Standard mask :",0)
        for j in range(ml):
            print("0x%02x " % ord(buffer[off]), end=' ')
            off += 1
        print()
    nv = ordw(buffer[off:off+2])
    off += 2
    box.print_indent(" Number of vendor features : %d" % nv)
    for i in range(nv):
        box.print_indent(" Vendor feature UUID: ",0)
        print("%02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x" % \
              (ord(buffer[off+ 0]), ord(buffer[off+ 1]), ord(buffer[off+ 2]), ord(buffer[off+ 3]),
               ord(buffer[off+ 4]), ord(buffer[off+ 5]), ord(buffer[off+ 6]), ord(buffer[off+ 7]),
               ord(buffer[off+ 8]), ord(buffer[off+ 9]), ord(buffer[off+10]), ord(buffer[off+11]),
               ord(buffer[off+12]), ord(buffer[off+13]), ord(buffer[off+14]), ord(buffer[off+15])))
        off += 16
        box.print_indent(" Vendor mask : ",0)
        for j in range(ml):
            print("0x%02x " % ord(buffer[off]), end=' ')
            off += 1
        print()

def parse_uuid_box(box,buffer):
    print("UUID box")
    if len(buffer) < 16:
        box.print_indent("invalid box")
        return
    box.print_indent("UUID      :",0)
    uuid = buffer[0:16]
    if uuid == "\x2d\x41\x21\xde\xb0\xf1\x47\x43\x83\x5b\x00\xf4\x0b\xae\xc2\xed":
        print("Pegasus J2K branding")
        avbrand = 1
    else:
        print("%02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x" % \
              (ord(uuid[ 0]), ord(uuid[ 1]), ord(uuid[ 2]), ord(uuid[ 3]),
               ord(uuid[ 4]), ord(uuid[ 5]), ord(uuid[ 6]), ord(uuid[ 7]),
               ord(uuid[ 8]), ord(uuid[ 9]), ord(uuid[10]), ord(uuid[11]),
               ord(uuid[12]), ord(uuid[13]), ord(uuid[14]), ord(uuid[15])))
        avbrand = 0
    box.print_indent("UUID Data :")
    if avbrand and len(buffer) >= 20:
        box.print_indent("Pegasus Version: %d " % ordl(buffer[16:20]))
        if len(buffer) > 20:
            print("Additional Data:")
            box.print_hex(buffer[20:])
    else:
        print()
        box.print_hex(buffer[16:])

def parse_filetype_box(box,buffer):
    box.print_indent("File Type box");

    if len(buffer) < 8 or len(buffer) % 4 != 0:
        box.print_indent("invalid box")
        
    # Print BR (brand)
    if buffer[0:4] == "jp2 ":
        brand = "JP2"
    elif buffer[0:4] == "jpxb":
        brand = "JPX baseline"
    elif buffer[0:4] == "jpx ":
        brand = "JPX"
    elif buffer[0:4] == "mjp2":
        brand = "mjp2"
    elif buffer[0:4] == "mjps":
        brand = "mjp2"
    elif buffer[0:4] == "jpxt":
        brand = "JPEG XT"
    elif buffer[0:4] == "jxs ":
        brand = "JPEG XS"
    else:
        brand = "0x%02x%02x%02x%02x" % \
                (ord(buffer[0]),ord(buffer[1]),ord(buffer[2]),ord(buffer[3]))
    box.print_indent("Brand        : %s" % brand)
    
    # Print MinV (minor version)
    minv = ordl(buffer[4:8])
    box.print_indent("Minor version: %d" % (minv))
    # Print CL (Compatibility List)
    box.print_indent("Compatibility:",0)
    clsize = (len(buffer) - 8) / 4
    for i in range(clsize):
        offset = i * 4 + 8
        if buffer[offset:offset+4] == "jp2 ":
            print("JPEG2000", end=' ')
        elif buffer[offset:offset+4] == "J2P0":
            print("JPEG2000,Profile 0", end=' ')
        elif buffer[offset:offset+4] == "J2P1":
            print("JPEG2000,Profile 1", end=' ')
        elif buffer[offset:offset+4] == "jpxb":
            print("JPEG2000-2,JPX", end=' ')
        elif buffer[offset:offset+4] == "jpx ":
            print("JPEG2000-2", end=' ')
        elif buffer[offset:offset+4] == "mjp2":
            print("Motion JPEG2000", end=' ')
        elif buffer[offset:offset+4] == "mjps":
            print("Motion JPEG2000,Simple profile", end=' ')
        elif buffer[offset:offset+4] == "jpxt":
            print("JPEG XT", end=' ')
        elif buffer[offset:offset+4] == "jxs ":
            print("JPEG XS", end=' ')
        elif buffer[offset:offset+4] == "irfp":
            print("JPEG XT Intermediate Range Coding", end=' ')
        elif buffer[offset:offset+4] == "xrdd":
            print("JPEG XT HDR Coding profile A", end=' ')
        elif buffer[offset:offset+4] == "xrxd":
            print("JPEG XT HDR Coding profile B", end=' ')
        elif buffer[offset:offset+4] == "xrad":
            print("JPEG XT HDR Coding profile C", end=' ')
        elif buffer[offset:offset+4] == "xrrf":
            print("JPEG XT HDR Coding profile D", end=' ')
        elif buffer[offset:offset+4] == "lsfp":
            print("JPEG XT Lossless coding", end=' ')
        elif buffer[offset:offset+4] == "acfp":
            print("JPEG XT alpha coding full profile", end=' ')
        elif buffer[offset:offset+4] == "acbp":
            print("JPEG XT alpha coding base profile", end=' ')
        else:
            print("0x%02x%02x%02x%02x" % \
                  (ord(buffer[offset + 0]),
                   ord(buffer[offset + 1]),
                   ord(buffer[offset + 2]),
                   ord(buffer[offset + 3])), end=' ')
    print()

    
def parse_image_header_box(box,buffer):
        print("Image Header box")
        if len(buffer) != 14:
            box.print_indent ("invalid box")
            return
        box.print_indent("Height               : %d" % ordl(buffer[0:4]))
        box.print_indent("Width                : %d" % ordl(buffer[4:8]))
        box.print_indent("Components           : %d" % ordw(buffer[8:10]))
        box.print_indent("Bits Per Component   : %d" % 
              ((ord(buffer[10]) & 0x7f) + 1))
        box.print_indent("Signed Components    :",0)
        if ord(buffer[10]) & 0x80:
            print("yes")
        else:
            print("no")
        box.print_indent("Compression Type     :",0)
        if ord(buffer[11]) == 0:
            print("uncompressed")
        elif ord(buffer[11]) == 1:
            print("ITU T.4 / modified Huffman")
        elif ord(buffer[11]) == 2:
            print("ITU T.4 / modified READ")
        elif ord(buffer[11]) == 3:
            print("ITU T.6 / modified modified READ")
        elif ord(buffer[11]) == 4:
            print("JBIG")
        elif ord(buffer[11]) == 5:
            print("JPEG")
        elif ord(buffer[11]) == 6:
            print("JPEG-LS")
        elif ord(buffer[11]) == 7:
            print("JPEG 2000")
        elif ord(buffer[11]) == 8:
            print("JBIG2")
        elif ord(buffer[11]) == 9:
            print("JBIG")
        elif ord(buffer[11]) == 11:
            print("JPEG XR")
        elif ord(buffer[11]) == 12:
            print("JPEG XS")
        else:
            print("unknown (%s)" % ord(buffer[11]))
        box.print_indent("Unknown Colourspace  :",0)
        if ord(buffer[12]) == 0:
            print("no")
        elif ord(buffer[12]) == 1:
            print("yes")
        else:
            print("invalid value")
        box.print_indent("Intellectual Property:",0)
        if ord(buffer[13]) == 0:
            print("no")
        elif ord(buffer[13]) == 1:
            print("yes")
        else:
            print("invalid value")

def parse_bpc_box(box,buffer):
        print("Bits Per Component box")

        bpc = len(buffer)
        for i in range(bpc):
            b = ord(buffer[i])
            depth = (b & 0x7f) + 1
            sign  = b & 0x80
            if sign:
                sign = "yes"
            else:
                sign = "no"
            box.print_indent("Bit Depth #%d: %d" % (i, depth))
            box.print_indent("Signed    #%d: %s" % (i, sign))

def parse_colorspec_box(box,buffer):
        print("Colour Specification box")

        if len(buffer) < 3:
            box.print_indent("invalid box")
            return
        # Unfortunately, this thing comes in two variants, the
        # jp2-inherited variant, and the iso-bmff variant.
        # Urgh. Try a best-attempt to find out what it is.
        id     = buffer[0:4]
        offset = 4
        if id == "nclx":
            method = 5
        elif id == "rICC":
            method = 2
        elif id == "prof":
            method = 3
        else:
            method = ord(buffer[0])
            offset = 3
        box.print_indent("Colour Specification Method:",0)
        if method == 1:
            print("enumerated colourspace")
        elif method == 2:
            print("restricted ICC profile")
        elif method == 3:
            print("full icc profile")
        elif method == 4:
            print("parametric colourspace")
        elif method == 5:
            print("coding independent code points")
        else:
            print("unknown")
        if offset == 3:
            prec = ord(buffer[1])
            if prec >= 128:
                prec -= 256;
                box.print_indent("Precedence   : %d" % prec)
                box.print_indent("Approximation: %d" % ord(buffer[2]))
        if method == 1:
            cs = ordl(buffer[offset:offset + 4])
            if len(buffer) != 7 and cs != 19 and cs != 14:
                box.print_indent("invalid box")
                return
            box.print_indent("Colourspace  :",0)
            if cs == 16:
                print("sRGB")
            elif cs == 17:
                print("greyscale")
            elif cs == 18:
                print("YCC")
            elif cs == 14:
                print("CIELab")
                if len(buffer) != 7+4*7:
                    box.print_indent("invalid box")
                    return
                rl = ordl(buffer[offset + 4:offset + 8])
                ol = ordl(buffer[offset + 8:offset + 12])
                ra = ordl(buffer[offset + 12:offset + 16])
                oa = ordl(buffer[offset + 16:offset + 20])
                rb = ordl(buffer[offset + 20:offset + 24])
                ob = ordl(buffer[offset + 24:offset + 28])
                il = ordl(buffer[offset + 28:offset + 32])
                box.print_indent("Range  L     : %d" % rl)
                box.print_indent("Origin L     : %d" % ol)
                box.print_indent("Range  a     : %d" % ra)
                box.print_indent("Origin a     : %d" % oa)
                box.print_indent("Range  b     : %d" % rb)
                box.print_indent("Origin b     : %d" % ob)
                box.print_indent("Illuminant   : %08x" % il)
            elif cs == 19:
                print("CIEJab")
                if len(buffer) != 7+4*6:
                    box.print_indent("invalid box")
                    return
                rj = ordl(buffer[offset + 4:offset + 8])
                oj = ordl(buffer[offset + 8:offset + 12])
                ra = ordl(buffer[offset + 12:offset + 16])
                oa = ordl(buffer[offset + 16:offset + 20])
                rb = ordl(buffer[offset + 20:offset + 24])
                ob = ordl(buffer[offset + 24:offset + 28])
                box.print_indent("Range  J     : %d" % rj)
                box.print_indent("Origin J     : %d" % oj)
                box.print_indent("Range  a     : %d" % ra)
                box.print_indent("Origin a     : %d" % oa)
                box.print_indent("Range  b     : %d" % rb)
                box.print_indent("Origin b     : %d" % ob)
            elif cs == 20:
                print("esRGB")
            elif cs == 21:
                print("rommRGB")
            elif cs == 24:
                print("esYCC")
            elif cs == 25:
                print("scRGB")
            elif cs == 0:
                print("black on white")
            elif cs == 1:
                print("YCbCr(1)")
            elif cs == 3:
                print("YCbCr(2)")
            elif cs == 4:
                print("YCbCr(3)")
            elif cs == 9:
                print("PhotoYCC")
            elif cs == 11:
                print("CMY")
            elif cs == 12:
                print("CMYK")
            elif cs == 13:
                print("YCCK")
            elif cs == 15:
                print("white on black")
            elif cs == 22:
                print("YPbPr(1125/60)")
            elif cs == 23:
                print("YPbPr(1250/50)")
            else:
                print("unknown (%d)" % (cs))
        elif method == 2 or method == 3:
            box.print_indent("ICC Colour Profile:")
            parse_icc(box.indent,buffer[offset:])
            #box.print_hex(buffer[3:])
        elif method == 5:
            cp = ordw(buffer[offset:offset + 2])
            tc = ordw(buffer[offset + 2:offset + 4])
            mc = ordw(buffer[offset + 4:offset + 6])
            v  = ord(buffer[offset + 6:offset + 7])
            if cp == 1 and tc == 13 and mc == 0 and v == 0:
                colorspec = "IEC 61966-2-1 sRGB"
            elif cp == 1 and tc == 13 and mc == 1 and v == 0:
                colorspec = "IEC 61966-2-1 sYCC"
            elif cp == 1 and tc == 1 and mc == 1 and v == 0:
                colorspec = "BT.709-6 full range"
            elif cp == 1 and tc == 1 and mc == 1 and v == 128:
                colorspec = "BT.709-6 with head & toe region"
            elif cp == 5 and tc == 6 and mc == 5 and v == 0:
                colorspec = "BT.601-7 625 full range"
            elif cp == 5 and tc == 6 and mc == 5 and v == 128:
                colorspec = "BT.601-7 625 with head & toe region"
            elif cp == 6 and tc == 6 and mc == 6 and v == 0:
                colorspec = "BT.601-7 525 full range"
            elif cp == 6 and tc == 6 and mc == 6 and v == 128:
                colorspec = "BT.601-7 525 with head & toe region"
            elif cp == 9 and (tc == 14 or tc == 15) and (mc == 9 or mc == 10) and v == 0:
                colorspec = "BT.2020-2 full range"
            elif cp == 9 and (tc == 14 or tc == 15) and (mc == 9 or mc == 10) and v == 128:
                colorspec = "BT.2020-2 with head & toe region"
            elif cp == 9 and (tc == 16 or tc == 18) and mc == 9 and v == 0:
                colorspec = "BT.2100-0 full range"
            elif cp == 9 and (tc == 16 or tc == 18) and mc == 9 and v == 128:
                colorspec = "BT.2100-0 with head & toe region"
            elif cp == 10 and tc == 17 and mc == 0 and v == 0:
                colorspec = "SMPTE ST 428-1"
            elif cp == 11 and tc == 17 and mc == 0 and v == 0:
                colorspec = "SMPTE RP 431-2"
            elif cp == 12 and tc == 17 and mc == 0 and v == 0:
                colorspec = "SMPTE EG 432-1"
            else:
                if v == 0:
                    vrange = "full range"
                elif v == 128:
                    vrange = "with head & toe region"
                else:
                    vrange = "invalid (%s)" % v
                colorspec = "Primaries: %d, Transfer: %d, Matrix: %d %s" % (cp,tc,mc,vrange)
            box.print_indent("Colour Space      : %s" % colorspec)
        else:
            box.print_indent("Colour Data:")
            box.print_hex(buffer[offset:])

def parse_palette_box(box, buffer):
        print("Palette box")
        if len(buffer) < 3:
            box.print_indent("invalid box")
            return
        ne = ordw(buffer[0:2])
        box.print_indent("Entries         : %d" % ne)
        npc = ord(buffer[2])
        box.print_indent("Created Channels: %d" % npc)
        # Read B[n] list
        if len(buffer) - 3 < npc:
            box.print_indent("invalid box")
            return
        depths     = []
        entrysizes = []
        entrysize  = 0  # byte size of one palette row
        for i in range(npc):
            b = ord(buffer[3 + i])
            depth = (b & 0x7f) + 1
            depths.append(depth)
            if b & 0x80:
                sign = "yes"
            else:
                sign = "no"
            box.print_indent("Depth  #%d : %d" % (i, depth))
            box.print_indent("Signed #%d : %s" % (i, sign))
            es = depth / 8
            if depth % 8 != 0:
                es = es + 1
            entrysizes.append(es)
            entrysize = entrysize + es

        # Read C[n,m] list
        if len(buffer) - 3 - npc != entrysize * ne:
            box.print_indent("invalid box")
            return
        pos = 3 + npc
        for i in range(ne):
            box.print_indent("Entry #%03d:" % (i),0)
            values = []
            for j in range(npc):
                v = 0
                for k in range(entrysizes[j]):
                    v = v << 8
                    v = v + ord(buffer[pos])
                    pos = pos + 1
                print("0x%010x" % (v), end=' ')
            print()

def parse_cmap_box(box,buffer):
        print("Component Mapping box")
        if len(buffer) % 4 != 0:
            box.print_indent("invalid box")
            return
        entries = len(buffer) / 4
        for i in range(entries):
            cmp  = ordw(buffer[i * 4 + 0:i * 4 + 2])
            mtyp = ord(buffer[i * 4 + 2])
            pcol = ord(buffer[i * 4 + 3])
            box.print_indent("Component      #%d: %d" % (i, cmp))
            box.print_indent("Mapping Type   #%d:" % (i),0)
            if mtyp == 0:
                print("direct use")
            elif mtyp == 1:
                print("palette mapping")
            else:
                print("unknown")
            box.print_indent("Palette Column #%d: %d" % (i,pcol))

def parse_opct_box(box,buffer):
        print("Opacity box")
        if len(buffer) < 1:
            box.print_indent("invalid box")
            return
        typ = ord(buffer[0])
        if typ == 0:
            box.print_indent("Opacity Type             : last channel is opacity channel")
        elif typ == 1:
            box.print_indent("Opacity Type             : last channel is premultiplied opacity channel");
        elif typ == 2:
            if len(buffer) < 2:
                box.print_indent("invalid box")
            box.print_indent("Opacity Type             : opacity by chroma key");
            nch = ord(buffer[1])
            # The following is actually a bug. I need to know the bit depth
            # to parse the opacity channel, but the bit depth is not in here.
            for i in range(nch):
                box.print_indent("Chroma key for channel #%d: 0x%02x" % (i,ord(buffer[2+i])))
                
                
def parse_cdef_box(box,buffer):
        print("Channel Definition box")
        if len(buffer) < 2:
            box.print_indent("invalid box")
            return
        num = ordw(buffer[0:2])
        if len(buffer) - 2 != num * 6:
            box.print_indent("invalid box")
            return
        for i in range(num):
            cn   = ordw(buffer[i * 6 + 2:i * 6 + 4])
            typ  = ordw(buffer[i * 6 + 4:i * 6 + 6])
            asoc = ordw(buffer[i * 6 + 6:i * 6 + 8])
            box.print_indent("Channel     #%d: %d" % (i, cn))
            box.print_indent("Type        #%d:" % (i),0)
            if typ == 0:
                print("color")
            elif typ == 1:
                print("opacity")
            elif typ == 2:
                print("premultiplied opacity")
            elif typ == 3:
                print("application defined color")
            elif typ == 0xffff:
                print("unspecified")
            else:
                print("unknown")
            box.print_indent("Association #%d:" % (i),0)
            if asoc == 0:
                print("whole image")
            elif asoc == 0xffff:
                print("none")
            else:
                print("%x" % asoc)

def parse_label_box(box,buffer):
    print("Label box")
    box.print_indent("Content : %s" % buffer)

def parse_nlst_box(box,buffer):
    box.print_indent("Number list box")
    size = len(buffer)
    if size < 4 or size % 4 != 0:
        box.print_indent("invalid box")
        return
    size = size / 4
    box.print_indent("Number of entries   : %d" % size)
    offset = 0
    for i in range(size):
        an = ordl(buffer[offset + 0:offset + 4])
        if an == 0:
            asoc = "the rendered result"
        else:
            atyp = an >> 24
            aid  = an & 0x00ffffff
            if atyp == 1:
                asoc = "codestream # %d" % aid
            elif atyp == 2:
                asoc = "compositing layer # %d" % aid
            else:
                asoc = "invalid association # %d" % aid
        box.print_indent("Association to item : %s" % asoc)
        offset += 4
    
def parse_copt_box(box,buffer):
    box.print_indent("Composition options box")
    if len(buffer) != 9:
        box.print_indent("invaild box")
        return
    height = ordl(buffer[0:4])
    width  = ordl(buffer[4:8])
    loop   = ord(buffer[8])
    box.print_indent("Rendered result width  : %d" % width)
    box.print_indent("Rendered result height : %d" % height)
    box.print_indent("Looping count          : %d" % loop)

def parse_inst_box(box,buffer):
    box.print_indent("Instruct set box");
    if len(buffer) < 8:
        box.print_indent("invalid box")
        return
    ityp  = ordw(buffer[0:2])
    rept  = ordw(buffer[2:4])
    tick  = ordl(buffer[4:8])
    size = 0
    if ityp & 1:
        offsets = "yes"
        size   += 8
    else:
        offsets = "no"
    if ityp & 2:
        dimens  = "yes"
        size   += 8
    else:
        dimens  = "no"
    if ityp & 4:
        life    = "yes"
        size   += 8
    else:
        life    = "no"
    if ityp & 32:
        crop    = "yes"
        size   += 16
    else:
        crop    = "no"
    box.print_indent("Layer offsets required            : %s" % offsets)
    box.print_indent("Layer scaling required            : %s" % dimens)
    box.print_indent("Life time and persistence included: %s" % life)
    box.print_indent("Image cropping required           : %s" % crop)
    box.print_indent("Number of repetitions             : %d" % rept)
    box.print_indent("Duration of a timer tick          : %dms" % tick)
    offset = 8
    length = len(buffer) - offset
    if size != 0:
        if length % size != 0:
            box.print_indent("invalid box length")
            return
        entries = length / size
    else:
        if length != 0:
            box.print_indent("invalid box length")
            return
        entries = 0
    box.print_indent("Number of instructions            : %d" % entries)
    for i in range(entries):
        box.print_indent("")
        box.print_indent("Instruction #                     : %d" % (i+1))
        if ityp & 1:
            offx = ordl(buffer[offset + 0:offset + 4])
            offy = ordl(buffer[offset + 4:offset + 8])
            box.print_indent("Horizontal layer offset           : %d" % offx)
            box.print_indent("Vertical   layer offset           : %d" % offy)
            offset += 8
        if ityp & 2:
            width = ordl(buffer[offset + 0:offset + 4])
            height= ordl(buffer[offset + 4:offset + 8])
            box.print_indent("Scaled layer width                : %d" % width)
            box.print_indent("Scaled layer height               : %d" % height)
            offset += 8
        if ityp & 4:
            if ord(buffer[offset]) & 0x80:
                persist = "yes"
            else:
                persist = "no"
            life = ordl(buffer[offset + 0:offset + 4]) & 0x7fffffff
            use  = ordl(buffer[offset + 4:offset + 8])
            box.print_indent("Layer pixels shall persist        : %s" % persist)
            if life == (1 << 31) - 1:
                box.print_indent("Layer life time                   : forever")
            else:
                box.print_indent("Layer life time                   : %d" % life)                
            box.print_indent("Number of instructions to resual  : %d" % use)
            offset += 8
        if ityp & 32:
            xc  = ordl(buffer[offset + 0:offset + 4])
            yc  = ordl(buffer[offset + 4:offset + 8])
            wc  = ordl(buffer[offset + 8:offset + 12])
            hc  = ordl(buffer[offset + 12:offset + 16])
            box.print_indent("Horizontal cropping offset        : %d" % xc)
            box.print_indent("Vertical   cropping offset        : %d" % yc)
            box.print_indent("Cropped width                     : %d" % wc)
            box.print_indent("Cropped height                    : %d" % hc)
            offset += 16
                    
def parse_creg_box(box,buffer):
    box.print_indent("Codestream registration box")
    if len(buffer) < 4:
        box.print_indent("invalid box")
        return
    xs     = ordw(buffer[0:2])
    ys     = ordw(buffer[2:4])
    box.print_indent("Horizontal grid size  : %d" % xs)
    box.print_indent("Vertical   grid size  : %d" % ys)
    offset = 4
    length = len(buffer) - offset
    if length % 6 != 0:
        box.print_indent("invalid box length")
    entries = length / 6
    for i in range(entries):
        cod  = ordw(buffer[offset + 0:offset + 2])
        xr   =  ord(buffer[offset + 2])
        yr   =  ord(buffer[offset + 3])
        xo   =  ord(buffer[offset + 4])
        yo   =  ord(buffer[offset + 5])
        box.print_indent("Codestream number     : %d" % cod)
        box.print_indent("Horizontal resolution : %d" % xr)
        box.print_indent("Vertical   resolution : %d" % yr)
        box.print_indent("Horizontal offset     : %d" % xo)
        box.print_indent("Vertical   offset     : %d" % yo)
        offset = offset + 6
    
def parse_flst_box(box,buffer):
    box.print_indent("Fragment list box")
    offset  = 0
    nf      = (ord(buffer[offset]) << 8) + (ord(buffer[offset+1]))
    offset += 2
    for i in range(nf):
        off = ordq(buffer[offset + 0:offset + 8])
        ln  = ordl(buffer[offset + 8:offset + 12])
        dr  = ordw(buffer[offset + 12:offset + 14])
        box.print_indent("fragment start: %10d, size %10d, data xref %x" % (off,ln,dr))
        offset += 14

def parse_cref_box(box,buffer):
    print("Cross reference box")
    if len(buffer) < 14:
        box.print_indent("invalid box")
        return
    type = buffer[0:4]
    box.print_indent("Referenced box: %s" % type)
    size = buffer[4:8]
    type = buffer[8:12]
    if type == "flst":
        box.new_box("\"%s\"" % (type))
        parse_flst_box(box,buffer[12:len(buffer)])
        box.end_box
    else:
        box.print_indent("sub-box %s is not a fragment list box" % type)

def parse_signature_box(box,buffer):
    print("JP2 Signature box")
    box.print_indent("Corrupted:",0)
    if buffer == "\x0d\x0a\x87\x0a":
        print("no")
    else:
        print("yes")

def parse_xml_box(box,buffer):
    print("XML box")
    box.print_indent("Data:")
    s = buffer
    if s[len(s) - 1] == "\0":
        s = s[:len(s) - 2]
    box.print_indent(s.decode('utf-8'))

def parse_uuidlist_box(box,buffer):
    print("UUID List box")

    if len(buffer) < 2:
        box.print_indent("invalid box")
        return
    ne = ordw(buffer[0:2])
    if len(buffer) != ne * 16 + 2:
        box.print_indent("invalid box")
        return

    for i in range(0, ne):
        box.print_indent("UUID #%d: %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x" \
                         % (i, \
                            ord(buffer[ 2]), ord(buffer[ 3]), ord(buffer[ 4]),
                            ord(buffer[ 5]), ord(buffer[ 6]), ord(buffer[ 7]),
                            ord(buffer[ 8]), ord(buffer[ 9]), ord(buffer[10]),
                            ord(buffer[11]), ord(buffer[12]), ord(buffer[13]),
                            ord(buffer[14]), ord(buffer[15]), ord(buffer[16]),
                            ord(buffer[17])))
        buffer = buffer[16:]

def parse_url_box(box,buffer):
    print("Data Entry URL box")

    if len(buffer) < 5:
        box.print_indent("invalid box")
        return

    box.print_indent("Version: %d" % ord(buffer[0]))
    box.print_indent("Flags: 0x%02x%02x%02x" % \
                     (ord(buffer[1]), ord(buffer[2]), ord(buffer[3])))
    box.print_indent("URL: %s" % fromCString(buffer[4:]))

def parse_roi_box(box,buffer):
    print("ROI description box")

    if len(buffer) < 1:
        box.print_indent("invalid box")

    count = ord(buffer[0])
    box.print_indent("Number of ROIs : %d" % count)
    offset = 1
    for i in range(count):
        r = ord(buffer[offset])
        if r == 0:
            present = "codestream does not contain a static ROI"
        elif r == 1:
            present = "codestream contains a static ROI"
        else:
            present = "invalid present flag"
            
        rtyp = ord(buffer[offset + 1])
        if rtyp == 0:
            shape = "rectangular"
        elif rtyp == 1:
            shape = "elliptical"
        else:
            shape = "invalid"

        prior  = ord(buffer[offset + 2])
        xpos   = ordl(buffer[offset + 3:offset + 7])
        ypos   = ordl(buffer[offset + 7:offset + 11])
        width  = ordl(buffer[offset + 11:offset + 15])
        height = ordl(buffer[offset + 15:offset + 19])

        print()
        box.print_indent("ROI entry #    : %d" % i)
        box.print_indent("ROI present    : %s" % present)
        box.print_indent("ROI shape      : %s" % shape)
        box.print_indent("Priority       : %d" % prior)
        box.print_indent("XPos           : %d" % xpos)
        box.print_indent("YPos           : %d" % ypos)
        box.print_indent("Width          : %d" % width)
        box.print_indent("Height         : %d" % height)

        offset += 19

def parse_mvhd_box(box,buffer):
    print("Movie header box")
    
    box.print_versflags(buffer)
    if version(buffer) == 1:
        creation = ordq(buffer[ 4:12])
        modific  = ordq(buffer[12:20])
        scale    = ordl(buffer[20:24])
        duration = ordq(buffer[24:32])
        offset   = 32
    elif version(buffer) == 0:
        creation = ordl(buffer[ 4: 8])
        modific  = ordl(buffer[ 8:12])
        scale    = ordl(buffer[12:16])
        duration = ordl(buffer[16:20])
        offset   = 20
    else:
        box.print_indent("invalid box version")

    box.print_indent("Creation time         : %s" % secsToTime(creation))
    box.print_indent("Modification time     : %s" % secsToTime(creation))
    box.print_indent("Ticks per second      : %d" % scale)
    box.print_indent("Duration in ticks     : %d" % duration)
    box.print_indent("Playback rate         : %f" % (ordl(buffer[offset:offset+4]) / 65536.0))
    box.print_indent("Playback volume       : %f" % (ordw(buffer[offset+4:offset+6]) / 256.0))
    offset = offset + 16
    for j in range(3):
        for i in range(3):
            if j == 2:
                scale = 1 << 30
            else:
                scale = 1 << 16
            box.print_indent("Matrix [%d,%d]          : %f" % \
                             (i+1,j+1,(ordl(buffer[offset:offset+4]) / float(scale))))
            offset = offset + 4
    offset = offset + 6*4
    box.print_indent("Next Track ID         : %d" % ordl(buffer[offset:offset+4]))

def parse_tkhd_box(box,buffer):
    print("Track header box")
    
    box.print_versflags(buffer)
    if version(buffer) == 1:
        creation = ordq(buffer[ 4:12])
        modific  = ordq(buffer[12:20])
        tid      = ordl(buffer[20:24])
        duration = ordq(buffer[28:36])
        offset   = 36
    elif version(buffer) == 0:
        creation = ordl(buffer[ 4: 8])
        modific  = ordl(buffer[ 8:12])
        tid      = ordl(buffer[12:16])
        duration = ordl(buffer[20:24])
        offset   = 24
    else:
        box.print_indent("invalid box version")
        
    box.print_indent("Creation time         : %s" % secsToTime(creation))
    box.print_indent("Modification time     : %s" % secsToTime(creation))
    box.print_indent("Track ID              : %d" % tid)
    box.print_indent("Duration in ticks     : %d" % duration)

    offset = offset + 8
    box.print_indent("Layer                 : %d" % ordw(buffer[offset:offset+2]))
    box.print_indent("Volume                : %f" % (ordw(buffer[offset+4:offset+6]) / 256.0))
    offset = offset + 8
    for j in range(3):
        for i in range(3):
            if j == 2:
                scale = 1 << 30
            else:
                scale = 1 << 16
            box.print_indent("Matrix [%d,%d]          : %f" % \
                             (i+1,j+1,(ordl(buffer[offset:offset+4]) / float(scale))))
            offset = offset + 4
    box.print_indent("Width                 : %f" % (ordl(buffer[offset:offset+4]) / 65536.0))
    box.print_indent("Height                : %f" % (ordl(buffer[offset+4:offset+8]) / 65536.0))

def parse_mhdr_box(box,buffer):
    print("Broken media header box")
    box.print_versflags(buffer)
    if version(buffer) == 1:
        creation = ordq(buffer[ 4:12])
        modific  = ordq(buffer[12:20])
        scale    = ordl(buffer[20:24])
        duration = ordq(buffer[24:32])
        offset   = 32
    elif version(buffer) == 0:
        creation = ordl(buffer[ 4: 8])
        modific  = ordl(buffer[ 8:12])
        scale    = ordl(buffer[12:16])
        duration = ordl(buffer[16:20])
        offset   = 20
    else:
        box.print_indent("invalid box version")
        
    box.print_indent("Creation time         : %s" % secsToTime(creation))
    box.print_indent("Modification time     : %s" % secsToTime(creation))
    box.print_indent("Ticks per second      : %d" % scale)
    box.print_indent("Duration in ticks     : %d" % duration)

    lang = ordw(buffer[offset:offset+2])
    slang = "%c%c%c" % ((((lang >> 10) & 0x1f) + 0x60), \
                        (((lang >>  5) & 0x1f) + 0x60), \
                        (((lang >>  0) & 0x1f) + 0x60))
    box.print_indent("Language              : %s" % slang)
    
def parse_mdhd_box(box,buffer):
    print("Media header box")
    
    box.print_versflags(buffer)
    if version(buffer) == 1:
        creation = ordq(buffer[ 4:12])
        modific  = ordq(buffer[12:20])
        scale    = ordl(buffer[20:24])
        duration = ordq(buffer[24:32])
        offset   = 32
    elif version(buffer) == 0:
        creation = ordl(buffer[ 4: 8])
        modific  = ordl(buffer[ 8:12])
        scale    = ordl(buffer[12:16])
        duration = ordl(buffer[16:20])
        offset   = 20
    else:
        box.print_indent("invalid box version")
        
    box.print_indent("Creation time         : %s" % secsToTime(creation))
    box.print_indent("Modification time     : %s" % secsToTime(creation))
    box.print_indent("Ticks per second      : %d" % scale)
    box.print_indent("Duration in ticks     : %d" % duration)

    lang = ordw(buffer[offset:offset+2])
    slang = "%c%c%c" % ((((lang >> 10) & 0x1f) + 0x60), \
                        (((lang >>  5) & 0x1f) + 0x60), \
                        (((lang >>  0) & 0x1f) + 0x60))
    box.print_indent("Language              : %s" % slang)

def parse_hdlr_box(box,buffer):
    print("Handler reference box")

    box.print_versflags(buffer)
    htyp = buffer[8:12]
    if htyp == "vide":
        htyp = "video track"
    elif htyp == "soun":
        htyp = "audio track"
    elif htyp == "hint":
        htyp = "hint track"
    box.print_indent("Handler type          : %s" % htyp)
    box.print_indent("Name                  : %s" % fromCString(buffer[24:]))
    
def parse_vmhd_box(box,buffer):
    print("Video media header box")
    
    box.print_versflags(buffer)
    mode=ordw(buffer[4:6])
    op1 =ordw(buffer[6:8])
    op2 =ordw(buffer[8:10])
    op3 =ordw(buffer[10:12])

    if mode == 0x00:
        desc="copy"
    elif mode == 0x24:
        desc="transparent"
    elif mode == 0x100:
        desc="alpha"
    elif mode == 0x101:
        desc="white alpha"
    elif mode == 0x102:
        desc="black alpha"
    else:
        desc="02%x (invalid)" % mode
    box.print_indent("Graphics mode         : %s" % desc)
    box.print_indent("Red chroma key        : 0x%04x" % op1)
    box.print_indent("Green chroma key      : 0x%04x" % op2)
    box.print_indent("Blue chroma key       : 0x%04x" % op3)

def parse_smhd_box(box,buffer):
    print("Sound media header box")
    box.print_versflags(buffer)
    bal = ordw(buffer[4:6])
    if bal >= 128:
        bal = bal - 256
    box.print_indent("Balance               : %f" % (bal / 256.0))

def parse_audio_box(box,buffer,name):
    print(name)
    offset = 6
    box.print_indent("Data reference index  : %d" % ordw(buffer[offset:offset+2]))
    offset = offset + 2 + 4*2
    box.print_indent("Channel count         : %d" % ordw(buffer[offset:offset+2]))
    box.print_indent("Sample size           : %d bits" % ordw(buffer[offset+2:offset+4]))
    box.print_indent("Sample rate           : %f" % (ordl(buffer[offset+8:offset+12])/ 65536.0))
    
def parse_dref_box(box,buffer):
    print("Data reference box")

    box.print_versflags(buffer)
    count = ordl(buffer[4:8])
    box.print_indent("Number of entries     : %d" % count)
    buf = Buffer(buffer[8:])
    box = JP2Box(box,buf,8)
    box.parse(dinf_superbox_hook)

def parse_durl_box(box,buffer):
    print("Data entry url box")
    box.print_versflags(buffer)
    if flags(buffer) & 0x01:
        location = "self-contained"
    else:
        location = fromCString(buffer[4:])
    box.print_indent("URL reference is      : %s" % location)

def parse_durn_box(box,buffer):
    print("Data entry urn box")
    box.print_versflags(buffer)
    name     = fromCString(buffer[4:])
    location = ""
    for i in range(4,len(buffer)):
        if ord(buffer[i,i+1]) == 0:
            location = fromCString(buffer[i+1:])
            break
    box.print_indent("Resource name is      : %s" % name)
    box.print_indent("URL reference is      : %s" % location)
   
            
def dinf_superbox_hook(box,id,len):
    if id == "url ":
        parse_durl_box(box,box.readbody())
    elif id == "urn ":
        parse_durn_box(box,box.readbody())
    else:
        superbox_hook(box,id,len)

def parse_stts_box(box,buffer):
    print("Time to sample box")
    box.print_versflags(buffer)
    count = ordl(buffer[4:8])
    offset = 8
    box.print_indent("Number of entries     : %d" % count)
    for i in range(count):
        box.print_indent("Sample count          : %d" % ordl(buffer[offset:offset+4]))
        box.print_indent("Sample delta          : %d" % ordl(buffer[offset+4:offset+8]))
        offset = offset + 8

def parse_stsd_box(box,buffer):
    print("Sample description box")
    box.print_versflags(buffer)
    count = ordl(buffer[4:8])
    offset = 8
    box.print_indent("Number of entries     : %d" % count)
    buf = Buffer(buffer[8:])
    box = JP2Box(box,buf,8)
    box.parse(superbox_hook)

def parse_jxsm_box(box,buffer):
    print("Visual sample entry")
    offset = 6
    box.print_indent("Data reference index  : %d" % ordw(buffer[offset:offset+2]))
    offset = offset + 2 + 2*2 + 3*4
    box.print_indent("Width                 : %d" % ordw(buffer[offset:offset+2]))
    box.print_indent("Height                : %d" % ordw(buffer[offset+2:offset+4]))
    box.print_indent("Horizontal resolution : %f" % (ordl(buffer[offset+4:offset+8]) / 65536.0))
    box.print_indent("Vertical   resolution : %f" % (ordl(buffer[offset+8:offset+12])/ 65536.0))
    offset = offset + 12 + 4 + 2
    box.print_indent("Processor name        : %s" % fromCString(buffer[offset:offset+32]))
    offset = offset + 32
    depth  = ordw(buffer[offset:offset+2])
    if depth == 0x18:
        desc="color with no alpha"
    elif depth == 0x28:
        desc="grayscale with no alpha"
    elif depth == 0x20:
        desc="color or grayscale with alpha"
    else:
        desc="0x%02x (invalid)" % depth
    box.print_indent("Depth                 : %s" % desc)
    offset=offset+4
    buf = Buffer(buffer[offset:])
    box = JP2Box(box,buf,offset)
    box.parse(superbox_hook)
    
def parse_mjp2_box(box,buffer):
    print("Visual sample entry")
    offset = 6
    box.print_indent("Data reference index  : %d" % ordw(buffer[offset:offset+2]))
    offset = offset + 2 + 2*2 + 3*4
    box.print_indent("Width                 : %d" % ordw(buffer[offset:offset+2]))
    box.print_indent("Height                : %d" % ordw(buffer[offset+2:offset+4]))
    box.print_indent("Horizontal resolution : %f" % (ordl(buffer[offset+4:offset+8]) / 65536.0))
    box.print_indent("Vertical   resolution : %f" % (ordl(buffer[offset+8:offset+12])/ 65536.0))
    offset = offset + 12 + 4 + 2
    box.print_indent("Processor name        : %s" % fromCString(buffer[offset:offset+32]))
    offset = offset + 32
    depth  = ordw(buffer[offset:offset+2])
    if depth == 0x18:
        desc="color with no alpha"
    elif depth == 0x28:
        desc="grayscale with no alpha"
    elif depth == 0x20:
        desc="color or grayscale with alpha"
    else:
        desc="0x%02x (invalid)" % depth
    box.print_indent("Depth                 : %s" % desc)
    offset=offset+4
    buf = Buffer(buffer[offset:])
    box = JP2Box(box,buf,offset)
    box.parse(superbox_hook)

def parse_jp2p_box(box,buffer):
    print("MJP2 profile box")
    box.print_versflags(buffer)
    count  = (len(buffer) - 4) / 4
    box.print_indent("Number of entries     : %d" % count)
    offset = 4
    for i in range(count):
        box.print_indent("Compatible brand %d   : %s" % (i+1,buffer[offset:offset+4]))
        offset = offset + 4

def parse_jp2x_box(box,buffer):
    print("MJP2 prefix box")
    if not ignore_codestream:
        box = JP2Box(box,Buffer(buffer),0)
        box.parse(superbox_hook)

def parse_stsc_box(box,buffer):
    print("Sample to chunk box")
    box.print_versflags(buffer)
    count = ordl(buffer[4:8])
    box.print_indent("Number of entries     : %d" % count)
    offset = 8
    for i in range(count):
        box.print_indent("First chunk %d         : %d" % (i+1,ordl(buffer[offset:offset+4])))
        box.print_indent("Samples per chunk %d   : %d" % (i+1,ordl(buffer[offset+4:offset+8])))
        box.print_indent("Sample description %d  : %d" % (i+1,ordl(buffer[offset+8:offset+12])))
        offset = offset + 12

def parse_stsz_box(box,buffer):
    print("Sample size box")
    box.print_versflags(buffer)
    count = ordl(buffer[8:12])
    defsz = ordl(buffer[4:8])
    box.print_indent("Number of entries     : %d" % count)
    box.print_indent("Default sample size   : %d" % defsz)
    offset = 12
    if defsz == 0:
        for i in range(count):
            box.print_indent("Entry %3d size        : %d" % (i+1,ordl(buffer[offset:offset+4])))
            offset = offset + 4

def parse_stco_box(box,buffer):
    print("Chunk offset box (32 bit)")
    box.print_versflags(buffer)
    count = ordl(buffer[4:8])
    box.print_indent("Number of entries     : %d" % count)
    offset = 8
    for i in range(count):
        box.print_indent("Chunk offset %3d      : %d" % (i+1,ordl(buffer[offset:offset+4])))
        offset = offset + 4

def parse_co64_box(box,buffer):
    print("Chunk offset box (64 bit)")
    box.print_versflags(buffer)
    count = ordl(buffer[4:8])
    box.print_indent("Number of entries     : %d" % count)
    offset = 8
    for i in range(count):
        box.print_indent("Chunk offset %3d      : %d" % (i+1,ordq(buffer[offset:offset+8])))
        offset = offset + 8

def parse_trex_box(box,buffer):
    print("Track extends box")
    box.print_versflags(buffer)
    box.print_indent("Track ID              : %d" % ordl(buffer[4:8]))
    box.print_indent("Default description   : %d" % ordl(buffer[8:12]))
    box.print_indent("Default duration      : %d" % ordl(buffer[12:16]))
    box.print_indent("Default size          : %d" % ordl(buffer[16:20]))
    box.print_indent("Default flags         : %d" % ordl(buffer[20:24]))

def parse_mfhd_box(box,buffer):
    print("Movie fragment header box")
    box.print_versflags(buffer)
    box.print_indent("Sequence number       : %d" % ordl(buffer[4:8]))

def parse_tfhd_box(box,buffer):
    print("Track fragment header box")
    box.print_versflags(buffer)
    flgs = flags(buffer)
    box.print_indent("Track ID              : %d" % ordl(buffer[4:8]))
    offset = 8
    if flgs & 0x01:
        box.print_indent("Base data offset      : %d" % ordq(buffer[offset:offset+8]))
        offset = offset + 8
    if flgs & 0x02:
        box.print_indent("Sample description    : %d" % ordl(buffer[offset:offset+4]))
        offset = offset + 4
    if flgs & 0x08:
        box.print_indent("Sample duration       : %d" % ordl(buffer[offset:offset+4]))
        offset = offset + 4
    if flgs & 0x10:
        box.print_indent("Sample size           : %d" % ordl(buffer[offset:offset+4]))
        offset = offset + 4
    if flgs & 0x20:
        box.print_indent("Sample flags          : 0x%04x" % ordl(buffer[offset:offset+4]))
        offset = offset + 4
    if flgs & 0x10000:
        box.print_indent("Duration is empty");

def parse_trun_box(box,buffer):
    print("Track fragment run box")
    box.print_versflags(buffer)
    flgs  = flags(buffer)
    count = ordl(buffer[4:8])
    box.print_indent("Number of entries     : %d" % count)
    offset = 8
    if flgs & 0x01:
        box.print_indent("Data offset           : %d" % ordl(buffer[offset:offset+4]))
        offset = offset + 4
    if flgs & 0x04:
        box.print_indent("First sample flags    : %d" % ordl(buffer[offset:offset+4]))
        offset = offset + 4
    for i in range(count):
        if flgs & 0x100:
            box.print_indent("Sample duration       : %d" % ordl(buffer[offset:offset+4]))
            offset = offset + 4
        if flgs & 0x200:
            box.print_indent("Sample size           : %d" % ordl(buffer[offset:offset+4]))
            offset = offset + 4
        if flgs & 0x400:
            box.print_indent("Sample flags          : 0x%04x" % ordl(buffer[offset:offset+4]))
            offset = offset + 4
        if flgs & 0x800:
            box.print_indent("Compos. time offset   : %d" % ordl(buffer[offset:offset+4]))
            offset = offset + 4

def parse_fiel_box(box,buffer):
    print("Field coding box")
    if ord(buffer[1]) == 0:
        order="unknown"
    elif ord(buffer[1]) == 1:
        order="first line in first sample"
    elif ord(buffer[1]) == 6:
        order="first line in second sample"
    else:
        order="%d (invalid)" % ord(buffer[1])
    box.print_indent("Field count           : %d" % ord(buffer[0]))
    box.print_indent("Field order           : %s" % order)

def parse_jsub_box(box,buffer):
    print("MJP2 subsampling box")
    box.print_indent("Horizontal subsampling: %d" % ord(buffer[0]))
    box.print_indent("Vertical   subsampling: %d" % ord(buffer[1]))
    box.print_indent("Horizontal offset     : %d" % ord(buffer[2]))
    box.print_indent("Vertical offset       : %d" % ord(buffer[3]))

def parse_elst_box(box,buffer):
    print("Edit list box")
    box.print_versflags(buffer)
    vers  = version(buffer)
    if vers != 0 and vers != 1:
        box.print_indent("Invalid box version %d" % vers)
    else:
        count = ordl(buffer[4:8])
        box.print_indent("Number of entries     : %d" % count)
        offset = 8
        for i in range(count):
            if vers == 1:
                duration = ordq(buffer[offset:offset+8])
                time     = ordq(buffer[offset+8:offset+16])
                if time == 0xffffffffffffffff:
                    stime = "empty edit"
                else:
                    stime = "%d" % time
                offset   = offset + 16
            else:
                duration = ordl(buffer[offset:offset+4])
                time     = ordl(buffer[offset+4:offset+8])
                if time == 0xffffffff:
                    stime = "empty edit"
                else:
                    stime = "%d" % time
                offset   = offset + 8
            rate = ordl(buffer[offset:offset+4])
            offset = offset + 4
            box.print_indent("Segment duration      : %d" % duration)
            box.print_indent("Starting time in media: %s" % stime)
            box.print_indent("Media rate            : %f" % (rate / 65536.0))

def parse_cprt_box(box,buffer):
    print("Copyright box")
    box.print_versflags(buffer)
    lang = ordw(buffer[4:6])
    slang = "%c%c%c" % ((((lang >> 10) & 0x1f) + 0x60), \
                        (((lang >>  5) & 0x1f) + 0x60), \
                        (((lang >>  0) & 0x1f) + 0x60))
    box.print_indent("Language              : %s" % slang)
    box.print_indent("Notice                : %s" % fromCString(buffer[6:]))

def parse_jp2i_box(box,buffer):
    box.print_indent("IPR box")
    box.print_hex(buffer)

def parse_TONE_box(box,buffer):
    box.print_indent("Integer Table Lookup box")
    v = ord(buffer[0:1])
    idx = v >> 4
    rb  = v & 0x0f
    box.print_indent("Table Index      : %d" % idx)
    box.print_indent("Output Precision : %d" % (rb + 8))
    offset = 1
    entries = (len(buffer) - 1) >> 1
    box.print_indent("Table Entries    : %d" % entries)
    outbuf=""
    outcnt=0
    for i in range(entries):
        v = ordw(buffer[offset:offset+2])
        offset = offset + 2
        fmt    = "%d -> %d" % (i,v)
        outbuf = outbuf + "%-20s" % fmt
        outcnt = outcnt + 1
        if outcnt > 3:
            box.print_indent("\t"+outbuf)
            outbuf = ""
            outcnt = 0
    if outcnt > 0:
        box.print_indent("\t"+outbuf)

def parse_FTON_box(box,buffer):
    box.print_indent("Floating Point Table Lookup box")
    v = ord(buffer[0:1])
    idx = v >> 4
    box.print_indent("Table Index      : %d" % idx)
    offset = 1
    entries = (len(buffer) - 1) >> 2
    box.print_indent("Table Entries    : %d" % entries)
    outbuf=""
    outcnt=0
    for i in range(entries):
        v = ieee_float_to_float(ordl(buffer[offset:offset+4]))
        offset = offset + 4
        fmt    = "%d -> %d" % (i,v)
        outbuf = outbuf + "%-20s" % fmt
        outcnt = outcnt + 1
        if outcnt > 3:
            box.print_indent("\t"+outbuf)
            outbuf = ""
            outcnt = 0
    if outcnt > 0:
        box.print_indent("\t"+outbuf)

def parse_RFIN_box(box,buffer,id):
    if id == 'FINE':
        name = "Refinement"
    elif id == 'RFIN':
        name = "Residual Refinement"
    elif id == 'AFIN':
        name = "Alpha Refinement"
    elif id == 'ARRF':
        name = "Alpha Residual Refinement"
    else:
        name = "Unknown"
    box.print_indent("JPEG XT %s Data Box" % name)
    box.print_indent("Raw entropy coded data : %d bytes" % len(buffer))

def parse_LCHK_box(box,buffer):
    box.print_indent("JPEG XT Legacy Data Checksum box") #Wuff,Wuff, Aruff, LeChuck, Grrrrr....
    box.print_indent("Legacy data checksum : 0x%x" % ordl(buffer[0:4]))

def parse_XTColorTrafo_box(box,buffer):
    box.print_indent("JPEG XT Linear Transformation Specification Box")
    v = ord(buffer[0]) >> 4
    if v == 0:
        typ = "Invalid (zero)"
    elif v == 1:
        typ = "Identity"
    elif v == 2:
        typ = "YCbCr"
    elif v == 3:
        typ = "Invalid (three)"
    elif v == 4:
        typ = "RCT"
    else:
        typ = "FreeForm, matrix %d" % v
    box.print_indent("Transformation type : %s" % typ)

def parse_XTNLT_box(box,buffer):
    box.print_indent("JPEG XT Non-Linear Point Transformation Specification box")
    v1 = ord(buffer[0]) >> 4
    v2 = ord(buffer[0]) & 0x0f
    v3 = ord(buffer[1]) >> 4
    v4 = ord(buffer[1]) & 0x0f
    box.print_indent("Non-Linear table for component 0 : %d" % v1)
    box.print_indent("Non-Linear table for component 1 : %d" % v2)
    box.print_indent("Non-Linear table for component 2 : %d" % v3)
    box.print_indent("Non-Linear table for component 3 : %d" % v4)

def parse_MTRX_box(box,buffer):
    box.print_indent("JPEG XT Fixpoint Matrix box")
    idx = ord(buffer[0]) >> 4;
    fxp = ord(buffer[0]) & 0x0f
    box.print_indent("Matrix identifier : %d" % idx)
    box.print_indent("Fractional bits   : %d" % fxp)
    ofs = 1
    fac = 1.0 / (1 << fxp)
    mtr = ""
    cnt = 0
    for i in range(9):
        ntry = ordw(buffer[ofs:ofs+2]);
        if ntry >= 32768:
            ntry = ntry - 65536
        ntry = ntry * fac
        mtr  = mtr + "\t%16s" % ntry
        cnt  = cnt + 1
        ofs  = ofs + 2
        if cnt == 3:
            box.print_indent(mtr)
            mtr = ""
            cnt = 0

def parse_FTRX_box(box,buffer):
    box.print_indent("JPEG XT Floating point Matrix box")
    idx = ord(buffer[0]) >> 4
    fxp = ord(buffer[0]) & 0x0f
    box.print_indent("Matrix identifier : %d" % idx)
    box.print_indent("Fractional bits   : %d" % fxp)
    ofs = 1
    mtr = ""
    cnt = 0
    for i in range(9):
        ntry = ieee_float_to_float(ordl(buffer[ofs:ofs+4]))
        mtr  = mtr + "\t%16s" % ntry
        cnt  = cnt + 1
        ofs  = ofs + 4
        if cnt == 3:
            box.print_indent(mtr)
            mtr = ""
            cnt = 0

def parse_AMUL_box(box,buffer):
    box.print_indent("JPEG XT Alpha Specification box")
    mode = ord(buffer[0]) >> 4
    res1 = ord(buffer[0]) & 0x0f
    res2 = ord(buffer[1]) >> 4
    res3 = ord(buffer[1]) & 0x0f
    if mode == 0:
        smode = "Opaque"
    elif mode == 1:
        smode = "Regular"
    elif mode == 2:
        smode = "Premultiplied"
    elif mode == 3:
        smode = "MatteRemoval"
    else:
        smode = "Invalid (%d)" % mode
    box.print_indent("Alpha Mode   : %s" % smode)
    box.print_indent("Reserved1    : %d" % res1)
    box.print_indent("Reserved2    : %d" % res2)
    box.print_indent("Reserved3    : %d" % res3)
    box.print_indent("Matte Color R: 0x%04x" % ordw(buffer[2:4]))
    box.print_indent("Matte Color G: 0x%04x" % ordw(buffer[4:6]))
    box.print_indent("Matte Color B: 0x%04x" % ordw(buffer[6:8]))
    box.print_indent("Reserved     : 0x%04x" % ordw(buffer[8:10]))

def parse_OCON_box(box,buffer):
    box.print_indent("JPEG XT Output Conversion Box")
    rb = ord(buffer[0]) >> 4
    box.print_indent("Total output range in bits       : %d" % (rb + 8))
    if ord(buffer[0]) & 0x08 != 0:
        ll = "precise DCT"
    else:
        ll = "relaxed DCT syntax"
    box.print_indent("DCT Requirements                 : %s" % ll)
    if ord(buffer[0]) & 0x04 != 0:
        cst = "half-logarithmic output map"
    else:
        cst = "identity output map"
    box.print_indent("Output Data Conversion           : %s" % cst)
    if ord(buffer[0]) & 0x02 != 0:
        clmp = "enabled"
    else:
        clmp = "disabled"
    box.print_indent("Output clamping                  : %s" % clmp)
    if ord(buffer[0]) & 0x01 != 0:
        luts = "enabled"
    else:
        luts = "disabled"
    box.print_indent("Output non-linearity             : %s" % luts)
    v1 = ord(buffer[1]) >> 4
    v2 = ord(buffer[1]) & 0x0f
    v3 = ord(buffer[2]) >> 4
    v4 = ord(buffer[2]) & 0x0f
    box.print_indent("Non-Linear table for component 0 : %d" % v1)
    box.print_indent("Non-Linear table for component 1 : %d" % v2)
    box.print_indent("Non-Linear table for component 2 : %d" % v3)
    box.print_indent("Non-Linear table for component 3 : %d" % v4)

def parse_RSPC_box(box,buffer):
    box.print_indent("JPEG XT Refinement Specification Box")
    base=ord(buffer[0]) >> 4;
    resi=ord(buffer[0]) & 0x0f
    box.print_indent("Legacy   image refinement passes : %d" % base)
    box.print_indent("Residual image refinement passes : %d" % resi)

def parse_CURV_box(box,buffer):
    box.print_indent("JPEG XT parametric non-linear point transformation box")
    idx=ord(buffer[0]) >> 4
    typ=ord(buffer[0]) & 0x0f
    rmo=ord(buffer[1]) >> 4
    res=ord(buffer[1]) & 0x0f
    if typ == 0:
        curve="Zero"
    elif typ == 1:
        curve="Constant"
    elif typ == 2:
        curve="Identity"
    elif typ == 4:
        curve="Gamma"
    elif typ == 5:
        curve="Linear"
    elif typ == 6:
        curve="Exponential"
    elif typ == 7:
        curve="Logarithmic"
    elif typ == 8:
        curve="Gamma with Scaling"
    else:
        curve="Invalid curve type %d" % typ
    if rmo == 0:
        rounding="Centered"
    elif rmo == 1:
        rounding="Keep extremes"
    else:
        rounding="Invalid rounding mode %d" % rmo
    box.print_indent("Table Index        : %d" % idx)
    box.print_indent("Curve type is      : %s" % curve) 
    box.print_indent("Rounding mode is   : %s" % rounding)
    box.print_indent("Reserved field is  : %d" % res)
    p1 = str(ieee_float_to_float(ordl(buffer[2:6])))
    p2 = str(ieee_float_to_float(ordl(buffer[6:10])))
    p3 = str(ieee_float_to_float(ordl(buffer[10:14])))
    p4 = str(ieee_float_to_float(ordl(buffer[14:18])))
    box.print_indent("Curve parameter P1 : %s" % p1)
    box.print_indent("Curve parameter P2 : %s" % p2)
    box.print_indent("Curve parameter P3 : %s" % p3)
    box.print_indent("Curve parameter P4 : %s" % p4)

def parse_DCT_box(box,buffer):
    box.print_indent("JPEG XT DCT Specification box")
    dct = ord(buffer[0]) >> 4
    nsh = ord(buffer[0]) & 0x0f
    if dct == 0:
        dcttype = "Fix Point DCT"
    elif dct == 2:
        dcttype = "Integer DCT"
    elif dct == 3:
        dcttype = "DCT bypass"
    else:
        dcttype = "Invalid DCT type %d" % dct
    if nsh == 0:
        nshtype = "Disabled"
    elif nsh == 1:
        nshtype = "Enabled"
    else:
        nshtype = "Invalid noise shaping type %d" % nsh
    box.print_indent("Discrete Cosine Type : %s" % dcttype)
    box.print_indent("Noise shaping        : %s" % nshtype)

def parse_pxfm_box(box,buffer):
    box.print_indent("Pixel Format box")
    count  = ordw(buffer[0:2])
    offset = 2
    for i in range(count):
        idx    = ordw(buffer[offset:offset+2])
        fmt    = ordw(buffer[offset+2:offset+4])
        offset = offset + 4
        typ    = fmt >> 12
        if typ == 0:
            tstring = "integer"
        elif typ == 1:
            tstring = "mantissa"
        elif typ == 2:
            tstring = "exponent"
        elif typ == 3:
            tstring = "fix point, %d fractional bits" % (fmt & 0x0fff)
        elif typ == 4:
            tstring = "floating point, %d mantissa bits" % (fmt & 0x0fff)
        else:
            tstring = "invalid or unknown type"
        box.print_indent("Channel %d type: %s" % (idx,tstring))

def parse_jxvi_box(box,buffer):
    box.print_indent("JPEG XS Video Information box")
    box.print_indent("Maximum bitrate : %s MBits/sec" % ordl(buffer[0:4]))
    frat = ordl(buffer[4:8])
    lace = frat >> 30
    if lace == 0:
        frame = "progressive"
    elif lace == 1:
        frame = "long field"
    elif lace == 2:
        frame = "short field"
    else:
        frame = "invalid (reserved)"
    denominator = (frat >> 24) & 0x3f
    reserved = (frat >> 16) & 0xff
    numerator = frat & 0xffff
    if denominator == 1:
        rate = numerator / 1.0
    elif denominator == 2:
        rate = numerator / 1.001
    else:
        rate = "invalid (%s)" % denominator
    box.print_indent("Frame rate        : %s" % rate)
    box.print_indent("Frame type        : %s" % frame)
    schar = ordw(buffer[8:10])
    if (schar >> 15) == 0:
        sampling = "undefined"
    else:
        if ((schar >> 8) & 0x7f) != 0:
            sampling = "invalid"
        else:
            bitdepth = ((schar >> 4) & 0x0f) + 1
            structure = schar & 0x0f
            if structure == 0:
                subs = "4:2:2 (YCbCr)"
            elif structure == 1:
                subs = "4:4:4 (YCbCr)"
            elif structure == 2:
                subs = "4:4:4 (RGB)"
            elif structure == 4:
                subs = "4:2:2:4 (YCbCrA)"
            elif structure == 5:
                subs = "4:4:4:4 (YCbCrA)"
            elif structure == 6:
                subs = "4:4:4:4 (RGBA)"
            else:
                subs = "Invalid (%s)" % structure
            sampling = "%s@%sbpp" % (subs,bitdepth)
    box.print_indent("Samping Structure : %s" % sampling)
    box.print_indent("Time code         : %02d:%02d:%02d:%02d" % (ord(buffer[10:11]),ord(buffer[11:12]),ord(buffer[12:13]),ord(buffer[13:14])))

def parse_jxpl_box(box,buffer):
    box.print_indent("JPEG Profile and Level box")
    profile = ordw(buffer[0:2])
    level   = ordw(buffer[2:4])
    box.print_indent("Profile           : %s" % decode_Profile(profile))
    box.print_indent("Level             : %s" % decode_Level(level))
    
def parse_bmdm_box(box,buffer):
    box.print_indent("JPEG Buffer Model Description box")
    model = ord(buffer[0:1])
    rd    = ord(buffer[1:2])
    hblank= ordw(buffer[2:4])
    vblank= ordw(buffer[4:6])
    if model == 0:
        buf = "No upper limit assumed"
    elif model == 1:
        buf = "CBR with limited transmission latency"
    elif model == 2:
        buf = "CBR with variable transmission latency"
    else:
        buf = "Invalid (%s)" % model
    box.print_indent("Buffer model      : %s" % buf)
    if rd == 0:
        rdstr = "0 (ok)"
    else:
        rdstr = "invalid (%s)"
    box.print_indent("Rd                : %s" % rdstr)
    box.print_indent("Horizontal blank  : %s coefficient groups" % hblank)
    box.print_indent("Vertical blank    : %s coefficient groups" % vblank)

def parse_dmon_box(box,buffer):
    box.print_indent("Mastering Display Metadata box")
    xc0 = ordw(buffer[0:2])
    yc0 = ordw(buffer[2:4])
    xc1 = ordw(buffer[4:6])
    yc1 = ordw(buffer[6:8])
    xc2 = ordw(buffer[8:10])
    yc2 = ordw(buffer[10:12])
    box.print_indent("Red primary   X,Y  : %6s,%6s" % (xc2 * 0.00002,yc2 * 0.00002))
    box.print_indent("Green primary X,Y  : %6s,%6s" % (xc0 * 0.00002,yc0 * 0.00002))
    box.print_indent("Blue primary  X,Y  : %6s,%6s" % (xc1 * 0.00002,yc1 * 0.00002))
    lmin = ordl(buffer[12:16])
    lmax = ordl(buffer[16:20])
    box.print_indent("Min. Luminance     : %s cd/m^2" % (lmin * 0.0001))
    box.print_indent("Max. Luminance     : %s cd/m^2" % (lmax * 0.0001))
    mcll = ordw(buffer[20:22])
    mfall = ordw(buffer[22:24])
    box.print_indent("Max. Content Lum.  : %s cd/m^2" % mcll)
    box.print_indent("Max. Frame Avg. Lum: %s cd/m^2" % mfall)

def parse_jptp_box(box,buffer):
    box.print_indent("JPEG XS Video Transport Parameter box")
    slgs = ordw(buffer[0:2])
    rsnc = ord(buffer[2:3])
    tseq = ord(buffer[3:4])
    mtu  = ordw(buffer[4:6])
    box.print_indent("Slice group size  : %d slices" % slgs)
    box.print_indent("Threads           : %d cores" % rsnc)
    if tseq == 0:
        reorder = "in order"
    else:
        reorder = "invalid (%d)" % rsnc
    box.print_indent("Packet ordering   : %s" % reorder)
    box.print_indent("MTU               : %d" % mtu)

def parse_jpvi_box(box,buffer):
    box.print_indent("JPEG XS Video Information box")
    brat = ordl(buffer[0:4])
    frat = ordl(buffer[4:8])
    schar= ordw(buffer[8:10])
    hours= ord(buffer[10:11])
    mins = ord(buffer[11:12])
    secs = ord(buffer[12:13])
    frms = ord(buffer[13:14])
    box.print_indent("Bitrate           : %d MBits per second" % brat)
    interlace = (frat >> 30) & 0x03
    denom     = (frat >> 24) & 0x3f
    reserved  = (frat >> 16) & 0xff
    num       = (frat >>  0) & 0xffff
    if interlace == 0:
        frame = "progressive"
    elif interlace == 1:
        frame = "interlaced, first field"
    elif interlace == 2:
        frame = "interlaced, second field"
    else:
        frame = "invalid (%d)" % interlace
    box.print_indent("Interlace mode    : %s" % frame)
    if denom == 1:
        denominator = "1.000"
        dnumber     = 1.000
    elif denom == 2:
        denominator = "1.001"
        dnumber     = 1.001
    else:
        denominator = "invalid (%d)" % denom
        dnumber     = 0.0
    box.print_indent("Rate numerator    : %s" % num)
    box.print_indent("Rate denominator  : %s" % denominator)
    if dnumber > 0.0:
        box.print_indent("Frame rate        : %g" % (num / dnumber))
    if reserved == 0:
        resv = "ok (0)"
    else:
        resv = "invalid (%d)" % reserved
    box.print_indent("Reserved          : %s" % resv)
    
# testBit() returns a nonzero result, 2**offset, if the bit at 'offset' is one.
def testBit(int_type, offset):
    mask = 1 << offset
    return(int_type & mask)

def parse_jumd_box(box):
    box.print_indent("JUMBF Description box")
    buffer = box.infile.read()
    type= buffer[0:16]
    box.print_indent("TYPE: %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x" % \
           (type[ 0], type[ 1], type[ 2], type[ 3],
            type[ 4], type[ 5], type[ 6], type[ 7],
            type[ 8], type[ 9], type[10], type[11],
            type[12], type[13], type[14], type[15]))
    toggles= ord(buffer[16:17])
    box.print_indent("TOGGLES: %s" % bin(toggles))
    opt_start = 17
    if testBit(toggles,1):
        label_len = 0
        for i in range(opt_start,len(buffer)):
            if ord(buffer[i:i+1]) == 0:
                label_len = i
                break
        label = fromCString(buffer[opt_start:label_len])
        box.print_indent("LABEL: %s" % label)
        opt_start = label_len+1   # reset for new start
    else:
        box.print_indent("No Label")
    if testBit(toggles,2):
        id = ordl(buffer[opt_start:opt_start+4])
        box.print_indent("ID: %s" % id)
        opt_start = opt_start + 4
    else:
        box.print_indent("No ID")
    if testBit(toggles,3):
        sig= buffer[opt_start:opt_start+32]
        box.print_indent("SIGNATURE: %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x" % \
            (sig[ 0], sig[ 1], sig[ 2], sig[ 3],
             sig[ 4], sig[ 5], sig[ 6], sig[ 7],
             sig[ 8], sig[ 9], sig[10], sig[11],
             sig[12], sig[13], sig[14], sig[15],
             sig[16], sig[17], sig[18], sig[19],
             sig[20], sig[21], sig[22], sig[23],
             sig[24], sig[25], sig[26], sig[27],
             sig[28], sig[29], sig[30], sig[31]))
    else:
        box.print_indent("No Signature")

def parse_json_box(box,buffer):
    print("JSON box")
    box.print_indent("Data:")
    s = buffer
    if s[len(s) - 1] == "\0":
        s = s[:len(s) - 2]
    box.print_indent(s.decode('utf-8'))

def parse_superbox(box,boxtype):
    print(boxtype)
    box = JP2Box(box,box.infile)
    box.parse(superbox_hook)
    
def superbox_hook(box,id,length):
    if id == "jp2c" or id == "jxsH" or id == "RESI" or id == "ARES" or id == "ALFA":
        if id == "jp2c":
            print("Codestream box")
        elif id == "jxsH":
            print("JPEG XS Header box")
        elif id == "ALFA":
            print("Alpha Codestream box")
        elif id == "ARES":
            print("Residual Alpha Codestream box")
        else:
            print("Residual Codestream box")
        if not ignore_codestream:
            if hasattr(box.infile,'offset'):
                cur  = box.infile.offset
                type = box.infile.read(2)
                box.infile.seek(cur)
            else:
                type = box.infile.read(2)
                box.infile.seek(box.offset)
            if ord(type[0]) == 0x57 and ord(type[1]) == 0x4d:
                jxr = JXRCodestream(box.infile,1)
                jxr.parse()
            elif ord(type[0]) == 0xff and ord(type[1]) == 0xd8:
                cs = JPGCodestream(indent = box.indent + 1, hook = superbox_hook)
                cs.stream_parse(box.infile,box.offset)
            elif ord(type[0]) == 0xff and ord(type[1]) == 0x10:
                cs = JXSCodestream(indent = box.indent + 1)
                cs.stream_parse(box.infile,box.offset)
            else:
                cs = JP2Codestream(indent = box.indent + 1)
                cs.stream_parse(box.infile,box.offset)
    elif id == "mdat":
        print("Media data box (skipping raw box contents of %s bytes)" % length)
    elif id == "free":
         print("Free space box (skipping raw box contents of %s bytes)" % length)
    elif id == "skip":
         print("Free space box (skipping raw box contents of %s bytes)" % length)
    elif id == "jp2h":
        parse_superbox(box,"JP2 Header box")
    elif id == "jpch":
        parse_superbox(box,"Codestream Header box")
    elif id == "jplh":
        parse_superbox(box,"Compositing Layer Header box")
    elif id == "uinf":
        parse_superbox(box,"UUID Info box")
    elif id == "ftbl":
        parse_superbox(box,"Fragment table box")
    elif id == "comp":
        parse_superbox(box,"Composition box")
    elif id == "asoc":
        parse_superbox(box,"Association box")
    elif id == "res ":
        parse_superbox(box,"Resolution box")
    elif id == "cgrp":
        parse_superbox(box,"Color Group box")
    elif id == "moov":
        parse_superbox(box,"Movie box")
    elif id == "trak":
        parse_superbox(box,"Track box")
    elif id == "mdia":
        parse_superbox(box,"Media box")
    elif id == "minf":
        parse_superbox(box,"Media information box")
    elif id == "dinf":
        parse_superbox(box,"Data information box")
    elif id == "stbl":
        parse_superbox(box,"Sample table box")
    elif id == "edts":
        parse_superbox(box,"Edit box")
    elif id == "traf":
        parse_superbox(box,"Track fragment box")
    elif id == "mvex":
        parse_superbox(box,"Movie extends box")
    elif id == "moof":
        parse_superbox(box,"Movie fragment box")
    elif id == "udta":
        parse_superbox(box,"User data box")
    elif id == "SPEC":
        parse_superbox(box,"JPEG XT Merging Specification box")
    elif id == "ASPC":
        parse_superbox(box,"JPEG XT Alpha Merging Specification box")
    elif id == "jpvs":
        parse_superbox(box,"JPEG XS Video Support box")
    elif id == "jumb":
        parse_superbox(box,"JUMBF Box")
    elif id == 'jumd':
        # because there is a null term in the box, we need to do it this way...
        parse_jumd_box(box)
    else:
        buffer = box.readbody()
        if id == "jP  ": # JP2 Signature Box
            parse_signature_box(box,buffer)
        elif id == "jXS ": # JPEG XS signature box
            parse_signature_box(box,buffer)
        elif id == "phld":
            parse_placeholder_box(box,buffer)
        elif id == "ftyp":
            parse_filetype_box(box,buffer)
        elif id == "xml ":
            parse_xml_box(box,buffer)
        elif id == "uuid":
            parse_uuid_box(box,buffer)
        elif id == "rreq":
            parse_rreq_box(box,buffer)
        elif id == "cref":
            parse_cref_box(box,buffer)
        elif id == "ihdr":
            parse_image_header_box(box,buffer)
        elif id == "bpcc":
            parse_bpc_box(box,buffer)
        elif id == "colr":
            parse_colorspec_box(box,buffer)
        elif id == "pclr":
            parse_palette_box(box,buffer)
        elif id == "cmap":
            parse_cmap_box(box,buffer)
        elif id == "cdef":
            parse_cdef_box(box,buffer)
        elif id == "lbl ":
            parse_label_box(box,buffer)
        elif id == "free":
            print("Free box")
            box.print_hex(buffer)
        elif id == "resc":
            print("Capture Resolution box")
            parse_resolution_box(box,buffer)
        elif id == "resd":	
            print("Default Display Resolution box")
            parse_resolution_box(box,buffer)
        elif id == "opct":
            parse_opct_box(box,buffer)
        elif id == "creg":
            parse_creg_box(box,buffer)
        elif id == "ulst":
            parse_uuidlist_box(box,buffer)
        elif id == "url ":
            parse_url_box(box,buffer)
        elif id == "flst":
            parse_flst_box(box,buffer)
        elif id == "nlst":
            parse_nlst_box(box,buffer)
        elif id == "copt":
            parse_copt_box(box,buffer)
        elif id == "inst":
            parse_inst_box(box,buffer)
        elif id == "roid":
            parse_roi_box(box,buffer)
        elif id == "mvhd":
            parse_mvhd_box(box,buffer)
        elif id == "tkhd":
            parse_tkhd_box(box,buffer)
        elif id == "mdhd":
            parse_mdhd_box(box,buffer)
        elif id == "mhdr":
            parse_mhdr_box(box,buffer)
        elif id == "hdlr":
            parse_hdlr_box(box,buffer)
        elif id == "vmhd":
            parse_vmhd_box(box,buffer)
        elif id == "smhd":
            parse_smhd_box(box,buffer)
        elif id == "dref":
            parse_dref_box(box,buffer)
        elif id == "stts":
            parse_stts_box(box,buffer)
        elif id == "stsd":
            parse_stsd_box(box,buffer)
        elif id == "mjp2":
            parse_mjp2_box(box,buffer)
        elif id == "jxsm":
            parse_jxsm_box(box,buffer)
        elif id == "jp2p":
            parse_jp2p_box(box,buffer)
        elif id == "jp2x":
            parse_jp2x_box(box,buffer)
        elif id == "stsc":
            parse_stsc_box(box,buffer)
        elif id == "stsz":
            parse_stsz_box(box,buffer)
        elif id == "stco":
            parse_stco_box(box,buffer)
        elif id == "co64":
            parse_co64_box(box,buffer)
        elif id == "twos":
            parse_audio_box(box,buffer,"Audio sample entry (signed)")
        elif id == "raw ":
            parse_audio_box(box,buffer,"Audio sample entry (unsigned)")
        elif id == "trex":
            parse_trex_box(box,buffer)
        elif id == "mfhd":
            parse_mfhd_box(box,buffer)
        elif id == "tfhd":
            parse_tfhd_box(box,buffer)
        elif id == "trun":
            parse_trun_box(box,buffer)
        elif id == "fiel":
            parse_fiel_box(box,buffer)
        elif id == "jsub":
            parse_jsub_box(box,buffer)
        elif id == "elst":
            parse_elst_box(box,buffer)
        elif id == "cprt":
            parse_cprt_box(box,buffer)
        elif id == "jp2i":
            parse_jp2i_box(box,buffer)
        elif id == 'pxfm':
            parse_pxfm_box(box,buffer)
        elif id == 'TONE':
            parse_TONE_box(box,buffer)
        elif id == 'FTON':
            parse_FTON_box(box,buffer)
        elif id == 'RFIN':
            parse_RFIN_box(box,buffer,id)
        elif id == 'FINE':
            parse_RFIN_box(box,buffer,id)
        elif id == 'AFIN':
            parse_RFIN_box(box,buffer,id)
        elif id == 'ARRF':
            parse_RFIN_box(box,buffer,id)
        elif id == 'LCHK':
            parse_LCHK_box(box,buffer)
        elif id == 'LTRF' or id == 'RTRF' or id == 'CTRF' or id == 'DTRF' or id == 'STRF':
            parse_XTColorTrafo_box(box,buffer)
        elif id == 'LPTS' or id == 'QPTS' or id == 'RPTS' or id == 'CPTS' or id == 'SPTS' or id == 'DPTS' or id == 'PPTS':
            parse_XTNLT_box(box,buffer)
        elif id == 'OCON':
            parse_OCON_box(box,buffer)
        elif id == 'RSPC':
            parse_RSPC_box(box,buffer)
        elif id == 'CURV':
            parse_CURV_box(box,buffer)
        elif id == 'LDCT' or id == 'RDCT':
            parse_DCT_box(box,buffer)
        elif id == 'MTRX':
            parse_MTRX_box(box,buffer)
        elif id == 'FTRX':
            parse_FTRX_box(box,buffer)
        elif id == 'AMUL':
            parse_AMUL_box(box,buffer)
        elif id == 'jxvs':
            parse_jxvs_box(box,buffer)
        elif id == 'jxpl':
            parse_jxpl_box(box,buffer)
        elif id == 'bmdm':
            parse_bmdm_box(box,buffer)
        elif id == 'dmon':
            parse_dmon_box(box,buffer)
        elif id == 'jptp':
            parse_jptp_box(box,buffer)
        elif id == 'jpvi':
            parse_jpvi_box(box,buffer)
        elif id == 'json':
            parse_json_box(box,buffer)
        else:
            box.print_indent("(unknown box)")
            box.print_hex(buffer)    

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
    print("# JP2 file format log file generated by jp2file.py            #")
    print("###############################################################")
    print()

    # Parse Files
    file = open(files[0],"rb")
    type = file.read(2)
    file.seek(0)
    try:
        if type[0] == 0xff and type[1] == 0x4f:
            jp2 = JP2Codestream()
            jp2.stream_parse(file,0)
        elif type[0] == 0xff and type[1] == 0xd8:
            jpg = JPGCodestream()
            jpg.stream_parse(file,0)
        elif type[0] == 0xff and type[1] == 0x10:
            jxs = JXSCodestream()
            jxs.stream_parse(file,0)
        else:
            jp2 = JP2Box(None,file)
            jp2.parse(superbox_hook)
            
    except JP2Error as e:
        print('***', str(e))
