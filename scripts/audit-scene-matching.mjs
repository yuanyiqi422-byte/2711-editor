#!/usr/bin/env node
/** One-off audit: SCENES PNG paths + KEYWORD_SCORES resolve tests */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const src = fs.readFileSync(path.join(root, "frontend/js/scene-images.js"), "utf8");

// Minimal eval of SceneImages logic
const VERSION = Number(src.match(/const VERSION = (\d+)/)?.[1] ?? 0);
const scenesBlock = src.match(/const SCENES = \{([\s\S]*?)\};/)[1];
const SCENES = {};
for (const m of scenesBlock.matchAll(/^\s+(\w+):/gm)) SCENES[m[1]] = true;
const sceneIds = Object.keys(SCENES);

const kwBlock = src.match(/const KEYWORD_SCORES = \{([\s\S]*?)\};/)[1];
const KEYWORD_SCORES = {};
for (const m of kwBlock.matchAll(/"([^"]+)":\s*\{([^}]+)\}/g)) {
  const weights = {};
  for (const w of m[2].matchAll(/(\w+):\s*(\d+)/g)) weights[w[1]] = Number(w[2]);
  KEYWORD_SCORES[m[1]] = weights;
}

const MOOD_DEFAULTS = {};
for (const m of src.match(/const MOOD_DEFAULTS = \{([\s\S]*?)\};/)[1].matchAll(/(\w+):\s*"([^"]+)"/g)) {
  MOOD_DEFAULTS[m[1]] = m[2];
}
const STYLE_DEFAULTS = {};
for (const m of src.match(/const STYLE_DEFAULTS = \{([\s\S]*?)\};/)[1].matchAll(/(\w+):\s*"([^"]+)"/g)) {
  STYLE_DEFAULTS[m[1]] = m[2];
}

function tokenize(text) {
  if (!text) return [];
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fff\s_-]/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

function scoreFromPrompt(prompt) {
  const scores = {};
  const tokens = tokenize(prompt);
  const blob = tokens.join(" ");
  const keywords = Object.keys(KEYWORD_SCORES).sort((a, b) => b.length - a.length);
  for (const keyword of keywords) {
    if (!blob.includes(keyword)) continue;
    for (const [sceneId, w] of Object.entries(KEYWORD_SCORES[keyword])) {
      scores[sceneId] = (scores[sceneId] || 0) + w;
    }
  }
  for (const token of tokens) {
    if (KEYWORD_SCORES[token]) {
      for (const [sceneId, w] of Object.entries(KEYWORD_SCORES[token])) {
        scores[sceneId] = (scores[sceneId] || 0) + w * 1.5;
      }
    }
  }
  return scores;
}

function resolve(mood, style, imagePrompt) {
  const moodKey = (mood || "neutral").toLowerCase();
  const scores = scoreFromPrompt(imagePrompt || "");
  if (Object.keys(scores).length === 0) {
    const fallback = MOOD_DEFAULTS[moodKey] || STYLE_DEFAULTS[style] || "calm_meadow";
    return { sceneId: fallback, score: 0, top: [] };
  }
  let bestId = null;
  let bestScore = -1;
  for (const [id, s0] of Object.entries(scores)) {
    if (!SCENES[id]) continue;
    let s = s0;
    if (MOOD_DEFAULTS[moodKey] === id) s += 2;
    if (STYLE_DEFAULTS[style] === id) s += 1.5;
    if (s > bestScore) {
      bestScore = s;
      bestId = id;
    }
  }
  const top = Object.entries(scores)
    .filter(([id]) => SCENES[id])
    .map(([id, s]) => {
      let adj = s;
      if (MOOD_DEFAULTS[moodKey] === id) adj += 2;
      if (STYLE_DEFAULTS[style] === id) adj += 1.5;
      return { id, score: adj };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);
  return { sceneId: bestId || "calm_meadow", score: bestScore, top };
}

// PNG audit
const pngDir = path.join(root, "frontend/images/scenes");
const pngFiles = new Set(fs.readdirSync(pngDir).filter((f) => f.endsWith(".png")).map((f) => f.replace(".png", "")));
const kwSceneIds = new Set();
for (const weights of Object.values(KEYWORD_SCORES)) {
  for (const id of Object.keys(weights)) kwSceneIds.add(id);
}
const missingInScenes = [...kwSceneIds].filter((id) => !SCENES[id]).sort();
const missingPng = sceneIds.filter((id) => !pngFiles.has(id)).sort();

console.log("=== PNG / SCENES ===");
console.log("SCENES:", sceneIds.length, "PNG files:", pngFiles.size);
console.log("KEYWORD refs missing SCENES entry:", missingInScenes.join(", ") || "(none)");
console.log("SCENES missing PNG:", missingPng.join(", ") || "(none)");

const samples = [
  { phrase: "食堂吃饭", mood: "neutral", style: "campus" },
  { phrase: "school cafeteria lunch", mood: "neutral", style: "campus" },
  { phrase: "皇宫大殿", mood: "neutral", style: "xianxia" },
  { phrase: "imperial palace throne hall", mood: "golden_dawn", style: "xianxia" },
  { phrase: "太平间", mood: "dark_mystery", style: "mystery" },
  { phrase: "morgue corridor", mood: "dark_mystery", style: "mystery" },
  { phrase: "考场", mood: "tense", style: "campus" },
  { phrase: "exam hall silent", mood: "tense", style: "campus" },
  { phrase: "客栈", mood: "neutral", style: "xianxia" },
  { phrase: "ancient inn courtyard rain", mood: "mysterious", style: "xianxia" },
  { phrase: "悬疑案发现场", mood: "dark_mystery", style: "mystery" },
  { phrase: "都市夜景霓虹", mood: "neon_rain", style: "urban_romance" },
  { phrase: "校园操场", mood: "hopeful", style: "campus" },
  { phrase: "古代客栈烟雨", mood: "mysterious", style: "xianxia" },
];

console.log("\n=== SAMPLE RESOLVE ===");
for (const s of samples) {
  const r = resolve(s.mood, s.style, s.phrase);
  console.log(`"${s.phrase}" [${s.style}/${s.mood}] -> ${r.sceneId} (${r.score})`);
  console.log("  top:", r.top.map((t) => `${t.id}:${t.score}`).join(", "));
}
