/**
 * 2711编辑器 · 全站品牌常量（单一来源）
 * 定位：视觉小说启动器 — 非 AI 写作工具
 */
(function (global) {
  const BRAND = {
    name: "2711编辑器",
    nameCn: "2711编辑器",
    nameNum: "2711",
    nameSuffix: "编辑器",
    nameEn: "2711 Editor",
    nameEnShort: "2711 Editor",
    nameEnUpper: "2711 EDITOR",
    tagline: "故事苏醒，成为可玩的旅程",
    taglineSub: "上传故事 · 选择世界 · 开启分支冒险",
    description:
      "2711编辑器 — 视觉小说启动器。将小说化为可推开的互动世界，携分支抉择与场景画面步入故事旅程。",
    documentTitle: "2711编辑器 · 视觉小说启动器",
    footerLine: "2711 Editor",
    eyebrow: "VISUAL NOVEL LAUNCHER",
    quoteLuminous: "Wish you a Luminous Journey",
    quoteZest: "May your Zest Continue to shine",
    /** Workbench topbar logo icon (book + quill) beside two-line wordmark */
    workbenchLogo: "images/workbench/2711-logo-icon.png",
    workbenchIcon: "images/workbench/2711-logo-icon.png",
    version: "0.2.5",
    logPrefix: "[2711编辑器]",
  };

  var EPIGRAPH_CAPS = {
    quoteLuminous: new Set(["W", "L", "J"]),
    quoteZest: new Set(["M", "Z", "C"]),
  };

  function wrapEpigraphCaps(el) {
    if (!el || el.dataset.capsWrapped) return;
    const brand = el.getAttribute("data-brand");
    const caps = brand && EPIGRAPH_CAPS[brand];
    if (!caps) return;
    const text = (el.textContent || "").trim();
    if (!text) return;
    el.innerHTML = text
      .split("")
      .map(function (ch) {
        if (caps.has(ch.toUpperCase())) {
          return '<span class="workbench__epigraph-cap">' + ch + "</span>";
        }
        return ch;
      })
      .join("");
    el.dataset.capsWrapped = "1";
  }

  function applyBrand() {
    if (BRAND.documentTitle) document.title = BRAND.documentTitle;
    const meta = document.querySelector('meta[name="description"]');
    if (meta && BRAND.description) meta.setAttribute("content", BRAND.description);
    document.querySelectorAll("[data-brand]").forEach(function (el) {
      const key = el.getAttribute("data-brand");
      if (key && BRAND[key] != null) el.textContent = BRAND[key];
    });
    document
      .querySelectorAll(".workbench__epigraph-line[data-brand]")
      .forEach(wrapEpigraphCaps);
    var brandLink = document.querySelector(".workbench__brand--logo");
    if (brandLink && BRAND.nameCn && BRAND.nameEn) {
      brandLink.setAttribute("aria-label", BRAND.nameCn + " · " + BRAND.nameEn);
    }
    var brandIcon = document.querySelector(".logo-lockup-unified__icon");
    var iconPath = BRAND.workbenchIcon || BRAND.workbenchLogo;
    if (brandIcon && iconPath) {
      brandIcon.setAttribute("src", iconPath);
    }
    var numerals = document.querySelector(".workbench__brand--logo .sigil-numerals");
    if (numerals && BRAND.nameNum) numerals.textContent = BRAND.nameNum;
    var sigilEditor = document.querySelector(".workbench__brand--logo .sigil-editor");
    if (sigilEditor && BRAND.nameEn) {
      var editorLabel = String(BRAND.nameEn).replace(/^\s*2711\s*/i, "").trim();
      sigilEditor.textContent = editorLabel || "Editor";
    }
    var sigilZh = document.querySelector(".workbench__brand--logo .sigil-zh");
    if (sigilZh && BRAND.nameSuffix) sigilZh.textContent = BRAND.nameSuffix;
    fetch("/api/health")
      .then(function (r) { return r.json(); })
      .then(function (h) {
        if (!h || !h.version) return;
        BRAND.version = h.version;
        document.querySelectorAll(".site-footer__copy").forEach(function (el) {
          el.textContent = "v" + h.version + " · 旅途愉快 · 内容仅供体验";
        });
      })
      .catch(function () {});
  }

  global.BRAND = BRAND;
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", applyBrand);
    } else {
      applyBrand();
    }
  }
})(typeof window !== "undefined" ? window : globalThis);
