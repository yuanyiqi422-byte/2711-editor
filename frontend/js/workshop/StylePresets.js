/**
 * StylePresets — 视觉风格选择器
 */
(function (global) {
  function createStylePresets(options) {
    const buttons = document.querySelectorAll(".preset-btn");
    let selectedStyle = options.initialStyle || "urban_romance";
    const onChange = options.onChange || function () {};

    function syncAria() {
      buttons.forEach(function (b) {
        const active = b.classList.contains("preset-btn--active");
        b.setAttribute("aria-pressed", active ? "true" : "false");
      });
    }

    function setStyle(style) {
      selectedStyle = style;
      buttons.forEach(function (b) {
        b.classList.toggle("preset-btn--active", b.dataset.style === style);
      });
      syncAria();
      onChange(style);
    }

    function getStyle() {
      return selectedStyle;
    }

    buttons.forEach(function (btn) {
      btn.setAttribute("aria-pressed", btn.classList.contains("preset-btn--active") ? "true" : "false");
      btn.addEventListener("keydown", function (e) {
        const btns = Array.from(buttons);
        const idx = btns.indexOf(btn);
        if (e.key === "ArrowRight" || e.key === "ArrowDown") {
          e.preventDefault();
          btns[(idx + 1) % btns.length].focus();
        } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
          e.preventDefault();
          btns[(idx - 1 + btns.length) % btns.length].focus();
        }
      });
      btn.addEventListener("click", function () {
        buttons.forEach(function (b) { b.classList.remove("preset-btn--active"); });
        btn.classList.add("preset-btn--active");
        selectedStyle = btn.dataset.style;
        syncAria();
        onChange(selectedStyle);
      });
    });
    syncAria();

    return { getStyle: getStyle, setStyle: setStyle };
  }

  global.StylePresets = { create: createStylePresets };
})(typeof window !== "undefined" ? window : globalThis);
