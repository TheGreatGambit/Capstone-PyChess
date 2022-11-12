#!/usr/bin/env python
"""
The primary script on the Raspberry Pi for The Great Gambit's autonomous chess robot. 
Uses the python-chess library and Stockfish to validate moves sent from the MSP, determine 
board state, and generate new moves to send to the MSP for the robot to make. Additionally, 
uses python-serial to enable straightforward UART communication with the MSP.
"""

import chess
import chess.engine
import serial

__author__ = "Keenan Alchaar"
__copyright__ = "Copyright 2022"
__version__ = "v6"
__email__ = "ka5nt@virginia.edu"
__status__ = "Development"

# PACKET STRUCTURE DEFINES
START_BYTE           =   0x0A             # Start byte at beginning of every instruction

# INSTRUCTION DEFINES
RESET_INSTR          =   0x00
START_W_INSTR        =   0x01
START_B_INSTR        =   0x02
HUMAN_MOVE_INSTR     =   0x03
ROBOT_MOVE_INSTR     =   0x04
ILLEGAL_MOVE_INSTR   =   0x05

# GAME STATUS CODES
GAME_ONGOING      =   0x01
GAME_CHECKMATE    =   0x02
GAME_STALEMATE    =   0x03

# INSTRUCTION AND OPERAND LENGTH BYTES
RESET_INSTR_AND_LEN         =     0x00
START_W_INSTR_AND_LEN       =     0x10
START_B_INSTR_AND_LEN       =     0x20
HUMAN_MOVE_INSTR_AND_LEN    =     0x35
ROBOT_MOVE_INSTR_AND_LEN    =     0x46
ILLEGAL_MOVE_INSTR_AND_LEN  =     0x50

# FULL INSTRUCTIONS
RESET            =       0x0A00           # Reset a terminated game
START_W          =       0x0A10           # Start signal if human plays white (goes first)
START_B          =       0x0A20           # Start signal if human plays black (goes second)
HUMAN_MOVE       =       0x0A350000000000 # 5 operand bytes for UCI representation of move (fill in trailing zeroes with move)
ROBOT_MOVE       =       0x0A460000000000 # 5 operand bytes for UCI representation of move (fill in trailing zeroes with move)
ILLEGAL_MOVE     =       0x0A50           # Declare the human has made an illegal move

IN_PROGRESS = True
TERMINATED = False

global game_state
game_state = IN_PROGRESS

def bytes_to_int(byte_stream):
    return int(byte_stream.hex(), 16)

def main():
    # Initialize the chess engine, give it a hash size of 64 MB, and create a new board
    engine = chess.engine.SimpleEngine.popen_uci("/home/thegreatgambit/Documents/Capstone-PyChess/stockfish/src/stockfish")
    engine.configure({"Hash": 64})
    board = chess.Board()

    # Initialize UART with a baud rate of 9600, no parity bit, one stop bit, eight data bits, and a 3s timeout
    global ser
    ser = serial.Serial(
        port="/dev/serial0", 
        baudrate = 9600, 
        parity=serial.PARITY_NONE, 
        stopbits=serial.STOPBITS_ONE, 
        bytesize=serial.EIGHTBITS,
#        timeout = 60,
    )

    if not ser.is_open:
        ser.open()
    print("Opened /dev/serial0")
    
    # Flush both UART buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # Starting board print
    print(board)

    # The main program loop
    while True:
        byte = ser.read(1)

        if len(byte) == 0:
            print("No start byte received")
            ser.reset_input_buffer()
            continue
        else:
            byte = bytes_to_int(byte)

        raw_operand = b""
        int_operand = -1
        dec_operand = ""
        received_msg = []

        if byte == START_BYTE:
            instr_and_op_len = ser.read(1)

            if len(instr_and_op_len) == 0:
                print("Didn't receive an instruction + operand length byte")
                ser.reset_input_buffer()
                continue

            instr_and_op_len = bytes_to_int(instr_and_op_len)
            instr = instr_and_op_len >> 4
            op_len = instr_and_op_len & (~0xF0)
            # DEBUGGING
            #print(f"Raw instr and op len: {hex(instr_and_op_len)}")
            #print(f"Raw instruction: {hex(instr)}")
            #print(f"Raw operand len: {hex(op_len)}")
            received_msg = [byte, instr_and_op_len]
            if (op_len > 0):
                raw_operand = ser.read(op_len)

                if len(raw_operand) < op_len:
                    print("Received shorter operand than expected")
                    ser.reset_input_buffer()
                    continue

                int_operand = bytes_to_int(raw_operand)
                dec_operand = raw_operand.decode('ascii')
                print(f"Raw operand: {int_operand}")
                print(f"Dec operand: {dec_operand}")

            check_bytes = ser.read(2)

            if len(check_bytes) < 2:
                print("Didn't receive two check bytes")
                ser.reset_input_buffer()
                continue

            c0 = bytes_to_int(check_bytes[0:1])
            c1 = bytes_to_int(check_bytes[1:2])

            # The only operand lengths present in this instruction set are 0, 1, and 5
            if (op_len not in [0, 1, 5]):
                print("Invalid operand length received")
                ser.reset_input_buffer()
                continue
            if (instr > 6):
                print("Invalid instruction ID received")
                ser.reset_input_buffer()
                continue
            
            # Only append operand bytes to received_msg if there are any
            if (op_len > 0):
                received_msg = [byte, instr_and_op_len] + [ord(c) for c in dec_operand] + [c0, c1]
            else:
                received_msg = [byte, instr_and_op_len] + [c0, c1]

            # Validate the check bytes and skip action if invalid
            if not validate_transmission(received_msg):
                print("Invalid transmission received")
                ser.reset_input_buffer()
                continue
            else:
                print("Valid transmission received!")

            # Take action based on the instruction ID
            if instr == RESET_INSTR:
                # Reset the board
                board = chess.Board()
                print("Resetting system")
            elif instr == START_W_INSTR:
                # Create a new board; human starts (wait for them to send a move)
                board = chess.Board()
                print("Human playing white; human to start")
                player_color = "W"
            elif instr == START_B_INSTR:
                # Create a new board; robot starts
                board = chess.Board()
                print("Human playing black; robot to start")
                player_color = "B"

                # Get Stockfish's move in 1 second
                stockfish_next_move = engine.play(board, chess.engine.Limit(time=1)).move
                # Convert the Move object to a UCI string
                stockfish_next_move_uci = stockfish_next_move.uci()
                # If it's a promotion, it will be overriden to a queen automatically
                if len(stockfish_next_move_uci) == 5:
                    stockfish_next_move_uci[4] = 'Q'

                # Get the fifth operand byte to be sent
                fifth_byte = get_fifth_byte(board, stockfish_next_move)
                # Update the board with the robot's move
                board.push(chess.Move.from_uci(stockfish_next_move_uci))
                # Print the new board
                print(board)
                # Check the game state after the robot has decided its move
                status_after_robot = check_game_state(board)
                # Form the game status byte with robot's move (player didn't move before, so its 4 bits are forced to GAME_ONGOING)
                game_status_byte = (GAME_ONGOING << 4) + status_after_robot
                # Package the bytes (ord(c) converts characters to ASCII encodings)
                robot_move_instr_bytes = [START_BYTE, ROBOT_MOVE_INSTR_AND_LEN] + [ord(c) for c in stockfish_next_move_uci] + [ord(fifth_byte), game_status_byte]
                # Append the checksum to the bytes preceding it
                robot_move_instr_bytes += fl16_get_check_bytes(fletcher16_nums(robot_move_instr_bytes))
                # Send the ROBOT_MOVE_INSTR to the MSP
                ser.write(bytearray(robot_move_instr_bytes))
                print(f"Sent move {stockfish_next_move_uci}")

            elif instr == HUMAN_MOVE_INSTR:
                # Remove the '_' from the move, or leave any promotions
                try:
                    print(f"Human makes move: {parse_move(dec_operand)}")
                    player_next_move = chess.Move.from_uci(parse_move(dec_operand))
                except (ValueError, TypeError) as e:
                    illegal_move_instr_bytes = [START_BYTE, ILLEGAL_MOVE_INSTR_AND_LEN]
                    illegal_move_instr_bytes += fl16_get_check_bytes(fletcher16_nums(illegal_move_instr_bytes))
                    ser.write(bytearray(illegal_move_instr_bytes))
                    print("Illegal move made")
                    continue

                # If the move the player made was not legal, do not push it; alert the MSP
                if player_next_move not in board.legal_moves:
                    illegal_move_instr_bytes = [START_BYTE, ILLEGAL_MOVE_INSTR_AND_LEN]
                    illegal_move_instr_bytes += fl16_get_check_bytes(fletcher16_nums(illegal_move_instr_bytes))
                    ser.write(bytearray(illegal_move_instr_bytes)) # ILLEGAL_MOVE
                    print("Illegal move made")
                    continue
                else:
                    # Update the board with the player's move
                    board.push(player_next_move)
                    # Print the new board
                    print(board)
                    # Check the game state after the player's move has been recognized
                    status_after_player = check_game_state(board)

                    # If the player's last move ended the game
                    if status_after_player != GAME_ONGOING:
                        # The game status byte will include the status the player caused, and a "filler" GAME_ONGOING for the robot
                        game_status_byte = (status_after_player << 4) + GAME_ONGOING
                        # Package the bytes, fill the move bytes with filler values (they don't matter since the game is over)
                        robot_move_instr_bytes = [START_BYTE, ROBOT_MOVE_INSTR_AND_LEN] + ['_', '_', '_', '_', '_', game_status_byte]
                        # Append the check bytes to the bytes preceding them
                        robot_move_instr_bytes += fl16_get_check_bytes(fletcher16_nums(robot_move_instr_bytes))
                        # Send ROBOT_MOVE_INSTR to the MSP; the player has ended the game at this point
                        ser.write(bytearray(robot_move_instr_bytes))
                        print(f"Game over!")
                    else:
                        # Get Stockfish's move in 1 second
                        stockfish_next_move = engine.play(board, chess.engine.Limit(time=1)).move
                        # Convert the Move object to a UCI string
                        stockfish_next_move_uci = stockfish_next_move.uci()
                        # If it's a promotion, it will be overriden to a queen automatically
                        if len(stockfish_next_move_uci) == 5:
                            stockfish_next_move_uci[4] = 'Q'
                        
                        # Get the fifth operand byte to be sent
                        fifth_byte = get_fifth_byte(board, stockfish_next_move)
                        # Update the board with the robot's move
                        board.push(chess.Move.from_uci(stockfish_next_move_uci))
                        # Print the new board
                        print(board)
                        # Check the game state after the robot has decided its move
                        status_after_robot = check_game_state(board)
                        # Form the game status byte with the statuses after human and robot moves
                        game_status_byte = (status_after_player << 4) + status_after_robot
                        # Package the bytes (ord(c) converts characters to ASCII encodings)
                        robot_move_instr_bytes = [START_BYTE, ROBOT_MOVE_INSTR_AND_LEN] + [ord(c) for c in stockfish_next_move_uci] + [ord(fifth_byte), game_status_byte]
                        # Append the check bytes to the bytes preceding them
                        robot_move_instr_bytes += fl16_get_check_bytes(fletcher16_nums(robot_move_instr_bytes))
                        # Send the ROBOT_MOVE_INSTR to the MSP
                        ser.write(bytearray(robot_move_instr_bytes))
                        print(f"Sent move {stockfish_next_move_uci}")
                        # If the robot's last move ended the game
                        if status_after_robot != GAME_ONGOING:
                            print("Game over!")

            else:
                print("Did not get a valid instruction")
            print("--------------------")
        else:
            continue

    return 0

def parse_move(move: str) -> str:
    """
    Takes a move from the MSP in UCI notation, removes the trailing '_' if it has it, 
    then returns it. 

    :param move: A move in UCI notation which is 5 characters long (as all messages from the MSP are
                 expected to be this long)

    :returns: The move, shortened to 4 characters or kept at 5 (must be a promotion in this case)
    """
    if len(move) != 5:
        print("DEBUG: Bad move given! Move length should be 5.")
        return move
    if move[4] == "_":
        return move[0:4]


def get_fifth_byte(board: chess.Board, move: chess.Move) -> str:
    """
    Given a move object and a board state object, returns the appropriate fifth byte to 
    describe the nature of the move to the MSP. 

    :param board: A chess.Board object representing the current board state
    :param move: A chess.Move object representing the move to be made

    :returns: A one-character string which will be appended to the other 4 characters of the UCI 
              string to be sent to the MSP. 
    """
    # Castling
    if board.is_castling(move):
        return "c"
    # En passant
    if board.is_en_passant(move):
        return "E"
    # Captures have two possibilities: regular captures and promotion captures
    if board.is_capture(move):
       # Promotion captures
       if len(move.uci()) == 5:
           return "q"
       # Regular captures
       else:
           return "C"
    # Non-capture promotions
    if len(move.uci()) == 5:
        return "Q"

    # Not a special move
    return "_"


def check_game_state(board: chess.Board) -> list:
    """
    Given a board, checks the game state to determine if the game has ended. 

    :param board: A chess.Board object representing the board state of interest

    :returns: A code corresponding to the game status 
    """ 

    if board.is_stalemate():
        print("Stalemate; game over")
        game_state = TERMINATED
        return GAME_STALEMATE
    elif board.is_checkmate():
        print("Checkmate; game over")
        game_state = TERMINATED
        return GAME_CHECKMATE
    else:
        print("The game continues")
        return GAME_ONGOING


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
