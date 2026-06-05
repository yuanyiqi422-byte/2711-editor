import js from "@eslint/js";
import globals from "globals";

/** Globals attached via ordered <script> tags in index.html (IIFE pattern). */
const appGlobals = {
  StudioController: "readonly",
  NarrativeGame: "readonly",
  MoodBackgrounds: "readonly",
  SceneImages: "readonly",
  HistoryPanel: "readonly",
  StylePresets: "readonly",
  EditorInput: "readonly",
  PipelineView: "readonly",
  CreateFlow: "readonly",
  DEMO_GAME_PACK: "readonly",
  BRAND: "readonly",
  SseClient: "readonly",
  ApiErrors: "readonly",
};

export default [
  {
    ignores: ["node_modules/**"],
  },
  js.configs.recommended,
  {
    files: ["frontend/js/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        ...globals.browser,
        ...appGlobals,
      },
    },
    rules: {
      "no-redeclare": "off",
      "no-unused-vars": ["warn", {
        argsIgnorePattern: "^_|^e$",
        varsIgnorePattern: "^(NarrativeGame|HistoryPanel|MoodBackgrounds|SceneImages|DEMO_GAME_PACK|_|e)$",
      }],
      "no-console": "off",
      eqeqeq: ["error", "smart"],
      "no-undef": "error",
    },
  },
  {
    files: ["scripts/**/*.mjs"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: globals.node,
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    },
  },
];
