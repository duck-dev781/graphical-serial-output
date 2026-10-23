# Upstream references used by PyO

These projects and documentation pages are useful references for implementing the host-to-device serial link. PyO is a separate experimental project and does not copy their source code.

- [pySerial documentation](https://pyserial.readthedocs.io/en/latest/) — serial port access, timeouts, and line-based I/O.
- [pySerial port enumeration](https://pyserial.readthedocs.io/en/latest/tools.html) — discover available serial ports with `serial.tools.list_ports.comports()`.
- [MicroPython ESP32 quick reference](https://docs.micropython.org/en/latest/esp32/quickref.html) — UART API and ESP32 pin notes.
- [MicroPython ESP32 getting started](https://docs.micropython.org/en/latest/esp32/tutorial/intro.html) — board setup, USB-to-serial bridge, and firmware basics.
- [MicroPython ESP32 port on GitHub](https://github.com/micropython/micropython/tree/master/ports/esp32) — firmware implementation and supported features.

## Why the first version is simple

The first version uses Tkinter for the Linux host UI and pySerial for transport, minimizing dependencies on an older antiX computer. The ESP32 side uses MicroPython's UART API. Full-screen image streaming, sound, Bluetooth audio, camera, SD-card mounting, and a network-connected app store are not yet implemented; each depends on actual hardware and needs a dedicated protocol and tests.
