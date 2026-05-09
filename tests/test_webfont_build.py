"""Tests for the webfont subsetting plan + helpers in webfont/build.py.

The functions under test all run *before* the actual `fontTools.subset`
call: they decide which codepoints land in which slice, what the slice
files are named, and what `unicode-range:` declarations the CSS will
emit. A bug in any of these silently rewrites the public CSS surface —
file names that npm consumers reference (`400.css`), `unicode-range:`
guards that determine which WOFF2 chunk the browser fetches, and
non-overlap of slices (a codepoint living in two slices forces the
browser to download both chunks for one character).

The actual `fontTools.subset` call is not exercised here — that's
covered indirectly by the `make webfont` integration step, and unit-
testing fontTools' own behavior is out of scope.
"""

import pytest

from webfont.build import (
    build_google_korean_subset_plan,
    format_unicode_range,
    is_han_codepoint,
    merge_codepoints_to_ranges,
    parse_slicing_strategy,
    weight_css_filename,
)

# ---------------------------------------------------------------------------
# merge_codepoints_to_ranges
# ---------------------------------------------------------------------------

class TestMergeCodepointsToRanges:
    """Coalesce contiguous codepoints into (start, end) tuples."""

    def test_groups_contiguous_runs(self):
        assert merge_codepoints_to_ranges([0x41, 0x42, 0x44, 0x46, 0x47, 0x48]) == [
            (0x41, 0x42),
            (0x44, 0x44),
            (0x46, 0x48),
        ]

    def test_empty_input_returns_empty(self):
        assert merge_codepoints_to_ranges([]) == []

    def test_single_codepoint(self):
        assert merge_codepoints_to_ranges([0x3042]) == [(0x3042, 0x3042)]

    def test_unsorted_input_is_sorted_first(self):
        # Implementation sorts internally, so callers don't need to.
        assert merge_codepoints_to_ranges([0x43, 0x41, 0x42]) == [(0x41, 0x43)]

    def test_duplicates_are_deduped(self):
        # Internal `set()` collapses duplicates before range-merging.
        assert merge_codepoints_to_ranges([0x41, 0x41, 0x42]) == [(0x41, 0x42)]


# ---------------------------------------------------------------------------
# format_unicode_range
# ---------------------------------------------------------------------------

class TestFormatUnicodeRange:
    """Produce CSS `unicode-range:` value strings."""

    def test_mixed_singletons_and_ranges(self):
        assert format_unicode_range([0x20, 0x41, 0x42, 0x3042]) == "U+0020, U+0041-0042, U+3042"

    def test_empty_returns_empty_string(self):
        assert format_unicode_range([]) == ""

    def test_pads_to_4_hex_digits_minimum(self):
        # CSS spec accepts shorter hex but Google's published unicode-range
        # values use 4-digit minimum padding. Match for visual diff sanity.
        assert format_unicode_range([0x1, 0x20]) == "U+0001, U+0020"

    def test_5_digit_supplementary_codepoints(self):
        # Plane 2 CJK ideographs land in 5-digit hex; the formatter must
        # not clip to 4 digits.
        assert format_unicode_range([0x20000]) == "U+20000"

    def test_5_digit_range(self):
        assert format_unicode_range([0x20000, 0x20001, 0x20002]) == "U+20000-20002"


# ---------------------------------------------------------------------------
# weight_css_filename
# ---------------------------------------------------------------------------

class TestWeightCssFilename:
    """Public CSS file naming on the npm package root.

    These names are part of the published distribution contract: jsDelivr
    consumers reference `gen-interface-kr/400.css` and
    `gen-interface-kr/display-400.css` directly. Renaming here is a
    breaking change in the public CDN URL space.
    """

    def test_normal_family_uses_bare_weight(self):
        # `normal` is the default family — its CSS lives at the package
        # root with no family prefix, matching how Google Fonts CSS is
        # commonly imported (`gen-interface-kr/400.css`).
        assert weight_css_filename("normal", 400) == "400.css"

    def test_display_family_is_prefixed(self):
        assert weight_css_filename("display", 400) == "display-400.css"

    def test_unknown_family_falls_back_to_prefix(self):
        # Defensive: any future family key uses `{key}-{weight}.css`.
        assert weight_css_filename("mono", 700) == "mono-700.css"


# ---------------------------------------------------------------------------
# is_han_codepoint
# ---------------------------------------------------------------------------

class TestIsHanCodepoint:
    """Boundary check for the Han block list used by the JIS-row planner."""

    def test_main_block(self):
        assert is_han_codepoint(0x4E00)  # 一
        assert is_han_codepoint(0x9FFF)

    def test_extension_a(self):
        assert is_han_codepoint(0x3400)
        assert is_han_codepoint(0x4DBF)

    def test_extension_supplementary(self):
        assert is_han_codepoint(0x20000)
        assert is_han_codepoint(0x2FA1F)

    def test_compatibility(self):
        assert is_han_codepoint(0xF900)
        assert is_han_codepoint(0xFAFF)

    def test_kana_excluded(self):
        assert not is_han_codepoint(0x3042)  # あ
        assert not is_han_codepoint(0x30A2)  # ア

    def test_ascii_excluded(self):
        assert not is_han_codepoint(0x0041)




# ---------------------------------------------------------------------------
# parse_slicing_strategy
# ---------------------------------------------------------------------------

class TestParseSlicingStrategy:
    """Textproto-flavored parser for googlefonts/nam-files slicing strategy."""

    def test_basic_two_subset_block(self, tmp_path):
        strategy = tmp_path / "strategy.txt"
        strategy.write_text(
            """
            subsets {
              codepoints: 0x20 # SPACE
              codepoints: 12354 # あ
              codepoints: 0x65E5 # 日
            }
            subsets {
              codepoints: 0x4E00 # 一
            }
            """,
            encoding="utf-8",
        )
        assert parse_slicing_strategy(strategy) == [
            {0x20, 12354, 0x65E5},
            {0x4E00},
        ]

    def test_closing_brace_inside_comment_does_not_terminate_block(self, tmp_path):
        # The actual nam-files strategy has lines like
        # `codepoints: 0x7D # } RIGHT CURLY BRACKET`. Naive `.endswith("}")`
        # parsers terminate the block early. This is exactly the trap the
        # implementation's `line == "}"` (post-strip) check is built to
        # avoid; lock the behavior down so a future "simplification"
        # doesn't reintroduce the bug.
        strategy = tmp_path / "strategy.txt"
        strategy.write_text(
            """
            subsets {
              codepoints: 0x7D # } RIGHT CURLY BRACKET
              codepoints: 0x20
            }
            """,
            encoding="utf-8",
        )
        assert parse_slicing_strategy(strategy) == [{0x7D, 0x20}]

    def test_decimal_and_hex_codepoints_both_parse(self, tmp_path):
        strategy = tmp_path / "strategy.txt"
        strategy.write_text(
            "subsets {\n  codepoints: 0x20\n  codepoints: 65\n}\n",
            encoding="utf-8",
        )
        assert parse_slicing_strategy(strategy) == [{0x20, 65}]

    def test_unclosed_block_raises(self, tmp_path):
        strategy = tmp_path / "strategy.txt"
        strategy.write_text(
            "subsets {\n  codepoints: 0x20\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Unclosed"):
            parse_slicing_strategy(strategy)

    def test_nested_blocks_raise(self, tmp_path):
        strategy = tmp_path / "strategy.txt"
        strategy.write_text(
            "subsets {\n  subsets {\n    codepoints: 0x20\n  }\n}\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Nested"):
            parse_slicing_strategy(strategy)

    def test_empty_strategy_raises(self, tmp_path):
        # No subsets means we'd produce no @font-face rules — surface
        # as an error rather than silently emitting an empty CSS.
        strategy = tmp_path / "strategy.txt"
        strategy.write_text("# just a comment\n", encoding="utf-8")
        with pytest.raises(ValueError, match="No subsets"):
            parse_slicing_strategy(strategy)

    def test_empty_subset_blocks_are_dropped(self, tmp_path):
        # `subsets { }` with no codepoints is treated as absent so the
        # planner doesn't emit empty-range @font-face entries.
        strategy = tmp_path / "strategy.txt"
        strategy.write_text(
            "subsets {\n}\nsubsets {\n  codepoints: 0x20\n}\n",
            encoding="utf-8",
        )
        assert parse_slicing_strategy(strategy) == [{0x20}]


# ---------------------------------------------------------------------------
# build_google_korean_subset_plan
# ---------------------------------------------------------------------------

class TestGoogleKoreanSubsetPlan:
    """Replays Google Fonts' Korean slicing strategy against this font's cmap."""

    def _write_strategy(self, tmp_path, blocks):
        strategy = tmp_path / "strategy.txt"
        body = "\n".join(
            "subsets {\n" +
            "\n".join(f"  codepoints: {cp:#x}" for cp in block) +
            "\n}"
            for block in blocks
        )
        strategy.write_text(body, encoding="utf-8")
        return strategy

    def test_strategy_subsets_followed_by_extras(self, tmp_path):
        strategy = self._write_strategy(tmp_path, [
            [0x20, 0x3042],
            [0x4E00],
        ])
        plan = build_google_korean_subset_plan(
            {0x20, 0x3042, 0x4E00, 0x41},  # 0x41 not in strategy → extra
            slice_path=strategy,
            remaining_slices=1,
        )
        assert [item.name for item in plan] == [
            "google-korean-000",
            "google-korean-001",
            "google-korean-extra-00",
        ]
        assert [set(item.codepoints) for item in plan] == [
            {0x20, 0x3042},
            {0x4E00},
            {0x41},
        ]

    def test_codepoint_only_in_first_slice(self, tmp_path):
        # If a codepoint appears in two strategy blocks, only the FIRST
        # slice should claim it. This matches the priority order of
        # Google's strategy file — earlier blocks are higher priority.
        strategy = self._write_strategy(tmp_path, [
            [0x20, 0x3042],
            [0x3042, 0x4E00],
        ])
        plan = build_google_korean_subset_plan(
            {0x20, 0x3042, 0x4E00},
            slice_path=strategy,
            include_remaining=False,
        )
        first = set(plan[0].codepoints)
        second = set(plan[1].codepoints)
        assert 0x3042 in first
        assert 0x3042 not in second

    def test_include_remaining_false_skips_extras(self, tmp_path):
        strategy = self._write_strategy(tmp_path, [[0x20]])
        plan = build_google_korean_subset_plan(
            {0x20, 0x41, 0x42},
            slice_path=strategy,
            include_remaining=False,
        )
        # Only the strategy slice; the un-claimed Latin letters get dropped.
        assert [item.name for item in plan] == ["google-korean-000"]
        assert set(plan[0].codepoints) == {0x20}

    def test_empty_intersection_skips_slice(self, tmp_path):
        # If a strategy block has zero codepoints in this font, the
        # corresponding @font-face entry would be useless. Verify the
        # slice is dropped entirely (slices keep contiguous numbering
        # only among non-empty intersections).
        strategy = self._write_strategy(tmp_path, [
            [0x20],          # in font
            [0x99999],       # NOT in font — should drop
            [0x3042],        # in font
        ])
        plan = build_google_korean_subset_plan(
            {0x20, 0x3042},
            slice_path=strategy,
            include_remaining=False,
        )
        # Note: the surviving slice from block index 2 keeps its
        # original index in the name (`google-korean-002`), preserving
        # the strategy's positional identity for cache-key stability.
        assert [item.name for item in plan] == [
            "google-korean-000",
            "google-korean-002",
        ]

    def test_slices_are_non_overlapping(self, tmp_path):
        # Same hard requirement as build_subset_plan — no codepoint may
        # land in two slices (browser would double-fetch).
        strategy = self._write_strategy(tmp_path, [
            [0x20, 0x3042, 0x4E00],
            [0x41, 0x3042, 0x4E00],  # overlapping with first
        ])
        plan = build_google_korean_subset_plan(
            {0x20, 0x3042, 0x4E00, 0x41},
            slice_path=strategy,
            include_remaining=False,
        )
        seen = set()
        for item in plan:
            current = set(item.codepoints)
            assert not (seen & current)
            seen.update(current)
