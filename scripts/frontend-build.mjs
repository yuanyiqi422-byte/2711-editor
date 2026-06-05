#!/usr/bin/env node
/**
 * Frontend build / validation — static site has no bundler;
 * this script verifies assets, JS syntax, and HTML references.
 */
import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const FRONTEND = join(ROOT, "frontend");
const INDEX = join(FRONTEND, "index.html");

let errors = 0;
let warnings = 0;

function fail(msg) {
  console.error("ERROR:", msg);
  errors += 1;
}

function warn(msg) {
  console.warn("WARN:", msg);
  warnings += 1;
}

function ok(msg) {
  console.log("OK:", msg);
}

function collectJsFiles(dir, acc = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) collectJsFiles(p, acc);
    else if (name.endsWith(".js")) acc.push(p);
  }
  return acc;
}

function checkJsSyntax(file) {
  const rel = relative(ROOT, file);
  const result = spawnSync(process.execPath, ["--check", file], { encoding: "utf8" });
  if (result.status !== 0) {
    fail(`${rel}: ${(result.stderr || result.stdout || "").trim()}`);
    return false;
  }
  ok(`syntax ${rel}`);
  return true;
}

function extractAssetRefs(html) {
  const refs = [];
  const re = /(?:href|src)=["']([^"']+)["']/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const url = m[1];
    if (url.startsWith("#")) continue;
    if (url.startsWith("http") || url.startsWith("//") || url.startsWith("data:")) continue;
    refs.push(url.split("?")[0]);
  }
  return refs;
}

function main() {
  console.log("2711 Editor frontend build validation\n");

  if (!existsSync(INDEX)) {
    fail("frontend/index.html missing");
    process.exit(1);
  }

  const html = readFileSync(INDEX, "utf8");
  const refs = extractAssetRefs(html);

  for (const ref of refs) {
    const path = join(FRONTEND, ref.replace(/^\//, ""));
    if (!existsSync(path)) {
      fail(`missing asset referenced in index.html: ${ref}`);
    }
  }
  if (errors === 0) ok(`all ${refs.length} index.html asset refs exist`);

  const jsDir = join(FRONTEND, "js");
  const jsFiles = collectJsFiles(jsDir);
  for (const file of jsFiles) {
    checkJsSyntax(file);
  }

  const cssDir = join(FRONTEND, "css");
  for (const name of ["tokens.css", "landing.css", "app.css"]) {
    const p = join(cssDir, name);
    if (!existsSync(p)) fail(`missing css/${name}`);
    else ok(`css/${name} present`);
  }

  if (html.includes("backend/.env")) {
    warn("index.html contains backend/.env reference in user-visible copy");
  }

  const backendMain = join(ROOT, "backend", "main.py");
  if (existsSync(backendMain)) {
    const py = spawnSync("python", ["-m", "py_compile", backendMain], {
      encoding: "utf8",
      cwd: ROOT,
    });
    if (py.status === 0) ok("backend/main.py compiles");
    else fail(`backend/main.py: ${(py.stderr || "").trim()}`);
  }

  console.log(`\nDone — ${errors} error(s), ${warnings} warning(s)`);
  if (errors > 0) process.exit(1);
  console.log("Build passed.");
}

main();
