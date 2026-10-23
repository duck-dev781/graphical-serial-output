# PyO ESP32 serial diagnostic
# Research basis: MicroPython ESP32 quick reference documents UART0 on
# GPIO1 (TX) and GPIO3 (RX), and identifies UART0 as the default REPL.
# This file deliberately tests operations one at a time and reports the stage.
# Run manually from Thonny; do not rename this to main.py yet.

import os
import time
from machine import UART

print("PYO DIAGNOSTIC: started")

# Test UART construction BEFORE changing the REPL.
try:
    print("STAGE 1: creating UART0")
    uart = UART(0, baudrate=115200, rx=3, tx=1, timeout=20, timeout_char=1)
    print("STAGE 1 PASS: UART0 created")
except Exception as exc:
    print("STAGE 1 FAIL:", repr(exc))
    raise

# Test a small write while preserving the REPL. Output may appear in Thonny
# and/or on the serial connection because UART0 is also the default REPL.
try:
    print("STAGE 2: writing a short test")
    result = uart.write(b"PYO_DIAGNOSTIC\n")
    print("STAGE 2 PASS: write returned", result)
except Exception as exc:
    print("STAGE 2 FAIL:", repr(exc))
    raise

# Test dupterm separately; do not suppress its error.
try:
    print("STAGE 3: detaching REPL from UART0")
    os.dupterm(None)
    print("STAGE 3 PASS: dupterm detached")
except Exception as exc:
    print("STAGE 3 FAIL:", repr(exc))
    raise

print("PYO DIAGNOSTIC COMPLETE")
print("If STAGE 3 passed, the REPL may no longer accept input on UART0.")
while True:
    time.sleep(1)
