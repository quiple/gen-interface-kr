"""Shared fixtures for font/build.py and font/proportional.py tests.

Two test fonts back the suite:

* **noto_subset** — a session-scoped subset of vendor Noto Sans JP variable,
  trimmed to a curated codepoint slice that exercises kana / CJK / punct /
  vertical-alternate / palt code paths. Subsetting once per session keeps
  the per-test cost in the millisecond range while still hitting real
  GSUB / GPOS data.

* **synthetic_ttf** — a hand-built minimal TrueType font used for tests
  that mutate every glyph (e.g. ``_apply_x_scale``, ``_apply_tracking``,
  ``_strip_extreme_glyphs``). A handful of glyphs is enough to verify
  the per-glyph logic without paying the cost of walking 17 000 Noto
  glyphs per assertion.

Both fixtures hand back fresh TTFont copies on demand so tests can
mutate without poisoning the shared state.
"""

import copy
import io
import os
from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont


REPO = Path(__file__).resolve().parents[1]
NOTO_VARIABLE_PATH = REPO / "vendor" / "fonts" / "Noto_Sans_JP" / "NotoSansJP-VariableFont_wght.ttf"


# ---------------------------------------------------------------------------
# Curated codepoints (mirrors font-baker's generate_test_subsets.py spirit)
# ---------------------------------------------------------------------------

# Pick at least one glyph from every block the build classifies on:
#   - Hiragana letters (U+3042 あ, U+304B か)
#   - Katakana letters (U+30A2 ア, U+30AB カ)
#   - CJK punctuation (U+3001 、, U+3002 。, U+30FB ・)
#   - CJK ideographs (U+4E00 一, U+6F22 漢)
#   - Latin (U+0041 A, U+0061 a)
#   - Iteration marks (U+3031 〱, U+3032 〲) — extreme bbox
#   - CJK-symbol numerals (U+3038 〸) — _is_cjk_codepoint boundary case
_TEST_CODEPOINTS = [
    0x0020, 0x0041, 0x0061,   # space, A, a
    0x3001, 0x3002, 0x3000,   # 、 。 ideographic space (CJK punct)
    0x3031, 0x3032,           # 〱 〲 iteration marks (extreme bbox)
    0x3038,                   # 〸 CJK numerals (range 3038..303B)
    0x3042, 0x304B,           # あ か (hiragana letters)
    0x30A2, 0x30AB,           # ア カ (katakana letters)
    0x30FB,                   # ・ middle dot (katakana-block punct, excluded from _is_kana_letter)
    0x4E00, 0x6F22,           # 一 漢 (CJK ideographs)
    0xFF21,                   # Ａ fullwidth A
]


# ---------------------------------------------------------------------------
# Noto subset (session-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _noto_subset_bytes() -> bytes:
    """Subset Noto Variable to the curated codepoints once per session.

    Returned as bytes so per-test fixtures can rehydrate via TTFont(BytesIO)
    without rerunning the subsetter. Layout features are kept (we want palt
    and vert/vrt2 GSUB intact for the tests that read them).
    """
    if not NOTO_VARIABLE_PATH.is_file():
        pytest.skip(f"Noto Variable not found at {NOTO_VARIABLE_PATH}")
    font = TTFont(str(NOTO_VARIABLE_PATH))
    options = Options()
    # Keep GSUB/GPOS so palt, vert/vrt2 reading is testable. Drop hinting
    # and unrelated extras to keep the subset small.
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    options.recalc_bounds = True
    subsetter = Subsetter(options=options)
    subsetter.populate(unicodes=_TEST_CODEPOINTS)
    subsetter.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


@pytest.fixture
def noto_subset(_noto_subset_bytes) -> TTFont:
    """Fresh Noto subset TTFont for tests that may mutate the font."""
    return TTFont(io.BytesIO(_noto_subset_bytes))


# ---------------------------------------------------------------------------
# Synthetic minimal TTF for whole-font mutation tests
# ---------------------------------------------------------------------------

def _build_synthetic_ttf() -> TTFont:
    """Build a tiny TrueType font with a hand-picked glyph mix.

    Glyph repertoire:
        .notdef, A (Latin), uni3042 (kana), uni30A2 (kana), uni4E00 (CJK),
        uni3001 (CJK punct), uni3031 (extreme-bbox iteration mark),
        uni3031.vert (vert alternate, also extreme-bbox)

    Each glyph carries a simple square outline at varying sizes so that
    advance widths, sidebearings, bbox extents, and composite handling
    can all be probed independently. The iteration-mark glyph deliberately
    has an outline that breaches ``head.yMax`` (1500 > _EXTREME_YMAX=1200)
    to drive ``_strip_extreme_glyphs``.
    """
    fb = FontBuilder(1000, isTTF=True)

    glyph_order = [
        ".notdef",
        "A",
        "uni3042",
        "uni30A2",
        "uni4E00",
        "uni3001",
        "uni3031",
        "uni3031.vert",
        "compositeA",  # composite of "A" — for _shift_glyph_x composite branch
    ]
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({
        0x41: "A",
        0x3042: "uni3042",
        0x30A2: "uni30A2",
        0x4E00: "uni4E00",
        0x3001: "uni3001",
        0x3031: "uni3031",
    })

    def _square(x_min: int, y_min: int, x_max: int, y_max: int) -> "Glyph":
        pen = TTGlyphPen(None)
        pen.moveTo((x_min, y_min))
        pen.lineTo((x_max, y_min))
        pen.lineTo((x_max, y_max))
        pen.lineTo((x_min, y_max))
        pen.closePath()
        return pen.glyph()

    glyphs = {
        ".notdef": _square(0, 0, 500, 700),
        "A": _square(50, 0, 450, 700),
        "uni3042": _square(50, 0, 950, 800),
        "uni30A2": _square(50, 0, 950, 800),
        "uni4E00": _square(0, 0, 1000, 800),
        "uni3001": _square(50, 0, 450, 200),
        # yMax = 1500 → past _EXTREME_YMAX, will be stripped
        "uni3031": _square(50, -500, 950, 1500),
        # vert alternate of 3031 — also extreme
        "uni3031.vert": _square(50, -500, 950, 1500),
    }
    # Composite that references "A" — used to test composite shift
    composite_pen = TTGlyphPen(glyphs)
    composite_pen.addComponent("A", (1, 0, 0, 1, 100, 0))
    glyphs["compositeA"] = composite_pen.glyph()

    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({
        ".notdef": (500, 0),
        "A": (500, 50),
        "uni3042": (1000, 50),
        "uni30A2": (1000, 50),
        "uni4E00": (1000, 0),
        "uni3001": (1000, 50),
        "uni3031": (1000, 50),
        "uni3031.vert": (1000, 50),
        "compositeA": (600, 100),
    })
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({
        "familyName": "GenInterfaceTest",
        "styleName": "Regular",
    })
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWeightClass=400)
    fb.setupPost()

    # Round-trip through bytes so the TTFont mirrors what a real font
    # produces on disk (sets up loca/maxp consistently).
    buf = io.BytesIO()
    fb.font.save(buf)
    buf.seek(0)
    return TTFont(buf)


@pytest.fixture(scope="session")
def _synthetic_bytes() -> bytes:
    font = _build_synthetic_ttf()
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


@pytest.fixture
def synthetic_ttf(_synthetic_bytes) -> TTFont:
    """Per-test copy of the synthetic minimal TTF."""
    return TTFont(io.BytesIO(_synthetic_bytes))
