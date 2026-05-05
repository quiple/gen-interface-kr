#!/usr/bin/env python3
"""
Build tiny font subsets for the site Composition section's build-time SVG
shape generation:

- Noto Sans JP Variable → "書体デザイン" only, keeping the wght axis and the
  features (palt, kern) that the generated shape data needs.
- Gen Interface JP Regular → "Type Design" only, used to render the Latin
  reference through the same SVG path as the JP side so the two read with the
  same anti-aliasing / weight.

Outputs land in site/public/_font-subsets/.
"""

from __future__ import annotations

import os
from fontTools import subset

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOTO_SRC = os.path.join(ROOT, "vendor", "fonts", "Noto_Sans_JP", "NotoSansJP-VariableFont_wght.ttf")
GEN_SRC = os.path.join(ROOT, "dist", "ttf", "Gen Interface JP", "GenInterfaceJP-Regular.ttf")
# Kept as tiny checked-in build inputs so the site build does not depend on
# generated dist/ font outputs.
OUT_DIR = os.path.join(ROOT, "site", "public", "_font-subsets")
NOTO_OUT = os.path.join(OUT_DIR, "NotoSansJP-Subset.ttf")
GEN_OUT = os.path.join(OUT_DIR, "GenInterfaceJP-Regular-Subset.ttf")


def _build_subset(src: str, out: str, chars: str, layout_features: list[str]) -> None:
    options = subset.Options()
    options.retain_gids = False
    options.glyph_names = True
    options.layout_features = layout_features
    options.name_IDs = [1, 2, 3, 4, 6]
    options.name_legacy = False
    options.name_languages = ["*"]
    options.drop_tables = []

    subsetter = subset.Subsetter(options=options)
    font = subset.load_font(src, options)
    subsetter.populate(text=chars)
    subsetter.subset(font)
    subset.save_font(font, out, options)

    size_kb = os.path.getsize(out) / 1024
    print(f"Wrote {out} ({size_kb:.1f} KB)")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    # palt is what the generated JP shape data stores for tweening.
    _build_subset(NOTO_SRC, NOTO_OUT, "書体デザイン", ["palt", "kern"])
    # Latin side just needs basic shaping (kern for Inter's pair adjustments).
    _build_subset(GEN_SRC, GEN_OUT, "Type Design", ["kern"])


if __name__ == "__main__":
    main()
