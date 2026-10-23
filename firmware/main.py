# PyO working character-stream graphics firmware.
# Upload this file to the ESP32 device as /main.py to run automatically at boot.
# MicroPython executes boot.py (if present), then main.py from the device root.

# PyO ESP32 compact live graphics stream.
# Uses print() on MicroPython's existing REPL output; no machine.UART setup.
# Each pixel is one palette character instead of four RGB565 hex digits.
# Host viewer protocol:
#   PYOCHAR <width> <height> <frame_number>
#   then HEIGHT rows of WIDTH palette characters.
#
# Palette is fixed in the host viewer. This avoids UART(0) construction,
# which fails on the user's current MicroPython build.

import math
import time

WIDTH = 32
HEIGHT = 24
FRAME_DELAY_MS = 100

# Palette index is the character position in the host viewer's PALETTE string.
# Palette: black, dark blue, cyan, magenta, yellow, blue, orange, purple,
# white, red, green, teal, pink, gray, light blue, dark red.
PALETTE = "0123456789ABCDEF"
COLORS = (
    (3, 5, 12), (8, 20, 55), (0, 220, 245), (245, 35, 210),
    (255, 190, 20), (60, 100, 255), (255, 120, 20), (120, 50, 255),
    (255, 255, 255), (255, 35, 35), (40, 220, 80), (0, 150, 150),
    (255, 120, 180), (120, 120, 120), (130, 200, 255), (100, 0, 20),
)

VERTICES = (
    (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
    (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
)
EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
    (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7),
)
EDGE_COLORS = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14)


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
    dx, sx = abs(x1 - x0), 1 if x0 < x1 else -1
    dy, sy = -abs(y1 - y0), 1 if y0 < y1 else -1
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
    buf = [0] * (WIDTH * HEIGHT)
    points = [project(rotate(v, angle * 0.72, angle, angle * 0.48))
              for v in VERTICES]
    for i, (a, b) in enumerate(EDGES):
        draw_line(buf, points[a][0], points[a][1],
                  points[b][0], points[b][1], EDGE_COLORS[i])
    return buf


def send_frame(frame_id, pixels):
    print("PYOCHAR %d %d %d" % (WIDTH, HEIGHT, frame_id))
    for y in range(HEIGHT):
        row = pixels[y * WIDTH:(y + 1) * WIDTH]
        print("".join(PALETTE[p] for p in row))


print("PyO character stream ready.")
frame_id = 0
angle = 0.0
while True:
    send_frame(frame_id, draw_cube(angle))
    frame_id += 1
    angle = (angle + 0.13) % (2 * math.pi)
    time.sleep_ms(FRAME_DELAY_MS)
