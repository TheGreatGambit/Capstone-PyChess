import chess
import sys
import os
from stockfish import Stockfish
from time import sleep
import serial

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
    global ser
    ser = serial.Serial('/dev/ttyS0')
    ser.write(b'Initialized /dev/ttyS0')
    sleep(0.05)
    bytes_to_read = ser.inWaiting()
    print(ser.read(bytes_to_read).decode('utf-8'))
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
