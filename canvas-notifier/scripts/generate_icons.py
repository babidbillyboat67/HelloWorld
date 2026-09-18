"""One-off script: draws a simple bell-on-navy-square app icon and writes it
out as plain PNGs (no Pillow dependency — just zlib + struct) at the sizes
the PWA manifest and Apple touch-icon need.

    python generate_icons.py
"""

import os
import struct
import zlib

BG = (0x1c, 0x2b, 0x3a)  # matches the workbench's --ink color
FG = (0xf2, 0x99, 0x4a)  # matches --amber


def _bell_mask(x, y, size):
    # Normalize to a 0..1 square, centered.
    nx, ny = x / size - 0.5, y / size - 0.5

    # Bell body: a circle sitting slightly above center, flowing into the flare.
    body_cx, body_cy, body_r = 0.0, -0.06, 0.26
    in_body = (nx - body_cx) ** 2 + (ny - body_cy) ** 2 <= body_r ** 2

    # Bell flare: a wider ellipse at the bottom of the body.
    flare_cy, flare_rx, flare_ry = 0.14, 0.34, 0.07
    in_flare = ((nx) ** 2) / (flare_rx ** 2) + ((ny - flare_cy) ** 2) / (flare_ry ** 2) <= 1.0

    # Clapper: small circle below the flare.
    clapper_cy, clapper_r = 0.24, 0.045
    in_clapper = nx ** 2 + (ny - clapper_cy) ** 2 <= clapper_r ** 2

    return in_body or in_flare or in_clapper


def make_png(size, path):
    rows = []
    for y in range(size):
        row = bytearray([0])  # filter type 0 (none) for this scanline
        for x in range(size):
            color = FG if _bell_mask(x, y, size) else BG
            row.extend(color)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit, RGB truecolor
    idat = zlib.compress(raw, 9)

    with open(path, "wb") as f:
        f.write(sig)
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", idat))
        f.write(chunk(b"IEND", b""))


def main():
    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "icons"
    )
    os.makedirs(out_dir, exist_ok=True)
    for size, name in [(192, "icon-192.png"), (512, "icon-512.png"), (180, "apple-touch-icon.png")]:
        make_png(size, os.path.join(out_dir, name))
        print(f"wrote {name} ({size}x{size})")


if __name__ == "__main__":
    main()
