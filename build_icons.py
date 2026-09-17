"""Génère icon.ico (Windows) ou un dossier icon.iconset (macOS) à partir du logo SVG.

Usage :
    python build_icons.py ico       # crée icon.ico
    python build_icons.py iconset   # crée icon.iconset/ (à passer ensuite à iconutil)
"""
import io
import os
import sys

from PIL import Image
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

SVG_PATH = "plcPlayground_logo.svg"


def render_png(size: int) -> Image.Image:
    """Rasterise le SVG à la taille (carrée) demandée, en pixels."""
    drawing = svg2rlg(SVG_PATH)
    scale = size / float(drawing.width)
    drawing.width *= scale
    drawing.height *= scale
    drawing.scale(scale, scale)

    buf = io.BytesIO()
    renderPM.drawToFile(drawing, buf, fmt="PNG")
    buf.seek(0)
    return Image.open(buf).convert("RGBA")


def build_ico() -> None:
    img = render_png(1024)
    img.save(
        "icon.ico",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("icon.ico créé")


def build_iconset() -> None:
    os.makedirs("icon.iconset", exist_ok=True)
    filename_sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for name, size in filename_sizes.items():
        render_png(size).save(f"icon.iconset/{name}")
    print("icon.iconset créé")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "ico"
    if target == "ico":
        build_ico()
    elif target == "iconset":
        build_iconset()
    else:
        raise SystemExit(f"Cible inconnue : {target!r} (attendu : 'ico' ou 'iconset')")
