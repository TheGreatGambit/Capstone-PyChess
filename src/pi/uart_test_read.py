import serial
from time import sleep

ser = serial.Serial(
    port="/dev/serial0", 
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
    print(received_data)
    print(received_data.hex())
    print(int(received_data.hex(), 16))
    print(received_data.decode('ascii'))
    print(received_data.decode('utf-8'))
    print("...")
