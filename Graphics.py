#!/usr/bin/env python3
"""PyO host prototype: fullscreen Tk desktop bridged to an ESP32 over serial.

The host renders the UI; the ESP32 runs firmware/main.py. Protocol is newline-
delimited JSON for the initial prototype, not a high-speed pixel-stream protocol.
"""
from __future__ import annotations

import json
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

try:
    import serial
    from serial.tools import list_ports
except ImportError as exc:
    raise SystemExit("Missing pySerial. Install it with: sudo apt install python3-serial") from exc

APP_NAME = "PyO"
BAUD = 115200
PROTOCOL_VERSION = 1


class PyOHost:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PyO — Graphical Serial Output")
        self.root.geometry("900x560")
        self.root.configure(bg="#101923")
        self.root.minsize(640, 420)
        self.ser = None
        self.reader_thread = None
        self.stop_reader = threading.Event()
        self.incoming: queue.Queue[dict] = queue.Queue()
        self.fullscreen = False
        self.dark_mode = True
        self.ready = False
        self.last_mouse_send = 0.0
        self.port_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Not connected")
        self.build_connect_screen()
        self.root.after(100, self.process_incoming)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def build_connect_screen(self) -> None:
        self.clear_root()
        panel = tk.Frame(self.root, bg="#172433", padx=28, pady=24)
        panel.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(panel, text="PyO", font=("DejaVu Sans", 34, "bold"), fg="#58b7ff", bg="#172433").pack(anchor="w")
        tk.Label(panel, text="Graphical Serial Output", font=("DejaVu Sans", 15), fg="#f2f6fb", bg="#172433").pack(anchor="w", pady=(0, 18))
        tk.Label(panel, text="Select the USB serial port connected to your ESP32-WROVER-E.", font=("DejaVu Sans", 10), fg="#c5d2df", bg="#172433").pack(anchor="w", pady=(0, 8))
        row = tk.Frame(panel, bg="#172433")
        row.pack(fill="x")
        self.port_box = ttk.Combobox(row, textvariable=self.port_var, width=36, state="readonly")
        self.port_box.pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Refresh", command=self.refresh_ports).pack(side="left")
        ttk.Button(panel, text="Connect and start desktop", command=self.connect).pack(anchor="w", pady=(14, 8))
        tk.Label(panel, textvariable=self.status_var, fg="#b5c6d8", bg="#172433", wraplength=430, justify="left").pack(anchor="w")
        tk.Label(panel, text="Tip: press Esc in the desktop to leave fullscreen.", fg="#8196aa", bg="#172433").pack(anchor="w", pady=(14, 0))
        self.refresh_ports()

    def clear_root(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def refresh_ports(self) -> None:
        ports = list(list_ports.comports())
        values = [f"{p.device} — {p.description}" for p in ports]
        self.port_box["values"] = values
        if values and self.port_var.get() not in values:
            self.port_var.set(values[0])
        if not values:
            self.port_var.set("")
            self.status_var.set("No serial ports found. Connect the board with a data-capable USB cable.")

    def connect(self) -> None:
        selection = self.port_var.get()
        if not selection:
            messagebox.showerror(APP_NAME, "Select a serial port first.")
            return
        device = selection.split(" — ", 1)[0]
        try:
            self.ser = serial.Serial(device, BAUD, timeout=0.15, write_timeout=1)
            # Opening some USB-UART bridges resets the ESP32. Give its startup script time.
            time.sleep(1.5)
            self.send({"type": "HELLO", "version": PROTOCOL_VERSION, "client": "PyO-host"})
        except Exception as exc:
            if self.ser:
                self.ser.close()
                self.ser = None
            messagebox.showerror(APP_NAME, f"Could not open {device}:\n{exc}\n\nOn Linux, check serial-port permissions (often the dialout group).")
            return
        self.status_var.set(f"Connected to {device}; waiting for firmware response…")
        self.stop_reader.clear()
        self.reader_thread = threading.Thread(target=self.reader_loop, daemon=True)
        self.reader_thread.start()
        self.root.after(1800, self.finish_connect_if_silent)

    def finish_connect_if_silent(self) -> None:
        if self.ser is not None and not self.ready:
            self.status_var.set("Port opened, but no PyO firmware handshake arrived. Check that firmware/main.py is installed and the board uses the expected serial port.")

    def send(self, payload: dict) -> None:
        if self.ser is None or not self.ser.is_open:
            return
        try:
            line = json.dumps(payload, separators=(",", ":")) + "\n"
            self.ser.write(line.encode("utf-8"))
        except Exception as exc:
            self.incoming.put({"type": "HOST_ERROR", "message": str(exc)})

    def reader_loop(self) -> None:
        while not self.stop_reader.is_set() and self.ser is not None:
            try:
                raw = self.ser.readline()
                if not raw:
                    continue
                try:
                    msg = json.loads(raw.decode("utf-8", errors="replace").strip())
                    if isinstance(msg, dict):
                        self.incoming.put(msg)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Boot messages or REPL output are not protocol packets; ignore them.
                    continue
            except Exception as exc:
                self.incoming.put({"type": "HOST_ERROR", "message": str(exc)})
                break

    def process_incoming(self) -> None:
        try:
            while True:
                msg = self.incoming.get_nowait()
                kind = msg.get("type")
                if kind in ("READY", "HELLO_ACK"):
                    self.ready = True
                    self.status_var.set(f"ESP32 ready — protocol v{msg.get('version', '?')}")
                    if not self.fullscreen:
                        self.build_desktop()
                elif kind == "LOG":
                    self.append_terminal(str(msg.get("message", "")))
                elif kind == "HOST_ERROR":
                    self.status_var.set("Serial error: " + str(msg.get("message", "unknown error")))
                elif kind == "ACK":
                    self.status_var.set(str(msg.get("message", "ESP32 acknowledged")))
        except queue.Empty:
            pass
        self.root.after(100, self.process_incoming)

    def build_desktop(self) -> None:
        self.fullscreen = True
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", self.leave_fullscreen)
        self.root.bind("<KeyPress>", self.on_key)
        self.root.bind("<Motion>", self.on_mouse_move)
        self.root.bind("<Button-1>", self.on_mouse_click)
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.clear_root()
        self.root.configure(bg="#0f1824")
        top = tk.Frame(self.root, bg="#172433", height=46, padx=16)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="PyO", bg="#172433", fg="#58b7ff", font=("DejaVu Sans", 16, "bold")).pack(side="left", pady=7)
        tk.Label(top, text="Serial desktop · ESP32-WROVER-E", bg="#172433", fg="#b9c9d9", font=("DejaVu Sans", 10)).pack(side="left", padx=18)
        ttk.Button(top, text="Light / dark", command=self.toggle_theme).pack(side="right", pady=6)
        ttk.Button(top, text="Exit desktop", command=self.leave_fullscreen).pack(side="right", padx=8, pady=6)
        self.desktop = tk.Frame(self.root, bg="#0f1824", padx=28, pady=26)
        self.desktop.pack(fill="both", expand=True)
        tk.Label(self.desktop, text="Welcome to PyO", bg="#0f1824", fg="#f4f8fc", font=("DejaVu Sans", 26, "bold")).pack(anchor="w")
        tk.Label(self.desktop, text="A lightweight serial-connected desktop prototype", bg="#0f1824", fg="#a8bbce", font=("DejaVu Sans", 11)).pack(anchor="w", pady=(4, 24))
        grid = tk.Frame(self.desktop, bg="#0f1824")
        grid.pack(anchor="nw")
        apps = [("▣", "Terminal", self.open_terminal), ("▤", "Text editor", self.open_editor), ("▧", "Gallery", self.open_gallery), ("▦", "PyStore", self.open_store), ("⚙", "Settings", self.open_settings), ("▣", "Files", self.open_files)]
        for index, (glyph, name, callback) in enumerate(apps):
            card = tk.Button(grid, text=f"{glyph}\n\n{name}", command=callback, width=15, height=5, relief="flat", bg="#1a2a3b", fg="#edf5fc", activebackground="#24425d", activeforeground="#ffffff", font=("DejaVu Sans", 11), cursor="hand2")
            card.grid(row=index // 3, column=index % 3, padx=(0, 14), pady=(0, 14), sticky="nsew")
        bottom = tk.Frame(self.root, bg="#172433", height=34, padx=14)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)
        tk.Label(bottom, text="● Connected" if self.ready else "○ Connecting", bg="#172433", fg="#85d6a1" if self.ready else "#f0c36b").pack(side="left", pady=6)
        self.desktop_status = tk.Label(bottom, text="F11 fullscreen · Esc exit fullscreen", bg="#172433", fg="#b9c9d9")
        self.desktop_status.pack(side="right", pady=6)
        self.send({"type": "DESKTOP_STARTED", "version": PROTOCOL_VERSION})

    def leave_fullscreen(self, _event=None) -> None:
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)
        self.root.unbind("<KeyPress>")
        self.root.unbind("<Motion>")
        self.root.unbind("<Button-1>")
        self.build_connect_screen()

    def toggle_fullscreen(self, _event=None) -> None:
        current = str(self.root.attributes("-fullscreen")).lower() in ("1", "true", "yes")
        self.root.attributes("-fullscreen", not current)

    def toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        self.send({"type": "SETTING", "name": "theme", "value": "dark" if self.dark_mode else "light"})
        self.build_desktop()
        if not self.dark_mode:
            self.root.configure(bg="#eaf2fa")
            self.desktop.configure(bg="#eaf2fa")
            for widget in self.desktop.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.configure(bg="#eaf2fa", fg="#172433")

    def on_key(self, event) -> None:
        if event.keysym == "Escape":
            return
        self.send({"type": "KEY", "key": event.keysym, "char": event.char, "state": event.state})

    def on_mouse_move(self, event) -> None:
        # Avoid flooding the low-bandwidth serial link with every motion event.
        now = time.monotonic()
        if now - self.last_mouse_send >= 0.05:
            self.last_mouse_send = now
            self.send({"type": "MOUSE_MOVE", "x": event.x, "y": event.y})

    def on_mouse_click(self, event) -> None:
        self.send({"type": "MOUSE_CLICK", "x": event.x, "y": event.y, "button": 1})

    def app_window(self, title: str, width: int = 640, height: int = 380):
        win = tk.Toplevel(self.root)
        win.title(f"{title} — PyO")
        win.geometry(f"{width}x{height}")
        win.configure(bg="#172433")
        win.transient(self.root)
        tk.Label(win, text=title, bg="#172433", fg="#58b7ff", font=("DejaVu Sans", 16, "bold")).pack(anchor="w", padx=14, pady=12)
        self.send({"type": "APP_OPEN", "app": title.lower().replace(" ", "_")})
        return win

    def open_terminal(self) -> None:
        win = self.app_window("Terminal")
        output = tk.Text(win, bg="#0b1118", fg="#dce9f5", insertbackground="white", font=("DejaVu Sans Mono", 10), height=14, wrap="word")
        output.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        output.insert("end", "PyO terminal prototype. Commands: help, status, clear\n")
        entry = ttk.Entry(win)
        entry.pack(fill="x", padx=12, pady=(0, 12))
        def run_command(_event=None):
            command = entry.get().strip()
            if not command:
                return
            output.insert("end", f"pyO$ {command}\n")
            entry.delete(0, "end")
            if command == "clear":
                output.delete("1.0", "end")
            elif command == "help":
                output.insert("end", "Built-ins: help, status, clear. Remote Python execution is intentionally not enabled yet.\n")
            elif command == "status":
                output.insert("end", f"serial={'connected' if self.ser and self.ser.is_open else 'disconnected'}; firmware_ready={self.ready}\n")
                self.send({"type": "COMMAND", "command": "status"})
            else:
                output.insert("end", "Unknown command. Try: help\n")
            output.see("end")
        entry.bind("<Return>", run_command)
        entry.focus_set()

    def open_editor(self) -> None:
        win = self.app_window("Text editor", 720, 480)
        text = tk.Text(win, bg="#f7f9fc", fg="#172433", insertbackground="#172433", font=("DejaVu Sans Mono", 11), undo=True)
        text.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        text.insert("1.0", "# PyO text editor prototype\n# Saving to the ESP32 filesystem will be added after the protocol is stable.\n")
        ttk.Button(win, text="Send buffer to ESP32", command=lambda: self.send({"type": "EDITOR_BUFFER", "text": text.get("1.0", "end-1c")[:4000]})).pack(anchor="e", padx=12, pady=(0, 12))

    def open_gallery(self) -> None:
        win = self.app_window("Gallery")
        tk.Label(win, text="Image viewer placeholder\n\nThe first release uses host-rendered UI. Image transfer will use chunked binary packets in a later protocol version.", bg="#172433", fg="#dce9f5", justify="left", wraplength=560).pack(anchor="w", padx=16, pady=8)

    def open_store(self) -> None:
        win = self.app_window("PyStore")
        tk.Label(win, text="PyStore is planned, not connected yet.\n\nApps need a documented PyO package format and compatibility metadata before downloading or executing code from a repository.", bg="#172433", fg="#dce9f5", justify="left", wraplength=560).pack(anchor="w", padx=16, pady=8)

    def open_settings(self) -> None:
        win = self.app_window("Settings")
        tk.Label(win, text="PyO settings prototype", bg="#172433", fg="#dce9f5").pack(anchor="w", padx=16)
        ttk.Button(win, text="Toggle dark / light theme", command=self.toggle_theme).pack(anchor="w", padx=16, pady=10)
        tk.Label(win, text="Camera, SD, Bluetooth audio, and Wi-Fi features require board-specific drivers and hardware support.", bg="#172433", fg="#a9bdcf", wraplength=560, justify="left").pack(anchor="w", padx=16, pady=8)

    def open_files(self) -> None:
        win = self.app_window("Files")
        tk.Label(win, text="File manager placeholder. SD-card mounting is not implemented until the actual SD interface and pin configuration are confirmed.", bg="#172433", fg="#dce9f5", wraplength=560, justify="left").pack(anchor="w", padx=16, pady=8)

    def append_terminal(self, message: str) -> None:
        # Reserved for firmware log events; terminal window routing will be added later.
        if hasattr(self, "desktop_status"):
            self.desktop_status.configure(text=message[:100])

    def close(self) -> None:
        self.stop_reader.set()
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    PyOHost(root)
    root.mainloop()


if __name__ == "__main__":
    main()
