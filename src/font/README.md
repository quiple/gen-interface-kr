# Font Baking

This is the core pipeline for Gen Interface KR.

It builds the downloadable font families by merging Inter / Inter Display with
proportional Noto Sans KR, then applying the spacing and metric adjustments
defined for this project.

Source fonts are read from `vendor/fonts/`:

```text
vendor/fonts/
  Inter-4.1/
  Noto_Sans_KR/
```

Outputs:

```text
dist/ttf/
```

Use the Makefile entry point:

```bash
make font
```

Direct module execution:

```bash
PYTHONPATH=src python3 -m font.build
```

Generated outputs stay under `dist/` and are not committed.
