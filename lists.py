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
    0xCC: ['ACK'],
    0x0C: ['NACK'],
    0xC0: ['BUSY'],
    0x00: ['NACK+BUSY'],
}
