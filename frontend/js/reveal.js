/** 滚动显现 + 导航 + 轻量视差 */
(function () {
  const nav = document.getElementById("site-nav");
  const menu = document.getElementById("site-nav-menu");
  const toggle = document.getElementById("site-nav-toggle");
  const navLinks = document.querySelectorAll(".site-nav__link[data-nav]");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function closeMenu() {
    if (!nav || !toggle) return;
    nav.classList.remove("is-menu-open");
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "打开导航菜单");
  }

  if (nav && toggle && menu) {
    toggle.addEventListener("click", function () {
      const open = nav.classList.toggle("is-menu-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "关闭导航菜单" : "打开导航菜单");
    });

    menu.querySelectorAll("a[href^='#']").forEach(function (a) {
      a.addEventListener("click", function () {
        if (window.matchMedia("(max-width: 767.98px)").matches) closeMenu();
      });
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeMenu();
    });
  }

  if (nav) {
    window.addEventListener(
      "scroll",
      function () {
        nav.classList.toggle("is-scrolled", window.scrollY > 24);
      },
      { passive: true }
    );
  }

  if (navLinks.length) {
    const sections = ["features", "how", "create"]
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);

    if (sections.length) {
      const spy = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (e) {
            if (!e.isIntersecting) return;
            const id = e.target.id;
            navLinks.forEach(function (link) {
              link.classList.toggle("is-active", link.getAttribute("data-nav") === id);
            });
          });
        },
        { rootMargin: "-42% 0px -48% 0px", threshold: 0.01 }
      );
      sections.forEach(function (el) { spy.observe(el); });
    }
  }

  const reveals = document.querySelectorAll(".reveal");
  if (reveals.length && !reduced) {
    const io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add("is-visible");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    reveals.forEach(function (el) {
      if (el.classList.contains("feature-card")) return;
      io.observe(el);
    });
  } else {
    reveals.forEach(function (el) { el.classList.add("is-visible"); });
  }

})();
