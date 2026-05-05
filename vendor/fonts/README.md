# Vendored Source Fonts

This directory contains the third-party source fonts used to build Gen
Interface JP.

Expected layout:

```text
vendor/fonts/
  Inter-4.1/
  Noto_Sans_JP/
```

`src/font/build.py` reads Inter static TTFs from `Inter-4.1/extras/ttf/` and
the Noto Sans JP variable font from `Noto_Sans_JP/NotoSansJP-VariableFont_wght.ttf`.
