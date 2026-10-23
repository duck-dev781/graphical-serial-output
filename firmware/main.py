# PyO ESP32 rotating-cube graphics test
# Runs on the ESP32-WROVER-E under MicroPython.
#
# Sends frames as ASCII RGB565 hex over UART0 at 115200 baud.
# Host side: python3 graphics_serial_viewer.py --port /dev/ttyUSB0
#
# Frame protocol:
#   PYOFRAME <width> <height> <frame_number>\n
#   <one line of WIDTH*HEIGHT RGB565 pixels, each 4 hex digits>\n
#
# WARNING: UART0 is commonly the board's USB serial/REPL connection.
# This program uses UART0 for frames and detaches the MicroPython REPL.
# Make sure you know how to recover/reflash the board before running it.

import math
import os
import time
from machine import UART

try:
    os.dupterm(None)
except Exception:
    pass

WIDTH = 32
HEIGHT = 24
BAUD = 115200
FRAME_DELAY_MS = 80

uart = UART(0, baudrate=BAUD, rx=3, tx=1, timeout=20, timeout_char=1)

# 3D cube vertices.
VERTICES = (
    (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
    (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
)
EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)
FACE_COLORS = (
    (0, 220, 245), (245, 35, 210), (255, 190, 20),
    (60, 100, 255), (255, 120, 20), (120, 50, 255),
)
BACKGROUND = (3, 5, 12)


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def rotate(p, ax, ay, az):
    x, y, z = p
    c, s = math.cos(ax), math.sin(ax)
    y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(ay), math.sin(ay)
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(az), math.sin(az)
    x, y = x * c - y * s, x * s + y * c
    return x, y, z


def project(p):
    x, y, z = p
    perspective = 3.6 / (3.6 - z)
    scale = min(WIDTH, HEIGHT) * 0.34
    return int(WIDTH / 2 + x * scale * perspective), int(HEIGHT / 2 - y * scale * perspective)


def draw_line(buf, x0, y0, x1, y1, color):
    # Integer Bresenham line rasterizer.
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        if 0 <= x0 < WIDTH and 0 <= y0 < HEIGHT:
            buf[y0 * WIDTH + x0] = color
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_cube(angle):
    bg = rgb565(*BACKGROUND)
    buf = [bg] * (WIDTH * HEIGHT)
    ax = angle * 0.72
    ay = angle
    az = angle * 0.48
    points = [project(rotate(v, ax, ay, az)) for v in VERTICES]

    # Colored edges; cycle colors for a clear orientation test.
    for i, edge in enumerate(EDGES):
        a, b = edge
        color = rgb565(*FACE_COLORS[i % len(FACE_COLORS)])
        draw_line(buf, points[a][0], points[a][1], points[b][0], points[b][1], color)
    return buf


def send_frame(frame_number, pixels):
    uart.write("PYOFRAME %d %d %d\n" % (WIDTH, HEIGHT, frame_number))
    # ASCII RGB565, row-major, top-left first. Chunk rows to avoid huge writes.
    for y in range(HEIGHT):
        row = pixels[y * WIDTH:(y + 1) * WIDTH]
        uart.write("".join("%04X" % p for p in row) + "\n")


frame = 0
angle = 0.0
while True:
    try:
        pixels = draw_cube(angle)
        send_frame(frame, pixels)
        frame += 1
        angle = (angle + 0.13) % (2 * math.pi)
        time.sleep_ms(FRAME_DELAY_MS)
    except Exception:
        # Avoid flooding the serial link if a transient write fails.
        time.sleep_ms(250)
