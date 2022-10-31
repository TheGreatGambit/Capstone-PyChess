import chess
import sys
import os
from stockfish import Stockfish
from time import sleep
import serial

# INSTRUCTION DEFINES
RESET                   0x0A00           # Reset a terminated game
START_W                 0x0A10           # Start signal if human plays white (goes first)
START_B                 0x0A20           # Start signal if human plays black (goes second)
HUMAN_MOVE              0x0A350000000000 # 5 operand bytes for UCI representation of move (fill in trailing zeroes with move)
ROBOT_MOVE              0x0A450000000000 # 5 operand bytes for UCI representation of move (fill in trailing zeroes with move)
GAME_ONGOING            0x0A5101         # Declare the game has not ended
GAME_CHECKMATE          0x0A5102         # Declare the game has ended to checkmate
GAME_STALEMATE          0x0A5103         # Declare the game has ended to stalemate
ILLEGAL_MOVE            0x0A60           # Declare the human has made an illegal move

IN_PROGRESS = True
TERMINATED = False

global game_state
game_state = IN_PROGRESS

def main():
    stockfish = Stockfish(path="/home/thegreatgambit/Documents/Capstone-PyChess/stockfish/src/stockfish")
    stockfish.update_engine_parameters({'Hash':64})
    stockfish.set_elo_rating(2000)
    if len(sys.argv) > 1:
        if stockfish.is_fen_valid(sys.argv[1]):
            stockfish.set_fen_position(sys.argv[1])
            print(stockfish.get_board_visual())
            confirm = input("Use this board? (Y/N)")
            if confirm.lower() == "y":
                pass
            else:
                return None
        else:
            print("Invalid FEN; exiting...")
            return None

    # INITIALIZE UART #
    global ser
    ser = serial.Serial(
        port="/dev/ttyS0", 
        baudrate = 9600, 
        parity=serial.PARITY_NONE, 
        stopbits=serial.STOPBITS_ONE, 
        bytesize=serial.EIGHTBITS,
    )
    
    # START SIGNAL HANDSHAKE #
    start_signal = ""

    while (start_signal != "S"):
        print("Waiting for start signal...")
        start_signal = ser.read(1).decode('ascii')
        sleep(2)

    print("Received S")
    ser.write(b"S")
    print("Sent back S")
    
    player_color = ""
    while (not (player_color == "W" or player_color == "B")):
        print("Waiting for player color...")
        player_color = ser.read(1).decode('ascii')
        sleep(2)
    print(f"Received color: {player_color}")
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
