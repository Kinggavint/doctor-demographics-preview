#!/usr/bin/env python3
"""Make WebP and resized JPEG variants of LCP / portrait photos.

Same photographs as the originals. Run from the repo root:
    python3 build/optimize_heroes.py
Outputs land in docs/assets/img/ next to the source files.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / 'docs' / 'assets' / 'img'

# filename -> target widths (a width >= the source width emits one native-size file)
JOBS = {
    '635195d6b495690eab7a6fa0.jpg': [480, 840, 1200],
    'banner-mike-68b5e065419f89ab7b17b8f3.jpg': [640, 1040, 1280],
    'banner-mike-68ae36a93ba6188b15e093ae.jpg': [640, 1040, 1138],
    'banner-mike-68a862537dc6b074cb6ee577.jpg': [640, 1040, 1600],
    'banner-mike-689bba15b52dae7d965071d5.jpg': [640, 1040, 1102],
    'banner-mike-6892773400987beaf980e0fc.jpg': [640, 1040, 1103],
    'banner-mike-67b50b86aea6db7f0ba29683.jpg': [640, 1040, 1280],
    'mike_profile_26.jpg': [320, 480, 800],
    '631c160e05c40c6f83ebc915.jpg': [320, 480, 610],
}


def main():
    for name, widths in JOBS.items():
        src = IMG / name
        im = Image.open(src)
        if im.mode != 'RGB':
            im = im.convert('RGB')
        w0, h0 = im.size
        seen_native = False
        for w in widths:
            if w >= w0:
                if seen_native:
                    continue
                tw, th = w0, h0
                seen_native = True
            else:
                tw, th = w, round(h0 * (w / w0))
            resized = im.resize((tw, th), Image.Resampling.LANCZOS)
            base = f'{src.stem}-{tw}w'
            webp = IMG / f'{base}.webp'
            jpg = IMG / f'{base}.jpg'
            resized.save(webp, 'WEBP', quality=80, method=6)
            resized.save(jpg, 'JPEG', quality=82, optimize=True, progressive=True)
            print(f'{name} -> {tw}x{th}  webp {webp.stat().st_size/1024:.1f}KB  jpg {jpg.stat().st_size/1024:.1f}KB')


if __name__ == '__main__':
    main()
