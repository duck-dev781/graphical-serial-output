# PyO ESP32 live graphics test: send RGB565 hex through the existing serial REPL.
#
# Research: MicroPython's ESP32 quick reference says the REPL normally uses
# UART0 (GPIO1 TX, GPIO3 RX) at 115200 baud. Since constructing UART(0) fails
# on this user's current firmware, this version does NOT construct a UART,
# change dupterm, or access the UART API. It emits frames with print(), through
# the already-working MicroPython output channel.
#
# Protocol:
# PYOFRAME <width> <height> <frame_number>
# Then HEIGHT lines, each WIDTH*4 RGB565 hex digits.
#
# Host viewer should open the same serial port at 115200 and parse PYOFRAME.
# Stop any other serial monitor before opening the host viewer.

import math
import time

WIDTH = 32
HEIGHT = 24
FRAME_DELAY_MS = 100

VERTICES = (
    (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
    (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
)
EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)
EDGE_COLORS = (
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
    return (int(WIDTH / 2 + x * scale * perspective),
            int(HEIGHT / 2 - y * scale * perspective))


def draw_line(buf, x0, y0, x1, y1, color):
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
    buf = [rgb565(*BACKGROUND)] * (WIDTH * HEIGHT)
    points = [
        project(rotate(v, angle * 0.72, angle, angle * 0.48))
        for v in VERTICES
    ]
    for i, (a, b) in enumerate(EDGES):
        draw_line(buf, points[a][0], points[a][1],
                  points[b][0], points[b][1],
                  rgb565(*EDGE_COLORS[i % len(EDGE_COLORS)]))
    return buf


def send_frame(frame_number, pixels):
    # Use print() so MicroPython's already-configured REPL output carries data.
    print("PYOFRAME %d %d %d" % (WIDTH, HEIGHT, frame_number))
    for y in range(HEIGHT):
        row = pixels[y * WIDTH:(y + 1) * WIDTH]
        print("".join("%04X" % p for p in row))


print("PYO hex stream starting; frames follow.")
frame = 0
angle = 0.0
while True:
    send_frame(frame, draw_cube(angle))
    frame += 1
    angle = (angle + 0.13) % (2 * math.pi)
    time.sleep_ms(FRAME_DELAY_MS)
