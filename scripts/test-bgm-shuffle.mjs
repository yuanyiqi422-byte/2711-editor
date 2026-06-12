/**
 * Smoke test for MusicPicker randomTrack / shuffle pool logic.
 * Run: node scripts/test-bgm-shuffle.mjs
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = readFileSync(join(root, "frontend/js/music-picker.js"), "utf8");

const sandbox = {
  document: {
    getElementById: () => null,
    addEventListener: () => {},
    dispatchEvent: () => {},
    createElement: (tag) => ({
      canPlayType: () => "probably",
    }),
  },
  localStorage: {
    getItem: () => null,
    setItem: () => {},
  },
  VnAudio: {
    preview: () => {},
    isPlaying: () => false,
  },
  console,
  window: {
    setTimeout: (fn) => {
      fn();
      return 0;
    },
  },
};
vm.createContext(sandbox);
vm.runInContext(src + "\nthis.MusicPicker = MusicPicker;", sandbox);

const MusicPicker = sandbox.MusicPicker;
let failures = 0;

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL:", msg);
    failures += 1;
  } else {
    console.log("OK:", msg);
  }
}

const urbanPool = MusicPicker.buildShufflePool("urban_romance");
assert(urbanPool.length > 0, "urban shuffle pool non-empty");
assert(
  MusicPicker.GENTLE.every((f) => urbanPool.includes(f)),
  "GENTLE tracks included in urban shuffle pool"
);
assert(
  MusicPicker.STYLE_BGM_POOL.urban_romance.every((f) => urbanPool.includes(f)),
  "style pool tracks included in urban shuffle pool"
);

const seen = new Set();
for (let i = 0; i < 30; i += 1) {
  const pick = MusicPicker.randomTrack("urban_romance");
  assert(typeof pick === "string" && pick.length > 0, "randomTrack returns filename (iter " + i + ")");
  seen.add(pick);
}
assert(seen.size > 1, "randomTrack produces variety over 30 draws");

const resolved1 = MusicPicker.resolveForPlay("urban_romance");
assert(resolved1.fileUrl && resolved1.trackId, "resolveForPlay returns fileUrl + trackId");
assert(resolved1.trackId.includes("OCTOBER") || resolved1.trackId.includes("Time_to_love"), "trackId embeds filename slug");

MusicPicker.shuffleTrack();
const resolvedAfterShuffle = MusicPicker.resolveForPlay("urban_romance");
assert(
  resolvedAfterShuffle.fileUrl !== resolved1.fileUrl || resolvedAfterShuffle.trackId !== resolved1.trackId,
  "after shuffleTrack resolveForPlay differs from default (may rarely collide)"
);

console.log("\n" + (failures ? failures + " failure(s)" : "All checks passed"));
process.exit(failures ? 1 : 0);
