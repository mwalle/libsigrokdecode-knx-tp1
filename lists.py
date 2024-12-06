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

a_ctrl = {
    0x0000: ['A_GroupValue_Read'],
    0x0040: ['A_GroupValue_Response'],
    0x0080: ['A_GroupValue_Write'],

    0x00c0: ['A_IndividualAddress_Write'],
    0x0100: ['A_IndividualAddress_Read'],
    0x0140: ['A_IndividualAddress_Response'],

    0x0180: ['A_ADC_Read'],
    0x01c0: ['A_ADC_Response'],

    0x01c8: ['A_SystemNetworkParameter_Read'],
    0x01c9: ['A_SystemNetworkParameter_Response'],
    0x01ca: ['A_SystemNetworkParameter_Write'],

    0x0200: ['A_Memory_Read'],
    0x0240: ['A_Memory_Response'],
    0x0280: ['A_Memory_Write'],

    0x02c0: ['A_UserMemory_Read'],
    0x02c1: ['A_UserMemory_Response'],
    0x02c2: ['A_UserMemory_Write'],

    0x02c4: ['A_UserMemoryBit_Write'],

    0x02c5: ['A_UserManufacturerInfo_Read'],
    0x02c6: ['A_UserManufacturerInfo_Response'],

    0x02c7: ['A_FunctionPropertyCommand'],
    0x02c8: ['A_FunctionPropertyState_Read'],
    0x02c9: ['A_FunctionPropertyState_Response'],

    0x02ca: ['A_UserMsg{no} Data:{data}'],
    0x02f8: ['A_ManufacturerUserMsg{no} Data:{data}'],

    0x0300: ['A_DeviceDescriptor_Read'],
    0x0340: ['A_DeviceDescriptor_Response'],
    0x0380: ['A_Restart'],

    0x03d5: ['A_PropertyValue_Read'],
    0x03d6: ['A_PropertyValue_Response'],
    0x03d7: ['A_PropertyValue_Write'],
    0x03d8: ['A_PropertyDescription_Read'],
    0x03d9: ['A_PropertyDescription_Response'],

    0x03da: ['A_NetworkParameter_Read'],
    0x03db: ['A_NetworkParameter_Response'],

    0x03dc: ['A_IndividualAddressSerialNumber_Read'],
    0x03dd: ['A_IndividualAddressSerialNumber_Response'],
    0x03de: ['A_IndividualAddressSerialNumber_Write'],
}
