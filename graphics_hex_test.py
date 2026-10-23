#!/usr/bin/env python3
"""
PyO Graphics Hex Test
---------------------
Generates a simple RGB565 graphics test frame as plain hexadecimal text.

Output format:
    # PyO Graphics Hex Frame v1
    WIDTH=64
    HEIGHT=32
    FORMAT=RGB565
    DATA
    F800 F800 ... (one 16-bit RGB565 pixel per token, row-major)

Each pixel is four hexadecimal digits. The first pixel is the top-left pixel.
No third-party packages are required.
"""

from pathlib import Path
import argparse

WIDTH = 64
HEIGHT = 32


def rgb565(red, green, blue):
    """Convert 8-bit RGB channels to a 16-bit RGB565 integer."""
    return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)


def pixel_for(x, y):
    """Build a recognizable test pattern: color bars, gradient, and checker."""
    bars = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255),
        (0, 0, 0), (255, 255, 0), (0, 255, 255), (255, 0, 255),
    ]
    bar_index = min(7, (x * 8) // WIDTH)
    red, green, blue = bars[bar_index]

    # Top half: eight solid color bars. Bottom half: red/green gradient
    # with a blue checker pattern so orientation and pixel order are obvious.
    if y < HEIGHT // 2:
        return rgb565(red, green, blue)

    gradient = int((x / (WIDTH - 1)) * 255)
    checker_blue = 255 if ((x // 4) + (y // 4)) % 2 == 0 else 0
    return rgb565(gradient, 255 - gradient, checker_blue)


def build_frame():
    """Return rows of 16-bit RGB565 pixel values, top to bottom."""
    return [
        [pixel_for(x, y) for x in range(WIDTH)]
        for y in range(HEIGHT)
    ]


def frame_to_hex_text(frame):
    """Serialize the frame into the documented PyO text-hex format."""
    lines = [
        "# PyO Graphics Hex Frame v1",
        f"WIDTH={WIDTH}",
        f"HEIGHT={HEIGHT}",
        "FORMAT=RGB565",
        "DATA",
    ]
    lines.extend(" ".join(f"{pixel:04X}" for pixel in row) for row in frame)
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Generate a PyO RGB565 graphics test frame as hexadecimal text."
    )
    parser.add_argument(
        "-o", "--output",
        default="graphics_frame.hex",
        help="output file path (default: graphics_frame.hex)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="print the complete hex frame to the terminal instead of writing a file",
    )
    args = parser.parse_args()

    text = frame_to_hex_text(build_frame())

    if args.stdout:
        print(text, end="")
        return

    output_path = Path(args.output)
    output_path.write_text(text, encoding="ascii")
    print("PyO graphics hex test frame generated.")
    print(f"Size: {WIDTH} x {HEIGHT} pixels")
    print("Pixel format: RGB565 (4 hex digits per pixel)")
    print(f"Output: {output_path.resolve()}")
    print("This is test image data only; it does not connect to or flash the ESP32.")


if __name__ == "__main__":
    main()
