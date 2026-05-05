#!/usr/bin/env python3
"""
Build Gen Interface JP font families.

Shared pipeline per weight:
  1. Bake Noto Sans JP variable → static TTF  (font-baker, base-only,
                                                metadataMode=inheritBase
                                                so Noto's name/OS2 survive)
  2. Convert to proportional metrics           (palt-based, proportional.py)
  3. Apply tracking                            (LSB +half, RSB +half)
  4. Merge Inter/InterDisplay + proportional Noto  (font-baker)

Families:
  - Gen Interface JP         : Inter       + proportional Noto, tracking +50 (kana/punct +60)
  - Gen Interface JP Display : InterDisplay + proportional Noto, tracking +20

Outputs TTF into dist/ttf/. Web delivery (subset WOFF2 chunks served via
unicode-range) is generated separately by the webfont module from these
TTF outputs — see src/webfont/.
"""

from __future__ import annotations

import os
import sys

from fontTools.ttLib import TTFont
from merge_fonts import merge_fonts
from .proportional import make_proportional


# ---------------------------------------------------------------------------
# Family / weight matrix
# ---------------------------------------------------------------------------

# (output_weight, weight_name, noto_wght_axis_value)
#
# The third column is the wght-axis location used to instantiate Noto Sans JP.
# Inter's discrete static masters happen to live at the round 100/200/.../800
# positions, but Noto's variable axis is non-linear: pulling the axis at 400
# yields a CJK weight that visually reads lighter than Inter Regular. The
# values below were tuned by eye-matching CJK stem density to each Inter
# master, hence the off-grid numbers (e.g. 465 for Regular, 800 for Bold).
WEIGHTS = [
    (100, "Thin",       100),
    (200, "ExtraLight",  260),
    (300, "Light",       355),
    (400, "Regular",     465),
    (500, "Medium",      575),
    (600, "SemiBold",    690),
    (700, "Bold",        800),
    (800, "ExtraBold",   900),
]

FAMILIES = {
    "normal": {
        "familyName": "Gen Interface JP",
        "interPrefix": "Inter",
        "tracking": 30,
        "trackingKana": 40,
        "halfPaltPunct": True,
        "folderPrefix": "GenInterfaceJP",
    },
    "display": {
        "familyName": "Gen Interface JP Display",
        "interPrefix": "InterDisplay",
        "tracking": 0,
        "trackingKana": 0,
        "halfPaltPunct": True,
        "folderPrefix": "GenInterfaceJPDisplay",
    },
}

# ---------------------------------------------------------------------------
# Filesystem layout
# ---------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENDOR_FONTS = os.path.join(ROOT, "vendor", "fonts")
INTER_DIR = os.path.join(VENDOR_FONTS, "Inter-4.1", "extras", "ttf")
NOTO_VARIABLE = os.path.join(VENDOR_FONTS, "Noto_Sans_JP", "NotoSansJP-VariableFont_wght.ttf")
DIST = os.path.join(ROOT, "dist")
DIST_TTF = os.path.join(DIST, "ttf")
INTERMEDIATE = os.path.join(DIST, "intermediate")

# Vertical alignment between Inter and Noto.
#
# When the merged font hands its baseline to Inter (`metricsSource: "sub"`),
# Noto sits a touch low — its CJK ideographs visually rest below the Latin
# x-height baseline. BASELINE_OFFSET nudges every Noto glyph up by 25 units
# so capitals and ideographs share an optical baseline. SCALE shrinks Noto
# to ~92.5% so a CJK character lines up in width with the cap-height of
# Inter at the same nominal point size — a typographic convention for
# Latin/CJK pairing where CJK is slightly down-scaled to feel proportionate.
BASELINE_OFFSET = 25
SCALE = 0.925


# ---------------------------------------------------------------------------
# Variable-font palt cache
# ---------------------------------------------------------------------------

_variable_palt_cache: dict | None = None


def _get_variable_palt() -> dict[str, tuple[int, int]]:
    """Read palt adjustments from the original Noto variable font (cached).

    The variable font's palt values are used as the source of truth across
    all weights instead of reading palt from each statically-instantiated
    inst.ttf. Reason: variable-font instantiation can quietly corrupt
    GPOS ValueRecords at non-default axis positions (some XPlacement /
    XAdvance pairs end up zeroed or shifted). The variable font itself
    carries the canonical palt definition, so we read it once and reuse.
    """
    global _variable_palt_cache
    if _variable_palt_cache is None:
        from .proportional import _read_palt

        font = TTFont(NOTO_VARIABLE)
        _variable_palt_cache = _read_palt(font)
    return _variable_palt_cache


# ---------------------------------------------------------------------------
# Glyph classification (codepoint-driven)
# ---------------------------------------------------------------------------

def _glyph_codepoint(glyph_name: str) -> int | None:
    """Parse the codepoint from an Adobe-style 'uniXXXX' glyph name.

    Glyph names that don't follow the convention return None. The check is
    deliberately tolerant: any prefix matching ``uni<4 hex>`` parses, even
    if extra characters follow (Noto sometimes ships names like
    ``uni3042.alt`` which we still treat as U+3042). Names lacking the
    ``uni`` prefix or with non-hex characters return None — those glyphs
    are excluded from kana/CJK classification rather than misclassified.
    """
    if not glyph_name.startswith("uni"):
        return None
    try:
        return int(glyph_name[3:7], 16)
    except (ValueError, IndexError):
        return None


def _is_kana_or_punct(glyph_name: str) -> bool:
    """Return True for hiragana, katakana, or CJK punctuation glyphs.

    Used by tracking to apply a separate (usually larger) tracking value
    to kana and punctuation, since they read at a wider rhythm than Latin
    when set at the same nominal size.
    """
    cp = _glyph_codepoint(glyph_name)
    if cp is None:
        return False
    return (
        0x3000 <= cp <= 0x303F    # CJK Symbols and Punctuation (。、・「」…)
        or 0x3040 <= cp <= 0x309F  # Hiragana
        or 0x30A0 <= cp <= 0x30FF  # Katakana
        or 0x31F0 <= cp <= 0x31FF  # Katakana Phonetic Extensions
        or 0xFF00 <= cp <= 0xFFEF  # Halfwidth and Fullwidth Forms
    )


# ---------------------------------------------------------------------------
# GSUB feature inspection
# ---------------------------------------------------------------------------

def _get_vert_alternates(font: TTFont) -> set[str]:
    """Return glyph names that appear as targets of ``vert`` / ``vrt2`` lookups.

    These are the rotated / vertical-form variants the OpenType engine picks
    up when set with vertical writing mode. We collect them so the proportional
    pass and the bbox-strip pass can avoid touching them: vertical-only glyphs
    don't contribute to the horizontal rhythm we're tuning, and rewriting
    their metrics would mismatch what the unrotated original expects.

    Only single-substitution lookups are walked (``hasattr(st, "mapping")``).
    Vertical lookups in Noto are exclusively single-subs in practice.
    """
    gsub = font.get("GSUB")
    if gsub is None or gsub.table is None or gsub.table.FeatureList is None:
        return set()
    alts = set()
    for fr in gsub.table.FeatureList.FeatureRecord:
        if fr.FeatureTag in ("vert", "vrt2"):
            for li in fr.Feature.LookupListIndex:
                lookup = gsub.table.LookupList.Lookup[li]
                for st in lookup.SubTable:
                    if hasattr(st, "mapping"):
                        alts.update(st.mapping.values())
    return alts


# ---------------------------------------------------------------------------
# CJK / kana classification
# ---------------------------------------------------------------------------

def _is_cjk_codepoint(cp: int) -> bool:
    """Return True for CJK ideograph / radical / compatibility ranges.

    These are the glyphs we keep at full-width metrics — palt's narrowing
    is for kana/punctuation rhythm, but a Han ideograph squeezed below
    full-width loses its grid alignment with surrounding kanji. The block
    list mirrors what Adobe and Google Noto treat as "ideographic" for
    the purposes of full-width preservation.
    """
    return (
        0x2E80 <= cp <= 0x2EFF      # CJK Radicals Supplement
        or 0x2F00 <= cp <= 0x2FDF   # Kangxi Radicals
        or 0x3020 <= cp <= 0x3029   # Hangzhou-style numerals (〇〡〢…)
        or 0x3038 <= cp <= 0x303B   # CJK Symbols: 〸〹〺〻
        or 0x3100 <= cp <= 0x312F   # Bopomofo
        or 0x3130 <= cp <= 0x318F   # Hangul Compatibility Jamo
        or 0x3190 <= cp <= 0x319F   # Kanbun
        or 0x31A0 <= cp <= 0x31EF   # Bopomofo Extended + CJK Strokes
        or 0x3200 <= cp <= 0x32FF   # Enclosed CJK Letters and Months
        or 0x3300 <= cp <= 0x33FF   # CJK Compatibility
        or 0x3400 <= cp <= 0x4DBF   # CJK Unified Ideographs Extension A
        or 0x4E00 <= cp <= 0x9FFF   # CJK Unified Ideographs
        or 0xF900 <= cp <= 0xFAFF   # CJK Compatibility Ideographs
        or 0x20000 <= cp <= 0x2FA1F  # CJK Extensions B-F + Supplements
    )


def _get_cjk_glyphs(font: TTFont) -> set[str]:
    """Resolve CJK ideograph glyph names through the font's cmap.

    cmap-driven lookup (rather than glyph-name parsing) catches ideographs
    whose names don't follow ``uniXXXX`` — Noto ships some Han glyphs as
    ``cidNNNNN`` or post-substitution names that wouldn't match a
    ``uni``-prefix check.
    """
    cmap = font.getBestCmap()
    if cmap is None:
        return set()
    return {gname for cp, gname in cmap.items() if _is_cjk_codepoint(cp)}


def _is_kana_letter(glyph_name: str) -> bool:
    """Return True for hiragana / katakana *letters*, excluding punctuation.

    Stricter than :func:`_is_kana_or_punct`: the kana proportional pass
    keeps full palt shrink on letters (where palt's optical kerning is
    designed to apply) and applies a reduced palt to punctuation.
    Notable exclusion: U+30FB (・) is punctuation, not a letter.
    """
    cp = _glyph_codepoint(glyph_name)
    if cp is None:
        return False
    return (
        0x3041 <= cp <= 0x3096    # Hiragana letters (ぁ-ゖ)
        or 0x3099 <= cp <= 0x309F  # Hiragana combining/iteration marks
        or 0x30A1 <= cp <= 0x30FA  # Katakana letters (ァ-ヺ), excludes ・(30FB)
        or 0x30FC <= cp <= 0x30FF  # Katakana prolonged sound / iteration marks
        or 0x31F0 <= cp <= 0x31FF  # Katakana Phonetic Extensions
    )


# ---------------------------------------------------------------------------
# Horizontal scale (長体 / condensed)
# ---------------------------------------------------------------------------

def _apply_x_scale(font: TTFont, scale: float) -> None:
    """Apply a horizontal-only scale (長体) to glyphs, hmtx, and GPOS.

    font-baker only supports uniform scale during merge, so condensing CJK
    relative to Latin has to happen *before* the merge step on the base
    font. This function squeezes Noto in x only — y stays untouched —
    then font-baker's uniform scale on top preserves the modified x:y
    ratio. GPOS X values (kerning, mark positioning) are scaled to match
    so kerning pairs continue to land where the design intends.
    """
    if scale == 1.0:
        return

    # Scale glyf coordinates and bbox.
    glyf = font["glyf"]
    for gname in font.getGlyphOrder():
        g = glyf[gname]
        if g.isComposite():
            for component in g.components:
                component.x = round(component.x * scale)
        elif g.numberOfContours > 0:
            coords = g.coordinates
            for i in range(len(coords)):
                x, y = coords[i]
                coords[i] = (round(x * scale), y)
            if hasattr(g, "xMin") and g.xMin is not None:
                g.xMin = round(g.xMin * scale)
                g.xMax = round(g.xMax * scale)

    # Scale advance widths and LSBs.
    hmtx = font["hmtx"]
    for gname in list(hmtx.metrics.keys()):
        aw, lsb = hmtx.metrics[gname]
        hmtx.metrics[gname] = (round(aw * scale), round(lsb * scale))

    # Scale GPOS X values (kerning, mark positioning, etc.).
    gpos = font.get("GPOS")
    if gpos is not None and gpos.table and gpos.table.LookupList:
        for lookup in gpos.table.LookupList.Lookup:
            for st in lookup.SubTable:
                _scale_gpos_x(st, scale)


def _scale_gpos_x(st, scale: float) -> None:
    """Scale every X-direction value in a GPOS subtable in place.

    Walks SinglePos (type 1), PairPos formats 1 and 2 (type 2), and the
    mark-anchor families (MarkArray / Mark1Array / Mark2Array, BaseArray).
    Subtable types not listed here — cursive attachment (type 3),
    contextual positioning (types 7 / 8), Extension (type 9 — handled by
    the caller via subtable unwrapping) — are not used by Noto Sans JP
    in any consequential way for our pipeline, so this targeted walk
    suffices.
    """
    def scale_value_record(vr):
        if vr is None:
            return
        if getattr(vr, "XPlacement", None) is not None:
            vr.XPlacement = round(vr.XPlacement * scale)
        if getattr(vr, "XAdvance", None) is not None:
            vr.XAdvance = round(vr.XAdvance * scale)

    def scale_anchor(anchor):
        if anchor is not None and hasattr(anchor, "XCoordinate"):
            anchor.XCoordinate = round(anchor.XCoordinate * scale)

    # SinglePos (type 1)
    if hasattr(st, "Value"):
        v = st.Value
        if isinstance(v, list):
            for vr in v:
                scale_value_record(vr)
        else:
            scale_value_record(v)

    # PairPos format 1
    if hasattr(st, "PairSet") and st.PairSet:
        for ps in st.PairSet:
            for pvr in ps.PairValueRecord:
                scale_value_record(pvr.Value1)
                scale_value_record(pvr.Value2)

    # PairPos format 2
    if hasattr(st, "Class1Record") and st.Class1Record:
        for c1r in st.Class1Record:
            for c2r in c1r.Class2Record:
                scale_value_record(c2r.Value1)
                scale_value_record(c2r.Value2)

    # Mark anchors (MarkArray, BaseArray, LigatureArray)
    for attr in ("MarkArray", "Mark1Array", "Mark2Array"):
        ma = getattr(st, attr, None)
        if ma and hasattr(ma, "MarkRecord"):
            for mr in ma.MarkRecord:
                scale_anchor(mr.MarkAnchor)
    for attr in ("BaseArray",):
        ba = getattr(st, attr, None)
        if ba and hasattr(ba, "BaseRecord"):
            for br in ba.BaseRecord:
                for anchor in br.BaseAnchor or []:
                    scale_anchor(anchor)


# ---------------------------------------------------------------------------
# Bbox / head-table cleanup
# ---------------------------------------------------------------------------

# Threshold for "extreme" glyphs whose bbox dominates head.yMax/yMin.
# em=1000 base; the legitimate Latin/CJK content of Noto stays well within
# these bounds, so anything past them is the vertical-only iteration-mark
# glyphs we want to neutralise.
_EXTREME_YMAX = 1200
_EXTREME_YMIN = -400


def _strip_extreme_glyphs(font: TTFont) -> None:
    """Neutralise glyphs whose bbox extends far beyond the em-square.

    Targets vertical-text-only glyphs (kana iteration marks 〱〲 and their
    vert/vrt2 alternates) that inflate head.yMax/yMin. Illustrator's text
    frame auto-sizing reads head bbox, so these outliers force frames to
    open with several extra hundred units of vertical padding even on a
    short string of plain Latin. Acceptable trade-off for a horizontal-only
    UI font: vertical typesetting is out of scope (see CLAUDE.md).

    Removing the glyph slots outright would shift every later index in
    GSUB / GPOS lookups. Instead we keep the slot in place and only
    replace the outline with an empty Glyph — the bbox no longer
    contributes to head, and dropping the cmap entry makes the
    codepoint fall through to .notdef when typed.
    """
    from fontTools.ttLib.tables._g_l_y_f import Glyph

    glyf = font["glyf"]
    hmtx = font["hmtx"]
    to_remove = set()
    for gname in font.getGlyphOrder():
        g = glyf[gname]
        if g.numberOfContours == 0:
            continue
        if not hasattr(g, "yMax") or g.yMax is None:
            continue
        if g.yMax > _EXTREME_YMAX or g.yMin < _EXTREME_YMIN:
            to_remove.add(gname)

    if not to_remove:
        return

    # Replace each target glyph with an empty outline.
    for gname in to_remove:
        empty = Glyph()
        empty.numberOfContours = 0
        empty.xMin = empty.yMin = empty.xMax = empty.yMax = 0
        glyf[gname] = empty
        if gname in hmtx.metrics:
            hmtx.metrics[gname] = (0, 0)

    # Drop cmap entries so typing these codepoints falls through to .notdef.
    for table in font["cmap"].tables:
        table.cmap = {cp: g for cp, g in table.cmap.items() if g not in to_remove}

    # Tidy GSUB: remove single-substitution mappings touching these glyphs.
    gsub = font.get("GSUB")
    if gsub is not None and gsub.table and gsub.table.LookupList:
        for lookup in gsub.table.LookupList.Lookup:
            for st in lookup.SubTable:
                if hasattr(st, "mapping"):
                    st.mapping = {
                        k: v for k, v in st.mapping.items()
                        if k not in to_remove and v not in to_remove
                    }


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------

def _apply_tracking(font: TTFont, tracking: int, tracking_kana: int | None = None) -> None:
    """Widen every glyph's advance width and split the gap evenly L/R.

    Adding tracking to a glyph means growing its advance by ``t`` and
    nudging the LSB by ``t // 2`` so that the same outline sits centred
    in the new wider slot — half the new whitespace ends up on the left
    sidebearing, the other half on the right. This matches how design
    apps interpret tracking in Latin typography, applied per-glyph
    rather than as a global text-engine setting.

    Zero-width glyphs (combining marks, mark-positioning anchors) are
    skipped so they keep their placement-only role intact.

    When *tracking_kana* is set, hiragana / katakana / punctuation glyphs
    receive that value instead of *tracking*. The Gen Interface JP
    families use this to give kana and punctuation a slightly looser
    rhythm than Latin — kana need more breathing room at small sizes
    to remain legible against the denser Han ideographs.
    """
    hmtx = font["hmtx"]
    for glyph_name in font.getGlyphOrder():
        aw, lsb = hmtx[glyph_name]
        if aw == 0:
            continue
        t = tracking
        if tracking_kana is not None and _is_kana_or_punct(glyph_name):
            t = tracking_kana
        half = t // 2
        hmtx[glyph_name] = (aw + t, lsb + half)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def build_one(family: dict, weight_num: int, weight_name: str, noto_wght: int) -> dict:
    """Build a single weight of a Gen Interface JP family.

    Three-stage pipeline:

    1. **Bake** Noto variable → static TTF at the chosen wght axis location,
       passed through font-baker with ``metadataMode: inheritBase`` so the
       Noto identity records survive into the inst.
    2. **Proportionalise** the inst — read palt from the variable cache
       (variable instantiation can corrupt palt), bake those adjustments
       into hmtx, apply tracking, strip extreme bbox glyphs, optionally
       apply x-scale.
    3. **Merge** the proportional Noto with the matching Inter master via
       font-baker. Output identity is rewritten to "Gen Interface JP",
       Inter's vertical metrics drive the merged hhea (``metricsSource: "sub"``),
       and our manufacturer / URL get stamped into nameID 8 / 11.
    """
    inter_path = os.path.join(INTER_DIR, f"{family['interPrefix']}-{weight_name}.ttf")
    if not os.path.isfile(inter_path):
        raise FileNotFoundError(f"Inter font not found: {inter_path}")

    os.makedirs(INTERMEDIATE, exist_ok=True)

    inst_path = os.path.join(INTERMEDIATE, f"NotoSansJP-{weight_name}-Inst.ttf")
    prop_path = os.path.join(INTERMEDIATE, f"NotoSansJP-{weight_name}-Prop.ttf")

    # ── Step 1: Bake Noto variable → static (font-baker, base-only) ──
    # `metadataMode: inheritBase` keeps Noto's name/OS2 records intact so
    # designer/OFL/version metadata survives into the inst TTF (no manual
    # save/restore needed). Only `weight` is overridden to stamp the static
    # instance — family/italic/width inherit from the Noto base.
    print(f"    [1/3] Baking Noto Sans JP (wght={noto_wght})...")
    bake_config = {
        "baseFont": {
            "path": NOTO_VARIABLE,
            "scale": 1.0,
            "baselineOffset": 0,
            "axes": [{"tag": "wght", "currentValue": noto_wght}],
        },
        "output": {
            "weight": weight_num,
            "metadataMode": "inheritBase",
        },
        "export": {
            "path": {
                "font": inst_path,
            },
        },
    }
    merge_fonts(bake_config)

    # ── Step 2: Convert to proportional + apply tracking ──
    tracking = family["tracking"]
    tracking_kana = family["trackingKana"]
    half_palt_punct = family.get("halfPaltPunct", False)

    desc = f"tracking +{tracking}"
    if tracking_kana is not None:
        desc += f" (kana/punct +{tracking_kana})"
    if half_palt_punct:
        desc += " (punct half-palt)"
    print(f"    [2/3] Proportional (palt) + {desc}...")

    font = TTFont(inst_path)

    # Read palt from the variable source rather than the freshly-baked inst:
    # variable instantiation can leave palt ValueRecords with zeroed or
    # otherwise stale XPlacement/XAdvance pairs. The cached variable read
    # is canonical across all weights.
    palt_data = _get_variable_palt()

    # Three-bucket policy for proportional metrics, only active when
    # ``halfPaltPunct`` is set on the family:
    #   - kana letters: keep the full palt shrink (unchanged below)
    #   - reduced_palt: glyphs that have palt entries but aren't kana
    #     letters — typically punctuation. These get a fraction of the
    #     full palt shift so punctuation doesn't pull as tight as kana.
    #   - squeeze_sb: glyphs without palt at all — non-kana, non-CJK,
    #     non-vertical. We squeeze their sidebearings by the same ratio
    #     so the rhythm stays consistent across the whole font.
    # CJK ideographs and vertical-only glyphs are excluded from both
    # buckets — they keep full-width metrics (see CLAUDE.md).
    reduced_palt_glyphs = None
    squeeze_sb_glyphs = None
    if half_palt_punct:
        palt_glyphs = set(palt_data.keys())
        vert_glyphs = _get_vert_alternates(font)
        cjk_glyphs = _get_cjk_glyphs(font)
        exclude = vert_glyphs | cjk_glyphs
        reduced_palt_glyphs = {
            g for g in palt_glyphs
            if not _is_kana_letter(g) and g not in exclude
        }
        squeeze_sb_glyphs = {
            g for g in font.getGlyphOrder()
            if g not in palt_glyphs
            and g not in exclude
            and not _is_kana_letter(g)
        }

    make_proportional(
        font,
        reduced_palt=reduced_palt_glyphs,
        squeeze_sb=squeeze_sb_glyphs,
        palt_override=palt_data,
    )
    _apply_tracking(font, tracking, tracking_kana)
    _strip_extreme_glyphs(font)
    x_scale = family.get("xScale", 1.0)
    if x_scale != 1.0:
        _apply_x_scale(font, x_scale)
    font.save(prop_path)

    # ── Step 3: Merge Inter + proportional Noto ──
    family_name = family["familyName"]
    file_name = f"{family['folderPrefix']}-{weight_name}"
    ttf_dir = os.path.join(DIST_TTF, family_name)
    print(f"    [3/3] Merging {family['interPrefix']} + proportional Noto...")
    merge_config = {
        "subFont": {
            "path": inter_path,
            "scale": 1.0,
            "baselineOffset": 0,
            "axes": [],
        },
        "baseFont": {
            "path": prop_path,
            "scale": SCALE,
            "baselineOffset": BASELINE_OFFSET,
            "axes": [],
        },
        "output": {
            "familyName": family_name,
            "weight": weight_num,
            "italic": False,
            "width": 5,
            "metricsSource": "sub",
            "manufacturer": "Yamato Iizuka",
            "manufacturerURL": "https://yamatoiizuka.com",
        },
        "export": {
            "path": {
                "font": os.path.join(ttf_dir, f"{file_name}.ttf"),
            },
        },
    }
    merge_fonts(merge_config)
    return {
        "fontPath": os.path.join(ttf_dir, f"{file_name}.ttf"),
    }


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main():
    """Drive the family/weight matrix from argv.

    Usage::

        python -m font.build                       # everything
        python -m font.build normal                # all weights of one family
        python -m font.build normal Regular Bold   # a slice
        python -m font.build all 400 700           # by weight, both families

    Argument parsing is positional and lenient: the first arg can be a
    family key (``normal`` / ``display`` / ``all``) or a weight; remaining
    args are always treated as weight filters. Weight filters match
    either by name (``Regular``) or by usWeightClass (``400``).
    """
    os.makedirs(DIST_TTF, exist_ok=True)

    # Parse arguments: [family] [weight ...]
    # family: normal, display, all (default: all)
    args = sys.argv[1:]

    families_to_build = list(FAMILIES.keys())
    weights_to_build = WEIGHTS

    if args:
        # First arg might be a family name
        first = args[0].lower()
        if first in FAMILIES or first == "all":
            if first != "all":
                families_to_build = [first]
            args = args[1:]

        # Remaining args are weight filters
        if args:
            requested = {s.strip() for s in args}
            weights_to_build = [
                (n, name, nw) for n, name, nw in WEIGHTS
                if name in requested or str(n) in requested
            ]
            if not weights_to_build:
                print(f"No matching weights. Available: {[n for _, n, _ in WEIGHTS]}")
                sys.exit(1)

    for family_key in families_to_build:
        family = FAMILIES[family_key]
        family_name = family["familyName"]
        total = len(weights_to_build)
        print(f"\n{'='*60}")
        print(f"  {family_name}  (tracking +{family['tracking']})")
        print(f"{'='*60}")

        for i, (weight_num, weight_name, noto_wght) in enumerate(weights_to_build, 1):
            print(f"\n[{i}/{total}] {family_name} {weight_name} ({weight_num})...")
            manifest = build_one(family, weight_num, weight_name, noto_wght)
            print(f"  -> {manifest['fontPath']}")

        print(f"\n  Done. {total} weight(s) of {family_name}")

    print(f"\nAll done. Output in {DIST_TTF}")


if __name__ == "__main__":
    main()
