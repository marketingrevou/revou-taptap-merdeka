"""Build the sound-audit page: tools/preview.template.html + the encoded audio.

    .venv/bin/python tools/make_preview.py

Everything is inlined as data URIs -- the font, the sprite sheet and the four
stems -- so the one file plays off the filesystem, off a static host, or as a
published Artifact, with no second request to go wrong.
"""

import base64
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

STEMS = ["bed", "crowd", "pulse", "hook"]


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def main():
    audio = os.path.join(ROOT, "audio")
    need = ["sfx.m4a", "sfx.json"] + [s + ".m4a" for s in STEMS]
    missing = [f for f in need if not os.path.exists(os.path.join(audio, f))]
    if missing:
        raise SystemExit("missing " + ", ".join(missing)
                         + "\nrun tools/make_audio.py then tools/encode_audio.sh")

    total = sum(os.path.getsize(os.path.join(audio, f))
                for f in os.listdir(audio) if f.endswith(".m4a"))

    with open(os.path.join(audio, "sfx.json")) as f:
        sfx_map = json.load(f)

    assets = {
        "sfx": b64(os.path.join(audio, "sfx.m4a")),
        "stems": {s: b64(os.path.join(audio, s + ".m4a")) for s in STEMS},
        "map": sfx_map,
        "totalKB": round(total / 1024, 1),
    }

    with open(os.path.join(HERE, "preview.template.html")) as f:
        html = f.read()

    html = html.replace("__FONT__", b64(os.path.join(ROOT, "fonts",
                                                     "ibm-plex-sans-latin.woff2")))
    html = html.replace("__ASSETS__", json.dumps(assets, separators=(",", ":")))

    out = os.path.join(audio, "preview.html")
    with open(out, "w") as f:
        f.write(html)

    print(f"  audio/preview.html   {os.path.getsize(out)/1024:7.1f} KB"
          f"   ({assets['totalKB']} KB of audio, {len(sfx_map['cues'])} cues,"
          f" {len(STEMS)} stems)")


if __name__ == "__main__":
    main()
