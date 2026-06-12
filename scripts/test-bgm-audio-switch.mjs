/**
 * Verify VnAudio.startHtmlFile switches src when trackId stable but url changes.
 * Run: node scripts/test-bgm-audio-switch.mjs
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

class FakeAudio {
  constructor(url) {
    this.src = url;
    this.currentSrc = url;
    this.loop = false;
    this.volume = 1;
    this.paused = true;
    this._listeners = {};
    this._children = [];
  }
  load() {}
  play() {
    this.paused = false;
    return Promise.resolve();
  }
  pause() {
    this.paused = true;
  }
  appendChild(node) {
    this._children.push(node);
    if (node && node.src) this.src = node.src;
    return node;
  }
  addEventListener(ev, fn) {
    (this._listeners[ev] = this._listeners[ev] || []).push(fn);
  }
}

let audioInstances = [];
const sandbox = {
  window: {},
  document: {
    addEventListener: () => {},
    dispatchEvent: () => {},
    createElement: function (tag) {
      if (tag === "audio") {
        return { canPlayType: () => "probably" };
      }
      if (tag === "source") {
        return { src: "", type: "" };
      }
      return {};
    },
  },
  localStorage: { getItem: () => null, setItem: () => {} },
  Audio: function (url) {
    const a = new FakeAudio(url);
    audioInstances.push(a);
    return a;
  },
  matchMedia: () => ({ matches: false }),
  console,
};
sandbox.window = sandbox;

vm.createContext(sandbox);
vm.runInContext(readFileSync(join(root, "frontend/js/audio.js"), "utf8") + "\nthis.VnAudio = VnAudio;", sandbox);

const VnAudio = sandbox.VnAudio;
const urlA = "audio/bgm/track-a.mp3";
const urlB = "audio/bgm/track-b.mp3";
const trackId = "auto_manual_urban_romance_same_id";

VnAudio.start({ style: "urban_romance", trackId, fileUrl: urlA });
const first = audioInstances[0];
if (!first || first.src !== urlA) throw new Error("first start failed");

VnAudio.start({ style: "urban_romance", trackId, fileUrl: urlB });
const second = audioInstances[1];
if (!second || second.src !== urlB) {
  throw new Error("second start did not create new audio with new url");
}
if (second === first) throw new Error("expected new Audio element after url change");

console.log("OK: VnAudio switches src when fileUrl changes even if trackId matches");
process.exit(0);
