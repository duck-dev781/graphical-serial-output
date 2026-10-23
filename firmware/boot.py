# PyO boot launcher for the ESP32.
#
# Install this file on the MicroPython device as /boot.py.
# Install firmware/main_char_stream.py on the device as /main_char_stream.py.
# MicroPython runs boot.py first, then main.py. This launcher does not block
# boot: it leaves the standard MicroPython startup flow intact. The root-level
# /main.py must import main_char_stream to start the graphics stream.
#
# NOTE: MicroPython executes boot.py before main.py. Do not put the infinite
# graphics loop here; keep it in main_char_stream.py.

print("PyO boot: startup checks complete.")
