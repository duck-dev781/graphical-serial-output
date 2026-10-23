#!/usr/bin/env python3
"""PyO serial graphics viewer: decode RGB565 hex or compact character frames from the ESP32.

Install dependencies on antiX/Debian:
    sudo apt install python3-tk python3-serial

Run:
    python3 graphics_serial_viewer.py
    python3 graphics_serial_viewer.py --port /dev/ttyUSB0

Press Q or Escape to quit. This viewer does not flash the ESP32.
"""

import argparse
import tkinter as tk
from tkinter import messagebox
import threading
import queue
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    raise SystemExit("pySerial is missing. Install it with: sudo apt install python3-serial")

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 115200
MAX_WIDTH = 160
MAX_HEIGHT = 120


class SerialCubeViewer:
    def __init__(self, root, port, baud):
        self.root = root
        self.port = port
        self.baud = baud
        self.serial_conn = None
        self.frames = queue.Queue(maxsize=1)
        self.stop_event = threading.Event()
        self.frame_count = 0
        self.last_frame_time = time.monotonic()
        self.fps = 0.0

        root.title("PyO Live Graphics — ESP32 Serial")
        root.configure(bg="#050810")
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.canvas = tk.Canvas(root, width=640, height=480, bg="#050810",
                                highlightthickness=0)
        self.canvas.pack(padx=10, pady=(10, 4))
        self.status = tk.Label(root, text="Connecting...", fg="#dce8ff",
                               bg="#050810", font=("monospace", 10))
        self.status.pack(fill="x", padx=10, pady=(4, 10))

        root.bind("<Key>", self.on_key)
        self.canvas.focus_set()
        self.connect()
        self.root.after(20, self.show_latest_frame)

    def connect(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baud, timeout=1)
        except Exception as exc:
            ports = ", ".join(p.device for p in list_ports.comports()) or "none found"
            messagebox.showerror(
                "PyO serial connection failed",
                f"Could not open {self.port}:\n{exc}\n\nDetected serial ports: {ports}\n\n"
                "Check the USB cable, port permissions, and that the ESP32 firmware is running."
            )
            self.status.config(text=f"Not connected: {self.port}")
            return
        self.status.config(text=f"Connected to {self.port} at {self.baud} baud — waiting for ESP32 frames...")
        threading.Thread(target=self.read_serial, daemon=True).start()

    @staticmethod
    def decode_rgb565(value):
        r = ((value >> 11) & 0x1F) * 255 // 31
        g = ((value >> 5) & 0x3F) * 255 // 63
        b = (value & 0x1F) * 255 // 31
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def decode_palette(value):
        colors = ((3, 5, 12), (8, 20, 55), (0, 220, 245), (245, 35, 210),
                  (255, 190, 20), (60, 100, 255), (255, 120, 20), (120, 50, 255),
                  (255, 255, 255), (255, 35, 35), (40, 220, 80), (0, 150, 150),
                  (255, 120, 180), (120, 120, 120), (130, 200, 255), (100, 0, 20))
        r, g, b = colors[value]
        return f"#{r:02x}{g:02x}{b:02x}"

    def read_serial(self):
        while not self.stop_event.is_set() and self.serial_conn:
            try:
                header = self.serial_conn.readline().decode("ascii", "ignore").strip()
                if not (header.startswith("PYOFRAME ") or header.startswith("PYOCHAR ")):
                    continue
                mode = "char" if header.startswith("PYOCHAR ") else "hex"
                parts = header.split()
                if len(parts) != 4:
                    continue
                width, height, frame_id = map(int, parts[1:])
                if not (1 <= width <= MAX_WIDTH and 1 <= height <= MAX_HEIGHT):
                    continue

                pixels = []
                valid = True
                for _ in range(height):
                    row = self.serial_conn.readline().decode("ascii", "ignore").strip()
                    if mode == "char":
                        if len(row) != width:
                            valid = False
                            break
                        try:
                            pixels.extend("0123456789ABCDEF".index(ch) for ch in row)
                        except ValueError:
                            valid = False
                            break
                    else:
                        if len(row) != width * 4:
                            valid = False
                            break
                        try:
                            pixels.extend(int(row[i:i + 4], 16) for i in range(0, len(row), 4))
                        except ValueError:
                            valid = False
                            break
                if not valid or len(pixels) != width * height:
                    continue

                try:
                    while True:
                        self.frames.get_nowait()
                except queue.Empty:
                    pass
                self.frames.put((width, height, frame_id, pixels, mode))
            except Exception as exc:
                if not self.stop_event.is_set():
                    self.root.after(0, lambda e=str(exc): self.status.config(text=f"Serial read error: {e}"))
                time.sleep(0.1)

    def show_latest_frame(self):
        try:
            width, height, frame_id, pixels, mode = self.frames.get_nowait()
            self.canvas.delete("all")
            canvas_w = max(1, self.canvas.winfo_width())
            canvas_h = max(1, self.canvas.winfo_height())
            scale = max(1, min(canvas_w // width, canvas_h // height))
            xoff = (canvas_w - width * scale) // 2
            yoff = (canvas_h - height * scale) // 2

            for y in range(height):
                for x in range(width):
                    color = self.decode_palette(pixels[y * width + x]) if mode == "char" else self.decode_rgb565(pixels[y * width + x])
                    self.canvas.create_rectangle(
                        xoff + x * scale, yoff + y * scale,
                        xoff + (x + 1) * scale, yoff + (y + 1) * scale,
                        fill=color, outline=""
                    )
            now = time.monotonic()
            elapsed = now - self.last_frame_time
            if elapsed > 0:
                self.fps = 0.8 * self.fps + 0.2 / elapsed if self.frame_count else 1.0 / elapsed
            self.last_frame_time = now
            self.frame_count += 1
            self.status.config(
                text=f"LIVE  |  {self.port}  |  {width}x{height} RGB565 HEX  |  "
                     f"frame {frame_id}  |  ~{self.fps:.1f} FPS  |  Q: quit"
            )
        except queue.Empty:
            pass
        self.root.after(20, self.show_latest_frame)

    def on_key(self, event):
        if event.keysym.lower() in ("q", "escape"):
            self.close()

    def close(self):
        self.stop_event.set()
        try:
            if self.serial_conn:
                self.serial_conn.close()
        except Exception:
            pass
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="Display RGB565 hex or compact character frames received from PyO on serial.")
    parser.add_argument("--port", default=DEFAULT_PORT, help="serial device (default: /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="serial baud rate (default: 115200)")
    args = parser.parse_args()

    root = tk.Tk()
    SerialCubeViewer(root, args.port, args.baud)
    root.mainloop()


if __name__ == "__main__":
    main()
