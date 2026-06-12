/**
 * StylePresets — RPG 职业式风格选择 + 场景舞台同步
 */
(function (global) {
  const SCENE_VERSION = 14;
  const STYLE_ORDER = ["xianxia", "urban_romance", "mystery", "campus"];

  /** Lite previews (~3MB) — full world-*.png variants are 8–10MB each */
  const PRESET_META = {
    xianxia: {
      label: "古风仙侠",
      labelEn: "Ancient Fantasy",
      tagline: "云海仙山 · 宗门秘境 · 剑意长风",
      desc: "叙事气质 · 场景图池",
      preview: "images/workbench/cloud-pavilion.png",
      hint: "仙侠文风的对白与选项；游玩时场景偏云海仙山、宗门秘境。",
      accent: "rgba(155, 122, 212, 0.42)",
      icon: "仙",
    },
    urban_romance: {
      label: "都市言情",
      labelEn: "Urban Romance",
      tagline: "霓虹深夜 · 咖啡香气",
      desc: "叙事气质 · 场景图池",
      preview: "images/workbench/city-terrace-cafe.png",
      hint: "都市恋爱口吻的对白与选项；游玩时场景偏霓虹街景、咖啡馆与写字楼。",
      accent: "rgba(216, 154, 165, 0.45)",
      icon: "都",
    },
    mystery: {
      label: "悬疑推理",
      labelEn: "Mystery Detective",
      tagline: "档案密室 · 雨夜迷踪",
      desc: "叙事气质 · 场景图池",
      preview: "images/workbench/rainy-library.png",
      hint: "克制悬疑语气的对白；游玩时场景偏雨夜追踪、档案室与冷灰蓝调。",
      accent: "rgba(143, 164, 200, 0.48)",
      icon: "悬",
    },
    campus: {
      label: "校园青春",
      labelEn: "Campus Youth",
      tagline: "蝉鸣操场 · 夏日午后",
      desc: "叙事气质 · 场景图池",
      preview: "images/workbench/school-corridor.png",
      hint: "青春口语的对白；游玩时场景偏教室走廊、社团与午后阳光。",
      accent: "rgba(141, 177, 143, 0.42)",
      icon: "校",
    },
  };

  function updateDots(style) {
    const dots = document.querySelectorAll(".scene-stage__dot");
    dots.forEach(function (dot) {
      dot.classList.toggle("is-active", dot.dataset.style === style);
    });
  }

  function thumbSrc(style) {
    const meta = PRESET_META[style];
    return meta && meta.preview ? meta.preview + "?v=" + SCENE_VERSION : "";
  }

  function ensurePresetThumbLoaded(btn) {
    if (!btn) return;
    const img = btn.querySelector(".class-rpg__bg img");
    if (!img) return;
    const src = thumbSrc(btn.dataset.style);
    if (!src) return;
    if (img.getAttribute("src") !== src) {
      img.setAttribute("src", src);
    }
    img.classList.remove("is-error");
  }

  function preloadAllPresetImages() {
    STYLE_ORDER.forEach(function (style) {
      const src = thumbSrc(style);
      if (!src) return;
      const img = new Image();
      img.decoding = "async";
      img.src = src;
    });
  }

  function bindPreviewRetry(img, src) {
    if (!img || img.dataset.retryBound === "1") return;
    img.dataset.retryBound = "1";
    img.addEventListener("error", function onPreviewError() {
      const retries = parseInt(img.dataset.retries || "0", 10);
      if (retries >= 2) {
        img.classList.add("is-error");
        return;
      }
      img.dataset.retries = String(retries + 1);
      setTimeout(function () {
        img.src = src + (src.indexOf("?") >= 0 ? "&" : "?") + "retry=" + Date.now();
      }, 900 + retries * 600);
    });
  }

  function applyStyleVisual(style) {
    const meta = PRESET_META[style] || PRESET_META.urban_romance;
    const panel = document.getElementById("studio");
    if (panel) panel.setAttribute("data-style", style);

    const src = meta.preview + "?v=" + SCENE_VERSION;
    const img = document.getElementById("style-preview-img");
    const hint = document.getElementById("style-preview-hint");
    const label = document.getElementById("style-preview-label");
    const tagline = document.getElementById("style-preview-tagline");
    const badge = document.getElementById("style-preview-badge");
    if (img) {
      bindPreviewRetry(img, src);
      if (img.getAttribute("src") !== src) {
        img.src = src;
      }
      img.alt = (meta.labelEn || meta.label) + " world preview";
      img.classList.remove("is-error");
    }

    const activeBtn = document.querySelector('.preset-btn[data-style="' + style + '"]');
    ensurePresetThumbLoaded(activeBtn);
    if (hint) hint.textContent = meta.hint;
    if (label) label.textContent = meta.label;
    if (tagline) tagline.textContent = meta.tagline;
    if (badge) badge.hidden = false;
    updateDots(style);
  }

  function createStylePresets(options) {
    const buttons = document.querySelectorAll(".preset-btn");
    const prevBtn = document.getElementById("style-preview-prev");
    const nextBtn = document.getElementById("style-preview-next");
    const styleHub = document.querySelector(".style-hub");
    let selectedStyle = options.initialStyle || "urban_romance";
    const onChange = options.onChange || function () {};

    function syncAria() {
      buttons.forEach(function (b) {
        const active = b.classList.contains("preset-btn--active");
        b.setAttribute("aria-pressed", active ? "true" : "false");
        if (b.getAttribute("role") === "radio") {
          b.setAttribute("aria-checked", active ? "true" : "false");
        }
      });
    }

    function setStyle(style) {
      if (!PRESET_META[style]) return;
      selectedStyle = style;
      buttons.forEach(function (b) {
        b.classList.toggle("preset-btn--active", b.dataset.style === style);
      });
      syncAria();
      applyStyleVisual(style);
      onChange(style);
    }

    function stepStyle(delta) {
      const idx = STYLE_ORDER.indexOf(selectedStyle);
      const base = idx >= 0 ? idx : 0;
      const next = STYLE_ORDER[(base + delta + STYLE_ORDER.length) % STYLE_ORDER.length];
      setStyle(next);
    }

    function getStyle() {
      return selectedStyle;
    }

    preloadAllPresetImages();
    buttons.forEach(function (btn) {
      btn.setAttribute("aria-pressed", btn.classList.contains("preset-btn--active") ? "true" : "false");
      ensurePresetThumbLoaded(btn);
      btn.addEventListener("keydown", function (e) {
        const btns = Array.from(buttons);
        const idx = btns.indexOf(btn);
        if (e.key === "ArrowRight" || e.key === "ArrowDown") {
          e.preventDefault();
          stepStyle(1);
          btns.find(function (b) { return b.dataset.style === selectedStyle; }).focus();
        } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
          e.preventDefault();
          stepStyle(-1);
          btns.find(function (b) { return b.dataset.style === selectedStyle; }).focus();
        } else if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setStyle(btn.dataset.style);
        }
      });
      btn.addEventListener("click", function () {
        setStyle(btn.dataset.style);
      });
    });

    if (prevBtn) {
      prevBtn.addEventListener("click", function () { stepStyle(-1); });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () { stepStyle(1); });
    }

    if (styleHub) {
      styleHub.addEventListener("keydown", function (e) {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
        const tag = (e.target && e.target.tagName) || "";
        if (tag === "TEXTAREA" || tag === "INPUT" || tag === "SELECT") return;
        e.preventDefault();
        stepStyle(e.key === "ArrowRight" ? 1 : -1);
      });
    }

    applyStyleVisual(selectedStyle);
    syncAria();

    return { getStyle: getStyle, setStyle: setStyle, getMeta: function () { return PRESET_META; } };
  }

  global.StylePresets = { create: createStylePresets, PRESET_META: PRESET_META, STYLE_ORDER: STYLE_ORDER };
})(typeof window !== "undefined" ? window : globalThis);
