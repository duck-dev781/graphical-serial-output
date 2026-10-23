"""PyO MicroPython firmware proof-of-concept for ESP32-WROVER-E.

WARNING: This prototype uses UART0 (GPIO1 TX / GPIO3 RX), which is commonly
also the board's USB-to-serial REPL. It detaches the default REPL so the JSON
protocol can own the port. Re-flash firmware or use a documented recovery
method if you need to restore the REPL. Do not install this until you are
comfortable recovering the board with BOOT/EN and a firmware tool.
"""
import json
import os
import time
from machine import UART

VERSION = 1
BAUD = 115200
MAX_LINE = 4096

# The USB serial connection on many WROVER-E development boards is UART0.
# Detach the MicroPython REPL from the same stream so it cannot corrupt JSON.
try:
    os.dupterm(None)
except Exception:
    pass

uart = UART(0, baudrate=BAUD, rx=3, tx=1, timeout=50, timeout_char=20)

def send(message):
    try:
        payload = json.dumps(message, separators=(",", ":")) + "\n"
        uart.write(payload.encode())
    except Exception:
        pass

def handle(message):
    kind = message.get("type", "")
    if kind == "HELLO":
        send({"type": "READY", "version": VERSION, "device": "ESP32-WROVER-E", "features": ["serial-json", "keyboard-events", "mouse-events"]})
    elif kind == "DESKTOP_STARTED":
        send({"type": "ACK", "message": "PyO desktop started on host"})
    elif kind == "COMMAND":
        command = message.get("command", "")
        if command == "status":
            send({"type": "LOG", "message": "firmware=ready protocol=" + str(VERSION)})
        else:
            send({"type": "LOG", "message": "Unknown firmware command"})
    elif kind == "APP_OPEN":
        send({"type": "ACK", "message": "App request: " + str(message.get("app", "unknown"))})
    elif kind in ("KEY", "MOUSE_MOVE", "MOUSE_CLICK", "SETTING", "EDITOR_BUFFER"):
        # Events are received and acknowledged. Application behavior is added
        # incrementally; editor text is intentionally not executed as code.
        if kind == "EDITOR_BUFFER":
            send({"type": "ACK", "message": "Received editor buffer (not executed or saved)"})
        elif kind == "SETTING":
            send({"type": "ACK", "message": "Setting received"})
    else:
        send({"type": "LOG", "message": "Unknown message type: " + str(kind)[:80]})

send({"type": "BOOT", "version": VERSION, "device": "ESP32-WROVER-E"})
while True:
    try:
        line = uart.readline()
        if not line:
            time.sleep_ms(10)
            continue
        if len(line) > MAX_LINE:
            send({"type": "LOG", "message": "Dropped oversized packet"})
            continue
        try:
            message = json.loads(line.decode().strip())
            if isinstance(message, dict):
                handle(message)
        except Exception:
            # Ignore partial lines and non-protocol data.
            continue
    except Exception as exc:
        send({"type": "LOG", "message": "UART loop error: " + str(exc)[:100]})
        time.sleep_ms(100)
