import serial
from time import sleep

ser = serial.Serial(
    port="/dev/ttyAMA0", 
    baudrate = 9600, 
    parity=serial.PARITY_NONE, 
    stopbits=serial.STOPBITS_ONE, 
    bytesize=serial.EIGHTBITS,
)
ser.reset_input_buffer()
ser.reset_output_buffer()
#while True:
#    ser.write(b'Hello World')
#    print("Wrote to /dev/ttyS0")
#    sleep(3)
#ser.write(b'\x0A')
#ser.write(b'\x60')
#ser.write(b'\x0A\x45e2e4_')
snm = "e2e4"
fifth_byte = "_"
robot_move_instr_bytes = bytearray([0x0A, 0x45] + [ord(c) for c in snm] + [ord(fifth_byte)])
ser.write(robot_move_instr_bytes)
print("Wrote to /dev/ttyAMA0")
