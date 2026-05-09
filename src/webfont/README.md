# Web Font Delivery

This is a derived pipeline built from the baked Gen Interface KR and Gen
Interface KR Display weights.

It generates a CSS file with `unicode-range` guarded `@font-face` rules and the
corresponding WOFF2 subset files for Korean web font delivery. The default
Korean slicing strategy uses the vendored `googlefonts/nam-files` data in
`vendor/nam-files/slices/korean_default.txt`; it does not inspect Google
Fonts live CSS.

## Build

```bash
make webfont
```

Direct module execution:

```bash
PYTHONPATH=src python3 -m webfont.build --all --clean --jobs 8
```

The default strategy is `google-korean`. The older JIS row based strategy is
still available for comparison:

```bash
PYTHONPATH=src python3 -m webfont.build --all --clean --strategy jis-row --jobs 8
```

Required inputs:

```text
dist/ttf/Gen Interface KR/*.ttf
dist/ttf/Gen Interface KR Display/*.ttf
```

The published assets are subset WOFF2 files only, but the generator uses TTF
inputs because subsetting from already-compressed WOFF2 is much slower.

Outputs:

```text
dist/webfont/gen-interface-kr/
  all.css
  100.css ... 800.css
  display-100.css ... display-800.css
  w/normal/{100,200,300,400,500,600,700,800}/*.woff2
  w/display/{100,200,300,400,500,600,700,800}/*.woff2
  nam/*.nam
  manifest.json
```

`nam/*.nam` follows the `googlefonts/nam-files` machine-readable style: one
`0x...` codepoint per line. With `google-korean`, the build intersects the
120 slices from `korean_default.txt` with the Gen Interface KR cmap, then
places supported codepoints outside that strategy into `google-korean-extra-*`
subsets.

## Loading

Subset delivery:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gen-interface-kr@latest/all.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gen-interface-kr@latest/400.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gen-interface-kr@latest/display-400.css">
```

Do not preload individual subset WOFF2 files. That would bypass the
`unicode-range` behavior that lets the browser fetch only the ranges used by
the page text. If preloading is needed, preload the CSS only:

```html
<link rel="preload" as="style" href="https://cdn.jsdelivr.net/npm/gen-interface-kr@latest/all.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gen-interface-kr@latest/all.css">
```

## References

- https://github.com/googlefonts/nam-files
- https://github.com/googlefonts/nam-files/tree/main/slices
- https://developer.mozilla.org/docs/Web/CSS/%40font-face/unicode-range
