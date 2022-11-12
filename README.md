# The Great Gambit &mdash; PyChess

<!-- Buttons that link to the associated repos, uncomment all but this repo -->
<div align="center">
    <img src="https://github.com/TheGreatGambit/Capstone-Electrical/blob/main/Images/logo_large.png" alt="The Great Gambit Logo" style="height:200px;width:880px">
    <a href="https://cadlab.io/project/25988/main/files">
        <img src="https://github.com/TheGreatGambit/Capstone-Electrical/blob/main/Images/logo_cadlab_small.png" alt="CadLab Logo" style="height:40px;width:200px">
    </a>
    <a href="https://github.com/TheGreatGambit/Capstone-Electrical">
        <img src="https://github.com/TheGreatGambit/Capstone-Electrical/blob/main/Images/logo_electrical_small.png" alt="Electrical Logo - Small" style="height:40px;width:200px">
    </a>
    <a href="https://github.com/TheGreatGambit/Capstone-Software">
        <img src="https://github.com/TheGreatGambit/Capstone-Electrical/blob/main/Images/logo_software_small.png" alt="Software Logo - Small" style="height:40px;width:200px">
    </a>
    <a href="https://github.com/TheGreatGambit/Capstone-Mechanical-CAD">
        <img src="https://github.com/TheGreatGambit/Capstone-Electrical/blob/main/Images/logo_mechanical_small.png" alt="Mechanical Logo - Small" style="height:40px;width:200px">
    </a>
    <!-- <a href="https://github.com/TheGreatGambit/Capstone-PyChess">
        <img src="https://github.com/TheGreatGambit/Capstone-Electrical/blob/main/Images/logo_pychess_small.png" alt="PyChess Logo - Small" style="height:40px;width:200px">
    </a> -->
</div>

<!-- Brief overview of this repo -->
## Overview
This project aims to create an autonomous robot capable of playing an intelligent, over-the-board game of chess against a human opponent. The system uses a three-axis, cantilevered, overhead gantry to move parallel to the chess board. Each axis is driven by a stepper motor, the horizontal axes using belts and the vertical axis using a rack and pinion. A crosspoint array of reed switches embedded in the physical chess board allows for piece detection, and with software record of the board state, piece recognition. This system is orchestrated by an [MSP432E401Y](https://www.ti.com/product/MSP432E401Y) microcontroller, with chess moves being pulled from the open-source [Stockfish](https://github.com/official-stockfish/Stockfish) chess engine, running on a [Raspberry Pi 3A+](https://www.raspberrypi.com/products/raspberry-pi-3-model-a-plus/). All communication between the Raspberry Pi and MSP432 is done through a universal asynchronous receiver-transmitter (UART) serial connection.

This repository contains all code running on the Raspberry Pi to interface with the Stockfish chess engine, written in Python.

## UART Protocol
### Protocol Overview
In this project, the MSP432 and Raspberry Pi communicate with each other via UART. A custom instruction protocol has been created to define the various instructions that can be exchanged. In this protocol, every UART message takes the form of an instruction with the following [format](https://i.imgur.com/gRhEl1u.png): 
- 1 start byte (0x0A)
- 1 byte containing the instruction ID and operand length
  - Upper 4 bits reserved for the instruction ID
  - Lower 4 bits reserved for the operand length
- n bytes containing the operand (if applicable), where n equals the operand length defined in the previous byte (n = 0, 5, 6)
- 2 bytes containing the [Fletcher-16](https://en.wikipedia.org/wiki/Fletcher's_checksum#Implementation) check bytes.

The start byte is used to identify the start of a UART message. The instruction ID bits define which instruction is being sent, which tells the MSP432 or Raspberry Pi what to do. The operand length bits define how many bytes long the following operand is. The operand, when present, is used by the instruction to perform its task. Finally, the check bytes (calculated from the [Fletcher-16 checksum](https://en.wikipedia.org/wiki/Fletcher's_checksum#Implementation)) are used to verify data integrity between the sender and receiver. 

### Instruction Set
The entire instruction set is summarized below: 
| Instruction Name 	| Instruction      	| Description                                  	|
|------------------	|------------------	|----------------------------------------------	|
| RESET            	| 0x0A00           	| Resets software                              	|
| START_W          	| 0x0A10           	| Human starts                                 	|
| START_B          	| 0x0A20           	| Robot starts                                 	|
| HUMAN_MOVE       	| 0x0A35XXXXXXXXXX 	| Human makes move represented by "XXXXXXXXXX" 	|
| ROBOT_MOVE       	| 0x0A46XXXXXXXXXXYY 	| Robot makes move represented by "XXXXXXXXXX"; additionally, includes game status data in "YY" after the human's last move and robot's move given in the instruction 	|
| ILLEGAL_MOVE     	| 0x0A50           	| Illegal move made                            	|

### Checksums
To ensure data integrity across transmission, this protocol reserves the last two bytes of any UART message for checksum bytes, the calculation for which can be found [here](https://en.wikipedia.org/wiki/Fletcher's_checksum#Implementation). Before any message is sent (whether from the MSP432 or the Pi), the Fletcher-16 checksum is generated. Then, this checksum is turned into two bytes which can be appended to the end of the transmission. When the receiver receives the message, they will calculate the Fletcher-16 checksum and check bytes for the message, *not including* the final two checksum bytes. If the final two check bytes sent equal the check bytes that were manually calculated by the receiver, then the data integrity has been verified, and the receiver can continue on with the instruction. Otherwise, the data has likely been corrupted, and the sender will have to re-send the previous message. 

<!-- Any repo-specific setup, etc. -->
