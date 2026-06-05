/** 2711 Editor · 全屏分页导航（点击切换，非长页滚动） */
(function () {
  const SLUGS = ["top", "features", "how", "create"];
  const SLUG_ALIASES = { studio: "create" };
  const LABELS = ["首屏", "能力", "流程", "创作"];

  const landing = document.getElementById("landing-view");
  const track = document.querySelector(".landing-pages__track");
  const pages = track ? Array.from(track.querySelectorAll(".landing-page")) : [];

  if (!landing || !track || !pages.length) return;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const nav = document.getElementById("site-nav");
  const prevBtn = document.getElementById("page-nav-prev");
  const nextBtn = document.getElementById("page-nav-next");
  const dotsHost = document.getElementById("page-nav-dots");
  const heroNextBtn = document.getElementById("hero-next-btn");

  let current = 0;
  let animating = false;
  const listeners = [];

  function slugIndex(slug) {
    const resolved = SLUG_ALIASES[slug] || slug;
    const i = SLUGS.indexOf(resolved);
    return i >= 0 ? i : 0;
  }

  function clampIndex(index) {
    return Math.max(0, Math.min(pages.length - 1, index));
  }

  function emitChange() {
    const detail = {
      index: current,
      slug: SLUGS[current] || "top",
      page: pages[current],
    };
    listeners.forEach(function (fn) { fn(detail); });
    document.dispatchEvent(new CustomEvent("landing:pagechange", { detail: detail }));
  }

  function applyTrack() {
    track.style.transform = "translate3d(0, " + (-current * 100) + "%, 0)";
    track.setAttribute("data-current", String(current));
    landing.setAttribute("data-page-index", String(current));
    landing.setAttribute("data-page-slug", SLUGS[current] || "top");

    if (nav) {
      nav.classList.toggle("is-scrolled", current > 0);
    }

    pages.forEach(function (page, i) {
      const active = i === current;
      page.classList.toggle("is-active", active);
      page.setAttribute("aria-hidden", active ? "false" : "true");
      if (active) page.scrollTop = 0;
    });

    if (dotsHost) {
      dotsHost.querySelectorAll(".page-nav__dot").forEach(function (dot, i) {
        const on = i === current;
        dot.classList.toggle("is-active", on);
        dot.setAttribute("aria-selected", on ? "true" : "false");
        dot.setAttribute("tabindex", on ? "0" : "-1");
      });
    }

    if (prevBtn) prevBtn.disabled = current <= 0;
    if (nextBtn) nextBtn.disabled = current >= pages.length - 1;

    const hash = SLUGS[current] === "top" ? "" : "#" + SLUGS[current];
    if (window.location.hash !== hash) {
      history.replaceState(null, "", hash || window.location.pathname + window.location.search);
    }

    emitChange();
  }

  function goTo(target, opts) {
    const index = typeof target === "number" ? clampIndex(target) : slugIndex(String(target));
    if (index === current || animating) return index;
    animating = true;
    current = index;
    applyTrack();
    window.setTimeout(function () { animating = false; }, reduced ? 0 : 620);
    return index;
  }

  function goNext() {
    goTo(current + 1);
  }

  function goPrev() {
    goTo(current - 1);
  }

  function buildDots() {
    if (!dotsHost) return;
    dotsHost.innerHTML = "";
    pages.forEach(function (_page, i) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "page-nav__dot";
      btn.setAttribute("role", "tab");
      btn.setAttribute("aria-label", "第 " + (i + 1) + " 页 · " + (LABELS[i] || SLUGS[i]));
      btn.setAttribute("aria-controls", pages[i].id || SLUGS[i]);
      btn.addEventListener("click", function () { goTo(i); });
      dotsHost.appendChild(btn);
    });
  }

  function interceptHashLinks() {
    landing.querySelectorAll('a[href^="#"]').forEach(function (a) {
      a.addEventListener("click", function (e) {
        const raw = a.getAttribute("href");
        if (!raw || raw === "#") {
          e.preventDefault();
          goTo(0);
          return;
        }
        const slug = raw.slice(1);
        const idx = slugIndex(slug);
        if (idx > 0 || slug === "top") {
          e.preventDefault();
          goTo(idx);
        }
      });
    });
  }

  function bindControls() {
    if (prevBtn) prevBtn.addEventListener("click", goPrev);
    if (nextBtn) nextBtn.addEventListener("click", goNext);
    if (heroNextBtn) heroNextBtn.addEventListener("click", function () { goTo("features"); });

    document.addEventListener("keydown", function (e) {
      if (landing.hidden || !landing.isConnected) return;
      if (e.target && (e.target.closest(".workshop__textarea") || e.target.closest(".magic-modal"))) return;
      if (e.key === "ArrowDown" || e.key === "PageDown") {
        e.preventDefault();
        goNext();
      } else if (e.key === "ArrowUp" || e.key === "PageUp") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "Home") {
        e.preventDefault();
        goTo(0);
      } else if (e.key === "End") {
        e.preventDefault();
        goTo(pages.length - 1);
      }
    });
  }

  function initFromHash() {
    const hash = window.location.hash.slice(1);
    if (hash) goTo(slugIndex(hash));
    else applyTrack();
  }

  buildDots();
  interceptHashLinks();
  bindControls();
  initFromHash();

  window.LandingPages = {
    goTo: goTo,
    goNext: goNext,
    goPrev: goPrev,
    getCurrent: function () { return current; },
    getSlug: function () { return SLUGS[current] || "top"; },
    onChange: function (fn) {
      if (typeof fn === "function") listeners.push(fn);
    },
  };
})();
