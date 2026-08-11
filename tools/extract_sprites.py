"""Slice the source sheets into per-character sprites with a transparent
background.

`Stand`, `Ready` and `Jump` are the side-on race poses; `Characters` is the
front-facing line-up used by the character picker. Every sheet holds the same 4
racers in the same left-to-right order. Background and cast shadow both sit on
the line between BG and SHADOW in RGB space, so a "tube" test around that
segment keys out both while keeping the brown sack, white shirts and skin tones.

Characters are isolated as connected components (a cap brim can overhang the
neighbour, so a plain column cut would clip it). The vertical crop range is
shared by all three poses of a character, so a bottom-anchored draw keeps the
jump pose genuinely airborne. The front sheet instead shares one crop range
across all four characters, so the picker can draw them in equal-height boxes
and still show Adik as the small one.

    python tools/extract_sprites.py
"""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sprites"
POSES = ["Stand", "Ready", "Jump"]
NAMES = ["bapak", "ibu", "adik", "kakak"]

BG = np.array([224.0, 206.0, 201.0])
SHADOW = np.array([178.0, 163.0, 158.0])
FRONT_BG = np.array([233.0, 219.0, 214.0])   # the front sheet is a shade lighter
FRONT_SHADOW = np.array([162.0, 152.0, 150.0])
SOFT_IN, SOFT_OUT = 15.0, 27.0  # alpha ramp on distance from the tube axis
TARGET_H = 460  # exported sprite height in px
FRONT_H = 620   # the picker shows these much larger
PAD = 6


def keyed(path, bg=BG, shadow=SHADOW):
    """Return (rgb, alpha) with background + cast shadow keyed out."""
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    axis = shadow - bg
    t = np.clip(((rgb - bg) @ axis) / float(axis @ axis), -0.25, 1.35)
    dist = np.linalg.norm(rgb - (bg + t[..., None] * axis), axis=-1)
    alpha = np.clip((dist - SOFT_IN) / (SOFT_OUT - SOFT_IN), 0.0, 1.0)
    # Grey anti-aliasing *inside* a character — the ring where a white eye meets
    # its pupil, say — lands in the tube too and would punch a hole. Only the
    # background reaches the sheet border, so re-solidify everything it encloses.
    alpha = np.maximum(alpha, ndimage.binary_fill_holes(alpha > 0.5))
    return rgb, alpha


def characters(alpha, count=4):
    """Masks for the `count` biggest blobs, ordered left to right."""
    labels, n = ndimage.label(alpha > 0.5, structure=np.ones((3, 3)))
    sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
    biggest = np.argsort(sizes)[::-1][:count] + 1
    masks = [labels == i for i in biggest]
    masks.sort(key=lambda m: float(np.argwhere(m)[:, 1].mean()))
    return masks


def cut(rgb, alpha, mask, y0, y1, target_h):
    """Crop one character to its own columns over a caller-chosen row range."""
    cols = np.argwhere(mask)[:, 1]
    x0, x1 = max(0, cols.min() - PAD), min(alpha.shape[1], cols.max() + PAD)
    # zero out anything belonging to a neighbouring racer
    a = np.where(mask, alpha, 0.0)[y0:y1, x0:x1] * 255.0
    img = Image.fromarray(np.dstack([rgb[y0:y1, x0:x1], a]).astype(np.uint8))
    scale = target_h / img.height
    return img.resize((max(1, round(img.width * scale)), target_h), Image.LANCZOS)


def fronts():
    """The picker line-up: one shared crop so the height differences survive."""
    rgb, alpha = keyed(ROOT / "Characters.png", FRONT_BG, FRONT_SHADOW)
    masks = characters(alpha)
    rows = [np.argwhere(m)[:, 0] for m in masks]
    y0 = max(0, min(r.min() for r in rows) - PAD)
    y1 = min(alpha.shape[0], max(r.max() for r in rows) + PAD + 2)
    for name, mask in zip(NAMES, masks):
        cut(rgb, alpha, mask, y0, y1, FRONT_H).save(OUT / f"{name}_front.png")
    print(f"fronts: y={y0}..{y1}")


def main():
    OUT.mkdir(exist_ok=True)
    sheets = {}
    for pose in POSES:
        rgb, alpha = keyed(ROOT / f"{pose}.png")
        sheets[pose] = (rgb, alpha, characters(alpha))

    h, w = sheets["Stand"][1].shape
    for i, name in enumerate(NAMES):
        rows = [np.argwhere(sheets[p][2][i])[:, 0] for p in POSES]
        y0 = max(0, min(r.min() for r in rows) - PAD)
        y1 = min(h, max(r.max() for r in rows) + PAD + 2)

        for pose in POSES:
            rgb, alpha, masks = sheets[pose]
            cut(rgb, alpha, masks[i], y0, y1, TARGET_H).save(OUT / f"{name}_{pose.lower()}.png")
        print(f"{name}: y={y0}..{y1}")

    fronts()


if __name__ == "__main__":
    main()
