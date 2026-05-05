/// <reference types="vite/client" />

// Injected at build time by `define` in vite.config.ts. The value is the
// `version` field from the repo-root pyproject.toml — see vite.config.ts
// for the read path. Use `APP_VERSION` from `./config` rather than the
// raw global so a single import covers both the version constant and the
// download URL/label that depend on it.
declare const __APP_VERSION__: string
