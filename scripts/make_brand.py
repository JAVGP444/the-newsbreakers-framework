"""Genera PNG, favicon, ICO e ICNS a partir del logo maestro."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "branding"
PUBLIC = ROOT / "frontend" / "public"
MAC = ROOT / "packaging" / "mac"
SOURCE_CANDIDATES = [
    BRAND / "logo-source.jpg",
    BRAND / "logo-source.png",
]


def _source() -> Path:
    for p in SOURCE_CANDIDATES:
        if p.is_file():
            return p
    raise SystemExit("Falta branding/logo-source.jpg")


def _square(im: Image.Image, size: int) -> Image.Image:
    rgb = im.convert("RGBA")
    w, h = rgb.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    crop = rgb.crop((left, top, left + side, top + side))
    return crop.resize((size, size), Image.Resampling.LANCZOS)


def main() -> int:
    src = _source()
    BRAND.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    im = Image.open(src)
    master = _square(im, 1024)
    png = BRAND / "logo.png"
    master.save(png, "PNG", optimize=True)
    master.save(PUBLIC / "logo.png", "PNG", optimize=True)
    master.resize((180, 180), Image.Resampling.LANCZOS).save(PUBLIC / "apple-touch-icon.png", "PNG")
    master.resize((32, 32), Image.Resampling.LANCZOS).save(PUBLIC / "favicon-32.png", "PNG")
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    master.save(BRAND / "logo.ico", format="ICO", sizes=ico_sizes)
    master.save(PUBLIC / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    shutil.copy2(png, ROOT / "packaging" / "linux" / "newsbreakers.png")

    iconset = MAC / "icon.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)
    for s, name in [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]:
        master.resize((s, s), Image.Resampling.LANCZOS).save(iconset / name, "PNG")
    icns = BRAND / "logo.icns"
    try:
        subprocess.check_call(["iconutil", "-c", "icns", str(iconset), "-o", str(icns)])
        shutil.copy2(icns, MAC / "AppIcon.icns")
    except (OSError, subprocess.CalledProcessError):
        print("iconutil no disponible; .icns se arma al empaquetar en Mac", file=sys.stderr)
    print(png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
