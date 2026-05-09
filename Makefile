SHELL := /bin/bash

PYTHON ?= python3
NODE ?= node
PYTHONPATH := src
PY := PYTHONPATH=$(PYTHONPATH) $(PYTHON)

WEBFONT_JOBS ?= 8
NPM_PACKAGE_DIR := dist/release/npm
NPM_PUBLISH_FLAGS ?= --access public
NPM_CACHE ?= $(CURDIR)/.npm-cache

.PHONY: all clean \
        font \
        webfont webfont-benchmark \
        release npm-pack npm-publish-dry-run npm-publish \
        site serve

# Default: produce everything publishable.
all: release


# ---------------------------------------------------------------------------
# src/font  —  TTF for both families × all weights
# ---------------------------------------------------------------------------

# Outputs land under dist/ttf/<Family>/. Web delivery goes through
# `make webfont` (subset WOFF2 served via unicode-range), not full WOFF2.
font:
	$(PY) -m font.build


# ---------------------------------------------------------------------------
# src/webfont  —  unicode-range subsetting
# ---------------------------------------------------------------------------

webfont: font
	$(PY) -m webfont.build --all --clean --strategy google-korean --jobs $(WEBFONT_JOBS)


# ---------------------------------------------------------------------------
# src/release  —  GitHub Release zips, npm package, Pages-hosted mirror
# ---------------------------------------------------------------------------

release: webfont
	$(PY) -m release.build

# Inspect the npm package that will be published (no upload, no tarball).
npm-pack: release
	cd $(NPM_PACKAGE_DIR) && npm_config_cache=$(NPM_CACHE) npm pack --dry-run

# Validate npm publishing without actually uploading.
npm-publish-dry-run: release
	cd $(NPM_PACKAGE_DIR) && npm_config_cache=$(NPM_CACHE) npm publish --dry-run $(NPM_PUBLISH_FLAGS)

# Publish the generated webfont package to npm.
npm-publish: release
	cd $(NPM_PACKAGE_DIR) && npm_config_cache=$(NPM_CACHE) npm publish $(NPM_PUBLISH_FLAGS)


# ---------------------------------------------------------------------------
# site  —  Vite static demo site (loads webfont via jsDelivr at runtime)
# ---------------------------------------------------------------------------

# site/dist/ is also the GitHub Pages artifact (.github/workflows/pages.yml
# uploads it directly), so this single target serves both local builds and
# Pages deployments.
site:
	cd site && npm run build

# Local Vite dev server.
serve:
	cd site && npm run dev


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

clean:
	rm -rf dist/
	rm -rf site/dist/
