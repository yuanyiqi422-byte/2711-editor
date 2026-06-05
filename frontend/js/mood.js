/** 场景氛围背景 — 绿野主色 + 蓝天 + 樱花粉点缀（吉卜力水彩） */
const MoodBackgrounds = (function () {
  const MOODS = {
    dark_mystery:
      "radial-gradient(ellipse 85% 65% at 50% 25%, #5a7860 0%, #4a6850 38%, #3a4858 72%, #2a3848 100%)",
    neon_rain:
      "radial-gradient(ellipse 80% 55% at 35% 18%, #a8d4ff 0%, #6b8e6b 32%, #7eb8ff 55%, rgba(248,168,200,0.35) 100%)",
    golden_dawn:
      "radial-gradient(ellipse 95% 60% at 50% 8%, #ffc8dd 0%, #b8d4c8 22%, #6b8e6b 48%, #a8d4ff 72%, #faf6ed 100%)",
    storm_sea:
      "radial-gradient(ellipse 78% 58% at 50% 42%, #6b8e6b 0%, #5a8fc8 38%, #4a5868 72%, #3a4058 100%)",
    neutral:
      "radial-gradient(ellipse 88% 62% at 50% 28%, #a8d4ff 0%, #8ab898 30%, #6b8e6b 52%, #eef5e8 78%, rgba(248,168,200,0.18) 100%)",
    calm:
      "radial-gradient(ellipse 88% 62% at 50% 28%, #a8d4ff 0%, #8ab898 30%, #6b8e6b 52%, #eef5e8 78%, rgba(248,168,200,0.18) 100%)",
    tense:
      "radial-gradient(ellipse 78% 58% at 50% 42%, #6b8e6b 0%, #5a8fc8 38%, #4a5868 72%, #3a4058 100%)",
    romantic:
      "radial-gradient(ellipse 95% 60% at 50% 8%, #ffc8dd 0%, #b8d4c8 22%, #6b8e6b 48%, #a8d4ff 72%, #faf6ed 100%)",
    mysterious:
      "radial-gradient(ellipse 85% 65% at 50% 25%, #5a7860 0%, #4a6850 38%, #3a4858 72%, #2a3848 100%)",
    sad:
      "radial-gradient(ellipse 78% 58% at 50% 42%, #6b8e6b 0%, #5a8fc8 38%, #4a5868 72%, #3a4058 100%)",
    hopeful:
      "radial-gradient(ellipse 95% 60% at 50% 8%, #ffc8dd 0%, #b8d4c8 22%, #6b8e6b 48%, #a8d4ff 72%, #faf6ed 100%)",
  };

  const STYLE_OVERLAY = {
    xianxia: "linear-gradient(165deg, rgba(107,142,107,0.18), rgba(126,184,255,0.12))",
    urban_romance: "linear-gradient(140deg, rgba(168,212,255,0.16), rgba(248,168,200,0.1))",
    mystery: "linear-gradient(180deg, rgba(74,104,80,0.22), rgba(58,64,88,0.16))",
    campus: "linear-gradient(155deg, rgba(107,142,107,0.16), rgba(255,200,221,0.12))",
  };

  let activeLayerId = "a";

  function gradientFor(mood, style) {
    const key = MOODS[mood] ? mood : "neutral";
    const base = MOODS[key] || MOODS.neutral;
    const overlay = STYLE_OVERLAY[style] || "";
    return overlay ? overlay + ", " + base : base;
  }

  function getLayers(container) {
    const root = container || document.getElementById("scene-bg");
    if (!root) return { root: null, a: null, b: null };
    return {
      root: root,
      a: root.querySelector("#scene-bg-a") || document.getElementById("scene-bg-a"),
      b: root.querySelector("#scene-bg-b") || document.getElementById("scene-bg-b"),
    };
  }

  function setLayerStyle(layer, backgroundImage, filter) {
    if (!layer) return;
    layer.style.backgroundImage = backgroundImage;
    layer.style.backgroundSize = "cover";
    layer.style.backgroundPosition = "center";
    layer.style.backgroundRepeat = "no-repeat";
    layer.style.backgroundColor = "#4a5850";
    layer.style.filter = filter || "saturate(0.96) brightness(1)";
  }

  function filterFor(mood) {
    if (mood === "neon_rain") return "saturate(0.94) brightness(0.97)";
    if (mood === "golden_dawn" || mood === "hopeful" || mood === "romantic") {
      return "saturate(1.04) brightness(1.02)";
    }
    return "saturate(0.96) brightness(1)";
  }

  function resolveScene(mood, style, imagePrompt) {
    const moodKey = (mood || "neutral").toLowerCase();
    if (typeof SceneImages !== "undefined" && SceneImages.resolve) {
      return SceneImages.resolve(moodKey, style, imagePrompt || "");
    }
    return {
      path: null,
      veil: null,
      mood: moodKey,
    };
  }

  function apply(container, mood, style, imagePrompt) {
    const layers = getLayers(container);
    if (!layers.root) return;

    const moodKey = MOODS[mood] ? mood : "neutral";
    const gradient = gradientFor(moodKey, style);
    const filter = filterFor(moodKey);
    const resolved = resolveScene(moodKey, style, imagePrompt);
    const veil = resolved.veil || "linear-gradient(180deg, rgba(250,246,237,0.08) 0%, rgba(58,72,58,0.14) 100%)";

    const next = activeLayerId === "a" ? layers.b : layers.a;
    const prev = activeLayerId === "a" ? layers.a : layers.b;
    if (!next) {
      layers.root.style.backgroundImage = gradient;
      return;
    }

    function showGradient() {
      setLayerStyle(next, gradient, filter);
      layers.root.classList.remove("has-scene-image");
    }

    if (resolved.path) {
      const probe = new Image();
      probe.onload = function () {
        setLayerStyle(next, veil + ', url("' + resolved.path + '")', filter);
        layers.root.classList.add("has-scene-image");
        layers.root.setAttribute("data-scene-mood", moodKey);
        if (prev) prev.classList.remove("is-active");
        next.classList.add("is-active");
        activeLayerId = activeLayerId === "a" ? "b" : "a";
      };
      probe.onerror = showGradient;
      probe.src = resolved.path;
    } else {
      showGradient();
      if (prev) prev.classList.remove("is-active");
      next.classList.add("is-active");
      activeLayerId = activeLayerId === "a" ? "b" : "a";
    }

    if (imagePrompt) {
      layers.root.setAttribute("data-image-prompt", imagePrompt.slice(0, 120));
    } else {
      layers.root.removeAttribute("data-image-prompt");
    }
  }

  return { apply, gradientFor };
})();
