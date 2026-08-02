@echo off
REM Run Rubik's Cube Solver in virtual mode on Windows (no hardware required)
py -m pip install -r requirements.txt
py main.py --virtual
