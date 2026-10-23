#!/usr/bin/env python3
"""
PyO rotating-cube graphics test.

A standalone Tkinter test for the PyO graphics pipeline. It animates a
3D cube continuously, rotates it around all three axes, rasterizes each
frame to a small RGB565 pixel buffer, and optionally writes that frame
as hexadecimal text for a future live-image decoder.

Run:
    python3 graphics_cube_test.py
    python3 graphics_cube_test.py --hex-out graphics_frame.hex

Keys:
    Q / Escape  Quit
    Space       Pause/resume rotation

No third-party packages are required. The hex file is a single current
frame overwritten on each update, not a recording of the whole animation.
"""

import argparse
import math
import tkinter as tk
from pathlib import Path

WIDTH = 160
HEIGHT = 120
FPS_MS = 33
BACKGROUND = (5, 8, 16)

VERTICES = [
    (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
    (-1, -1, 1),  (1, -1, 1),  (1, 1, 1),  (-1, 1, 1),
]

# Each face: vertex indices and an RGB face color.
FACES = [
    ((0, 1, 2, 3), (35, 100, 255)),    # back
    ((4, 5, 6, 7), (0, 220, 245)),      # front
    ((0, 1, 5, 4), (245, 35, 210)),     # bottom
    ((2, 3, 7, 6), (255, 190, 20)),     # top
    ((1, 2, 6, 5), (255, 120, 20)),    # right
    ((0, 3, 7, 4), (120, 50, 255)),    # left
]


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def rotate_vertex(point, ax, ay, az):
    x, y, z = point

    # Rotate around X.
    y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
    # Rotate around Y.
    x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
    # Rotate around Z.
    x, y = x * math.cos(az) - y * math.sin(az), x * math.sin(az) + y * math.cos(az)
    return x, y, z


def project(point):
    x, y, z = point
    camera_distance = 4.2
    perspective = camera_distance / (camera_distance - z)
    scale = min(WIDTH, HEIGHT) * 0.31
    return WIDTH / 2 + x * scale * perspective, HEIGHT / 2 - y * scale * perspective, z


def rasterize(projected):
    """Rasterize visible cube faces into a WIDTH x HEIGHT RGB565 buffer."""
    pixels = [rgb565(*BACKGROUND) for _ in range(WIDTH * HEIGHT)]
    zbuffer = [-float("inf")] * (WIDTH * HEIGHT)

    # Painter/z-buffer approach using triangles for each face.
    for indices, color in FACES:
        points = [projected[i] for i in indices]
        # Split quad into two triangles.
        for tri in ((points[0], points[1], points[2]), (points[0], points[2], points[3])):
            (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = tri
            area = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
            if abs(area) < 0.0001:
                continue
            min_x = max(0, int(min(x0, x1, x2)))
            max_x = min(WIDTH - 1, int(max(x0, x1, x2)) + 1)
            min_y = max(0, int(min(y0, y1, y2)))
            max_y = min(HEIGHT - 1, int(max(y0, y1, y2)) + 1)
            for py in range(min_y, max_y + 1):
                for px in range(min_x, max_x + 1):
                    # Sample pixel center and compute barycentric coordinates.
                    sx, sy = px + 0.5, py + 0.5
                    w0 = ((x1 - sx) * (y2 - sy) - (y1 - sy) * (x2 - sx)) / area
                    w1 = ((x2 - sx) * (y0 - sy) - (y2 - sy) * (x0 - sx)) / area
                    w2 = 1.0 - w0 - w1
                    if w0 >= -0.001 and w1 >= -0.001 and w2 >= -0.001:
                        depth = w0 * z0 + w1 * z1 + w2 * z2
                        pos = py * WIDTH + px
                        if depth > zbuffer[pos]:
                            zbuffer[pos] = depth
                            pixels[pos] = rgb565(*color)
    return pixels


def write_hex_frame(path, pixels):
    lines = [
        "# PyO Graphics Hex Frame v1",
        f"WIDTH={WIDTH}",
        f"HEIGHT={HEIGHT}",
        "FORMAT=RGB565",
        "DATA",
    ]
    for y in range(HEIGHT):
        row = pixels[y * WIDTH:(y + 1) * WIDTH]
        lines.append(" ".join(f"{value:04X}" for value in row))
    Path(path).write_text("\n".join(lines) + "\n", encoding="ascii")


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def main():
    parser = argparse.ArgumentParser(description="Animate a rotating PyO graphics test cube.")
    parser.add_argument("--hex-out", default=None, help="optional path to overwrite with each RGB565 frame")
    args = parser.parse_args()

    root = tk.Tk()
    root.title("PyO Graphics Test — Rotating Cube")
    root.configure(bg="#050810")
    root.resizable(False, False)

    scale = 4
    canvas = tk.Canvas(root, width=WIDTH * scale, height=HEIGHT * scale,
                       bg="#050810", highlightthickness=0)
    canvas.pack()
    info = tk.Label(root, text="RGB565 HEX  |  Rotation: 0°  |  SPACE: pause  |  Q: quit",
                    fg="#dce8ff", bg="#050810", font=("monospace", 10))
    info.pack(fill="x", padx=8, pady=6)

    angle = 0.0
    paused = False
    frame_count = 0
    cube_items = []

    def keypress(event):
        nonlocal paused
        if event.keysym.lower() in ("q", "escape"):
            root.destroy()
        elif event.keysym == "space":
            paused = not paused

    root.bind("<Key>", keypress)
    canvas.focus_set()

    def draw():
        nonlocal angle, frame_count
        if not paused:
            angle = (angle + 2.0) % 360.0
        ax = math.radians(angle * 0.72)
        ay = math.radians(angle)
        az = math.radians(angle * 0.48)
        projected = [project(rotate_vertex(v, ax, ay, az)) for v in VERTICES]
        pixels = rasterize(projected)

        canvas.delete("all")
        # Draw the rasterized frame as enlarged pixels, making the preview
        # faithfully represent the RGB565 data written to the hex file.
        for y in range(HEIGHT):
            for x in range(WIDTH):
                value = pixels[y * WIDTH + x]
                r = ((value >> 11) & 0x1F) * 255 // 31
                g = ((value >> 5) & 0x3F) * 255 // 63
                b = (value & 0x1F) * 255 // 31
                canvas.create_rectangle(
                    x * scale, y * scale, (x + 1) * scale, (y + 1) * scale,
                    fill=rgb_to_hex((r, g, b)), outline=""
                )

        frame_count += 1
        if args.hex_out:
            try:
                write_hex_frame(args.hex_out, pixels)
            except OSError as exc:
                info.config(text=f"HEX WRITE ERROR: {exc}  |  Q: quit")
            else:
                info.config(text=f"RGB565 HEX  |  Rotation: {angle:05.1f}°  |  Frame: {frame_count}  |  Q: quit")
        else:
            info.config(text=f"RGB565 preview  |  Rotation: {angle:05.1f}°  |  Frame: {frame_count}  |  SPACE: pause  |  Q: quit")
        root.after(FPS_MS, draw)

    draw()
    root.mainloop()


if __name__ == "__main__":
    main()
