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

<!-- Any repo-specific setup, etc. -->
