/** 2711 Editor · Workbench chrome — 三栏布局 + 移动端历史侧栏 */



(function () {

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const desktopMq = window.matchMedia("(min-width: 1024px)");

  const THEME_KEY = "2711-workbench-theme";



  const host = document.getElementById("workbench-particles");

  const loadPanel = document.getElementById("workshop-history");

  const closeBtn = document.getElementById("history-close-btn");

  const backdrop = document.getElementById("history-backdrop");

  const studio = document.getElementById("studio");

  const workbenchRoot = document.getElementById("landing-view");

  const themeToggle = document.getElementById("workbench-theme-toggle");

  const sunIcon = themeToggle && themeToggle.querySelector(".workbench__theme-toggle-icon--sun");

  const moonIcon = themeToggle && themeToggle.querySelector(".workbench__theme-toggle-icon--moon");



  if (host && !reduced) {

    const count = window.matchMedia("(max-width: 767.98px)").matches ? 8 : 14;

    for (let i = 0; i < count; i += 1) {

      const p = document.createElement("span");

      p.className = "workbench__particle";

      p.setAttribute("aria-hidden", "true");

      const size = 2 + Math.random() * 3;

      p.style.width = size + "px";

      p.style.height = size + "px";

      p.style.left = (6 + Math.random() * 88).toFixed(1) + "%";

      p.style.top = (10 + Math.random() * 80).toFixed(1) + "%";

      p.style.setProperty("--p-dur", (18 + Math.random() * 20).toFixed(1) + "s");

      p.style.setProperty("--p-delay", (-Math.random() * 24).toFixed(1) + "s");

      p.style.setProperty("--p-x", (-16 + Math.random() * 32).toFixed(0) + "px");

      p.style.setProperty("--p-y", (-60 - Math.random() * 40).toFixed(0) + "px");

      p.style.setProperty("--p-opacity", (0.15 + Math.random() * 0.25).toFixed(2));

      host.appendChild(p);

    }

  }



  function isDesktopRail() {

    return desktopMq.matches;

  }



  function syncRailMode() {

    if (!loadPanel || !studio) return;

    studio.classList.add("has-load-rail");

    loadPanel.classList.remove("is-open");

    loadPanel.setAttribute("aria-hidden", "false");

    if (backdrop) {

      backdrop.hidden = true;

      backdrop.classList.remove("is-visible");

    }

  }



  function setDrawerOpen(open) {

    if (!loadPanel || isDesktopRail()) return;

    loadPanel.classList.toggle("is-open", open);

    loadPanel.setAttribute("aria-hidden", open ? "false" : "true");

    if (backdrop) {

      backdrop.hidden = !open;

      backdrop.classList.toggle("is-visible", open);

    }

    if (open && typeof HistoryPanel !== "undefined" && HistoryPanel.refresh) {

      HistoryPanel.refresh();

    }

  }



  function pulseLoadPanel() {

    if (!loadPanel) return;

    loadPanel.classList.add("is-highlight");

    window.setTimeout(function () {

      loadPanel.classList.remove("is-highlight");

    }, 1200);

    const first = loadPanel.querySelector(".history-item");

    if (first) first.focus({ preventScroll: true });

  }



  function applyTheme(dim) {

    if (!workbenchRoot) return;

    workbenchRoot.classList.toggle("workbench--dim", dim);

    workbenchRoot.classList.toggle("workbench--luminous", !dim);

    if (themeToggle) {

      themeToggle.classList.toggle("is-active", !dim);

      themeToggle.setAttribute("aria-pressed", dim ? "true" : "false");

      themeToggle.setAttribute(

        "aria-label",

        dim ? "切换为明亮光效" : "切换为柔和光效"

      );

      themeToggle.title = dim ? "切换为明亮光效" : "切换为柔和光效";

    }

    if (sunIcon) sunIcon.hidden = dim;

    if (moonIcon) moonIcon.hidden = !dim;

    try {

      localStorage.setItem(THEME_KEY, dim ? "dim" : "luminous");

    } catch (_e) { /* ignore */ }

  }



  function readStoredTheme() {

    try {

      return localStorage.getItem(THEME_KEY);

    } catch (_e) {

      return null;

    }

  }



  if (closeBtn) {

    closeBtn.addEventListener("click", function () {

      setDrawerOpen(false);

    });

  }



  if (backdrop) {

    backdrop.addEventListener("click", function () {

      setDrawerOpen(false);

    });

  }



  document.addEventListener("keydown", function (e) {

    if (e.key === "Escape" && loadPanel && loadPanel.classList.contains("is-open") && !isDesktopRail()) {

      setDrawerOpen(false);

    }

  });



  if (themeToggle && workbenchRoot) {

    const stored = readStoredTheme();

    applyTheme(stored === "dim");

    themeToggle.addEventListener("click", function () {

      applyTheme(!workbenchRoot.classList.contains("workbench--dim"));

    });

  }



  if (desktopMq.addEventListener) {

    desktopMq.addEventListener("change", syncRailMode);

  } else if (desktopMq.addListener) {

    desktopMq.addListener(syncRailMode);

  }

  syncRailMode();



  window.WorkbenchChrome = { pulseLoadPanel: pulseLoadPanel };

})();


