# -*- coding: utf-8 -*-
"""
JPEG codestream-parser (All-JPEG Codestream/File Format Parser Tools)
See LICENCE.txt for copyright and licensing conditions.
"""
from __future__ import print_function, division
import getopt
import sys

from jp2utils import ordb, ordl, ordw, print_indent, print_hex, JP2Error


def s15d(num):
    if num >= 0x80000000:
        return (num - 0x100000000) * 1.0 / 65536
    else:
        return num * 1.0 / 65536


def print_datetime(buffer, indent):
    print_indent("Year   : %d " % ordw(buffer[0:2]), indent)
    print_indent("Month  : %d " % ordw(buffer[2:4]), indent)
    print_indent("Day    : %d " % ordw(buffer[4:6]), indent)
    print_indent("Hours  : %d " % ordw(buffer[6:8]), indent)
    print_indent("Minutes: %d " % ordw(buffer[8:10]), indent)
    print_indent("Seconds: %d " % ordw(buffer[10:12]), indent)


def print_xyz(buffer, indent):
    x = ordl(buffer[0:4])
    y = ordl(buffer[4:8])
    z = ordl(buffer[8:12])
    print_indent("X : 0x%08x = %g" % (x, s15d(x)), indent)
    print_indent("Y : 0x%08x = %g" % (y, s15d(y)), indent)
    print_indent("Z : 0x%08x = %g" % (z, s15d(z)), indent)


def print_meas(buffer, indent):
    obs = ordl(buffer[0:4])
    if obs == 0:
        observer = "unknown"
    elif obs == 1:
        observer = "CIE 1931"
    elif obs == 2:
        observer = "CIE 1964"
    else:
        observer = "invalid"
    print_indent("Observer  : %s" % observer, indent)
    print_indent("Backing   :", indent)
    print_xyz(buffer[4:], indent + 1)
    geom = ordl(buffer[16:20])
    if geom == 0:
        geometry = "unknown"
    elif geom == 1:
        geometry = "0/45 or 45/0"
    elif geom == 2:
        geometry = "0/d or d/0"
    else:
        geometry = "invalid"
    print_indent("Geometry  : %s" % geometry, indent)
    flare = ordl(buffer[20:24])
    print_indent("Flare     : 0x%08x = %g%%" % (flare, flare * 100.0 / 65536.0), indent)
    ilm = ordl(buffer[24:38])
    if ilm == 0:
        illum = "unknown"
    elif ilm == 1:
        illum = "D50"
    elif ilm == 2:
        illum = "D65"
    elif ilm == 3:
        illum = "D93"
    elif ilm == 4:
        illum = "F2"
    elif ilm == 5:
        illum = "D55"
    elif ilm == 6:
        illum = "A"
    elif ilm == 7:
        illum = "E"
    elif ilm == 8:
        illum = "F8"
    else:
        illum = "invalid"
    print_indent("Illuminant: %s" % illum, indent)


def print_view(buffer, indent):
    print_indent("Illuminant:", indent)
    print_xyz(buffer, indent + 1)
    print_indent("Surround  :", indent)
    print_xyz(buffer[12:], indent + 1)
    ilm = ordl(buffer[24:38])
    if ilm == 0:
        illum = "unknown"
    elif ilm == 1:
        illum = "D50"
    elif ilm == 2:
        illum = "D65"
    elif ilm == 3:
        illum = "D93"
    elif ilm == 4:
        illum = "F2"
    elif ilm == 5:
        illum = "D55"
    elif ilm == 6:
        illum = "A"
    elif ilm == 7:
        illum = "E"
    elif ilm == 8:
        illum = "F8"
    else:
        illum = "invalid"
    print_indent("Illuminant: %s" % illum, indent)


def readsignature(buf):
    signature = ordl(buf[0:4])
    return "0 (undefined)" if signature == 0 else buf[0:4]


def print_curve(buffer, indent):
    count = ordl(buffer[0:4])
    if count == 0:
        print_indent("Identity mapping", indent)
    elif count == 1:
        gamma = ordw(buffer[4:6])
        print_indent("Gamma mapping, gamma : 0x%04x = %g" % (gamma, gamma * 1.0 / 256.0), indent)
    else:
        off = 4
        for i in range(count):
            value = ordw(buffer[off:off + 2])
            if i % 4 == 0:
                if i != 0:
                    print("")
                for j in range(indent):
                    print(" ", end=' ')
            print("0x%04x = %g " % (value, value * 1.0 / 65535), end=' ')
            off += 2
        print("")


def print_lutheader(buf, indent):
    print_indent("Input  channels  : %d" % ordb(buf[0]), indent)
    print_indent("Output channels  : %d" % ordb(buf[1]), indent)
    print_indent("Grid points      : %d" % ordb(buf[2]), indent)
    e00 = ordl(buf[4:8])
    e01 = ordl(buf[8:12])
    e02 = ordl(buf[12:16])
    e10 = ordl(buf[16:20])
    e11 = ordl(buf[20:24])
    e12 = ordl(buf[24:28])
    e20 = ordl(buf[28:32])
    e21 = ordl(buf[32:36])
    e22 = ordl(buf[36:40])
    print_indent("Matrix           : 0x%08x 0x%08x 0x%08x\t%8g\t%8g\t%8g" %
                 (e00, e01, e02, s15d(e00), s15d(e01), s15d(e02)), indent)
    print_indent("                   0x%08x 0x%08x 0x%08x\t%8g\t%8g\t%8g" %
                 (e10, e11, e12, s15d(e10), s15d(e11), s15d(e01)), indent)
    print_indent("                   0x%08x 0x%08x 0x%08x\t%8g\t%8g\t%8g" %
                 (e20, e21, e22, s15d(e20), s15d(e21), s15d(e22)), indent)


def print_matrix(buf, indent):
    e1 = ordl(buf[0:4])
    e2 = ordl(buf[4:8])
    e3 = ordl(buf[8:12])
    e4 = ordl(buf[12:16])
    e5 = ordl(buf[16:20])
    e6 = ordl(buf[20:24])
    e7 = ordl(buf[24:28])
    e8 = ordl(buf[28:32])
    e9 = ordl(buf[32:36])
    e10 = ordl(buf[36:40])
    e11 = ordl(buf[40:44])
    e12 = ordl(buf[44:48])
    print_indent("Matrix           : 0x%08x 0x%08x 0x%08x\t%8g\t%8g\t%8g" %
                 (e1, e2, e3, s15d(e1), s15d(e2), s15d(e3)), indent)
    print_indent("                   0x%08x 0x%08x 0x%08x\t%8g\t%8g\t%8g" %
                 (e4, e5, e6, s15d(e4), s15d(e5), s15d(e6)), indent)
    print_indent("                   0x%08x 0x%08x 0x%08x\t%8g\t%8g\t%8g" %
                 (e7, e8, e9, s15d(e7), s15d(e8), s15d(e9)), indent)
    print_indent("Offset           : 0x%08x 0x%08x 0x%08x\t%8g\t%8g\t%8g" %
                 (e10, e11, e12, s15d(e10), s15d(e11), s15d(e11)), indent)


def print_clut(buf, ic, oc, indent):
    of = 0
    prod = 1
    for i in range(ic):
        gp = ordb(buf[of])
        print_indent("Entries in channel %d   : %d" % (i, gp), indent)
        prod = prod * gp
        of += 1
    print_indent("Total number of entries: %d" % prod, indent)
    prec = ordb(buf[16])
    print_indent("Precision              : %d" % prec, indent)
    of = 20
    v = 0
    for j in range(prod):
        entry = ""
        for k in range(oc):
            if prec == 1:
                v = ordb(buf[of])
                of += 1
            elif prec == 2:
                v = ordw(buf[of:of + 2])
                of += 2
            if entry == "":
                entry = "%5d" % v
            else:
                entry = "%s, %5d" % (entry, v)
        print_indent("Entry %4d : %s" % (j, entry), indent)


def print_lutmAB(buf, indent):
    ic = ordb(buf[0])
    oc = ordb(buf[1])
    boffs = ordl(buf[4:8])
    mtffs = ordl(buf[8:12])
    moffs = ordl(buf[12:16])
    coffs = ordl(buf[16:20])
    aoffs = ordl(buf[20:24])
    print_indent("Input  channels   : %d" % ic, indent)
    print_indent("Output channels   : %d" % oc, indent)
    if aoffs != 0:
        print_indent("A curve           :", indent)
        print_tag(buf[aoffs - 8:], len(buf[aoffs - 8:]), indent + 2)
    if boffs != 0:
        print_indent("B curve           :", indent)
        print_tag(buf[boffs - 8:], len(buf[boffs - 8:]), indent + 2)
    if moffs != 0:
        print_indent("M curve           :", indent)
        print_tag(buf[moffs - 8:], len(buf[moffs - 8:]), indent + 2)
    if coffs != 0:
        print_indent("Color Lookup Table:", indent)
        print_clut(buf[coffs - 8:], ic, oc, indent + 2)
    if mtffs != 0:
        print_indent("Affine Trafo      :", indent)
        print_matrix(buf[mtffs - 8:], indent + 2)


def print_lut8(buf, indent):
    print_lutheader(buf, indent)
    ic = ordb(buf[0])
    oc = ordb(buf[1])
    g = ordb(buf[2])
    n = 256
    m = 256
    print_indent("Input  entries   : %d" % 256, indent)
    print_indent("Output entries   : %d" % 256, indent)
    of = 40
    for i in range(ic):
        print_indent("Input  table %d :" % i, indent)
        print_hex(buf[of:of + n], indent + 1)
        of += n
    print_indent("CLUT table :", indent)
    print_hex(buf[of:of + pow(g, ic) * oc], indent + 1)
    of += pow(g, ic) * oc
    for i in range(oc):
        print_indent("Output table %d :" % i, indent)
        print_hex(buf[of:of + m], indent + 1)
        of += m


def print_lut16(buf, indent):
    print_lutheader(buf, indent)
    ic = ordb(buf[0])
    oc = ordb(buf[1])
    g = ordb(buf[2])
    n = ordw(buf[40:42])
    m = ordw(buf[42:44])
    print_indent("Input  entries   : %d" % ordw(buf[40:42]), indent)
    print_indent("Output entries   : %d" % ordw(buf[42:44]), indent)
    of = 44
    for i in range(ic):
        print_indent("Input  table %d :" % i, indent)
        print_hex(buf[of:of + 2 * n], indent + 1)
        of += 2 * n
    print_indent("CLUT table %d :" % ic, indent)
    print_hex(buf[of:of + 2 * pow(g, ic) * oc], indent + 1)
    of += 2 * pow(g, ic) * oc
    for i in range(oc):
        print_indent("Output table %d :" % i, indent)
        print_hex(buf[of:of + 2 * m], indent + 1)
        of += 2 * m


def print_para(buf, indent):
    curv = ordw(buf[0:2])
    if curv == 0:
        print_indent("Gamma mapping", indent)
        gamma = s15d(ordl(buf[4:8]))
        print_indent("Gamma        : %g" % gamma, indent)
    elif curv == 1:
        print_indent("CIE 122-1966", indent)
        gamma = s15d(ordl(buf[4:8]))
        a = s15d(ordl(buf[8:12]))
        b = s15d(ordl(buf[12:16]))
        print_indent("Gamma        : %g" % gamma, indent)
        print_indent("A            : %g" % a, indent)
        print_indent("B            : %g" % b, indent)
    elif curv == 2:
        print_indent("IEC 61996-3", indent)
        gamma = s15d(ordl(buf[4:8]))
        a = s15d(ordl(buf[8:12]))
        b = s15d(ordl(buf[12:16]))
        c = s15d(ordl(buf[16:20]))
        print_indent("Gamma        : %g" % gamma, indent)
        print_indent("A            : %g" % a, indent)
        print_indent("B            : %g" % b, indent)
        print_indent("C            : %g" % c, indent)
    elif curv == 3:
        gamma = s15d(ordl(buf[4:8]))
        a = s15d(ordl(buf[8:12]))
        b = s15d(ordl(buf[12:16]))
        c = s15d(ordl(buf[16:20]))
        d = s15d(ordl(buf[20:24]))
        print_indent("IEC 61966-2.1 (sRGB)", indent)
        print_indent("Gamma        : %g" % gamma, indent)
        print_indent("A            : %g" % a, indent)
        print_indent("B            : %g" % b, indent)
        print_indent("C            : %g" % c, indent)
        print_indent("D            : %g" % d, indent)
    elif curv == 4:
        print_indent("Affine Gamma with Toe", indent)
        gamma = s15d(ordl(buf[4:8]))
        a = s15d(ordl(buf[8:12]))
        b = s15d(ordl(buf[12:16]))
        c = s15d(ordl(buf[16:20]))
        d = s15d(ordl(buf[20:24]))
        e = s15d(ordl(buf[24:28]))
        print_indent("Gamma        : %g" % gamma, indent)
        print_indent("A            : %g" % a, indent)
        print_indent("B            : %g" % b, indent)
        print_indent("C            : %g" % c, indent)
        print_indent("D            : %g" % d, indent)
        print_indent("E            : %g" % e, indent)


def print_mluc(buf, indent):
    count = ordl(buf[0:4])
    recs = ordl(buf[4:8])
    offs = 8
    for i in range(count):
        code = ordw(buf[offs:offs + 2])
        cntr = ordw(buf[offs + 2:offs + 4])
        lnth = ordl(buf[offs + 4:offs + 8])
        disp = ordl(buf[offs + 8:offs + 12])
        offs = offs + recs
        print_indent("Entry %d for language %c%c, country %c%c :" % (i, code >> 8, code & 0xff, cntr >> 8, cntr & 0xff),
                     indent)
        print_hex(buf[disp - 8:disp - 8 + lnth], indent + 2)


def print_sf32(buf, indent):
    off = 0
    for i in range(len(buf) // 4):
        v = ordl(buf[off:off + 4])
        off = off + 4
        print_indent("Entry %d : 0x%08x = %g" % (i, v, s15d(v)), indent + 2)


def print_tag(buf, size, indent):
    sign = buf[0:4]
    print_indent("Tag type: %s" % sign, indent)
    print_indent("Reserved: %d" % ordl(buf[4:8]), indent)
    if sign == "desc":
        size = ordl(buf[8:12])
        print_indent("Profile description: %s" % buf[12:12 + size - 1], indent)
    elif sign == "text":
        print_indent("Text: %s" % buf[8:len(buf) - 1], indent)
    elif sign == "XYZ ":
        count = (len(buf) - 8) // 12
        off = 8
        for i in range(count):
            print_xyz(buf[off:off + 12], indent)
            off += 12
    elif sign == "curv":
        print_curve(buf[8:8 + size], indent)
    elif sign == "dtim":
        print_datetime(buf[8:8 + size], indent)
    elif sign == "view":
        print_view(buf[8:8 + size], indent)
    elif sign == "meas":
        print_meas(buf[8:8 + size], indent)
    elif sign == "sig ":
        print_indent("Signature : %s " % readsignature(buf[8:8 + size]), indent)
    elif sign == "mft1":
        print_lut8(buf[8:8 + size], indent)
    elif sign == "mft2":
        print_lut16(buf[8:8 + size], indent)
    elif sign == "mAB ":
        print_lutmAB(buf[8:8 + size], indent)
    elif sign == "mBA ":
        print_lutmAB(buf[8:8 + size], indent)
    elif sign == "para":
        print_para(buf[8:8 + size], indent)
    elif sign == "mluc":
        print_mluc(buf[8:8 + size], indent)
    elif sign == "sf32":
        print_sf32(buf[8:8 + size], indent)
    else:
        print_hex(buf[8:8 + size], indent)


def print_desctag(buf, indent):
    size = ordl(buf[8:12])
    print_indent("Profile description: %s" % buf[12:12 + size])


def parse_icc(indent, buf):
    indent += 1
    print_indent("ICC profile size        : %d bytes" % ordl(buf[0:4]), indent)
    print_indent("Preferred CMM type      : %d" % ordl(buf[0:8]), indent)
    print_indent("ICC major version       : %d" % ordb(buf[8]), indent)
    print_indent("ICC minor version       : %d" % ordb(buf[9]), indent)
    print_indent("Profile class           : %s" % buf[12:16], indent)
    print_indent("Canonical input space   : %s" % buf[16:20], indent)
    print_indent("Profile connection space: %s" % buf[20:24], indent)
    print_indent("Creation date :", indent)
    print_datetime(buf[24:36], indent + 1)
    print_indent("Profile signature       : %s" % buf[36:40], indent)
    print_indent("Platform singature      : %s" % readsignature(buf[40:44]), indent)
    print_indent("Profile flags           : 0x%08x" % ordl(buf[44:48]), indent)
    print_indent("Device manufacturer     : %s" % readsignature(buf[48:52]), indent)
    print_indent("Device model            : %s" % readsignature(buf[52:56]), indent)
    print_indent("Device attributes       : 0x%08x%08x" % (ordl(buf[56:60]), ordl(buf[60:64])), indent)
    intent = ordl(buf[64:68])
    if intent == 0:
        rendering = "perceptual"
    elif intent == 1:
        rendering = "media-relative colorimetric"
    elif intent == 2:
        rendering = "saturation"
    elif intent == 3:
        rendering = "icc absolute colorimetric"
    else:
        rendering = "undefined intent %d" % intent
    print_indent("Rendering intent        : %s" % rendering, indent)
    print_indent("PCS illuminant          :", indent)
    print_xyz(buf[68:80], indent + 1)
    print_indent("Profile creator         : %s" % readsignature(buf[80:84]), indent)
    print_indent("Profile MD5 sum         : %08lx%08lx%08x%08lx" % (
        ordl(buf[84:88]), ordl(buf[88:92]), ordl(buf[92:96]), ordl(buf[96:100])), indent)
    count = ordl(buf[128:132])
    print_indent("Number of ICC tags      : %d" % count, indent)
    off = 128 + 4
    for i in range(count):
        offset = ordl(buf[off + 4:off + 8])
        size = ordl(buf[off + 8:off + 12])
        print_indent("ICC tag %s at offset %d size %d:" % (buf[off:off + 4], offset, size), indent + 1)
        print_tag(buf[offset:offset + size], size, indent + 2)
        off += 12


if __name__ == "__main__":
    # Read Arguments
    (args, files) = getopt.getopt(sys.argv[1:], "")

    if len(files) != 1:
        print("Usage: [OPTIONS] %s FILE" % (sys.argv[0]))
        sys.exit(1)

    print("###############################################################")
    print("# ICC format log file generated by icc.py                     #")
    print("# jp2file.py is copyrighted (c) 2001-2016 ISO                 #")
    print("# Read LICENSE.txt for licence details                        #")
    print("###############################################################")
    print("")

    # Parse Files
    file = open(files[0], "rb")
    try:
        parse_icc(0, file.read())

    except JP2Error as e:
        print("***{}".format(str(e)))
