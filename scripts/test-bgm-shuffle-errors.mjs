/**
 * Simulates stale BGM load errors during shuffle — ensures one shuffle → one play.
 * Run: node scripts/test-bgm-shuffle-errors.mjs
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const pickerSrc = readFileSync(join(root, "frontend/js/music-picker.js"), "utf8");

const playLog = [];
let playing = false;

const listeners = new Map();

const sandbox = {
  document: {
    getElementById: () => null,
    addEventListener: (type, fn) => {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(fn);
    },
    dispatchEvent: (ev) => {
      const fns = listeners.get(ev.type) || [];
      fns.forEach((fn) => fn(ev));
      return true;
    },
    createElement: () => ({
      canPlayType: () => "probably",
    }),
  },
  localStorage: {
    getItem: () => null,
    setItem: () => {},
  },
  VnAudio: {
    preview: (opts) => {
      playLog.push({ action: "preview", trackId: opts && opts.trackId, fileUrl: opts && opts.fileUrl });
      playing = true;
    },
    start: (opts) => {
      playLog.push({ action: "start", trackId: opts && opts.trackId, fileUrl: opts && opts.fileUrl });
      playing = true;
    },
    stop: () => {
      playing = false;
    },
    isPlaying: () => playing,
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
vm.runInContext(pickerSrc + "\nthis.MusicPicker = MusicPicker;", sandbox);
sandbox.MusicPicker.init();

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

function dispatchLoadError(detail) {
  sandbox.document.dispatchEvent({
    type: "vn-bgm-load-error",
    detail,
  });
}

playLog.length = 0;
MusicPicker.shuffleTrack();
assert(playLog.length === 1, "single shuffle triggers exactly one preview");
const firstTrack = playLog[0].trackId;

dispatchLoadError({
  trackId: "style_urban_romance|Journey.mp3",
  filename: "Journey.mp3",
  style: "urban_romance",
  reason: "load_error",
});
assert(playLog.length === 1, "stale error for different trackId does not auto-skip");

const activeFilename = MusicPicker.getCurrentFilename();
dispatchLoadError({
  trackId: firstTrack,
  filename: activeFilename,
  style: "urban_romance",
  reason: "load_error",
});
assert(playLog.length === 2, "active track load error triggers one auto-skip");
assert(playLog[1].action === "start", "auto-skip uses VnAudio.start");

const debounceBase = playLog.length;
MusicPicker.shuffleTrack();
const afterOneShuffle = playLog.length - debounceBase;
MusicPicker.shuffleTrack();
assert(
  playLog.length - debounceBase === afterOneShuffle,
  "rapid second shuffle does not trigger another preview"
);

console.log("\n" + (failures ? failures + " failure(s)" : "All error-simulation checks passed"));
process.exit(failures ? 1 : 0);
