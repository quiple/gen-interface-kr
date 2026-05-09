#!/usr/bin/env node
import { spawn } from "node:child_process";
import { createServer, request as httpRequest } from "node:http";
import { readFile, mkdtemp, rm, writeFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const DEFAULT_ARTIFACTS = path.join(ROOT, "dist", "webfont", "gen-interface-kr");
const DEFAULT_OUT = path.join(ROOT, "dist", "webfont", "benchmark");
const VALID_MODES = new Set(["subset", "full"]);

const SITE_PARAGRAPHS = [
  "Gen Interface KR은 가독성 높은 본문과 정보 설계에 최적화된 한국어 UI 폰트입니다. 화면상의 제목, 설명글, 폼, 버튼, 수치, 짧은 알림 등이 동일한 밀도로 나열되는 상황을 상정하여 제작되었습니다.",
  "제품 페이지에서는 도입 사례, 요금, 기능 목록, 자주 묻는 질문, 고객 지원 창구와 같은 짧은 섹션들이 이어집니다. 일반적인 웹사이트에서는 글자 수가 너무 많지 않으며, 한글과 문장 부호, 기본적인 한자가 중심이 됩니다.",
  "본 테스트에서는 이미지나 JavaScript의 부하를 억제하여, 웹 폰트의 CSS와 WOFF2 파일의 로드 시간을 확인할 수 있도록 했습니다. 통신 환경은 로컬 서버 측에서 지연 시간과 대역폭을 추가하여 재현합니다.",
];

const NOVEL_PARAGRAPHS = [
  "동트기 전의 역에는 옅은 푸른빛이 남아 있었다. 개찰구 너머로 신문을 접는 소리가 들려왔고, 멀리 떨어진 승강장에서는 짧은 발차 벨 소리가 울렸다. 누구도 서두르지 않는 것처럼 보였지만, 마을 전체는 고요하게 움직이기 시작하고 있었다.",
  "그녀는 낡은 가방을 품에 안고, 어제 받은 편지의 내용을 몇 번이고 되뇌었다. 그곳에는 이유도 설명도 없이, 그저 북쪽 항구에서 기다리겠다는 말만 적혀 있었다. 의심할 여지는 충분했지만, 확인하지 않은 채 잊어버릴 수는 없었다.",
  "상점가의 지붕을 빠져나오자, 비에 젖은 보도 위로 간판의 색들이 비치고 있었다. 생선가게 주인은 대야를 씻고 있었고, 꽃가게 딸은 젖은 잎을 하나씩 털어내고 있었다. 익숙한 아침 풍경 속에서, 오직 그녀만이 다른 이야기 속으로 향하고 있는 듯했다.",
];

function parseArgs() {
  const args = {
    artifacts: DEFAULT_ARTIFACTS,
    output: DEFAULT_OUT,
    runs: 3,
    latencyMs: 80,
    kbps: 1600,
    profiles: ["site", "novel"],
    modes: ["subset", "full"],
    chromePath: process.env.CHROME_PATH || "",
    timeoutMs: 120000,
    freshBrowserPerRun: true,
  };
  for (let i = 2; i < process.argv.length; i += 1) {
    const arg = process.argv[i];
    const next = process.argv[i + 1];
    if (arg === "--artifacts") args.artifacts = path.resolve(next), i += 1;
    else if (arg === "--output") args.output = path.resolve(next), i += 1;
    else if (arg === "--runs") args.runs = Number(next), i += 1;
    else if (arg === "--latency") args.latencyMs = Number(next), i += 1;
    else if (arg === "--kbps") args.kbps = Number(next), i += 1;
    else if (arg === "--profiles") args.profiles = next.split(","), i += 1;
    else if (arg === "--modes") args.modes = next.split(","), i += 1;
    else if (arg === "--chrome") args.chromePath = path.resolve(next), i += 1;
    else if (arg === "--timeout") args.timeoutMs = Number(next), i += 1;
    else if (arg === "--reuse-browser") args.freshBrowserPerRun = false;
    else if (arg === "--help") {
      console.log(`Usage: node src/webfont/benchmark.mjs [options]

Options:
  --runs 3             Number of cold-load runs per profile/mode
  --latency 80         Added latency before each font response, in ms
  --kbps 1600          Font response throughput, in kilobits per second
  --profiles site,novel
  --modes subset,full
  --chrome /path/to/Chrome
  --reuse-browser       Reuse one Chrome process across runs. Faster, but can mix cold and warm font-resolution state.
`);
      process.exit(0);
    }
  }
  const unknownModes = args.modes.filter((mode) => !VALID_MODES.has(mode));
  if (unknownModes.length) {
    throw new Error(`Unknown mode(s): ${unknownModes.join(", ")}. Supported modes: subset, full`);
  }
  return args;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function readManifest(artifacts) {
  const manifestPath = path.join(artifacts, "manifest.json");
  if (!existsSync(manifestPath)) {
    throw new Error(`Missing ${manifestPath}. Run: make webfont`);
  }
  return JSON.parse(await readFile(manifestPath, "utf8"));
}

function loadModeConfigs(args, primaryManifest) {
  return {
    subset: {
      kind: "subset",
      family: "Gen Interface KR",
      artifacts: args.artifacts,
      manifest: primaryManifest,
    },
    full: {
      kind: "full",
      family: "Gen Interface KR",
      artifacts: args.artifacts,
      manifest: primaryManifest,
    },
  };
}

function parseUnicodeRange(range) {
  const codepoints = [];
  for (const raw of range.split(",")) {
    const part = raw.trim().replace(/^U\+/i, "");
    if (!part) continue;
    const [startRaw, endRaw] = part.split("-");
    const start = Number.parseInt(startRaw, 16);
    const end = endRaw ? Number.parseInt(endRaw, 16) : start;
    if (Number.isFinite(start) && Number.isFinite(end)) {
      codepoints.push([start, end]);
    }
  }
  return codepoints;
}

function sampleSubsetCharacters(manifest, maxPerSubset = 3) {
  const chars = [];
  for (const entry of manifest.files.subsets) {
    const rangeText = entry.cmapUnicodeRange || entry.unicodeRange;
    const ranges = parseUnicodeRange(rangeText);
    const hanRanges = ranges.filter(([start, end]) => end >= 0x3400 && start <= 0x2FA1F);
    if (entry.name && !entry.name.startsWith("jp-kanji")) continue;
    if (!hanRanges.length) continue;
    let taken = 0;
    for (const [rawStart, rawEnd] of hanRanges) {
      const start = Math.max(rawStart, 0x3400);
      const end = Math.min(rawEnd, 0x2FA1F);
      chars.push(String.fromCodePoint(start));
      taken += 1;
      if (end > start && taken < maxPerSubset) {
        chars.push(String.fromCodePoint(Math.floor((start + end) / 2)));
        taken += 1;
      }
      if (end > start && taken < maxPerSubset) {
        chars.push(String.fromCodePoint(end));
        taken += 1;
      }
      if (taken >= maxPerSubset) break;
    }
  }
  return chars.join("");
}

function makeText(profile, manifest) {
  if (profile === "site") {
    const repeated = [];
    while (repeated.join("\n").length < 3600) repeated.push(...SITE_PARAGRAPHS);
    return repeated.join("\n\n");
  }
  if (profile === "novel") {
    const broadChars = sampleSubsetCharacters(manifest, 2);
    const repeated = [];
    let i = 0;
    while (repeated.join("\n").length < 90000) {
      repeated.push(NOVEL_PARAGRAPHS[i % NOVEL_PARAGRAPHS.length]);
      if (i % 4 === 0) repeated.push(broadChars);
      i += 1;
    }
    return repeated.join("\n\n");
  }
  throw new Error(`Unknown profile: ${profile}`);
}

function makeCss(modeName, modeConfig, runId) {
  const face = (src, unicodeRange = "") => `@font-face {
  font-family: "${modeConfig.family}";
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url("${src}?run=${encodeURIComponent(runId)}") format("woff2");
${unicodeRange ? `  unicode-range: ${unicodeRange};\n` : ""}}`;

  if (modeConfig.kind === "full") {
    return face(`/font/${modeName}/${modeConfig.manifest.files.full.path}`);
  }
  return modeConfig.manifest.files.subsets
    .map((entry) => face(`/font/${modeName}/${entry.path}`, entry.unicodeRange))
    .join("\n\n");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function makePage({ mode, profile, runId, text, family }) {
  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="/css/${mode}.css?run=${encodeURIComponent(runId)}">
  <style>
    body {
      margin: 0;
      font-family: "${family}", system-ui, sans-serif;
      font-size: 16px;
      line-height: 1.8;
      color: #171717;
      background: #fff;
    }
    main {
      max-width: 760px;
      margin: 0 auto;
      padding: 32px 20px 80px;
    }
    #content {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
  </style>
</head>
<body>
  <main>
    <h1>${profile} / ${mode}</h1>
    <div id="content">${escapeHtml(text)}</div>
  </main>
  <script>
    const start = performance.now();
    const text = document.getElementById("content").textContent;
    const uniqueCodepoints = new Set(Array.from(text, ch => ch.codePointAt(0))).size;
    document.body.offsetHeight;
    document.fonts.ready.then(() => {
      const resources = performance.getEntriesByType("resource");
      const fonts = resources.filter(r => r.name.includes(".woff2"));
      const css = resources.filter(r => r.name.includes("/css/"));
      const navigation = performance.getEntriesByType("navigation")[0];
      const lastFontResponseEnd = fonts.reduce((max, r) => Math.max(max, r.responseEnd), 0);
      window.__FONT_BENCHMARK_RESULT__ = {
        mode: ${JSON.stringify(mode)},
        profile: ${JSON.stringify(profile)},
        runId: ${JSON.stringify(runId)},
        textLength: text.length,
        uniqueCodepoints,
        fontReadyMs: performance.now(),
        scriptStartMs: start,
        lastFontResponseEndMs: lastFontResponseEnd,
        afterLastFontResponseMs: performance.now() - lastFontResponseEnd,
        navigation: navigation ? {
          domContentLoadedEventEnd: navigation.domContentLoadedEventEnd,
          loadEventEnd: navigation.loadEventEnd,
          responseEnd: navigation.responseEnd
        } : null,
        fontResources: fonts.map(r => ({
          name: r.name,
          startTime: r.startTime,
          fetchStart: r.fetchStart,
          requestStart: r.requestStart,
          responseStart: r.responseStart,
          responseEnd: r.responseEnd,
          duration: r.duration,
          transferSize: r.transferSize,
          encodedBodySize: r.encodedBodySize,
          decodedBodySize: r.decodedBodySize
        })),
        cssResources: css.map(r => ({
          name: r.name,
          startTime: r.startTime,
          responseEnd: r.responseEnd,
          duration: r.duration,
          transferSize: r.transferSize
        }))
      };
    });
  </script>
</body>
</html>`;
}

async function sendThrottledFont(res, filePath, counters, runId, args) {
  const data = await readFile(filePath);
  counters.set(runId, counters.get(runId) || { fontRequests: 0, fontBytes: 0, files: [] });
  const counter = counters.get(runId);
  counter.fontRequests += 1;
  counter.fontBytes += data.length;
  counter.files.push({ file: path.basename(filePath), bytes: data.length });

  res.writeHead(200, {
    "Content-Type": "font/woff2",
    "Content-Length": data.length,
    "Cache-Control": "no-store",
    "Timing-Allow-Origin": "*",
    "Access-Control-Allow-Origin": "*",
  });
  await delay(args.latencyMs);
  const bytesPerSecond = Math.max(1024, (args.kbps * 1024) / 8);
  const intervalMs = 50;
  const chunkSize = Math.max(1024, Math.floor(bytesPerSecond * (intervalMs / 1000)));
  for (let offset = 0; offset < data.length; offset += chunkSize) {
    res.write(data.subarray(offset, offset + chunkSize));
    await delay(intervalMs);
  }
  res.end();
}

async function startServer(args, textManifest, modeConfigs) {
  const counters = new Map();
  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url, "http://127.0.0.1");
      if (url.pathname === "/bench") {
        const mode = url.searchParams.get("mode") || "subset";
        const profile = url.searchParams.get("profile") || "site";
        const runId = url.searchParams.get("run") || `${Date.now()}`;
        const modeConfig = modeConfigs[mode];
        if (!modeConfig) throw new Error(`Unknown mode: ${mode}`);
        const text = makeText(profile, textManifest);
        const html = makePage({ mode, profile, runId, text, family: modeConfig.family });
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
        res.end(html);
        return;
      }
      if (url.pathname.startsWith("/css/")) {
        const mode = path.basename(url.pathname, ".css");
        const modeConfig = modeConfigs[mode];
        if (!modeConfig) throw new Error(`Unknown mode: ${mode}`);
        const runId = url.searchParams.get("run") || `${Date.now()}`;
        res.writeHead(200, { "Content-Type": "text/css; charset=utf-8", "Cache-Control": "no-store" });
        res.end(makeCss(mode, modeConfig, runId));
        return;
      }
      if (url.pathname.startsWith("/font/")) {
        const parts = decodeURIComponent(url.pathname.replace(/^\/font\//, "")).split("/");
        const mode = parts.shift();
        const modeConfig = modeConfigs[mode];
        if (!modeConfig) throw new Error(`Unknown font mode: ${mode}`);
        const rel = parts.join("/");
        const artifactRoot = path.resolve(modeConfig.artifacts);
        const filePath = path.resolve(artifactRoot, rel);
        if (!filePath.startsWith(artifactRoot)) throw new Error("Invalid font path");
        await sendThrottledFont(res, filePath, counters, url.searchParams.get("run") || "unknown", args);
        return;
      }
      res.writeHead(404);
      res.end("not found");
    } catch (error) {
      res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
      res.end(String(error.stack || error));
    }
  });

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  return { server, port, counters };
}

function requestJson(url, method = "GET") {
  return new Promise((resolve, reject) => {
    const req = httpRequest(url, { method }, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => (body += chunk));
      res.on("end", () => {
        if (res.statusCode >= 400) reject(new Error(`${method} ${url} failed: ${res.statusCode} ${body}`));
        else {
          try {
            resolve(JSON.parse(body));
          } catch (error) {
            reject(error);
          }
        }
      });
    });
    req.on("error", reject);
    req.end();
  });
}

async function freePort() {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

function findChrome(chromePath) {
  const candidates = [
    chromePath,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
  const found = candidates.find((candidate) => existsSync(candidate));
  if (!found) {
    throw new Error("Chrome/Chromium was not found. Pass --chrome /path/to/chrome or set CHROME_PATH.");
  }
  return found;
}

async function waitForDebugPort(port) {
  const url = `http://127.0.0.1:${port}/json/version`;
  for (let i = 0; i < 100; i += 1) {
    try {
      return await requestJson(url);
    } catch {
      await delay(100);
    }
  }
  throw new Error("Timed out waiting for Chrome remote debugging port");
}

class CdpClient {
  constructor(ws) {
    this.ws = ws;
    this.nextId = 1;
    this.pending = new Map();
    ws.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (!message.id) return;
      const pending = this.pending.get(message.id);
      if (!pending) return;
      this.pending.delete(message.id);
      if (message.error) pending.reject(new Error(JSON.stringify(message.error)));
      else pending.resolve(message.result);
    });
  }

  send(method, params = {}) {
    const id = this.nextId++;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
  }

  close() {
    this.ws.close();
  }
}

async function withBrowser(args, fn) {
  const chrome = findChrome(args.chromePath);
  const debugPort = await freePort();
  const userDataDir = await mkdtemp(path.join(os.tmpdir(), "gen-interface-kr-font-bench-"));
  const proc = spawn(chrome, [
    "--headless=new",
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${userDataDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-cache",
    "--font-render-hinting=none",
    "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });

  let stderr = "";
  proc.stderr.on("data", (chunk) => (stderr += chunk.toString()));
  try {
    await waitForDebugPort(debugPort);
    return await fn(debugPort);
  } finally {
    proc.kill("SIGTERM");
    await Promise.race([
      new Promise((resolve) => proc.on("exit", resolve)),
      delay(2000),
    ]);
    await rm(userDataDir, { recursive: true, force: true });
    if (proc.exitCode && proc.exitCode !== 0) {
      console.error(stderr.trim());
    }
  }
}

async function runPage(debugPort, url, timeoutMs) {
  const target = await requestJson(`http://127.0.0.1:${debugPort}/json/new?${encodeURIComponent("about:blank")}`, "PUT");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", reject, { once: true });
  });
  const cdp = new CdpClient(ws);
  try {
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Network.enable");
    await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
    await cdp.send("Network.clearBrowserCache");
    await cdp.send("Page.navigate", { url });
    const expression = `new Promise((resolve) => {
      const deadline = Date.now() + ${timeoutMs};
      const tick = () => {
        if (window.__FONT_BENCHMARK_RESULT__) resolve(window.__FONT_BENCHMARK_RESULT__);
        else if (Date.now() > deadline) resolve({ error: "timeout" });
        else setTimeout(tick, 50);
      };
      tick();
    })`;
    const result = await cdp.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
    });
    return result.result.value;
  } finally {
    cdp.close();
    await requestJson(`http://127.0.0.1:${debugPort}/json/close/${target.id}`).catch(() => {});
  }
}

function summarize(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const avg = values.reduce((sum, value) => sum + value, 0) / values.length;
  const median = sorted[Math.floor(sorted.length / 2)];
  return { avg, median, min: sorted[0], max: sorted[sorted.length - 1] };
}

function printSummary(results) {
  console.log("\nSummary");
  console.log("profile\tmode\truns\tfontReady avg\tfont bytes avg\tfont req avg");
  for (const group of results.summary) {
    console.log([
      group.profile,
      group.mode,
      group.runs,
      `${Math.round(group.fontReadyMs.avg)} ms`,
      `${Math.round(group.fontBytes.avg / 1024)} KB`,
      group.fontRequests.avg.toFixed(1),
    ].join("\t"));
  }
}

async function main() {
  const args = parseArgs();
  const manifest = await readManifest(args.artifacts);
  const modeConfigs = loadModeConfigs(args, manifest);
  const { server, port, counters } = await startServer(args, manifest, modeConfigs);
  const rows = [];
  const runOne = async (debugPort, profile, mode, run) => {
    const runId = `${profile}-${mode}-${run}-${Date.now()}`;
    const url = `http://127.0.0.1:${port}/bench?profile=${profile}&mode=${mode}&run=${encodeURIComponent(runId)}`;
    const result = await runPage(debugPort, url, args.timeoutMs);
    const counter = counters.get(runId) || { fontRequests: 0, fontBytes: 0, files: [] };
    if (result.error) throw new Error(`${profile}/${mode} run ${run}: ${result.error}`);
    rows.push({ ...result, ...counter });
    console.log(`${profile}/${mode} #${run}: ${Math.round(result.fontReadyMs)} ms, ${Math.round(counter.fontBytes / 1024)} KB, ${counter.fontRequests} font requests`);
  };
  try {
    if (args.freshBrowserPerRun) {
      for (const profile of args.profiles) {
        for (const mode of args.modes) {
          for (let run = 1; run <= args.runs; run += 1) {
            await withBrowser(args, (debugPort) => runOne(debugPort, profile, mode, run));
          }
        }
      }
    } else {
      await withBrowser(args, async (debugPort) => {
        for (const profile of args.profiles) {
          for (const mode of args.modes) {
            for (let run = 1; run <= args.runs; run += 1) {
              await runOne(debugPort, profile, mode, run);
            }
          }
        }
      });
    }
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }

  const summary = [];
  for (const profile of args.profiles) {
    for (const mode of args.modes) {
      const group = rows.filter((row) => row.profile === profile && row.mode === mode);
      summary.push({
        profile,
        mode,
        runs: group.length,
        textLength: group[0]?.textLength || 0,
        uniqueCodepoints: group[0]?.uniqueCodepoints || 0,
        fontReadyMs: summarize(group.map((row) => row.fontReadyMs)),
        fontBytes: summarize(group.map((row) => row.fontBytes)),
        fontRequests: summarize(group.map((row) => row.fontRequests)),
      });
    }
  }

  const results = {
    createdAt: new Date().toISOString(),
    network: { latencyMs: args.latencyMs, kbps: args.kbps },
    browser: { freshBrowserPerRun: args.freshBrowserPerRun },
    artifacts: Object.fromEntries(
      Object.entries(modeConfigs).map(([mode, config]) => [mode, path.relative(ROOT, config.artifacts)])
    ),
    rows,
    summary,
  };

  await mkdir(args.output, { recursive: true });
  const stamp = new Date().toISOString().replaceAll(":", "").replace(/\..+$/, "Z");
  const outPath = path.join(args.output, `font-benchmark-${stamp}.json`);
  await writeFile(outPath, `${JSON.stringify(results, null, 2)}\n`, "utf8");
  printSummary(results);
  console.log(`\nWrote ${outPath}`);
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exit(1);
});
