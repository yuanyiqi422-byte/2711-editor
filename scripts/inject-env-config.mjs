#!/usr/bin/env node
/**
 * Inject production API config into frontend before static deploy.
 *
 * Env vars (Cloudflare Pages / Netlify → Site settings → Environment variables):
 *   API_BACKEND_URL — backend origin, e.g. https://two711-editor-api.onrender.com
 *                     sets __API_BASE__ for browser direct calls (required for SSE)
 *   API_BASE_URL    — override direct API origin (skips any /api proxy)
 *
 * Platform auto-detection:
 *   Cloudflare Pages sets CF_PAGES=1 during build
 *   Netlify sets NETLIFY=true during build
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const FRONTEND = join(ROOT, "frontend");
const REDIRECTS = join(FRONTEND, "_redirects");
const NETLIFY_TOML = join(ROOT, "netlify.toml");
const INJECT_MARKER = "# [injected-api-proxy]";
const DEFAULT_PRODUCTION_API = "https://two711-editor-api.onrender.com";

function stripSlash(url) {
  return (url || "").trim().replace(/\/+$/, "");
}

function escapeRegExp(text) {
  return String(text).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const isCloudflarePages =
  process.env.CF_PAGES === "1" ||
  process.env.CLOUDFLARE_PAGES === "1" ||
  Boolean(process.env.CF_PAGES_URL);
const isNetlify = process.env.NETLIFY === "true" || process.env.NETLIFY === "1";
const isHostedDeploy = isCloudflarePages || isNetlify;

const backendProxy = stripSlash(
  process.env.API_BACKEND_URL ||
    process.env.BACKEND_URL ||
    process.env.RENDER_EXTERNAL_URL ||
    (isHostedDeploy ? DEFAULT_PRODUCTION_API : "")
);
// Static-host /api rewrite proxies truncate long SSE streams — always prefer direct backend URL.
const apiBase =
  stripSlash(process.env.API_BASE_URL || process.env.VITE_API_BASE || "") || backendProxy;

const envConfig = `/** Auto-generated — do not edit manually */
(function (g) {
  g.__API_BASE__ = ${JSON.stringify(apiBase)};
})(typeof window !== "undefined" ? window : globalThis);
`;

writeFileSync(join(FRONTEND, "js", "env-config.js"), envConfig, "utf8");
console.log("[inject-env-config] __API_BASE__ =", apiBase || "(empty → same-origin /api)");
console.log(
  "[inject-env-config] platform:",
  isCloudflarePages ? "cloudflare-pages" : isNetlify ? "netlify" : "local"
);

function writeSpaRedirects() {
  writeFileSync(REDIRECTS, "/* /index.html 200\n", "utf8");
  console.log("[inject-env-config] _redirects SPA → /* /index.html 200");
}

function stripInjectedProxyBlocks(content) {
  const markerEscaped = escapeRegExp(INJECT_MARKER);
  const blockRe = new RegExp(
    "\\n?" +
      markerEscaped +
      "[\\s\\S]*?(?=\\n(?:\\[\\[redirects\\]\\]|" +
      markerEscaped +
      "|\\[build\\]|\\[headers\\]|$))",
    "g"
  );
  let next = content;
  let prev;
  do {
    prev = next;
    next = next.replace(blockRe, "\n");
  } while (next !== prev);
  const apiBlockRe =
    /\n\[\[redirects\]\]\r?\n  from = "\/api\/\*"[\s\S]*?force = true\r?\n/g;
  next = next.replace(apiBlockRe, "\n");
  return next.replace(/\n{3,}/g, "\n\n");
}

function updateNetlifyToml() {
  if (!existsSync(NETLIFY_TOML)) return;
  let content = stripInjectedProxyBlocks(readFileSync(NETLIFY_TOML, "utf8"));
  writeFileSync(NETLIFY_TOML, content, "utf8");
  console.log("[inject-env-config] removed netlify.toml API proxy block (if any)");
}

// Cloudflare Pages reads _redirects from the publish directory (Netlify-compatible format).
writeSpaRedirects();
updateNetlifyToml();

if (!apiBase && !backendProxy) {
  console.warn(
    "[inject-env-config] WARN: no API_BACKEND_URL or API_BASE_URL — /api/* will 404 until backend URL is set."
  );
}
