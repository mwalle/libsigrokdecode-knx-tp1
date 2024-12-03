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
    )
    annotation_rows = (
        ('bits', 'Bits', (0, 1, 2, 3, 4, 5)),
        ('raw', 'Raw data', (6,)),
    )
    binary = (
        ('rxtx', 'RX/TX dump'),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.samplerate = None
        self.state = 'IDLE'
        self.bitnum = 0
        self.parity = False
        self.byte = 0

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
                    self.parity = False
                    self.byte = 0
                    self.state = 'DATA'
            elif self.state == 'DATA':
                rxtx, tx = self.wait({'skip': self.bit_width})
                if self.options['polarity'] == 'inverted':
                    rxtx ^= 1
                self.putb([1, ['1'] if rxtx else ['0']])
                self.byte = (rxtx << 8 | self.byte) >> 1
                self.bitnum += 1
                if rxtx:
                    self.parity = not self.parity
                if self.bitnum == 8:
                    self.putd([6, [f'{self.byte:02X}']])
                    self.putbinary([0, self.byte.to_bytes()])
                    self.state = 'PARITY'
            elif self.state == 'PARITY':
                rxtx, tx = self.wait({'skip': self.bit_width})
                if self.options['polarity'] == 'inverted':
                    rxtx ^= 1
                if int(self.parity) == rxtx:
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
                self.bitnum += 1
                if self.bitnum == 2:
                    self.state = 'IDLE'
