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
    received_data = ser.read()
    sleep(1)
    data_left = ser.inWaiting()
    received_data += ser.read(data_left)
    print(received_data.decode('ascii'))
    print("...")
