# -*- coding: utf-8 -*-
"""
JPEG codestream-parser (All-JPEG Codestream/File Format Parser Tools)
See LICENCE.txt for copyright and licensing conditions.
"""

import StringIO

from jp2utils import *
from jp2box import *


class BoxSegment:
    def __init__(self,buffer,offset):
        self.offset=offset
        self.en=ordw(buffer[6:8])
        self.seq=ordl(buffer[8:12])
        self.lbox=ordl(buffer[12:16])
        if self.lbox != 1 and self.lbox < 8:
            raise InvalidBoxSize()
        self.type=buffer[16:20]
        if self.lbox == 1:
            self.lbox=ordq(buffer[20:28])
            self.buffer=buffer[28:]
            self.body=self.lbox-4-4-8
        else:
            self.buffer=buffer[20:]
            self.body=self.lbox-4-4

    def __lt__(self,other):
        return self.seq < other.seq


class BoxIndex:
    def __init__(self,boxtype,en):
        self.type=boxtype
        self.en=en

    def __hash__(self):
        return hash(self.type)^hash(self.en)

    def __eq__(self,other):
        return self.type == other.type and self.en == other.en

class BoxList:
    def __init__(self):
        self.boxlist=dict()

    def addBoxSegment(self,segment):
        index=BoxIndex(segment.type,segment.en)
        if not index in self.boxlist:
            self.boxlist[index] = list()
        self.boxlist[index].append(segment)

    def isComplete(self,segment):
        index=BoxIndex(segment.type,segment.en)
        if not index in self.boxlist:
            return False
        else:
            total=0
            boxsize=None
            for segment in self.boxlist[index]:
                total = total+len(segment.buffer)
                if boxsize == None:
                    boxsize = segment.body
                else:
                    if boxsize != segment.body:
                        raise BoxSizesInconsistent()
            if boxsize != None and boxsize == total:
                return True
        return False

    def toBox(self,segment,indent):
        index=BoxIndex(segment.type,segment.en)
        if not index in self.boxlist:
            return None
        else:
            if segment.lbox > 0xffffffff:
                buffer=chrl(1)+segment.type+chrq(segment.lbox)
            else:
                buffer=chrl(segment.lbox)+segment.type
            sortedlist=sorted(self.boxlist[index])
            offset=sortedlist[0].offset
            for seg in sortedlist:
                buffer=buffer+seg.buffer
            stringstream=StringIO.StringIO(buffer)
            box=JP2Box(None,stringstream)
            box.indent = indent
            return box

        



    
