import serial
from time import sleep

ser = serial.Serial(
    port="/dev/ttyS0", 
    baudrate = 9600, 
    parity=serial.PARITY_NONE, 
    stopbits=serial.STOPBITS_ONE, 
    bytesize=serial.EIGHTBITS,
)
while True:
    ser.write(b'Hello World')
    print("Wrote to /dev/ttyS0")
    sleep(3)
