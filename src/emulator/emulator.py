import serial

com_port = 'COM5'  # Change this
START_BYTE = 0x0A
HUMAN_MOVE_INSTR_AND_LEN = 0x35

# Sends the moves from the terminal to the MSP
with serial.Serial(com_port, 9600) as ser:
    while True:
        try:
            user_input = input("Move (ex: e2e4): ")
            user_input = user_input.strip().lower()
            # TODO: Add input checking

            message = bytes(chr(START_BYTE) + chr(HUMAN_MOVE_INSTR_AND_LEN) + user_input + '_', 'ascii')
            ser.write(message)
            print(f'Sent {message}')
        except KeyboardInterrupt:
            print('\n')
            break
    print("Exiting")