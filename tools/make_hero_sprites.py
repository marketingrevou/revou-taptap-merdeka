"""Downscale the 3D character renders in `images/` into the menu art.

These are the portraits from the campaign creative — bust-length, each racer
already inside their sack, with the sack running flush to the bottom edge of the
frame. That bottom anchoring is what lets the picker, the nameplate and the
results board draw them with `object-position: bottom` and have every character
line up on the same ground line without any per-character offsets.

Nothing here keys or crops: the source files are already tight RGBA cutouts. The
only job is to name them after the characters (the originals have spaces in their
filenames) and to bring ~500 KB renders down to something a web page should ship.

    python tools/make_hero_sprites.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sprites"
TARGET_H = 700  # tallest the picker ever draws them, at 2x for retina

# left-to-right in the source sheets, matching extract_sprites.py's NAMES
SOURCES = {
    "bapak": "karakter-01 1.png",   # headband and tie
    "ibu": "karakter-02 1.png",     # bun and red earrings
    "adik": "karakter-03 1.png",    # Garuda cap and suspenders — the ad's hero
    "kakak": "karakter-04 1.png",   # headband and long hair
}


def main() -> None:
    for name, src in SOURCES.items():
        im = Image.open(ROOT / "images" / src).convert("RGBA")
        im = im.resize((round(im.width * TARGET_H / im.height), TARGET_H), Image.LANCZOS)
        dst = OUT / f"{name}_hero.png"
        im.save(dst, optimize=True)
        print(f"{dst.relative_to(ROOT)}  {im.width}x{im.height}")


if __name__ == "__main__":
    main()
