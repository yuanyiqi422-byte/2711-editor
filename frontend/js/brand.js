/**
 * 2711编辑器 · 全站品牌常量（单一来源）
 */
(function (global) {
  const BRAND = {
    name: "2711编辑器",
    nameEn: "2711 Editor",
    nameEnShort: "2711 Editor",
    tagline: "您的故事与艺术刹那间生成互动场景",
    taglineSub:
      "上传小说或粘贴章节 · 选择视觉风格 · 自动生成分支剧情与场景画面",
    description:
      "2711编辑器 — 互动故事创作平台。将文本转化为带分支选择与场景画面的视觉小说，支持 TXT、Word、PDF、EPUB。",
    documentTitle: "2711编辑器 · 2711 Editor",
    footerLine: "2711 EDITOR · 2711编辑器",
    eyebrow: "V 0.2.5 · Interactive Story Studio",
    version: "0.2.5",
    logPrefix: "[2711编辑器]",
  };

  function applyBrand() {
    if (BRAND.documentTitle) document.title = BRAND.documentTitle;
    const meta = document.querySelector('meta[name="description"]');
    if (meta && BRAND.description) meta.setAttribute("content", BRAND.description);
    document.querySelectorAll("[data-brand]").forEach(function (el) {
      const key = el.getAttribute("data-brand");
      if (key && BRAND[key] != null) el.textContent = BRAND[key];
    });
    fetch("/api/health")
      .then(function (r) { return r.json(); })
      .then(function (h) {
        if (!h || !h.version) return;
        BRAND.version = h.version;
        BRAND.eyebrow = "V " + h.version + " · Interactive Story Studio";
        document.querySelectorAll('[data-brand="eyebrow"]').forEach(function (el) {
          el.textContent = BRAND.eyebrow;
        });
        document.querySelectorAll(".site-footer__copy").forEach(function (el) {
          el.textContent = "v" + h.version + " · AI 辅助创作 · 内容仅供体验";
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
