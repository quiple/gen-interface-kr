# Release Packaging

This pipeline packages generated outputs for distribution.

It creates a GitHub Release zip of the TTFs (for users installing the
font into design tools, OS font folders, or bitmap conversion utilities)
and prepares an npm package that delivers the
font on the web via CSS + unicode-range subset WOFF2.

## Build

```bash
make release
```

This target runs:

```bash
PYTHONPATH=src python3 -m font.build
PYTHONPATH=src python3 -m webfont.build --all --clean --strategy google-korean
PYTHONPATH=src python3 -m release.build
```

Direct module execution:

```bash
PYTHONPATH=src python3 -m release.build
```

## npm Publishing

The publishable npm package is `dist/release/npm/`. During `make release`,
the `[project].version` from `pyproject.toml` is written into
`dist/release/npm/package.json`.

Before publishing:

```bash
make npm-pack
make npm-publish-dry-run
```

Publish:

```bash
make npm-publish
```

Override npm publish flags with `NPM_PUBLISH_FLAGS`:

```bash
make npm-publish NPM_PUBLISH_FLAGS="--access public --tag next"
```

The npm cache defaults to the repository-local `.npm-cache/` directory. Override
it with `NPM_CACHE` if needed:

```bash
make npm-pack NPM_CACHE=/tmp/gen-interface-kr-npm-cache
```

## GitHub Release Assets

GitHub Release assets are written to:

```text
dist/release/github/
  GenInterfaceKR-<version>.zip   # TTF, all weights × both families
```

The asset filename embeds the version so each release can be linked
unambiguously even after a newer "latest" lands.

Web delivery flows through the npm package below; full single-file WOFF2
is intentionally not redistributed.

### Publishing

Run `make release` to produce the zip, then upload it to a GitHub
Release with the `gh` CLI:

```bash
# Create a new release
gh release create v<version> dist/release/github/GenInterfaceKR-<version>.zip \
  --title "Gen Interface KR v<version>" \
  --notes "Release notes..."

# Or attach to an existing (e.g. draft) release
gh release upload v<version> dist/release/github/*.zip --clobber
```

A draft can be created up front and assets attached afterwards:

```bash
gh release create v<version> --draft --target main \
  --title "Gen Interface KR v<version>" --notes "..."
make release
gh release upload v<version> dist/release/github/*.zip --clobber
# Review on the GitHub UI, then "Publish release"
```

## Web Font Hosting

Web font files are written to an npm package root:

```text
dist/release/npm/
  package.json
  OFL.txt
  all.css
  100.css ... 800.css
  display-100.css ... display-800.css
  w/normal/.../*.woff2
  w/display/.../*.woff2
```

For non-npm static hosting, copy the contents of `dist/release/npm/` to
your public directory. Example CSS path:

```text
/webfonts/all.css
```

Publishing `dist/release/npm/` to npm makes the jsDelivr URL:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gen-interface-kr@latest/all.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gen-interface-kr@latest/400.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gen-interface-kr@latest/display-400.css">
```

The WOFF2 URLs inside the CSS are relative, so the CSS files and `w/` only need
to stay together at the package root.
