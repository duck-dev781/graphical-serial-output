# PyO graphics diagnostics — save this file to the ESP32 root as /boot.py.
# This intentionally runs the graphics test from boot.py, as requested.
# Serial protocol: PYOCHAR <width> <height> <frame>, followed by palette rows.

import math
import time
import random

WIDTH = 40
HEIGHT = 30
FRAME_DELAY_MS = 120
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
frame_id = 0

def send_frame(pixels):
    global frame_id
    print("PYOCHAR %d %d %d" % (WIDTH, HEIGHT, frame_id))
    for y in range(HEIGHT):
        print("".join(PALETTE[p] for p in pixels[y * WIDTH:(y + 1) * WIDTH]))
    frame_id += 1

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
    scale = min(WIDTH, HEIGHT) * 0.36
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

def cube(angle):
    buf = [0] * (WIDTH * HEIGHT)
    points = [project(rotate(v, angle * 0.72, angle, angle * 0.48)) for v in VERTICES]
    for i, (a, b) in enumerate(EDGES):
        draw_line(buf, points[a][0], points[a][1], points[b][0], points[b][1], EDGE_COLORS[i])
    return buf

def solid(color):
    return [color] * (WIDTH * HEIGHT)

def diagnostics():
    # 1. Rotating cube at higher resolution (smaller apparent pixels).
    angle = 0.0
    for _ in range(90):
        send_frame(cube(angle))
        angle = (angle + 0.13) % (2 * math.pi)
        time.sleep_ms(FRAME_DELAY_MS)

    # 2. Full-screen color flashes: red, green, blue, pink, cyan, yellow, white, black.
    for color in (9, 10, 5, 3, 2, 4, 8, 0):
        send_frame(solid(color))
        time.sleep_ms(350)

    # 3. Multi-color block/grid pattern.
    for phase in range(12):
        pixels = []
        for y in range(HEIGHT):
            for x in range(WIDTH):
                pixels.append(((x // 5) + (y // 5) + phase) % 16)
        send_frame(pixels)
        time.sleep_ms(250)

    # 4. Color bars and checkerboard.
    bars = [0] * (WIDTH * HEIGHT)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bars[y * WIDTH + x] = min(15, (x * 16) // WIDTH)
    send_frame(bars)
    time.sleep_ms(900)
    checker = [(((x // 2) + (y // 2)) % 2) * 8 + 3 for y in range(HEIGHT) for x in range(WIDTH)]
    send_frame(checker)
    time.sleep_ms(900)

    # 5. Finish with animated multicolor static, then keep static running.
    while True:
        send_frame([random.randrange(16) for _ in range(WIDTH * HEIGHT)])
        time.sleep_ms(180)

print("PyO graphics diagnostics starting")
diagnostics()
