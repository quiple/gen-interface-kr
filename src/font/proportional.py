#!/usr/bin/env python3
"""
Convert a CJK font to proportional metrics using its palt GPOS feature.

CJK fonts ship with full-width metrics by default — every glyph occupies
the same em-square box regardless of its actual outline width — and rely
on the GPOS ``palt`` feature to optically narrow kana, punctuation, and
Latin-in-CJK glyphs at runtime. Apps that don't enable ``palt`` (Adobe's
Japanese composer, browser fallbacks, anything that treats CJK as
monospaced for layout) miss those adjustments and lay the text out at
full-width spacing.

This module bakes ``palt`` into the static hmtx so the font reads as
proportional everywhere, then removes the now-redundant ``palt``/``vpal``/
``halt``/``vhal`` features to prevent apps that *do* honor them from
double-applying. Glyphs not covered by ``palt`` keep their original
metrics — nothing is forced.

Usage:
    python3 -m font.proportional INPUT.ttf OUTPUT.ttf
"""

from __future__ import annotations

import sys

from fontTools.ttLib import TTFont

# GPOS features that provide proportional metric adjustments.
# These become redundant once the font itself is proportional, so we strip
# them to keep apps from double-applying the shrink.
#   palt  - proportional alternate widths (horizontal)
#   vpal  - proportional alternate widths (vertical)
#   halt  - alternate metrics (horizontal, ½-width / pseudo-half)
#   vhal  - alternate metrics (vertical)
PROP_FEATURES = {"palt", "vpal", "halt", "vhal"}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def make_proportional(
    font: TTFont,
    reduced_palt: set[str] | None = None,
    reduced_palt_scale: float = 1 / 3,
    squeeze_sb: set[str] | None = None,
    squeeze_sb_scale: float | None = None,
    palt_override: dict[str, tuple[int, int]] | None = None,
) -> None:
    """Bake palt adjustments into hmtx in place, then strip prop features.

    Three groups of glyphs:

    - **Full palt**: glyphs in ``palt_adjustments`` that aren't called out in
      ``reduced_palt``. The XPlacement / XAdvance from palt is applied at
      full strength — outline shifts left by XPlacement, advance grows
      by XAdvance (negative = narrower).
    - **Reduced palt** (``reduced_palt``): same glyphs as palt but the
      adjustment is scaled by ``reduced_palt_scale`` (default 1/3).
      Used in this project for punctuation, where full palt feels too
      tight when set against kana that already shrank.
    - **Squeeze SB** (``squeeze_sb``): glyphs *without* palt entries that
      should still narrow proportionally. Their LSB and RSB each shrink
      by ``(1 - squeeze_sb_scale)`` so the rhythm of the squeeze stays
      consistent with reduced-palt punctuation.

    ``palt_override`` lets the caller supply palt values from elsewhere
    (e.g. the variable-font source) when the font's own GPOS palt has
    been corrupted by variable instantiation. Variable→static baking can
    leave palt ValueRecords with zeroed XPlacement/XAdvance pairs.

    Only TrueType-outlined fonts are supported — palt baking writes back
    to ``glyf``, not to CFF.
    """
    if "glyf" not in font:
        raise ValueError("Only TrueType-outline fonts are supported")

    if squeeze_sb_scale is None:
        squeeze_sb_scale = reduced_palt_scale

    # Extract palt adjustments before removing features
    palt_adjustments = palt_override if palt_override is not None else _read_palt(font)

    glyf = font["glyf"]
    hmtx = font["hmtx"]

    # ── Apply palt adjustments ──
    for glyph_name, (x_placement, x_advance) in palt_adjustments.items():
        if glyph_name not in hmtx.metrics:
            continue

        # Reduced palt: apply a fraction of the adjustment
        if reduced_palt and glyph_name in reduced_palt:
            x_placement = round(x_placement * reduced_palt_scale)
            x_advance = round(x_advance * reduced_palt_scale)

        aw, lsb = hmtx[glyph_name]

        # x_placement: shift the glyph origin (negative = shift left)
        # x_advance: adjust the advance width (negative = narrower)
        new_lsb = lsb + x_placement
        new_aw = aw + x_advance

        # Shift outlines by x_placement
        if x_placement != 0 and glyph_name in glyf:
            glyph = glyf[glyph_name]
            if glyph.numberOfContours != 0 and hasattr(glyph, "xMin") and glyph.xMin is not None:
                _shift_glyph_x(glyph, x_placement)

        hmtx[glyph_name] = (new_aw, new_lsb)

    # ── Squeeze sidebearings for non-palt glyphs ──
    if squeeze_sb:
        for glyph_name in squeeze_sb:
            if glyph_name in palt_adjustments:
                continue  # already handled above
            if glyph_name not in hmtx.metrics:
                continue
            if glyph_name not in glyf:
                continue

            glyph = glyf[glyph_name]
            if glyph.numberOfContours == 0:
                continue
            if not hasattr(glyph, "xMin") or glyph.xMin is None:
                continue

            aw, lsb = hmtx[glyph_name]
            bbox_w = glyph.xMax - glyph.xMin
            rsb = aw - lsb - bbox_w

            # How much to remove: (1 - scale) of each sidebearing
            cut = 1 - squeeze_sb_scale
            lsb_remove = round(lsb * cut)
            rsb_remove = round(rsb * cut)

            if lsb_remove == 0 and rsb_remove == 0:
                continue

            # Shift outlines left by lsb_remove
            if lsb_remove != 0:
                _shift_glyph_x(glyph, -lsb_remove)

            new_lsb = lsb - lsb_remove
            new_aw = aw - lsb_remove - rsb_remove
            hmtx[glyph_name] = (new_aw, new_lsb)

    # Remove proportional-metric GPOS features
    _remove_prop_features(font)


# ---------------------------------------------------------------------------
# GPOS palt extraction
# ---------------------------------------------------------------------------

def _read_palt(font: TTFont) -> dict[str, tuple[int, int]]:
    """Walk GPOS palt lookups and return ``{glyph_name: (XPlacement, XAdvance)}``.

    Handles SinglePos formats 1 (one ValueRecord shared by all glyphs in the
    coverage) and 2 (one ValueRecord per glyph), and unwraps Extension
    lookups (type 9). Other lookup types (PairPos, contextual) don't appear
    in real-world palt features so they're skipped silently.

    Missing GPOS, missing FeatureList, or no palt records all return an
    empty dict — callers treat the absence of palt as "leave hmtx alone".
    """
    gpos = font.get("GPOS")
    if gpos is None or gpos.table is None:
        return {}
    if gpos.table.FeatureList is None:
        return {}

    # Find palt feature
    palt_lookup_indices = []
    for fr in gpos.table.FeatureList.FeatureRecord:
        if fr.FeatureTag == "palt":
            palt_lookup_indices.extend(fr.Feature.LookupListIndex)

    if not palt_lookup_indices:
        return {}

    adjustments: dict[str, tuple[int, int]] = {}

    for li in palt_lookup_indices:
        lookup = gpos.table.LookupList.Lookup[li]
        lookup_type = lookup.LookupType

        subtables = lookup.SubTable
        # Unwrap Extension lookups (type 9)
        if lookup_type == 9:
            subtables = [st.ExtSubTable for st in subtables]

        for subtable in subtables:
            glyphs = subtable.Coverage.glyphs
            for j, glyph_name in enumerate(glyphs):
                if subtable.Format == 1:
                    # Format 1: single ValueRecord for all glyphs
                    v = subtable.Value
                elif subtable.Format == 2:
                    # Format 2: array of ValueRecords
                    v = subtable.Value[j]
                else:
                    continue

                xp = getattr(v, "XPlacement", 0) or 0
                xa = getattr(v, "XAdvance", 0) or 0
                adjustments[glyph_name] = (xp, xa)

    return adjustments


# ---------------------------------------------------------------------------
# Glyph mutation helpers
# ---------------------------------------------------------------------------

def _shift_glyph_x(glyph, dx: int) -> None:
    """Translate a TrueType glyph horizontally by ``dx`` in place.

    Composite glyphs are shifted by adjusting each component's anchor
    offset rather than recursing into the referenced glyph — that keeps
    the underlying base glyph shareable with other composites and avoids
    double-shifting when both a base and a composite-of-base appear in
    the same call sequence.

    The bounding box (xMin / xMax) is updated to match. yMin/yMax are
    unaffected — this is x-only.
    """
    if glyph.isComposite():
        for component in glyph.components:
            component.x += dx
    else:
        coords = glyph.coordinates
        for i in range(len(coords)):
            x, y = coords[i]
            coords[i] = (x + dx, y)

    # Update bounding box
    glyph.xMin += dx
    glyph.xMax += dx


# ---------------------------------------------------------------------------
# GPOS feature removal
# ---------------------------------------------------------------------------

def _remove_prop_features(font: TTFont) -> None:
    """Strip palt/vpal/halt/vhal from GPOS, keeping every other feature intact.

    GPOS feature indices live in two places that must stay in sync:
    the FeatureRecord list itself (the data) and the FeatureIndex arrays
    inside every LangSys (the references). Removing a record changes the
    indices of every later record, so the LangSys references need to be
    remapped — the helpers ``_filter_feature_indices`` and
    ``_remap_feature_indices`` handle the two halves of that update.

    Lookup tables aren't touched: the lookups behind palt may also be
    referenced by other features we want to keep, and orphaned lookups
    are harmless. fontTools will write them out unchanged.
    """
    gpos = font.get("GPOS")
    if gpos is None or gpos.table is None:
        return
    if gpos.table.FeatureList is None:
        return

    feature_list = gpos.table.FeatureList
    records = feature_list.FeatureRecord

    # Find indices of features to remove
    indices_to_remove = set()
    for i, fr in enumerate(records):
        if fr.FeatureTag in PROP_FEATURES:
            indices_to_remove.add(i)

    if not indices_to_remove:
        return

    # Remove from ScriptList references
    if gpos.table.ScriptList:
        for script_record in gpos.table.ScriptList.ScriptRecord:
            script = script_record.Script
            if script.DefaultLangSys:
                _filter_feature_indices(script.DefaultLangSys, indices_to_remove)
            if script.LangSysRecord:
                for lsr in script.LangSysRecord:
                    _filter_feature_indices(lsr.LangSys, indices_to_remove)

    # Build index remapping (old → new) for kept features
    kept = sorted(set(range(len(records))) - indices_to_remove)
    remap = {old: new for new, old in enumerate(kept)}

    # Rebuild FeatureRecord list
    feature_list.FeatureRecord = [records[i] for i in kept]
    feature_list.FeatureCount = len(feature_list.FeatureRecord)

    # Remap all feature indices in ScriptList
    if gpos.table.ScriptList:
        for script_record in gpos.table.ScriptList.ScriptRecord:
            script = script_record.Script
            if script.DefaultLangSys:
                _remap_feature_indices(script.DefaultLangSys, remap)
            if script.LangSysRecord:
                for lsr in script.LangSysRecord:
                    _remap_feature_indices(lsr.LangSys, remap)


def _filter_feature_indices(langsys, indices_to_remove: set) -> None:
    """Remove feature indices from a LangSys."""
    if langsys.FeatureIndex:
        langsys.FeatureIndex = [
            i for i in langsys.FeatureIndex if i not in indices_to_remove
        ]
        langsys.FeatureCount = len(langsys.FeatureIndex)


def _remap_feature_indices(langsys, remap: dict) -> None:
    """Remap feature indices in a LangSys after removal."""
    if langsys.FeatureIndex:
        langsys.FeatureIndex = [
            remap[i] for i in langsys.FeatureIndex if i in remap
        ]
        langsys.FeatureCount = len(langsys.FeatureIndex)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} INPUT.ttf OUTPUT.ttf")
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]

    font = TTFont(input_path)
    make_proportional(font)
    font.save(output_path)
    print(f"Proportional font saved to {output_path}")


if __name__ == "__main__":
    main()
