# PyO serial protocol v1

The prototype uses newline-delimited UTF-8 JSON objects over a 115200-baud 8-N-1 serial connection. Each object is one line and must be shorter than 4096 bytes. This is intentionally easy to debug; a future version should use framed binary packets for images and high-rate mouse/display traffic.

## Startup

1. The ESP32 firmware boots and may emit `BOOT`.
2. The host opens the serial port and sends `{"type":"HELLO","version":1,"client":"PyO-host"}`.
3. Firmware replies with `READY`, including protocol version and feature names.
4. Host opens its fullscreen UI and sends `DESKTOP_STARTED`.

## Message types

| Direction | Type | Purpose |
|---|---|---|
| Host → ESP32 | `HELLO` | Negotiate protocol version |
| ESP32 → Host | `BOOT` | Firmware started |
| ESP32 → Host | `READY` | Handshake accepted |
| Host → ESP32 | `DESKTOP_STARTED` | Host UI is ready |
| Host → ESP32 | `KEY` | Key name, character, and modifier state |
| Host → ESP32 | `MOUSE_MOVE` | Host-window pointer coordinates |
| Host → ESP32 | `MOUSE_CLICK` | Pointer coordinates and button |
| Host → ESP32 | `APP_OPEN` | App launch request |
| Host → ESP32 | `SETTING` | Setting update, such as theme |
| Host → ESP32 | `COMMAND` | A small named firmware command |
| Host → ESP32 | `EDITOR_BUFFER` | Text buffer preview; never executed automatically |
| ESP32 → Host | `ACK` | Acknowledgment/status text |
| ESP32 → Host | `LOG` | Human-readable diagnostic message |

## Design rules

- Never execute text received from the host as Python code.
- Bound packet size and validate message types.
- The host UI remains responsible for rendering in this prototype; the ESP32 is not sending full-screen pixel buffers yet.
- Do not send one JSON object per raw pixel. Future images should use chunked binary frames with a frame ID, byte offset, payload length, and checksum.
- Serial input is untrusted. Future PyStore downloads must be validated and confirmed before any code is installed or run.

## Hardware note

Many ESP32-WROVER-E boards use a USB-to-UART bridge connected to UART0 (GPIO1 TX / GPIO3 RX), which is also the default MicroPython REPL. `firmware/main.py` detaches the REPL to reserve UART0 for this prototype. Have a recovery method ready before installing it.
