# -*- coding: utf-8 -*-
"""
JPEG codestream-parser (All-JPEG Codestream/File Format Parser Tools)
See LICENCE.txt for copyright and licensing conditions.
"""
from __future__ import print_function, division
from io import StringIO

from jp2utils import ordw, ordl, ordq, chrl, chrq, InvalidBoxSize, BoxSizesInconsistent
from jp2box import JP2Box


class BoxSegment:
    def __init__(self, buf, offset):
        self.offset = offset
        self.en = ordw(buf[6:8])
        self.seq = ordl(buf[8:12])
        self.lbox = ordl(buf[12:16])
        if self.lbox != 1 and self.lbox < 8:
            raise InvalidBoxSize()
        self.type = buf[16:20]
        if self.lbox == 1:
            self.lbox = ordq(buf[20:28])
            self.buffer = buf[28:]
            self.body = self.lbox - 4 - 4 - 8
        else:
            self.buffer = buf[20:]
            self.body = self.lbox - 4 - 4

    def __lt__(self, other):
        return self.seq < other.seq


class BoxIndex:
    def __init__(self, box_type, en):
        self.type = box_type
        self.en = en

    def __hash__(self):
        return hash(self.type) ^ hash(self.en)

    def __eq__(self, other):
        return self.type == other.type and self.en == other.en


class BoxList:
    def __init__(self):
        self._box_list = dict()

    def addBoxSegment(self, segment):
        index = BoxIndex(segment.type, segment.en)
        if index not in self._box_list:
            self._box_list[index] = list()
        self._box_list[index].append(segment)

    def isComplete(self, segment):
        index = BoxIndex(segment.type, segment.en)
        if index not in self._box_list:
            return False
        else:
            total = 0
            box_size = None
            for segment in self._box_list[index]:
                total = total + len(segment.buffer)
                if box_size is None:
                    box_size = segment.body
                else:
                    if box_size != segment.body:
                        raise BoxSizesInconsistent()
            if box_size == total:
                return True
        return False

    def toBox(self, segment, indent):
        index = BoxIndex(segment.type, segment.en)
        if index not in self._box_list:
            return None
        else:
            if segment.lbox > 0xffffffff:
                buf = chrl(1) + segment.type + chrq(segment.lbox)
            else:
                buf = chrl(segment.lbox) + segment.type
            sortedlist = sorted(self._box_list[index])
            # offset = sortedlist[0].offset
            for seg in sortedlist:
                buf = buf + seg.buffer
            string_stream = StringIO(buf)
            box = JP2Box(None, string_stream)
            box.indent = indent
            return box
