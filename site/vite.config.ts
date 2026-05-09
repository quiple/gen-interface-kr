import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Source-of-truth for the project version is the Python pyproject.toml at
// the repo root. Read it once at config-load time and surface it to both
// the runtime (via `define`) and to index.html (via a tiny HTML transform
// plugin) so a single bump in pyproject.toml propagates to:
//   - <link href="https://cdn.jsdelivr.net/npm/gen-interface-kr@X.Y.Z/...">
//     in index.html
//   - the "Download vX.Y.Z" label rendered in Hero / Footer
//   - the @X.Y.Z reference inside the Variation Web Fonts code sample
const __dirname = dirname(fileURLToPath(import.meta.url))
const PYPROJECT_PATH = resolve(__dirname, '..', 'pyproject.toml')

function readProjectVersion(path: string): string {
  const text = readFileSync(path, 'utf8')
  // Match the first top-level `version = "x.y.z"`. We don't pull in a TOML
  // parser dep just to read one field — the pyproject layout is stable
  // and the regex is anchored to a quoted string at line start.
  const match = text.match(/^version\s*=\s*"([^"]+)"/m)
  if (!match) {
    throw new Error(`version not found in ${path}`)
  }
  return match[1]
}

const APP_VERSION = readProjectVersion(PYPROJECT_PATH)

// https://vite.dev/config/
export default defineConfig({
  base: './',
  define: {
    __APP_VERSION__: JSON.stringify(APP_VERSION),
  },
  plugins: [
    react(),
    {
      // Replace `%APP_VERSION%` placeholders in index.html (Vite only
      // auto-substitutes `%VITE_*%` from env, not arbitrary tokens, so
      // this hook covers the gap for our pyproject-derived version).
      name: 'app-version-html',
      transformIndexHtml: (html) =>
        html.replace(/%APP_VERSION%/g, APP_VERSION),
    },
  ],
})
