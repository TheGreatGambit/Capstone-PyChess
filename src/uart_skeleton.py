import serial
from time import sleep

ser = serial.Serial(
    port="/dev/ttyS0", 
    baudrate = 9600, 
    parity=serial.PARITY_NONE, 
    stopbits=serial.STOPBITS_ONE, 
    bytesize=serial.EIGHTBITS,
)

start_signal = ""

while (start_signal != "S"):
    start_signal = ser.read(1).decode('ascii')
    sleep(3)
    print("Waiting for start signal...")

print("Received S")

ser.write(b"S")
print("Sent back S")

while True:
    pass
