/** 2711 Editor · 滚动落地页导航（锚点 + 活跃态） */
(function () {
  const SECTIONS = [
    { id: "top", slug: "top", el: document.getElementById("top") },
    { id: "journey", slug: "journey", el: document.getElementById("journey") },
    { id: "features", slug: "features", el: document.getElementById("features") },
    { id: "create", slug: "create", el: document.getElementById("create") },
  ].filter(function (s) { return s.el; });

  const listeners = [];

  function getCurrentSlug() {
    const y = window.scrollY + (window.innerHeight * 0.35);
    let current = SECTIONS[0];
    SECTIONS.forEach(function (section) {
      if (section.el && section.el.offsetTop <= y) current = section;
    });
    return current ? current.slug : "top";
  }

  function emitChange(slug) {
    const section = SECTIONS.find(function (s) { return s.slug === slug; });
    const detail = {
      index: SECTIONS.indexOf(section),
      slug: slug,
      page: section ? section.el : null,
    };
    listeners.forEach(function (fn) { fn(detail); });
    document.dispatchEvent(new CustomEvent("landing:pagechange", { detail: detail }));
  }

  window.LandingPages = {
    goTo: function (slug) {
      const section = SECTIONS.find(function (s) { return s.slug === slug || s.id === slug; });
      if (!section || !section.el) return;
      section.el.scrollIntoView({ behavior: "smooth", block: "start" });
    },
    goNext: function () {
      const slug = getCurrentSlug();
      const i = SECTIONS.findIndex(function (s) { return s.slug === slug; });
      if (i >= 0 && i < SECTIONS.length - 1) this.goTo(SECTIONS[i + 1].slug);
    },
    goPrev: function () {
      const slug = getCurrentSlug();
      const i = SECTIONS.findIndex(function (s) { return s.slug === slug; });
      if (i > 0) this.goTo(SECTIONS[i - 1].slug);
    },
    getCurrent: function () {
      const slug = getCurrentSlug();
      return SECTIONS.findIndex(function (s) { return s.slug === slug; });
    },
    getSlug: function () { return getCurrentSlug(); },
    onChange: function (fn) {
      if (typeof fn === "function") listeners.push(fn);
    },
  };

  let scrollTimer = null;
  window.addEventListener("scroll", function () {
    if (scrollTimer) clearTimeout(scrollTimer);
    scrollTimer = setTimeout(function () {
      emitChange(getCurrentSlug());
    }, 80);
  }, { passive: true });

  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    link.addEventListener("click", function (e) {
      const hash = link.getAttribute("href");
      if (!hash || hash === "#") return;
      const id = hash.slice(1);
      const target = document.getElementById(id);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      history.replaceState(null, "", hash);
    });
  });

  emitChange(getCurrentSlug());
})(typeof window !== "undefined" ? window : globalThis);
