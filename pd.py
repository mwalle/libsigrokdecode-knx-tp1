##
## This file is part of the libsigrokdecode project.
##
## Copyright (c) 2025 Michael Walle <michael@walle.cc>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##

from functools import lru_cache
from math import ceil, floor
import sigrokdecode as srd
from .lists import *

def tp1_address_to_str(msb, lsb):
    return '{}.{}.{}'.format(msb, lsb >> 4, lsb & 0xf)

class SamplerateError(Exception):
    pass

class Decoder(srd.Decoder):
    api_version = 3
    id = 'knx-tp1'
    name = 'KNX TP1'
    longname = 'KNX fieldbus, TP1 medium'
    desc = 'KNX fieldbus (TP1 medium) for building automation.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = []
    tags = ['Automation']
    channels = (
        {'id': 'knx', 'name': 'KNX', 'desc': 'KNX data line'},
    )
    optional_channels = (
        {'id': 'tx', 'name': 'KNX TX', 'desc': 'KNX transmit line'},
    )
    options = (
        {'id': 'polarity', 'desc': 'Polarity', 'default': 'normal',
            'values': ('normal', 'inverted')},
    )
    annotations = (
        ('start', 'start bits'),
        ('data', 'data bits'),
        ('parity-ok', 'parity OK bits'),
        ('parity-err', 'parity error bits'),
        ('stop-ok', 'stop OK bits'),
        ('stop-err', 'stop error bits'),
        ('raw', 'Raw data'),
        ('logical', 'Logical data'),
    )
    annotation_rows = (
        ('bits', 'Bits', (0, 1, 2, 3, 4, 5)),
        ('raw-data', 'Raw data', (6,)),
        ('logical-data', 'Logical data', (7,)),
    )
    binary = (
        ('rxtx', 'RX/TX dump'),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.samplerate = None
        self.state = 'IDLE'
        self.octet_num = 0
        self.last_ss = 0
        self.last_octet = 0
        self.length = 0
        self.last_frame_se = 0

    @lru_cache()
    def get_annotation_id(self, name):
        for i, a in enumerate(self.annotations):
            if a[0] == name:
                return i
        raise KeyError(name)

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_binary = self.register(srd.OUTPUT_BINARY)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value
            self.bit_width = self.samplerate / 9600

    def put(self, ss, se, output_id, data):
        if type(data[0]) is str:
            # create a copy in case data is an immutable tuple
            data = [self.get_annotation_id(data[0]), data[1]]
        super().put(ss, se, output_id, data)

    def get_sample_range(self, numbits):
        ss = self.samplenum - ceil(self.bit_width * numbits - self.bit_width / 12)
        se = self.samplenum + floor(self.bit_width / 12)
        return ss, se

    def putb(self, data):
        ss, se = self.get_sample_range(1)
        self.put(ss, se, self.out_ann, data)

    def putd(self, data):
        ss, se = self.get_sample_range(8)
        self.put(ss, se, self.out_ann, data)

    def putbinary(self, data):
        ss, se = self.get_sample_range(8)
        self.put(ss, se, self.out_binary, data)

    def handle_octet(self, octet):
        ss, se = self.get_sample_range(12)

        # ACK has a spacing of 15 bit times (see 3.2.2 System Specifications
        # Twisted Pair 1 Fig. 38), so a timeout of 10 bit times seems
        # appropriate for decoding
        if ss > self.last_frame_se + self.bit_width * 10:
            self.octet_num = 0
        self.last_frame_se = se

        if self.octet_num == 0:
            self.fcs = 0xff
            se = ss + floor(self.bit_width * 12)
            if octet & 0x33 == 0:
                desc = ack_frames.get(octet, ['Invalid', 'Inv'])
            elif octet == 0xf0:
                desc = ['Poll Data Frame']
            elif octet & 0x80:
                repeated = '' if octet & 0x20 else 'Repeated '
                if octet & 0x0c == 0x00:
                    priority = 'system'
                elif octet & 0x0c == 0x08:
                    priority = 'urgent'
                elif octet & 0x0c == 0x04:
                    priority = 'normal'
                elif octet & 0x0c == 0x0c:
                    priority = 'low'
                desc = ['{}Data Standard Frame, {} priority'.format(repeated, priority)]
            else:
                desc = ['Data Extended Frame']
            self.put(ss, se, self.out_ann, ['logical', desc])
            if octet & 0x33 == 0:
                return
        elif self.octet_num == 2:
            sa = tp1_address_to_str(octet, self.last_octet)
            self.put(self.last_ss, se, self.out_ann,
                     ['logical', ['Source Address:{}'.format(sa)]])
        elif self.octet_num == 4:
            da = tp1_address_to_str(octet, self.last_octet)
            self.put(self.last_ss, se, self.out_ann,
                     ['logical', ['Destination Address:{}'.format(da)]])
        elif self.octet_num == 5:
            # save length for FCS calculation
            self.length = octet & 15

            len = self.length
            at = 'Group Address' if octet & 0x80 else 'Individal Address'
            hc = (octet >> 4) & 7
            desc = ['{}, Hop count:{}, Length:{}'.format(at, hc, len)]
            self.put(ss, se, self.out_ann, ['logical', desc])
        elif self.octet_num > 5 and self.octet_num <= self.length + 6:
            self.put(ss, se, self.out_ann, ['logical', ['Data:{:02X}'.format(octet)]])
        elif self.octet_num == 7 + self.length:
            if self.fcs == octet:
                desc = ['FCS OK']
            else:
                desc = ['FCS error (expected {:02X})'.format(self.fcs), 'FCS error']
            self.put(ss, se, self.out_ann, ['logical', desc])
        self.fcs ^= octet
        self.last_ss = ss
        self.last_octet = octet
        self.octet_num += 1

    # oversampling by 6
    def get_next_sample_point(self):
        samplenum = self.frame_start + round(self.bit_width / 12)
        samplenum += self.sample_point * self.bit_width / 6
        self.sample_point += 1

        return ceil(samplenum)

    def sample_bit(self):
        self.bit_ss = -1
        bits = 0
        for i in range(6):
            want_num = self.get_next_sample_point()
            rxtx, _ = self.wait({'skip': want_num - self.samplenum})
            if self.bit_ss == -1:
                self.bit_ss = self.samplenum - ceil(self.bit_width / 12)

            if self.options['polarity'] == 'inverted':
                rxtx ^= 1

            bits = bits << 1 | rxtx

        # iff the first five bits (out of six) are one then it's a one
        return 1 if bits & 0x3e == 0x3e else 0

    def decode(self):
        if not self.samplerate:
            raise SampleRateError('Cannot decode without samplerate.')

        while True:
            # State machine.
            if self.state == 'IDLE':
                # wait for edge of start bit
                self.wait({0: 'f' if self.options['polarity'] == 'normal' else 'r'})
                self.frame_start = self.samplenum
                self.sample_point = 0

                rxtx = self.sample_bit()
                if not rxtx:
                    self.putb(['start', ['Start bit', 'Start', 'S']])
                    self.bitnum = 0
                    self.parity = 0
                    self.frame_error = False
                    self.byte = 0
                    self.state = 'DATA'
            elif self.state == 'DATA':
                rxtx = self.sample_bit()
                self.putb(['data', ['1'] if rxtx else ['0']])
                self.byte = (rxtx << 8 | self.byte) >> 1
                self.bitnum += 1
                self.parity = self.parity ^ rxtx
                if self.bitnum == 8:
                    self.putd(['raw', ['{:02X}'.format(self.byte)]])
                    self.putbinary([0, self.byte.to_bytes()])
                    self.state = 'PARITY'
            elif self.state == 'PARITY':
                rxtx = self.sample_bit()
                self.parity = self.parity ^ rxtx
                if not self.parity:
                    self.putb(['parity-ok', ['Parity bit', 'Parity', 'P']])
                else:
                    self.putb(['parity-err', ['Parity error', 'Parity err', 'PE']])
                self.state = 'STOP'
                self.bitnum = 0
            elif self.state == 'STOP':
                rxtx = self.sample_bit()
                if rxtx:
                    self.putb(['stop-ok', ['Stop bit', 'Stop', 'T']])
                else:
                    self.putb(['stop-err', ['Stop bit error', 'Stop err', 'TE']])
                    self.frame_error = True
                self.bitnum += 1
                if self.bitnum == 2:
                    if not self.parity and not self.frame_error:
                        self.handle_octet(self.byte)
                    self.state = 'IDLE'
