import serial
from time import sleep

ser = serial.Serial(
    port="/dev/ttyAMA0", 
    baudrate = 9600, 
    parity=serial.PARITY_NONE, 
    stopbits=serial.STOPBITS_ONE, 
    bytesize=serial.EIGHTBITS,
)
#while True:
#    ser.write(b'Hello World')
#    print("Wrote to /dev/ttyS0")
#    sleep(3)
#ser.write(b'\x0A')
#ser.write(b'\x60')
ser.write(b'\x0A\x45e2e4_')
print("Wrote to /dev/ttyAMA0")
