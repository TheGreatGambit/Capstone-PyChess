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
__version__ = "v3"
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
GAME_STATUS_INSTR    =   0x05
ILLEGAL_MOVE_INSTR   =   0x06

# GAME STATUS OPERANDS
GAME_ONGOING_OP      =   0x01
GAME_CHECKMATE_OP    =   0x02
GAME_STALEMATE_OP    =   0x03

# INSTRUCTION AND OPERAND LENGTH BYTES
RESET_INSTR_AND_LEN         =     0x00
START_W_INSTR_AND_LEN       =     0x10
START_B_INSTR_AND_LEN       =     0x20
HUMAN_MOVE_INSTR_AND_LEN    =     0x35
ROBOT_MOVE_INSTR_AND_LEN    =     0x45
GAME_STATUS_INSTR_AND_LEN   =     0x51
ILLEGAL_MOVE_INSTR_AND_LEN  =     0x60

# FULL INSTRUCTIONS
RESET            =       0x0A00           # Reset a terminated game
START_W          =       0x0A10           # Start signal if human plays white (goes first)
START_B          =       0x0A20           # Start signal if human plays black (goes second)
HUMAN_MOVE       =       0x0A350000000000 # 5 operand bytes for UCI representation of move (fill in trailing zeroes with move)
ROBOT_MOVE       =       0x0A450000000000 # 5 operand bytes for UCI representation of move (fill in trailing zeroes with move)
GAME_ONGOING     =       0x0A5101         # Declare the game has not ended
GAME_CHECKMATE   =       0x0A5102         # Declare the game has ended to checkmate
GAME_STALEMATE   =       0x0A5103         # Declare the game has ended to stalemate
ILLEGAL_MOVE     =       0x0A60           # Declare the human has made an illegal move

IN_PROGRESS = True
TERMINATED = False

global game_state
game_state = IN_PROGRESS

def bytes_to_int(byte_stream):
    return int(byte_stream.hex(), 16)

def main():
    engine = chess.engine.SimpleEngine.popen_uci("/home/thegreatgambit/Documents/Capstone-PyChess/stockfish/src/stockfish")
    engine.configure({"Hash": 64})
    board = chess.Board()

    # Initialize UART
    global ser
    ser = serial.Serial(
        port="/dev/serial0", 
        baudrate = 9600, 
        parity=serial.PARITY_NONE, 
        stopbits=serial.STOPBITS_ONE, 
        bytesize=serial.EIGHTBITS,
    )
    
    # Flush both UART buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # The main program loop
    while True:
        byte = bytes_to_int(ser.read(1))
        raw_operand = b""
        int_operand = -1
        dec_operand = ""
        if byte == START_BYTE:
            instr_and_op_len = bytes_to_int(ser.read(1))
            instr = instr_and_op_len >> 4
            op_len = instr_and_op_len & (~0xF0)
            print(f"Raw instr and op len: {hex(instr_and_op_len)}")
            print(f"Raw instruction: {hex(instr)}")
            print(f"Raw operand len: {hex(op_len)}")
            if (op_len > 0):
                raw_operand = ser.read(op_len)
                int_operand = bytes_to_int(raw_operand)
                dec_operand = raw_operand.decode('ascii')
                print(f"Raw operand: {int_operand}")
                print(f"Dec operand: {dec_operand}")
            checksum = bytes_to_int(ser.read(1))
            if instr == RESET_INSTR:
                # TODO: actually do some resetting
                print("Resetting system")
            elif instr == START_W_INSTR:
                # TODO: Any other setup needed? 
                print("Human playing white; human to start")
                player_color = "W"
            elif instr == START_B_INSTR:
                print("Human playing black; robot to start")
                player_color = "B"
            elif instr == HUMAN_MOVE_INSTR:
                # Remove the '_' from the move, or leave any promotions
                player_next_move = chess.Move.from_uci(parse_move(dec_operand))

                # If the move the player made was not legal, do not push it; alert the MSP
                if player_next_move not in board.legal_moves:
                    illegal_move_instr_bytes = bytearray([START_BYTE, ILLEGAL_MOVE_INSTR_AND_LEN])
                    ser.write(illegal_move_instr_bytes) # ILLEGAL_MOVE
                else:
                    # Update the board with the player's move
                    board.push(player_next_move)
                    # Check the game state and send information to the MSP
                    ser.write(check_game_state(board))

                    # Get Stockfish's move in 1 second
                    stockfish_next_move = engine.play(board, chess.engine.Limit(time=1)).move
                    # Convert the Move object to a UCI string
                    stockfish_next_move_uci = stockfish_next_move.uci()
                    # If it's a promotion, it will be overriden to a queen automatically
                    if len(stockfish_next_move_uci) == 5:
                        stockfish_next_move_uci = stockfish_next_move_uci[0:4]
                    
                    # Get the fifth operand byte to be sent
                    fifth_byte = get_fifth_byte(board, stockfish_next_move)
                    # Package the bytes (ord(c) converts characters to ASCII encodings)
                    robot_move_instr_bytes = [START_BYTE, ROBOT_MOVE_INSTR_AND_LEN] + [ord(c) for c in stockfish_next_move_uci] + [ord(fifth_byte)]
                    # Append the checksum to the bytes preceding it
                    robot_move_instr_bytes += fl16_get_check_bytes(fletcher16_nums(robot_move_instr_bytes))
                    # Send the ROBOT_MOVE_INSTR to the MSP
                    ser.write(bytearray(robot_move_instr_bytes))
                    # Update the board with the robot's move
                    chess_board.push(chess.Move.from_uci(stockfish_next_move_uci))
                print(f"Human makes move: {player_next_move}")
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


def get_fith_byte(board: chess.Board, move: chess.Move) -> str:
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
       if len(move) == 5:
           return "q"
       # Regular captures
       else:
           return "C"
    # Non-capture promotions
    if len(move) == 5:
        return "Q"

    # Not a special move
    return "_"


def check_game_state(board: chess.Board) -> list:
"""
Given a board, checks the game state to determine if the game has ended. 

:param board: A chess.Board object representing the board state of interest

:returns: A list of the bytes to be sent to the MSP 
""" 
    game_state_instr_bytes = []

    if board.is_stalemate():
        # Return GAME_STALEMATE instr
        print("Stalemate; game over")
        game_state = TERMINATED
        game_state_instr_bytes = [START_BYTE, GAME_STATUS_INSTR_AND_LEN, GAME_STALEMATE_OP]
    elif board.is_checkmate():
        # Return GAME_CHECKMATE instr
        print("Checkmate; game over")
        game_state = TERMINATED
        game_state_instr_bytes = [START_BYTE, GAME_STATUS_INSTR_AND_LEN, GAME_CHECKMATE_OP]
    else:
        # Return GAME_ONGOING instr
        print("The game continues")
        game_state_instr_bytes = [START_BYTE, GAME_STATUS_INSTR_AND_LEN, GAME_ONGOING_OP]

    checksum_bytes = fl16_get_check_bytes(fletcher16_nums(game_state_instr_bytes))
    game_state_instr_bytes += checksum_bytes
    return game_state_instr_bytes


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

:param message: A list of bytes representing the entire instruction and its checksum
                This parameter should have a length of at least 4, much like all UART
                instructions.

:returns: True if calculated checksum == checksum in list, False otherwise
"""
    if len(list) < 4:
        return False

    checksum_bytes = message[(len(message) - 2):(len(message)]
    instruction_bytes = message[0:(len(message) - 2)]

    return fl16_get_check_bytes(fletcher16_nums(instruction_bytes)) == checksum_bytes

if __name__ == "__main__":
    main()
