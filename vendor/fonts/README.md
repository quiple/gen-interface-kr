# Vendored Source Fonts

This directory contains the third-party source fonts used to build Gen
Interface KR.

Expected layout:

```text
vendor/fonts/
  Inter-4.1/
  Noto_Sans_KR/
```

`src/font/build.py` reads Inter static TTFs from `Inter-4.1/extras/ttf/` and
the Noto Sans KR variable font from `Noto_Sans_KR/NotoSansKR-VF.ttf`.
