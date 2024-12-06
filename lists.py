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

ack_frames = {
    0xcc: ['ACK'],
    0x0c: ['NACK'],
    0xc0: ['BUSY'],
    0x00: ['NACK+BUSY'],
}

priority = {
    0x00: ['System Priority', 'System', 'Sys'],
    0x08: ['Urgent Priority', 'Urgent', 'Urg'],
    0x04: ['Normal Priority', 'Normal', 'Norm'],
    0x0c: ['Low Priority', 'Low'],
}

t_ctrl = {
    0x8000: ['T_Data_Broadcast/T_Data_Group'],
    0x8001: ['T_Data_Tag_Group'],
    0x0000: ['T_Data_Individual'],
    0x0040: ['T_Data_Connected SeqNo:{seqno:d}'],
    0x0080: ['T_Connect'],
    0x0081: ['T_Disconnect'],
    0x00c2: ['T_ACK SeqNo:{seqno:d}'],
    0x00c3: ['T_NAK SeqNo:{seqno:d}'],
}
