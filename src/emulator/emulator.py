import serial

com_port = 'COM16'  # Change this
START_BYTE = 0x0A
HUMAN_MOVE_INSTR_AND_LEN = 0x35

# Sends moves from the terminal to the MSP
def main():
    with serial.Serial(com_port, 9600) as ser:
        while True:
            valid_move = True
            message = []
            try:
                user_input = input("Move (ex: e2e4): ")
                user_input = user_input.strip().lower()

                # Light input checking
                if len(user_input) == 4:
                    # Check for castling
                    if user_input == 'e1c1' or user_input == 'e1g1' or user_input == 'e8c8' or user_input == 'e8g8':
                        message = [START_BYTE, HUMAN_MOVE_INSTR_AND_LEN] + [ord(c) for c in user_input] + [ord('c')]
                    else:
                        message = [START_BYTE, HUMAN_MOVE_INSTR_AND_LEN] + [ord(c) for c in user_input] + [ord('_')]
                elif (len(user_input) == 5) and (user_input[4] == 'Q'):
                    message = [START_BYTE, HUMAN_MOVE_INSTR_AND_LEN] + [ord(c) for c in user_input]
                else:
                    print("Invalid move given!")
                    valid_move = False

                # If the move is potentially valid, send it
                if valid_move:
                    # Add the checkbytes, then send the message
                    message += fl16_get_check_bytes(fletcher16_nums(message))
                    ser.write(bytearray(message))
                    print(f'Sent {message}')
            except KeyboardInterrupt:
                print('\n')
                break
        print("Exiting")

def fletcher16_nums(data: list) -> int:
    """
    Calculates and returns the Fletcher-16 checksum of a given list of 8-bit numbers.
    :param data: A list containing the 8-bit nums to be evaluated
    :returns: The Fletcher-16 checksum of param data
    """ 
    sum1 = 0
    sum2 = 0

    for num in data:
        sum1 = (sum1 + num) % 255
        sum2 = (sum2 + sum1) % 255

    return (sum2 << 8) | sum1


def fl16_get_check_bytes(checksum: int) -> list:
    """
    Takes a Fletcher-16 checksum and converts it into a pair of corresponding check bytes. 
    :param checksum: A Fletcher-16 checksum
    :returns: A pair of corresponding check bytes in a list
    """ 
    f0 = checksum & 0xFF;
    f1 = (checksum >> 8) & 0xFF;
    c0 = 0xFF - ((f0 + f1) % 0xFF);
    c1 = 0xFF - ((f0 + c0) % 0xFF);
    return [c0, c1]


def validate_transmission(message: list) -> bool:
    """
    Validates error-free transmission by checking the non-checksum bytes against the
    checksum (last two in the "message" argument) bytes. 
    :param message: A list of bytes representing the entire instruction AND its check bytes.
                    This parameter should have a length of at least 4, much like all UART
                    instructions.
    :returns: True if calculated checksum == checksum in list, False otherwise
    """
    if len(message) < 4:
        return False

    checksum_bytes = message[(len(message) - 2):(len(message))]
    instruction_bytes = message[0:(len(message) - 2)]

    return fl16_get_check_bytes(fletcher16_nums(instruction_bytes)) == checksum_bytes

if __name__ == "__main__":
    main()