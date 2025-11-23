import serial
import struct

ser = serial.Serial('COM3', 9600, timeout=2)

while True:
    if ser.read() == b'\x42':          # Frame header byte 1
        if ser.read() == b'\x4d':      # Frame header byte 2
            frame = ser.read(30)       # Remaining bytes
            data = struct.unpack('>HHHHHHHHHHHHHH', frame[2:30])
            pm2_5 = data[2]            # PM2.5 (CF=1)
            print("PM2.5 =", pm2_5)
