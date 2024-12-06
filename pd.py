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

def tp1_address_to_str(addr):
    return '{}/{}/{}'.format(addr >> 12, addr >> 8 & 0xf, addr & 0xff)

def get_desc(desc, key, **kwargs):
    desc_list = desc.get(key, ['Invalid', 'Inv'])
    return list(map(lambda s: str.format(s, **kwargs), desc_list))

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
        ('link', 'Link layer data'),
        ('transport', 'Transport layer data'),
        ('application', 'Application layer data'),
    )
    annotation_rows = (
        ('bits', 'Bits', (0, 1, 2, 3, 4, 5)),
        ('raw-data', 'Raw data', (6,)),
        ('layers', 'Layers', (7,8,9,)),
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

    def handle_apdu(self, apdu):
        if len(apdu) >= 2:
            _, se0, ctrl0 = apdu[0]
            _, se, ctrl1 = apdu[1]
            ss = se0 - floor(self.bit_width * 2)
            ctrl = (ctrl0 << 8) & 0x300 | ctrl1

            data = ' '.join(map(lambda d: str.format('{:02X}', d[2]), apdu[2:]))
            # special handling for UserMsg
            if ctrl >= 0x2ca and ctrl <= 0x2f7:
                no = ctrl - 0x2ca
                se = apdu[-1][1]
                desc = get_desc(a_ctrl, ctrl-no, no=no, data=data)
            elif ctrl >= 0x2f8 and ctrl <= 0x2fe:
                no = ctrl - 0x2f8
                se = apdu[-1][1]
                desc = get_desc(a_ctrl, ctrl-no, no=no, data=data)
            else:
                desc = get_desc(a_ctrl, ctrl)

            self.put(ss, se, self.out_ann, ['application', desc])

    def handle_tpdu(self, tpdu):
        if len(tpdu) >= 1:
            ss, se, ctrl = tpdu[0]
            if self.at:
                ctrl |= 0x8000
            seqno = 0
            if not ctrl & 0x80:
                ctrl &= 0x80fc
                se -= floor(self.bit_width * 2)
                self.handle_apdu(tpdu)
            if ctrl & 0x40:
                seqno = ctrl >> 2 & 0xf
                ctrl &= 0x80c3
            desc = get_desc(t_ctrl, ctrl, seqno=seqno)
            self.put(ss, se, self.out_ann, ['transport', desc])

    def handle_octet(self, octet):
        ss, se = self.get_sample_range(8)

        # ACK has a spacing of 15 bit times (see 3.2.2 System Specifications
        # Twisted Pair 1 Fig. 38), so a timeout of 10 bit times seems
        # appropriate for decoding
        if ss > self.last_frame_se + self.bit_width * 10:
            self.octet_num = 0
        self.last_frame_se = se

        if self.octet_num == 0:
            self.fcs = 0xff
            self.sa = None
            self.da = None
            self.length = 0
            self.at = False
            self.tpdu = []
            if octet & 0x33 == 0:
                desc = get_desc(ack_frames, octet)
            elif octet == 0xf0:
                desc = ['Poll Data Frame']
            elif octet & 0x80:
                repeated = '' if octet & 0x20 else 'Repeated '
                prio = get_desc(priority, octet & 0x0c)[0]
                desc = ['{}Data Standard Frame, {}'.format(repeated, prio)]
            else:
                desc = ['Data Extended Frame']
            self.put(ss, se, self.out_ann, ['link', desc])
            if octet & 0x33 == 0:
                return
        elif self.octet_num == 2:
            self.sa = self.last_octet << 8 | octet
            sa = tp1_address_to_str(self.sa)
            self.put(self.last_ss, se, self.out_ann,
                     ['link', ['Source Address:{}'.format(sa)]])
        elif self.octet_num == 4:
            self.da = self.last_octet << 8 | octet
            da = tp1_address_to_str(self.da)
            self.put(self.last_ss, se, self.out_ann,
                     ['link', ['Destination Address:{}'.format(da)]])
        elif self.octet_num == 5:
            self.length = octet & 15
            self.at = bool(octet & 0x80)
            at = 'Group Address' if self.at else 'Individal Address'
            hc = (octet >> 4) & 7
            desc = ['{}, Hop count:{}, Length:{}'.format(at, hc, self.length)]
            self.put(ss, se, self.out_ann, ['link', desc])
        elif self.octet_num > 5 and self.octet_num <= self.length + 6:
            self.tpdu.append((ss, se, octet))
        elif self.octet_num == 7 + self.length:
            if self.fcs == octet:
                desc = ['FCS OK']
                self.handle_tpdu(self.tpdu)
            else:
                desc = ['FCS error (expected {:02X})'.format(self.fcs), 'FCS error']
            self.put(ss, se, self.out_ann, ['link', desc])
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
                    self.putbinary([0, self.byte.to_bytes(length=1, byteorder='big')])
                    self.handle_octet(self.byte)
                    self.state = 'PARITY'
            elif self.state == 'PARITY':
                rxtx = self.sample_bit()
                self.parity = self.parity ^ rxtx
                if not self.parity:
                    self.putb(['parity-ok', ['Parity bit', 'Parity', 'P']])
                else:
                    self.putb(['parity-err', ['Parity error', 'Parity err', 'PE']])
                self.state = 'STOP'
            elif self.state == 'STOP':
                rxtx = self.sample_bit()
                if rxtx:
                    self.putb(['stop-ok', ['Stop bit', 'Stop', 'T']])
                else:
                    self.putb(['stop-err', ['Stop bit error', 'Stop err', 'TE']])
                self.state = 'IDLE'
