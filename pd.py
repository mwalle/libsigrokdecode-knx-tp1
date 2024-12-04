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

import sigrokdecode as srd
from .lists import *

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
    tags = ['Embedded/industrial']
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
        ('raw', 'Raw data', (6,)),
        ('logical', 'Logical data', (7,)),
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

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_binary = self.register(srd.OUTPUT_BINARY)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value
            self.bit_width = int(self.samplerate / 9600)

    def putb(self, data):
        ss = self.samplenum - int(self.bit_width / 6)
        self.put(ss, ss + self.bit_width, self.out_ann, data)

    def putd(self, data):
        ss = self.samplenum - int(self.bit_width / 6) - self.bit_width * 7
        se = ss + self.bit_width * 8
        self.put(ss, se, self.out_ann, data)

    def putbinary(self, data):
        ss = self.samplenum - int(self.bit_width / 6) - self.bit_width * 7
        se = ss + self.bit_width * 8
        self.put(ss, se, self.out_binary, data)

    def handle_octet(self, octet):
        ss = self.samplenum - int(self.bit_width / 6) - self.bit_width * 11
        se = ss + self.bit_width * 12
        if self.octet_num == 0:
            self.fcs = 0xff
            se = ss + self.bit_width * 12
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
                desc = [f'{repeated}Data Standard Frame, {priority} priority']
            else:
                desc = ['Data Extended Frame']
            self.put(ss, se, self.out_ann, [7, desc])
            if octet & 0x33 == 0:
                return
        elif self.octet_num == 2:
            sa = f'{octet:d}.{self.last_octet >> 4:d}.{self.last_octet & 0xf:d}'
            self.put(self.last_ss, se, self.out_ann, [7, [f'Source Address:{sa}']])
        elif self.octet_num == 4:
            sa = f'{octet:d}.{self.last_octet >> 4:d}.{self.last_octet & 0xf:d}'
            self.put(self.last_ss, se, self.out_ann, [7, [f'Destination Address:{sa}']])
        elif self.octet_num == 5:
            at = 'Group Address' if octet & 0x80 else 'Individal Address'
            hop_count = (octet >> 4) & 7
            self.length = octet & 15
            desc = [f'{at}, Hop count:{hop_count}, Length:{self.length}']
            self.put(ss, se, self.out_ann, [7, desc])
        elif self.octet_num > 5 and self.octet_num <= self.length + 6:
            self.put(ss, se, self.out_ann, [7, [f'Data:{octet:02X}']])
        elif self.octet_num == 7 + self.length:
            if self.fcs == octet:
                desc = ['FCS OK']
            else:
                desc = [f'FCS error (expected {self.fcs:02X})', 'FCS error']
            self.put(ss, se, self.out_ann, [7, desc])
            self.octet_num = 0
            return
        self.fcs ^= octet
        self.last_ss = ss
        self.last_octet = octet
        self.octet_num += 1

    def decode(self):
        if not self.samplerate:
            raise SampleRateError('Cannot decode without samplerate.')

        while True:
            # State machine.
            if self.state == 'IDLE':
                self.wait({0: 'f' if self.options['polarity'] == 'normal' else 'r'})
                # skip a sixth of the bit width
                rxtx, tx = self.wait({'skip': int(self.bit_width / 6)})
                if self.options['polarity'] == 'inverted':
                    rxtx ^= 1
                if not rxtx:
                    self.putb([0, ['Start bit', 'Start', 'S']])
                    self.bitnum = 0
                    self.parity = 0
                    self.frame_error = False
                    self.byte = 0
                    self.state = 'DATA'
            elif self.state == 'DATA':
                rxtx, tx = self.wait({'skip': self.bit_width})
                if self.options['polarity'] == 'inverted':
                    rxtx ^= 1
                self.putb([1, ['1'] if rxtx else ['0']])
                self.byte = (rxtx << 8 | self.byte) >> 1
                self.bitnum += 1
                self.parity = self.parity ^ rxtx
                if self.bitnum == 8:
                    self.putd([6, [f'{self.byte:02X}']])
                    self.putbinary([0, self.byte.to_bytes()])
                    self.state = 'PARITY'
            elif self.state == 'PARITY':
                rxtx, tx = self.wait({'skip': self.bit_width})
                if self.options['polarity'] == 'inverted':
                    rxtx ^= 1
                self.parity = self.parity ^ rxtx
                if not self.parity:
                    self.putb([2, ['Parity bit', 'Parity', 'P']])
                else:
                    self.putb([3, ['Parity error', 'Parity err', 'PE']])
                self.state = 'STOP'
                self.bitnum = 0
            elif self.state == 'STOP':
                rxtx, tx = self.wait({'skip': self.bit_width})
                if self.options['polarity'] == 'inverted':
                    rxtx ^= 1
                if rxtx:
                    self.putb([4, ['Stop bit', 'Stop', 'T']])
                else:
                    self.putb([5, ['Stop bit error', 'Stop err', 'TE']])
                    self.frame_error = True
                self.bitnum += 1
                if self.bitnum == 2:
                    if not self.parity and not self.frame_error:
                        self.handle_octet(self.byte)
                    self.state = 'IDLE'
