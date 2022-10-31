import chess
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
    stockfish = Stockfish(path="/home/thegreatgambit/Documents/Capstone-PyChess/stockfish/src/stockfish")
    stockfish.update_engine_parameters({'Hash':64})
    stockfish.set_elo_rating(2000)

    # INITIALIZE UART #
    global ser
    ser = serial.Serial(
        port="/dev/serial0", 
        baudrate = 9600, 
        parity=serial.PARITY_NONE, 
        stopbits=serial.STOPBITS_ONE, 
        bytesize=serial.EIGHTBITS,
    )

    ser.reset_input_buffer()
    ser.reset_output_buffer()

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
                print("Resetting system")
            elif instr == START_W_INSTR:
                print("Human playing white; human to start")
            elif instr == START_B_INSTR:
                print("Human playing black; robot to start")
            elif instr == HUMAN_MOVE_INSTR:
                print(f"Human makes move: {dec_operand}")
            elif instr == ROBOT_MOVE_INSTR:
                print(f"Robot makes move: {dec_operand}")
            elif instr == GAME_STATUS_INSTR:
                if int_operand == GAME_ONGOING_OP:
                    print("The game continues...")
                elif int_operand == GAME_CHECKMATE_OP:
                    print("Checkmate!")
                elif int_operand == GAME_STALEMATE_OP:
                    print("Stalemate!")
                else:
                    print("Invalid game status operand")
            elif instr == ILLEGAL_MOVE_INSTR:
                print("Illegal move made; please try again")
            else:
                print("Did not get a valid instruction")
            print("--------------------")
        else:
            continue

    return 0

    player_color = input("Select a color (\"W\" or \"B\"): ")
    while player_color not in ["W", "B"]:
        player_color = input("Incorrect input. Select a color (\"W\" or \"B\"): ")
    global chess_board
    chess_board = chess.Board(stockfish.get_fen_position())
    if player_color == "W":
        while True:
            p_move = player_move(stockfish, player_color)
            check_game_state(p_move)
            if game_state == TERMINATED:
                break

            sf_move = stockfish_move(stockfish, player_color)
            check_game_state(sf_move)
            if game_state == TERMINATED:
                break
    else:
        while True:
            sf_move = stockfish_move(stockfish, player_color)
            check_game_state(sf_move)
            if game_state == TERMINATED:
                break

            p_move = player_move(stockfish, player_color)
            check_game_state(p_move)
            if game_state == TERMINATED:
                break

    print("Thanks for playing!")

def player_move(stockfish:Stockfish, player_color):
    print(stockfish.get_board_visual(perspective_white=(True if player_color=="W" else False)))
    valid_move = False
    while not valid_move:
        try:
            player_next_move = input("Select your next move: ")
            stockfish.make_moves_from_current_position([player_next_move])
            chess_board.push(chess.Move.from_uci(player_next_move))
        except ValueError:
            print("That move is invalid. Please try again.\n")
        else:
            valid_move = True
            return chess.Board(stockfish.get_fen_position())



def stockfish_move(stockfish:Stockfish, player_color):
    print(stockfish.get_board_visual(perspective_white=(True if player_color=="W" else False)))
    print("Stockfish making move...\n")
    stockfish_next_move = stockfish.get_best_move_time(3000)

    is_capture = "0"
    is_castling = "0"
    is_promotion = "0"
    is_en_passant = "0"

    stockfish.make_moves_from_current_position([stockfish_next_move])
    if chess_board.is_capture(chess.Move.from_uci(stockfish_next_move)):
        is_capture = "1"

    if chess_board.is_castling(chess.Move.from_uci(stockfish_next_move)):
        is_castling = "1"
    
    if chess_board.is_en_passant(chess.Move.from_uci(stockfish_next_move)):
        is_en_passant = "1"

    if len(stockfish_next_move) > 4:
        is_promotion = stockfish_next_move[4]

    ser.write(bytes(stockfish_next_move, encoding='utf-8'))
    sleep(0.05)
    bytes_to_read = ser.inWaiting()
    print("Read on UART_RX: " + ser.read(bytes_to_read).decode('utf-8'))

    ser.write(bytes(is_capture, encoding='utf-8'))
    sleep(0.01)
    print("is_capture: " + ser.read(1).decode('utf-8'))

    ser.write(bytes(is_castling, encoding='utf-8'))
    sleep(0.01)
    print("is_castling: " + ser.read(1).decode('utf-8'))

    ser.write(bytes(is_promotion, encoding='utf-8'))
    sleep(0.01)
    print("is_promotion: " + ser.read(1).decode('utf-8'))
 
    ser.write(bytes(is_en_passant, encoding='utf-8'))
    sleep(0.01)
    print("is_en_passant: " + ser.read(1).decode('utf-8'))

    chess_board.push(chess.Move.from_uci(stockfish_next_move))
    print(f"Stockfish's move: {stockfish_next_move}")
    #print(stockfish.get_evaluation())
    return chess.Board(stockfish.get_fen_position())

def check_game_state(board:chess.Board):
    if board.is_stalemate():
        print("Stalemate; game over")
        game_state = TERMINATED
    elif board.is_checkmate():
        print("Checkmate; game over")
        game_state = TERMINATED
    elif board.is_check():
        print("Check")
    else:
        pass

if __name__ == "__main__":
    main()
