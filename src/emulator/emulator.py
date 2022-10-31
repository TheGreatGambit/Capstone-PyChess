import serial

com_port = 'COM16'  # Change this

# Sends the moves from the terminal to the MSP
with serial.Serial(com_port, 9600) as ser:
    while True:
        try:
            user_input = input("Move (ex: e2e4): ")
            user_input = user_input.strip().lower()
            # TODO: Add input checking

            message = bytes(user_input + 'M', 'utf-8')
            ser.write(message)
            print(f'Sent {message}')
        except KeyboardInterrupt:
            print('\n')
            break
    print("Exiting")