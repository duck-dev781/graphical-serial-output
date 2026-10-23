# PyO — Graphical Serial Output

PyO is an experimental serial-connected desktop prototype for an ESP32-WROVER-E and a Linux host. The Linux host renders the fullscreen interface; the ESP32 runs MicroPython firmware and exchanges framed messages over USB serial.

> **Status:** early prototype scaffold. This is not a complete operating system yet. USB serial transport, host GUI, and firmware must be tested together on the actual board.

## Architecture

- `Graphics.py` — Linux host application: serial-port selection, fullscreen desktop window, keyboard/mouse events, and serial receive loop.
- `firmware/main.py` — MicroPython-side protocol prototype.
- `protocol/PROTOCOL.md` — packet framing and message types.
- `requirements.txt` — host-side Python dependency.

## Host setup (antiX / Debian-based Linux)

```bash
sudo apt update
sudo apt install python3 python3-tk python3-serial
```

Alternatively, in a virtual environment install the dependency from `requirements.txt` with `python3 -m pip install -r requirements.txt`.

Connect the ESP32 with a **data-capable USB cable**, find its port with `ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null`, then run:

```bash
python3 Graphics.py
```

If your Linux account cannot open the serial port, add your user to the appropriate device group (often `dialout`) and log out/in. Do not run the GUI as root unless absolutely necessary; `sudo` is not normally required for the host app.

## Firmware

Flash a compatible MicroPython build for your ESP32-WROVER board, copy `firmware/main.py` to the board as `main.py`, and reboot. The current firmware is a protocol proof-of-concept, not a complete desktop OS. Check board-specific USB/UART behavior before using it: many WROVER-E development boards expose UART0 through a USB-to-serial bridge rather than native USB CDC.

## Safety and limitations

- The first version sends small text-framed messages; it does not stream raw full-screen frames or implement all planned apps.
- A serial connection does not automatically provide SD-card, camera, Bluetooth-audio, or display support. Those require the correct board peripherals, drivers, and pin configuration.
- PyStore packages must be treated as untrusted code. A future installer should verify package metadata and require user confirmation before executing code.

## Roadmap

1. Establish reliable serial handshake.
2. Render a fullscreen host desktop and forward keyboard/mouse events.
3. Add a versioned protocol and incremental drawing updates.
4. Add ESP32 app logic and hardware services one at a time.
5. Add a curated PyStore manifest and compatible app format.
