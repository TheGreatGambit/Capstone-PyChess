import chess
import chess.engine
import sys
import os
from stockfish import Stockfish
from time import sleep
import serial

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
                    # Package the bytes (ord(c) converts characters to ASCII)
                    robot_move_instr_bytes = [0x0A, 0x45] + [ord(c) for c in stockfish_next_move_uci] + [ord(fifth_byte)]
                    robot_move_instr_checksum = 0
                    for byte in robot_move_instr_bytes:
                        robot_move_instr_checksum += byte
                    robot_move_instr_checksum = robot_move_instr_checksum % 512
                    # Send the ROBOT_MOVE_INSTR to the MSP
                    ser.write(robot_move_instr_bytes)
                    # Update the board with the robot's move
                    chess_board.push(chess.Move.from_uci(stockfish_next_move_uci))
                print(f"Human makes move: {player_next_move}")
            else:
                print("Did not get a valid instruction")
            print("--------------------")
        else:
            continue

    return 0

def parse_move_from_(move):
    if len(move) != 5:
        print("DEBUG: Bad move given! Move length should be 5.")
        return move
    if move[4] == "_":
        return move[0:4]

def get_fith_byte(board:chess.Board, move:chess.Move):
    # Castling
    if board.is_castling(move):
        return "L"
    # En passant
    if board.is_en_passant(move):
        return "P"
    # Captures have two possibilities: regular captures and promotion captures
    if board.is_capture(stockfish_next_move):
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

def check_game_state(board:chess.Board):
    game_state_instr_bytes = bytearray([])

    if board.is_stalemate():
        # Return GAME_STALEMATE instr
        print("Stalemate; game over")
        game_state = TERMINATED
        game_state_instr_bytes = bytearray([START_BYTE, GAME_STATUS_INSTR_AND_LEN, GAME_STALEMATE])
        return game_state_instr_bytes
    elif board.is_checkmate():
        # Return GAME_CHECKMATE instr
        print("Checkmate; game over")
        game_state = TERMINATED
        game_state_instr_bytes = bytearray([START_BYTE, GAME_STATUS_INSTR_AND_LEN, GAME_CHECKMATE])
        return game_state_instr_bytes
    else:
        # Return GAME_ONGOING instr
        print("The game continues")
        game_state_instr_bytes = bytearray([START_BYTE, GAME_STATUS_INSTR_AND_LEN, GAME_ONGOING])

    return game_state_instr_bytes

if __name__ == "__main__":
    main()
