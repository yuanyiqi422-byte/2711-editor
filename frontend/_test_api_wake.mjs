/**
 * Smoke test for backend wake / retry helpers (Node --check companion).
 * Run: node frontend/_test_api_wake.mjs
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(__dirname, "js/lib/api-config.js"), "utf8");

const sandbox = {
  window: {},
  globalThis: {},
  fetch: async () => ({ ok: true, headers: { get: () => "application/json" }, text: async () => '{"ok":true,"has_key":true}' }),
  setTimeout,
  clearTimeout,
  AbortController: globalThis.AbortController,
  DOMException: globalThis.DOMException,
  document: { addEventListener: () => {} },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

vm.runInNewContext(src, sandbox, { filename: "api-config.js" });

const ApiConfig = sandbox.ApiConfig;
let failed = 0;

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL:", msg);
    failed += 1;
  } else {
    console.log("OK:", msg);
  }
}

assert(typeof ApiConfig.ensureBackendReady === "function", "ensureBackendReady exported");
assert(typeof ApiConfig.isTransientProbeFailure === "function", "isTransientProbeFailure exported");
assert(ApiConfig.isBackendAvailable(), "unknown state should not block create");
assert(
  ApiConfig.isTransientProbeFailure(new TypeError("Failed to fetch")),
  "network error is transient"
);
assert(
  ApiConfig.isTransientProbeFailure(Object.assign(new Error("x"), { cause: "timeout" })),
  "timeout is transient"
);

if (failed > 0) {
  process.exit(1);
}
console.log("All api wake smoke checks passed.");
