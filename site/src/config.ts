// `__APP_VERSION__` is injected by vite.config.ts at build time from the
// repo-root pyproject.toml. Re-exported as `APP_VERSION` so consumers
// don't need to know about the build-time global.
export const APP_VERSION = __APP_VERSION__

// The GitHub Release asset filename embeds the version, and the URL is
// tag-pinned (no `releases/latest/download/...`). Older deploys of this
// site therefore keep pointing at the exact archive they were built
// against, even after newer releases ship.
export const DOWNLOAD_URL =
  import.meta.env.VITE_DOWNLOAD_URL ||
  `https://github.com/yamatoiizuka/gen-interface-jp/releases/download/v${APP_VERSION}/GenInterfaceJP-${APP_VERSION}.zip`

export const DOWNLOAD_LABEL =
  import.meta.env.VITE_DOWNLOAD_LABEL || `Download v${APP_VERSION}`
