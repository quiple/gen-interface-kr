# Vendored Inputs

This directory contains third-party source materials used by the build
pipeline.

```text
vendor/
  fonts/      # Inter and Noto Sans JP source fonts
  nam-files/  # pinned googlefonts/nam-files data for web font slicing
```

These files are build inputs, not generated outputs. Generated fonts and release
artifacts are written under `dist/`.
