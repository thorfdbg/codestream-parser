# -*- coding: utf-8 -*-
"""
JPEG codestream-parser (All-JPEG Codestream/File Format Parser Tools)
See LICENCE.txt for copyright and licensing conditions.
"""

import sys

from jp2utils import ordw, ordl, ordq, ieee_float_to_float, ieee_double_to_float,\
    JP2Error, InvalidMarker, InvalidMarkerField, InvalidSizedMarker, RequiredMarkerMissing, UnexpectedEOC,\
    MisplacedData, BaseCodestream


class JP2Codestream(BaseCodestream):
    """
    JP2 Codestream class.
    """

    def __init__(self, indent=0):
        super(JP2Codestream, self).__init__(indent=indent)
        self.datacount = 0
        self.bytecount = 0
        self.offset = 0
        self.buffer = None
        self.marker = None
        self.pos = 0
        self.size = None
        self.csiz = 0

    def print_header(self, header, content):
        self._headers.append((header, content))

    def print_data(self, count):
        if count > 0:
            self.datacount = self.datacount + count
            self.bytecount = self.bytecount + count
            self._print_indent("Data : %d bytes" % (count))
            print

    def parse(self, buf, startpos):
        self.buffer = buf
        self.pos = 0
        self.datacount = 0
        self.offset = startpos

        # Read SOC Marker
        if len(self.buffer) - self.pos < 2:
            raise RequiredMarkerMissing("SOC")
        if ord(self.buffer[self.pos + 0]) != 0xff or \
                ord(self.buffer[self.pos + 1]) != 0x4f:
            raise RequiredMarkerMissing("SOC")
        self.pos += 2
        self.read_SOC()

        # Read SIZ Marker
        if len(self.buffer) - self.pos < 2:
            raise RequiredMarkerMissing("SIZ")
        if ord(self.buffer[self.pos + 0]) != 0xff or \
                ord(self.buffer[self.pos + 1]) != 0x51:
            raise RequiredMarkerMissing("SIZ")
        self.pos += 2
        self.read_SIZ()

        # Read other header markers
        while len(self.buffer) - self.pos >= 2 and \
                ord(self.buffer[self.pos + 1]) != 0x90:
            if ord(self.buffer[self.pos + 0]) != 0xff:
                raise MisplacedData()
            if len(self.buffer) - self.pos < 4:
                raise UnexpectedEOC()
            self.read_header_marker()

        # Read Tile Parts
        while len(self.buffer) - self.pos >= 2 and \
                ord(self.buffer[self.pos + 0]) == 0xff and \
                ord(self.buffer[self.pos + 1]) == 0x90:
            self.pos += 2
            self.read_SOT()

            # Read Next Marker
            while len(self.buffer) - self.pos >= 2 and \
                    ord(self.buffer[self.pos + 1]) != 0x93:  # SOD
                if ord(self.buffer[self.pos + 0]) != 0xff:
                    raise MisplacedData()
                if len(self.buffer) - self.pos < 4:
                    raise UnexpectedEOC()
                self.read_header_marker()

            if len(self.buffer) - self.pos < 2:
                raise UnexpectedEOC()

            self.pos += 2
            self._new_marker("SOD", "Start of data")
            self._end_marker()

            self.parse_data()

        if len(self.buffer) - self.pos > 0:
            raise MisplacedData()

        l = len(self.buffer)
        oh = l - self.datacount
        self._print_indent("Size      : %d bytes" % (l))
        self._print_indent("Data Size : %d bytes" % (self.datacount))
        self._print_indent("Overhead  : %d bytes (%d%%)" % (oh, 100 * oh / l))

    def load_marker(self, file, marker):
        mrk = ((ord(marker[0]) << 8) +
               (ord(marker[1]) << 0))
        if 0xff30 <= mrk <= 0xff3f:
            self.buffer = marker
        elif mrk == 0xff93 or mrk == 0xff4f or mrk == 0xffd9 or mrk == 0xff92:
            self.buffer = marker
        elif 0xff4f <= mrk <= 0xff93:
            size = file.read(2)
            ln = ((ord(size[0]) << 8) +
                  (ord(size[1]) << 0))
            if ln < 2:
                raise InvalidSizedMarker("Marker too short")
            self.buffer = marker + size + file.read(ln - 2)
            if len(self.buffer) != ln + 2:
                raise UnexpectedEOC()
        else:
            raise MisplacedData()
        self.bytecount = self.bytecount + len(self.buffer)
        self.pos = 0

    def load_buffer(self, file):
        marker = file.read(2)
        if len(marker) == 0:
            self.buffer = []
        else:
            if len(marker) < 2:
                raise UnexpectedEOC()
            self.load_marker(file, marker)

    def stream_parse(self, file, startpos):
        self.pos = 0
        self.datacount = 0
        self.bytecount = 0
        self.offset = startpos

        # Read SOC Marker
        self.load_buffer(file)
        if ord(self.buffer[self.pos + 0]) != 0xff or \
                ord(self.buffer[self.pos + 1]) != 0x4f:
            raise RequiredMarkerMissing("SOC")
        self.pos += 2
        self.read_SOC()
        self.offset += len(self.buffer)

        # Read SIZ Marker
        self.load_buffer(file)
        if ord(self.buffer[self.pos + 0]) != 0xff or \
                ord(self.buffer[self.pos + 1]) != 0x51:
            raise RequiredMarkerMissing("SIZ")
        self.pos += 2
        self.read_SIZ()
        self.offset += len(self.buffer)

        # Read other header markers
        self.load_buffer(file)
        while len(self.buffer) - self.pos >= 2 and \
                ord(self.buffer[self.pos + 1]) != 0x90:
            if ord(self.buffer[self.pos + 0]) != 0xff:
                raise MisplacedData()
            if len(self.buffer) - self.pos < 4:
                raise UnexpectedEOC()
            self.read_header_marker()
            self.offset += len(self.buffer)
            self.load_buffer(file)

        # Read Tile Parts
        while len(self.buffer) >= 2 and \
                ord(self.buffer[0]) == 0xff and \
                ord(self.buffer[1]) == 0x90:
            self.pos += 2
            self.read_SOT()
            self.offset += len(self.buffer)
            self.load_buffer(file)

            # Read Next Marker
            while len(self.buffer) >= 2 and \
                    ord(self.buffer[self.pos + 1]) != 0x93:  # SOD
                if ord(self.buffer[self.pos + 0]) != 0xff:
                    raise MisplacedData()
                if len(self.buffer) - self.pos < 4:
                    raise UnexpectedEOC()
                self.read_header_marker()
                self.offset += len(self.buffer)
                self.load_buffer(file)

            self.offset += len(self.buffer)
            self._new_marker("SOD", "Start of data")
            self._end_marker()

            self.stream_data(file)

        if len(self.buffer) - self.pos > 0:
            raise MisplacedData()

        oh = self.bytecount - self.datacount
        self._print_indent("Size      : %d bytes" % (self.bytecount))
        self._print_indent("Data Size : %d bytes" % (self.datacount))
        self._print_indent("Overhead  : %d bytes (%d%%)" % (oh, 100 * oh / self.bytecount))

    def stream_data(self, file):
        count = 0
        while True:
            byte = file.read(1)
            if len(byte) != 1:
                raise UnexpectedEOC()
            count += 1
            if ord(byte[0]) == 0xff:
                marker = file.read(1)
                if len(marker) == 1:
                    count += 1
                    if ord(marker[0]) >= 0x90:
                        self.offset += count - 2
                        self.print_data(count - 2)
                        self.load_marker(file, byte + marker)
                        if self.read_data_marker():
                            break
                        self.offset += len(self.buffer)
                        count = 0

    def parse_data(self, buf=None):
        if buf:
            self.buffer = buf
            self.pos = 0

        while True:
            count = 0
            while len(self.buffer) - self.pos >= 2 and \
                    (ord(self.buffer[self.pos + 0]) != 0xff or ord(self.buffer[self.pos + 1]) < 0x90):
                self.pos += 1
                count += 1

            if len(self.buffer) - self.pos == 1:
                self.pos += 1
                count += 1

            self.print_data(count)

            if len(self.buffer) - self.pos == 0:
                return
            if len(self.buffer) - self.pos < 2:
                raise UnexpectedEOC()

            # Read Marker
            if self.read_data_marker():
                break

    def read_SGco(self):
        if len(self.buffer) - self.pos < 4:
            raise InvalidSizedMarker("SGco")

        self.print_header("Progression Order",
                          self.progression_order(ord(self.buffer[self.pos + 0])))
        self.print_header("Layers", str(ordw(self.buffer[self.pos + 1:self.pos + 3])))
        trafo = ord(self.buffer[self.pos + 3])
        if trafo == 0:
            s = "none"
        elif trafo == 1:
            s = "components 0,1,2"
        elif trafo == 2:
            s = "generic array based transform"
        elif trafo == 4:
            s = "wavelet based transform"
        elif trafo == 6:
            s = "array and wavelet based transform"
        else:
            s = str(ord(self.buffer[self.pos + 3]))
        self.print_header("Multiple Component Transformation", s)
        self.pos += 4

    def read_SPco(self, precincts):
        if len(self.buffer) - self.pos < 5 + precincts:
            raise InvalidSizedMarker("SPco")

        levels = ord(self.buffer[self.pos + 0])
        if levels <= 32:
            self.print_header("Decomposition Levels", str(levels))
        else:
            self.print_header("Downsampling factor style", str(levels))
        self.print_header("Code-block size", "%dx%d" % \
                          (1 << (ord(self.buffer[self.pos + 1]) + 2),
                           1 << (ord(self.buffer[self.pos + 2]) + 2)))
        x = ord(self.buffer[self.pos + 3])
        self.print_header("Selective Arithmetic Coding Bypass", "yes" if x & 0x01 else "no")
        self.print_header("Reset Context Probabilities", "yes" if x & 0x02 else "no")
        self.print_header("Termination on Each Coding Pass", "yes" if x & 0x04 else "no")
        self.print_header("Vertically Causal Context", "yes" if x & 0x08 else "no")
        self.print_header("Predictable Termination", "yes" if x & 0x10 else "no")
        self.print_header("Segmentation Symbols", "yes" if x & 0x20 else "no")
        self.print_header("Entropy Coding", "FBCOT (Part 15)" if x & 0x40 else "EBCOT")
        if x & 0x40:
            self.print_header("Mixing of FBCOT and EBCOT", "yes" if x & 0x80 else "no")
        if ord(self.buffer[self.pos + 4]) == 0x00:
            s = "9-7 irreversible"
        elif ord(self.buffer[self.pos + 4]) == 0x01:
            s = "5-3 reversible"
        else:
            s = "arbitrary ATK specified transform"
        self.print_header("Wavelet Transformation", s)
        for i in range(precincts):
            x = ord(self.buffer[self.pos + i + 5])
            self.print_header("Precinct #%d Size Exponents" % (i),
                              "%dx%d" % (x & 0x0f, x >> 4))
        self.pos += 5 + precincts

    def read_SOC(self):
        self._new_marker("SOC", "Start of codestream")
        self._end_marker()

    def read_NSI(self):
        self._new_marker("NSI", "Additional Dimension Image and Tile Size")
        size = ordw(self.buffer[self.pos + 0:self.pos + 2])
        if size < 20 or size > 16403:
            raise InvalidSizedMarker("NSI")
        ndim = ord(self.buffer[self.pos + 2])
        zsiz = ordl(self.buffer[self.pos + 3:self.pos + 7])
        osiz = ordl(self.buffer[self.pos + 7:self.pos + 11])
        tsiz = ordl(self.buffer[self.pos + 11:self.pos + 15])
        tosz = ordl(self.buffer[self.pos + 15:self.pos + 19])
        self.print_header("Dimensionality", "%d" % ndim)
        self.print_header("Image Depth", "%d" % zsiz)
        self.print_header("Image Depth Offset", "%d" % osiz)
        self.print_header("Tile Depth", "%d" % tsiz)
        self.print_header("Tile Depth Offset", "%d" % tosz)
        for i in range(size - 19):
            self.print_header("Z Sample Separation for component %d" % i, "%d" % ord(self.buffer[self.pos + 19 + i]))
        self.pos += size
        self._end_marker()

    def read_SIZ(self):
        self._new_marker("SIZ", "Image and tile size")
        size = ordw(self.buffer[self.pos + 0:self.pos + 2])
        if size < 41:
            raise InvalidSizedMarker("SIZ")
        if (size - 38) % 3 != 0:
            raise InvalidSizedMarker("SIZ")

        # Read Csiz
        components = (size - 38) / 3
        self.csiz = ordw(self.buffer[self.pos + 36:self.pos + 38])
        if self.csiz != components:
            raise InvalidSizedMarker("SIZ")

        # Read Rsiz
        rsiz = ordw(self.buffer[self.pos + 2:self.pos + 4])
        if rsiz == 0:
            s = "JPEG2000 full standard"
        elif rsiz == 1:
            s = "JPEG2000 profile 0"
        elif rsiz == 2:
            s = "JPEG2000 profile 1"
        elif rsiz == 3:
            s = "DCI 2K profile"
        elif rsiz == 4:
            s = "DCI 4K profile"
        elif rsiz == 5:
            s = "DCI long term storage profile"
        elif rsiz == 6:
            s = "DCI 2K scalable profile"
        elif rsiz & (1 << 14):
            s = "JPEG2000 part 15"
        elif rsiz & (1 << 15):
            s = "JPEG2000 part 2"
            if rsiz & (1 << 11):
                s += " Precinct dependent QNT"
            if rsiz & (1 << 10):
                s += " Arbitrary ROIs"
            if rsiz & (1 << 9):
                s += " NLT transform"
            if rsiz & (1 << 8):
                s += " Multi-component transform"
            if rsiz & (1 << 7):
                s += " WSS transformation kernel"
            if rsiz & (1 << 6):
                s += " Arbitrary kernel"
            if rsiz & (1 << 5):
                s += " Arbitrary decomposition"
            if rsiz & (1 << 4):
                s += " Single sample overlap"
            if rsiz & (1 << 3):
                s += " Visual masking"
            if rsiz & (1 << 2):
                s += " Trellis quantization"
            if rsiz & (1 << 1):
                s += " Variable scalar quantization"
            if rsiz & (1 << 0):
                s += " Variable DC offset"
        else:
            s = "unknown"
        self.print_header("Required Capabilities", s)

        # Read Xsiz and Ysiz
        xsiz = ordl(self.buffer[self.pos + 4:self.pos + 8])
        ysiz = ordl(self.buffer[self.pos + 8:self.pos + 12])
        self.print_header("Reference Grid Size", "%dx%d" % (xsiz, ysiz))

        # Read XOsiz and YOsiz
        xosiz = ordl(self.buffer[self.pos + 12:self.pos + 16])
        yosiz = ordl(self.buffer[self.pos + 16:self.pos + 20])
        self.print_header("Image Offset", "%dx%d" % (xosiz, yosiz))

        # Read XTsiz and YTsiz
        xtsiz = ordl(self.buffer[self.pos + 20:self.pos + 24])
        ytsiz = ordl(self.buffer[self.pos + 24:self.pos + 28])
        self.print_header("Reference Tile Size", "%dx%d" % (xtsiz, ytsiz))

        # Read XTOsiz and YTOsiz
        xtosiz = ordl(self.buffer[self.pos + 28:self.pos + 32])
        ytosiz = ordl(self.buffer[self.pos + 32:self.pos + 36])
        self.print_header("Reference Tile Offset", "%dx%d" % (xtosiz, ytosiz))

        # Csiz (already read)
        self.print_header("Components", str(components))

        # Read Components
        for i in range(0, components):
            ssiz = ord(self.buffer[self.pos + 38 + i * 3])
            xrsiz = ord(self.buffer[self.pos + 39 + i * 3])
            yrsiz = ord(self.buffer[self.pos + 40 + i * 3])
            self.print_header("Component #%d Depth" % (i), "%d" % ((ssiz & 0x7f) + 1))
            self.print_header("Component #%d Signed" % (i), "yes" if ssiz & 0x80 else "no")
            self.print_header("Component #%d Sample Separation" % (i),
                              "%dx%d" % (xrsiz, yrsiz))

        self._end_marker()
        self.pos += size

    def read_SOT(self):
        self._new_marker("SOT", "Start of tile-part")
        if len(self.buffer) - self.pos < 10:
            raise InvalidSizedMarker("SOT")
        size = ordw(self.buffer[self.pos + 0:self.pos + 2])
        if size != 10:
            raise InvalidSizedMarker("SOT")
        self.print_header("Tile", str(ordw(self.buffer[self.pos + 2:self.pos + 4])))
        length = ordl(self.buffer[self.pos + 4:self.pos + 8])
        self.print_header("Length", str(length))
        self.print_header("Index", str(ord(self.buffer[self.pos + 8])))
        if ord(self.buffer[self.pos + 9]) == 0:
            s = "unknown"
        else:
            s = str(ord(self.buffer[self.pos + 9]))
        self.print_header("Tile-Parts", s)
        self._end_marker()
        self.pos += 10

    def read_COD(self):
        self._new_marker("COD", "Coding style default")
        if self.size < 3:
            raise InvalidSizedMarker("COD")
        cod = ord(self.buffer[self.pos + 2])
        self.print_header("Default Precincts of 2^15x2^15", "no" if cod & 0x01 else "yes")
        self.print_header("SOP Marker Segments", "yes" if cod & 0x02 else "no")
        self.print_header("EPH Marker Segments", "yes" if cod & 0x04 else "no")
        self.print_header("Codeblock X offset", "1" if cod & 0x08 else "0")
        self.print_header("Codeblock Y offset", "1" if cod & 0x10 else "0")
        self.print_header("All Flags", "%08x" % (cod))
        self.pos += 3
        self.read_SGco()
        self.read_SPco(self.size - 12)
        self._end_marker()

    def read_COC(self):
        self._new_marker("COC", "Coding style component")
        if self.csiz <= 256 and self.size < 9 or \
                self.csiz > 256 and self.size < 10:
            raise InvalidSizedMarker("COC")

        self.pos += 2

        # Print Ccoc
        if self.csiz <= 256:
            component = ord(self.buffer[self.pos + 0])
            self.pos += 1
        else:
            component = ordw(self.buffer[self.pos + 0:self.pos + 2])
            self.pos += 2
        self.print_header("Component", str(component))

        # Print Scoc
        prec = ord(self.buffer[self.pos + 0])
        self.pos += 1
        if prec == 0:
            s = "default"
        elif prec == 1:
            s = "custom"
        else:
            s = "unknown"
        self.print_header("Precincts", s)

        # Print SPcoc
        if prec == 0:
            if self.csiz <= 256 and self.size != 9 or \
                    self.csiz > 256 and self.size != 10:
                raise InvalidSizedMarker("COC")
        precincts = self.size - 9
        if self.csiz > 256:
            precincts -= 1
        self.read_SPco(precincts)
        self._end_marker()

    def read_QCD(self):
        self._new_marker("QCD", "Quantization default")
        if self.size < 4:
            raise InvalidSizedMarker("QCD")
        sqcd = ord(self.buffer[self.pos + 2])
        if sqcd & 0x1f == 0:
            s = "none"
        elif sqcd & 0x1f == 1:
            s = "scalar derived"
        elif sqcd & 0x1f == 2:
            s = "scalar expounded"
        elif sqcd & 0x1f == 3:
            s = "variable deadzone scalar derived"
        elif sqcd & 0x1f == 4:
            s = "variable deadzone scalar expounded"
        elif sqcd & 0x1f == 5:
            s = "variable deadzone scalar expounded"
        elif sqcd & 0x1f == 9:
            s = "trellis quantization derived"
        elif sqcd & 0x1f == 10:
            s = "trellis quantization expounded"
        else:
            s = "unknown"
        self.print_header("Quantization Type", s)
        self.print_header("Guard Bits", str(sqcd >> 5))
        subbands = self.size - 3
        if sqcd & 0x1f == 1 or sqcd & 0x1f == 2:
            if subbands % 2 != 0:
                raise InvalidSizedMarker("QCD")
            subbands /= 2
        for i in range(subbands):
            mantissa = 1.0
            if sqcd & 0x1f == 1 or sqcd & 0x1f == 2:
                spqcd = ordw(self.buffer[self.pos + i * 2 + 3:self.pos + i * 2 + 5])
                mantissa = 1.0 + ((spqcd & 0x7ff) / 2048.0)
                self.print_header("Mantissa #%d" % (i), str(spqcd & 0x7ff))
                exponent = spqcd >> 11
            else:
                spqcd = ord(self.buffer[self.pos + i + 3])
                exponent = spqcd >> 3
            self.print_header("Exponent #%d" % (i), str(exponent))
            self.print_header("Delta    #%d" % (i), str(mantissa * pow(2.0, -exponent)))
        self._end_marker()
        self.pos += self.size

    def read_QCC(self):
        self._new_marker("QCC", "Quantization component")
        if self.size < 4:
            raise InvalidSizedMarker("QCC")
        if self.csiz <= 256:
            index = ord(self.buffer[self.pos + 2])
            self.pos += 3
        else:
            index = ordw(self.buffer[self.pos + 2:self.pos + 4])
            self.pos += 4
        self.print_header("Index", str(index))
        sqcc = ord(self.buffer[self.pos + 0])
        self.pos += 1
        if sqcc & 0x1f == 0:
            s = "none"
        elif sqcc & 0x1f == 1:
            s = "scalar derived"
        elif sqcc & 0x1f == 2:
            s = "scalar expounded"
        else:
            s = "unknown"
        self.print_header("Quantization Type", s)
        self.print_header("Guard Bits", str(sqcc >> 5))
        if self.csiz <= 256:
            subbands = self.size - 4
        else:
            subbands = self.size - 5
        if sqcc & 0x1f == 1 or sqcc & 0x1f == 2:
            if subbands % 2 != 0:
                raise InvalidSizedMarker("QCC")
            subbands /= 2
        for i in range(subbands):
            mantissa = 1.0
            if sqcc & 0x1f == 1 or sqcc & 0x1f == 2:
                spqcd = ordw(self.buffer[self.pos + 0:self.pos + 2])
                self.pos += 2
                mantissa = 1.0 + ((spqcd & 0x7ff) / 2048.0)
                self.print_header("Mantissa #%d" % (i), str(spqcd & 0x7ff))
                exponent = spqcd >> 11
            else:
                spqcd = ord(self.buffer[self.pos + 0])
                self.pos += 1
                exponent = spqcd >> 3
            self.print_header("Exponent #%d" % (i), str(exponent))
            self.print_header("Delta    #%d" % (i), mantissa * pow(2.0, -exponent))
        self._end_marker()

    def read_RGN(self):
        self._new_marker("RGN", "Region-of-interest")
        # Print Crgn
        if self.csiz <= 256:
            cmp = ord(self.buffer[self.pos + 2])
            self.pos += 3
        else:
            cmp = ordw(self.buffer[self.pos + 2:self.pos + 4])
            self.pos += 4
        self.print_header("Component", str(cmp))
        method = ord(self.buffer[self.pos + 0])
        if method == 0:
            s = "implicit"
        elif method == 1:
            s = "rectangle"
        elif method == 2:
            s = "ellipse"
        else:
            s = str(method)
        self.pos += 1
        self.print_header("Style", s)
        self.print_header("Implicit ROI Shift",
                          str(ord(self.buffer[self.pos + 0])))
        self.pos += 1
        self._end_marker()

    def read_POC(self):
        self._new_marker("POC", "Progression order change")
        if self.size < 9:
            raise InvalidSizedMarker("POC")
        if self.csiz <= 256:
            if (self.size - 2) % 7 != 0:
                raise InvalidSizedMarker("POC")
            num = (self.size - 2) / 7
        else:
            if (self.size - 2) % 9 != 0:
                raise InvalidSizedMarker("POC")
            num = (self.size - 2) / 9
        self.pos += 2
        for i in range(num):
            self.print_header("Resolution Level Index #%d (Start)" % (i),
                              str(ord(self.buffer[self.pos])))
            if self.csiz <= 256:
                rspoc = ord(self.buffer[self.pos + 1])
                self.pos += 2
            else:
                rspoc = ordw(self.buffer[self.pos + 1:self.pos + 3])
                self.pos += 3
            self.print_header("Component Index #%d (Start)" % (i), str(rspoc))
            lyepoc = ordw(self.buffer[self.pos + 0:self.pos + 2])
            self.print_header("Layer Index #%d (End)" % (i), str(lyepoc))
            self.print_header("Resolution Level Index #%d (End)" % (i),
                              str(ord(self.buffer[self.pos + 2])))
            if self.csiz <= 256:
                cepoc = ord(self.buffer[self.pos + 3])
                if cepoc == 0:
                    cepoc = 256
                self.pos += 4
            else:
                cepoc = ordw(self.buffer[self.pos + 3:self.pos + 5])
                if cepoc == 0:
                    cepoc = 16384
                self.pos += 5
            self.print_header("Component Index #%d (End)" % (i), str(cepoc))
            po = self.progression_order(ord(self.buffer[self.pos]))
            self.print_header("Progression Order #%d" % (i), po)
            self.pos += 1
        self._end_marker()

    def read_PPM(self):
        self._new_marker("PPM", "Packed packet headers, main header")
        if self.size < 3:
            raise InvalidSizedMarker("PPM")
        self.print_header("Index Zppm", str(ord(self.buffer[self.pos + 2])))
        self.print_header("Marker Length Lppm", str(self.size))
        self._end_marker()
        self.pos += self.size

    def read_PPT(self):
        self._new_marker("PPT", "Packed packet headers, tile-part header")
        if self.size < 3:
            raise InvalidSizedMarker("PPT")
        self.print_header("Index", str(ord(self.buffer[self.pos + 2])))
        self.print_header("Contents", "")
        self._flush_marker()
        restlen = self.size - 3
        self.pos += 3
        cs = JP2Codestream(self._indent + 1)
        cs.parse_data(self.buffer[self.pos:self.pos + restlen])
        self.datacount = self.datacount + cs.datacount
        self._end_marker()
        self.pos += restlen

    def read_SOP(self):
        self._new_marker("SOP", "Start of packet")
        if self.size != 4:
            raise InvalidSizedMarker("SOP")
        self.print_header("Sequence",
                          str(ordw(self.buffer[self.pos + 2:self.pos + 4])))
        self._end_marker()
        self.pos += self.size

    def read_EPH(self):
        self._new_marker("EPH", "End of packet header")
        self._end_marker()

    def read_TLM(self):
        self._new_marker("TLM", "Tile-part length")
        if self.size < 4:
            raise InvalidSizedMarker("TLM")
        self.print_header("Index", str(ord(self.buffer[self.pos + 2])))
        stlm = ord(self.buffer[self.pos + 3]) >> 4
        st = stlm & 0x03
        sp = (stlm >> 2) & 0x1
        if st == 3:
            raise InvalidMarkerField("TLM", "Stlm")
        if st == 0:
            if sp == 0:
                if (self.size - 4) % 2 != 0:
                    raise InvalidSizedMarker("TLM")
                tileparts = (self.size - 4) / 2
            else:
                if (self.size - 4) % 4 != 0:
                    raise InvalidSizedMarker("TLM")
                tileparts = (self.size - 4) / 4
        elif st == 1:
            if sp == 0:
                if (self.size - 4) % 3 != 0:
                    raise InvalidSizedMarker("TLM")
                tileparts = (self.size - 4) / 3
            else:
                if (self.size - 4) % 5 != 0:
                    raise InvalidSizedMarker("TLM")
                tileparts = (self.size - 4) / 5
        else:
            if sp == 0:
                if (self.size - 4) % 4 != 0:
                    raise InvalidSizedMarker("TLM")
                tileparts = (self.size - 4) / 4
            else:
                if (self.size - 4) % 6 != 0:
                    raise InvalidSizedMarker("TLM")
                tileparts = (self.size - 4) / 6
        self.pos += 4
        for i in range(tileparts):
            if st == 0:
                ttlm = "in order"
            if st == 1:
                ttlm = str(ord(self.buffer[self.pos + 0]))
                self.pos += 1
            elif st == 2:
                ttlm = str(ordw(self.buffer[self.pos + 0:self.pos + 2]))
                self.pos += 2
            self.print_header("Tile index #%d" % (i), ttlm)
            if sp == 0:
                length = ordw(self.buffer[self.pos + 0:self.pos + 2])
                self.pos += 2
            else:
                length = ordl(self.buffer[self.pos + 0:self.pos + 4])
                self.pos += 4
            self.print_header("Length #%d" % (i), str(length))
        self._end_marker()

    def read_PLM(self):
        self._new_marker("PLM", "Packet length, main header")
        if self.size < 3:
            raise InvalidSizedMarker("PLM")
        self.print_header("Index", str(ord(self.buffer[self.pos + 2])))
        self.pos += 3
        self.size -= 3
        self.print_header("Length", str(self.size))
        self._end_marker()
        self.pos += self.size

    def read_PLT(self):
        self._new_marker("PLT", "Packet length, tile-part header")
        if self.size < 3:
            raise InvalidSizedMarker("PLT")
        self.print_header("Index Zplt", str(ord(self.buffer[self.pos + 2])))
        self.print_header("Marker size Lplt", "%d bytes" % (self.size))
        self._end_marker()
        self.pos += self.size

    def read_CRG(self):
        self._new_marker("CRG", "Component registration")
        if self.size != self.csiz * 4 + 2:
            raise InvalidSizedMarker("CRG")
        self.pos += 2
        for i in range(self.csiz):
            x = ordw(self.buffer[self.pos + 0:self.pos + 2])
            y = ordw(self.buffer[self.pos + 2:self.pos + 4])
            self.print_header("Offset #%d" % (i), "%dx%d" % (x, y))
            self.pos += 4
        self._end_marker()

    def read_CBD(self):
        self._new_marker("CBD", "Component bit depth definition")
        if self.size < 5:
            raise InvalidSizedMarker("CBD")
        nbcd = ordw(self.buffer[self.pos + 2:self.pos + 4])
        if nbcd & (1 << 15):
            nbcd -= 1 << 15
            self.print_header("Definition style", "Identical depth and signs")
            count = 1
        else:
            self.print_header("Definition style", "Individual depths and signs")
            count = nbcd
        self.print_header("Number of generated components", str(nbcd))
        self.pos += 4
        for i in range(count):
            if ord(self.buffer[self.pos]) & (1 << 7):
                self.print_header("Component %d sign" % i, "signed")
            else:
                self.print_header("Component %d sign" % i, "unsigned")
            self.print_header("Component %d Bit Depth" % i, str(1 + (ord(self.buffer[self.pos]) & 0x7f)))
            self.pos += 1
        self._end_marker()

    def read_MCO(self):
        self._new_marker("MCO", "Multiple component transform ordering")
        if self.size < 3:
            raise InvalidSizedMarker("MCO")
        nmco = ord(self.buffer[self.pos + 2])
        if self.size != nmco + 3:
            raise InvalidSizedMarker("MCO")
        self.print_header("Number of component collections", "%d" % nmco)
        self.pos += 3
        for i in range(nmco):
            self.print_header("MCC collection %d" % i, str(ord(self.buffer[self.pos])))
            self.pos += 1
        self._end_marker()

    def read_MCC(self):
        self._new_marker("MCC", "Multiple component collection")
        if self.size < 5:
            raise InvalidSizedMarker("MCC")
        zmcc = ordw(self.buffer[self.pos + 2:self.pos + 4])
        self.print_header("Concatenation index", str(zmcc))
        imcc = ord(self.buffer[self.pos + 4])
        self.print_header("Reference index", str(imcc))
        self.pos += 5
        if zmcc == 0:
            ymcc = ordw(self.buffer[self.pos + 0:self.pos + 2])
            self.print_header("Last concatenation index", str(ymcc))
            qmcc = ordw(self.buffer[self.pos + 2:self.pos + 4])
            self.print_header("Number of collections", str(qmcc))
            self.pos += 4
        for i in range(qmcc):
            ctp = ord(self.buffer[self.pos])
            if ctp & 3 == 0:
                s = "array based dependency transformation"
            elif ctp & 3 == 1:
                s = "array based decorrelation transformation"
            elif ctp & 3 == 3:
                s = "wavelet based transformation"
            else:
                s = "invalid type"
            self.print_header("Transformation type", s)
            self.pos += 1
            nmcc = ordw(self.buffer[self.pos + 0:self.pos + 2])
            if nmcc & (1 << 15):
                self.print_header("Collection %d input index size" % i, "16 bit")
                intype = 2
                nmcc -= 1 << 15
            else:
                self.print_header("Collection %d input index size" % i, "8 bit")
                intype = 1
            self.print_header("Collection %d # of input components" % i, nmcc)
            self.pos += 2
            for j in range(nmcc):
                if intype == 2:
                    incom = ordw(self.buffer[self.pos + 0:self.pos + 2])
                    self.pos += 2
                else:
                    incom = ord(self.buffer[self.pos])
                    self.pos += 1
                self.print_header("Collection %d input component %d" % (i, j), str(incom))
            mmcc = ordw(self.buffer[self.pos + 0:self.pos + 2])
            if mmcc & (1 << 15):
                self.print_header("Collection %d output index size" % i, "16 bit")
                outtype = 2
                mmcc -= 1 << 15
            else:
                self.print_header("Collection %d output index size" % i, "8 bit")
                outtype = 1
            self.print_header("Collection %d # of output components" % i, mmcc)
            self.pos += 2
            for j in range(mmcc):
                if outtype == 2:
                    outcom = ordw(self.buffer[self.pos + 0:self.pos + 2])
                    self.pos += 2
                else:
                    outcom = ord(self.buffer[self.pos])
                    self.pos += 1
                self.print_header("Collection %d output component %d" % (i, j), str(outcom))
            if ctp & 3 == 3:
                self.print_header("Number of decomposition levels", ord(self.buffer[self.pos]))
                if ord(self.buffer[self.pos + 1]) == 0:
                    s = "null"
                else:
                    s = "in MCT marker %d" % ord(self.buffer[self.pos + 1])
                self.print_header("Collection %d offset vector" % i, s)
                if ord(self.buffer[self.pos + 2]) == 0:
                    s = "9-7 irreversible"
                elif ord(self.buffer[self.pos + 2]) == 1:
                    s = "5-3 reversible"
                else:
                    s = "defined in ATK segment %d " % ord(self.buffer[self.pos + 2])
                self.print_header("Wavelet filter used", s)
                self.pos += 3
                self.print_header("Collection %d reference grid offset" % i,
                                  ordl(self.buffer[self.pos + 0:self.pos + 4]))
                self.pos += 4
            else:
                if ord(self.buffer[self.pos]) & 1:
                    s = "reversible"
                else:
                    s = "irreversible"
                self.print_header("Collection %d transformation is" % i, s)
                if ord(self.buffer[self.pos + 1]) == 0:
                    s = "null"
                else:
                    s = "in MCT marker %d" % ord(self.buffer[self.pos + 1])
                self.print_header("Collection %d offset vector" % i, s)
                if ord(self.buffer[self.pos + 2]) == 0:
                    s = "identity"
                else:
                    s = "in MCT marker %d" % ord(self.buffer[self.pos + 2])
                self.print_header("Collection %d matrix" % i, s)
                self.pos += 3
        self._end_marker()

    def read_MCT(self):
        self._new_marker("MCT", "Multiple component transformation")
        len = self.size - 6
        if len < 0:
            raise InvalidSizedMarker("MCT")
        zmct = ordw(self.buffer[self.pos + 2:self.pos + 4])
        self.print_header("Concatenation index", str(zmct))
        imct = ord(self.buffer[self.pos + 5])
        self.print_header("Reference index", str(imct))
        type = ord(self.buffer[self.pos + 4])
        if type & 3 == 0:
            s = "Dependency transform"
        elif type & 3 == 1:
            s = "Decorrelation matrix"
        elif type & 3 == 2:
            s = "Offset vector"
        else:
            s = "Unknown"
        self.print_header("Transform type", s)
        if type & 12 == 0:
            s = "16 bit integer"
            l = 2
        elif type & 12 == 4:
            s = "32 bit integer"
            l = 4
        elif type & 12 == 8:
            s = "32 bit IEEE float"
            l = 4
        elif type & 12 == 12:
            s = "64 bit IEEE float"
            l = 8
        self.print_header("Data type", s)
        self.pos += 6
        if zmct == 0:
            ymct = ordw(self.buffer[self.pos + 0:self.pos + 2])
            self.print_header("Last concatenation index", str(ymct))
            self.pos += 2
            len -= 2
        if len % l != 0:
            raise InvalidSizedMarker("MCT")
        count = len / l
        self.print_header("Number of entries", str(count))
        for i in range(count):
            if type & 12 == 0:
                dt = ordw(self.buffer[self.pos + 0:self.pos + 2])
                if dt >= (1 << 15):
                    dt -= 1 << 16
                s = str(dt)
                self.pos += 2
            elif type & 12 == 4:
                dt = ordl(self.buffer[self.pos + 0:self.pos + 4])
                if dt >= (1 << 31):
                    dt -= 1 << 32
                s = str(dt)
                self.pos += 4
            elif type & 12 == 8:
                dt = ordl(self.buffer[self.pos + 0:self.pos + 4])
                s = str(ieee_float_to_float(dt))
                self.pos += 4
            elif type & 12 == 12:
                dtl = ordq(self.buffer[self.pos + 0:self.pos + 8])
                s = str(ieee_double_to_float(dtl))
                self.pos += 8
            self.print_header("Data entry %d" % i, s)
        self._end_marker()

    def read_NLT(self):
        self._new_marker("NLT", "Nonlinearity transformation")
        if self.size < 6:
            raise InvalidSizedMarker("NLT")
        cnlt = ordw(self.buffer[self.pos + 2:self.pos + 4])
        if cnlt == 0xffff:
            s = "for all components"
        else:
            s = "for component %d" % cnlt
        self.print_header("Non-Linearity defined", s)
        bdnlt = ord(self.buffer[self.pos + 4])
        if bdnlt & 0x80:
            s = "signed"
            bdnlt -= 0x80
        else:
            s = "unsigned"
        self.print_header("Output sign", s)
        self.print_header("Output bit depth", str(bdnlt + 1))
        tnlt = ord(self.buffer[self.pos + 5])
        if tnlt == 0:
            s = "none"
        elif tnlt == 1:
            s = "Gamma transformation"
        elif tnlt == 2:
            s = "Table lookup"
        elif tnlt == 3:
            s = "Two's completement to sign-magnitude conversion"
        else:
            s = "unknown"
        self.print_header("Non-Linearity type", s)
        self.pos += 6
        if tnlt == 1:
            e = (ord(self.buffer[self.pos + 0]) << 16) + \
                (ord(self.buffer[self.pos + 1]) << 8) + \
                (ord(self.buffer[self.pos + 2]) << 0)
            l = (ord(self.buffer[self.pos + 3]) << 16) + \
                (ord(self.buffer[self.pos + 4]) << 8) + \
                (ord(self.buffer[self.pos + 5]) << 0)
            t = (ord(self.buffer[self.pos + 6]) << 16) + \
                (ord(self.buffer[self.pos + 7]) << 8) + \
                (ord(self.buffer[self.pos + 8]) << 0)
            a = (ord(self.buffer[self.pos + 9]) << 16) + \
                (ord(self.buffer[self.pos + 10]) << 8) + \
                (ord(self.buffer[self.pos + 11]) << 0)
            b = (ord(self.buffer[self.pos + 12]) << 16) + \
                (ord(self.buffer[self.pos + 13]) << 8) + \
                (ord(self.buffer[self.pos + 14]) << 0)
            if e == 0:
                s = "ill-defined"
            else:
                s = str(1.0 / (e / 65536.0))
            self.print_header("Gamma exponent", s)
            if l == 0:
                s = "ill-defined"
            else:
                s = str(1.0 / (l / 65536.0))
            self.print_header("Linear slope", s)
            self.print_header("Threshold", str(t / 65536.0))
            if a == 0:
                s = "ill-defined"
            else:
                s = str(1.0 / (a / 65536.0))
            self.print_header("Nonlinear slope", s)
            self.print_header("Offset", str(b / 65536.0))
            self.pos += 15
        elif tnlt == 2:
            npts = ordw(self.buffer[self.pos + 0:self.pos + 2])
            dmin = ordl(self.buffer[self.pos + 2:self.pos + 6])
            dmax = ordl(self.buffer[self.pos + 6:self.pos + 10])
            prec = ord(self.buffer[self.pos + 10])
            self.print_header("Number of points", npts)
            self.print_header("Range minimum", dmin / ((1L << 32) - 1.0))
            self.print_header("Range maximum", dmax / ((1L << 32) - 1.0))
            self.print_header("Data precision", "%d bits" % prec)
            self.pos += 11
            for i in range(npts):
                if prec <= 8:
                    dt = ord(self.buffer[self.pos]) + 0L
                    s = str(dt / ((1L << prec) - 1.0))
                    self.pos += 1
                elif prec <= 16:
                    dt = ordw(self.buffer[self.pos + 0:self.pos + 2])
                    s = str(dt / ((1L << prec) - 1.0))
                    self.pos += 2
                elif prec <= 32:
                    dt = ordl(self.buffer[self.pos + 0:self.pos + 4])
                    s = str(dt / ((1L << prec) - 1.0))
                    self.pos += 4
                else:
                    s = "ill-defined"
                self.print_header("Data entry %d" % i, s)
        self._end_marker()

    def read_COM(self):
        self._new_marker("COM", "Comment")
        if self.size < 4:
            raise InvalidSizedMarker("COM")
        reg = ordw(self.buffer[self.pos + 2:self.pos + 4])
        if reg == 0:
            s = "binary"
        elif reg == 1:
            s = "ISO-8859-15"
        else:
            s = "unknown"
        self.print_header("Registration", s)
        if reg == 1:
            self.print_header("Comment", self.buffer[self.pos + 4:self.pos + self.size])
        else:
            self.print_header("Comment", "...")
        self._end_marker()
        self.pos += self.size

    def read_EOC(self):
        self._new_marker("EOC", "End of codestream")
        self._end_marker()

    def read_CAP(self):
        self._new_marker("CAP", "Extended Capabilities Marker")
        pcap = ordl(self.buffer[self.pos + 2:self.pos + 6])
        offs = self.pos + 6
        for i in range(32):
            if pcap & (1 << (32 - i)):
                if offs >= self.pos + self.size:
                    raise InvalidSizedMarker("CAP")
                self.print_header("Extended capabilities for part %d" % i,
                                  "0x%x" % (ordw(self.buffer[offs:offs + 2])))
                offs += 2
        self._end_marker()
        self.pos += self.size

    def read_CPF(self):
        self._new_marker("CPF", "Corresponding Profile Marker")
        offs = self.pos + 2
        pcan = self.size - 2
        if pcan < 0 or pcan & 1:
            raise InvalidSizedMarker("CPF")
        cpfnum = -1
        bpos = 1
        for i in range(0, pcan / 2):
            cpfnum += ordw(self.buffer[offs:offs + 2]) * bpos
            bpos *= 65536
            offs += 2
        if cpfnum == 4095:
            self.print_header("Corresponding Profile", "to be found in the PRF marker")
        else:
            self.print_header("Corresponding Profile", "0x%x" % cpfnum)
        self._end_marker()
        self.pos += self.size

    def read_unknown_marker(self):
        if self.marker == 0x00 or self.marker == 0x01 or self.marker == 0xfe or \
                0xc0 <= self.marker <= 0xdf:
            type = "ISO/IEC 10918-1"
        elif 0xf0 <= self.marker <= 0xf6:
            type = "ISO/IEC 10918-3"
        elif 0xf7 <= self.marker <= 0xf8:
            type = "ISO/IEC 14495-1"
        elif 0x30 <= self.marker <= 0x3f:
            type = "segment-less"
        elif 0x50 <= self.marker <= 0xff:
            type = "invalid ISO/IEC 15444-xx"
        else:
            raise InvalidMarker("%02x" % (self.marker))
        self._new_marker("0xff%02x" % (self.marker), "unknown %s" % (type))
        self._end_marker()
        if self.size is not None:
            if self.size < 2:
                raise InvalidSizedMarker("unknown")
            self._end_marker()
            self.pos += self.size

    def read_marker(self):
        if len(self.buffer) - self.pos < 2:
            raise UnexpectedEOC()
        if ord(self.buffer[self.pos + 0]) != 0xff:
            raise MisplacedData()

        self.marker = ord(self.buffer[self.pos + 1])
        self.pos += 2

        if 0x30 <= self.marker <= 0x3f or \
                self.marker == 0x4f or self.marker == 0x93 or \
                self.marker == 0x92 or self.marker == 0xd9:
            self.size = None
        else:
            if len(self.buffer) - self.pos < 2:
                raise UnexpectedEOC()
            self.size = (ord(self.buffer[self.pos + 0]) << 8) + \
                        (ord(self.buffer[self.pos + 1]) << 0)

    def read_header_marker(self):
        self.read_marker()

        if self.marker == 0x50:
            self.read_CAP()
        elif self.marker == 0x52:
            self.read_COD()
        elif self.marker == 0x53:
            self.read_COC()
        elif self.marker == 0x54:
            self.read_NSI()
        elif self.marker == 0x55:
            self.read_TLM()
        elif self.marker == 0x57:
            self.read_PLM()
        elif self.marker == 0x58:
            self.read_PLT()
        elif self.marker == 0x59:
            self.read_CPF()
        elif self.marker == 0x5c:
            self.read_QCD()
        elif self.marker == 0x5d:
            self.read_QCC()
        elif self.marker == 0x5e:
            self.read_RGN()
        elif self.marker == 0x5f:
            self.read_POC()
        elif self.marker == 0x60:
            self.read_PPM()
        elif self.marker == 0x61:
            self.read_PPT()
        elif self.marker == 0x63:
            self.read_CRG()
        elif self.marker == 0x64:
            self.read_COM()
        elif self.marker == 0x74:
            self.read_MCT()
        elif self.marker == 0x75:
            self.read_MCC()
        elif self.marker == 0x76:
            self.read_NLT()
        elif self.marker == 0x77:
            self.read_MCO()
        elif self.marker == 0x78:
            self.read_CBD()
        else:
            self.read_unknown_marker()

    def read_data_marker(self):
        self.read_marker()

        if self.marker == 0xd9:  # EOC
            self.read_EOC()
            return 1
        elif self.marker == 0x90:  # SOT
            self.pos -= 2
            return 1
        elif self.marker == 0x91:  # SOP
            self.read_SOP()
            return 0
        elif self.marker == 0x92:  # EPH
            self.read_EPH()
            return 0
        else:
            self.read_unknown_marker()
            return 0

    def progression_order(self, x):
        if x == 0:
            return "layer-resolution level-component-position"
        elif x == 1:
            return "resolution level-layer-component-position"
        elif x == 2:
            return "resolution level-position-component-layer"
        elif x == 3:
            return "position-component-resolution level-layer"
        elif x == 4:
            return "component-position-resolution level-layer"
        else:
            return "unknown"


#
# Main Function for Codestream Parsing
#

if __name__ == "__main__":
    # Read Arguments
    if len(sys.argv) != 2:
        print("Usage: %s FILE" % (sys.argv[0]))
        sys.exit(1)

    print("###############################################################")
    print("# JP2 codestream log file generated by jp2codestream.py       #")
    print("# jp2codestream.py is copyrighted (c) 2001-2016 ISO           #")
    print("# Read LICENSE.txt for licence details                        #")
    print("###############################################################")
    print("")

    # Parse Files
    filename = sys.argv[1]
    file = open(filename, "rb")
    jp2 = JP2Codestream()
    try:
        jp2.stream_parse(file, 0)
    except JP2Error, e:
        print("***{}".format(str(e)))
