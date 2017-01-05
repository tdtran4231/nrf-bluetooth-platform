#!/usr/bin/env python
# encoding: utf-8
"""
Adapted from i2c-test.py from Peter Huewe by Jean-Michel Picod 
Modified by Don C. Weber (cutaway) and InGuardians, Inc. 20141015

This file is part of pyBusPirate.

pyBusPirate is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pyBusPirate is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pyBusPirate.  If not, see <http://www.gnu.org/licenses/>.
"""
import sys
from pyBusPirateLite.I2C import *
import argparse

speed = [\
    I2CSpeed._5KHZ,\
    I2CSpeed._50KHZ,\
    I2CSpeed._100KHZ,\
    I2CSpeed._400KHZ\
    ]

speed_names = [\
    "5 KHZ",\
    "50 KHZ",\
    "100 KHZ",\
    "400 KHZ"\
    ]

def i2c_write_data(data):
    i2c.send_start_bit()
    i2c.bulk_trans(len(data),data)
    i2c.send_stop_bit()

def i2c_read_bytes(address, numbytes, ret=False):
    data_out=[]
    i2c.send_start_bit()
    i2c.bulk_trans(len(address),address)
    while numbytes > 0:
        if not ret:
            print ord(i2c.read_byte())
        else:
            data_out.append(ord(i2c.read_byte()))
        if numbytes > 1:
            i2c.send_ack()
        numbytes-=1
    i2c.send_nack()
    i2c.send_stop_bit()
    if ret:
        return data_out

if __name__ == '__main__':
    parser = argparse.ArgumentParser(sys.argv[0])
    parser.add_argument("-o", "--output", dest="outfile", metavar="OUTFILE", type=argparse.FileType('wb'),
            required=True,
            help="File name to write data dump. Example: -o /tmp/i2c_dump.bin")
    parser.add_argument("-d", "--serial-port", dest="bp", default="/dev/ttyUSB0",
                        help="The comm device to connect to. Example: -d /dev/ttyUSB0")
    parser.add_argument("-b", "--block-size", dest="bsize", default=256, type=int,
                        help="EEPROM memory block size. See the EEPROM's data sheet.")
    parser.add_argument("-s", "--size", dest="size", type=int, required=True,
                        help="EEPROM memory size. See the EEPROM's data sheet.")
    parser.add_argument("-S", "--i2c-speed", dest="i2c_speed", default=3, type=int,
                        help="0=5KHZ, 1=50KHZ,2=100KHZ, 3=400KHZ")
    # Debug mode not implemented yet
    #parser.add_option("-D", "--debug",
                        #dest="DEBUG", action="store_true", default=False,
                        #help="Debug mode to print debug information about SPI transations.")

    args = parser.parse_args(sys.argv[1:])

    #NOTE: Leave USB speed at max because it never really changes when using the BusPirate.
    i2c = I2C(args.bp, 115200)

    print "Entering binmode: ",
    if i2c.BBmode():
        print "OK."
    else:
        print "failed."
        sys.exit()

    print "Entering raw I2C mode: ",
    if i2c.enter_I2C():
        print "OK."
    else:
        print "failed."
        sys.exit()
        
    print "Configuring I2C."
    if not i2c.cfg_pins(I2CPins.POWER | I2CPins.PULLUPS):
        print "Failed to set I2C peripherals."
        sys.exit()
    #if not i2c.set_speed(I2CSpeed._400KHZ):
    if not i2c.set_speed(speed[args.i2c_speed]):
        print "Failed to set I2C Speed."
        sys.exit()
    i2c.timeout(0.2)
    
    print "Dumping %d bytes out of the EEPROM." % args.size

    # Start dumping
    for block in range(0, args.size, args.bsize):
        # Reset the address
        i2c_write_data([0xa0 + ((block / args.bsize) << 1), 0])
        args.outfile.write("".join([chr(x) for x in i2c_read_bytes([0xa1 + ((block / args.bsize) << 1)], args.bsize, True)]))
    if args.size % 16 != 0:
        end = 16 * (args.size / args.bsize)
        args.outfile.write("".join([chr(x) for x in i2c_read_bytes([0xa1 + ((args.size / args.bsize) << 1)], args.size % args.bsize, True)]))
    args.outfile.close()

    print "Reset Bus Pirate to user terminal: "
    if i2c.resetBP():
        print "OK."
    else:
        print "failed."
        sys.exit()

