/** 首页三动效：英雄视差层 · 花瓣云雾漂游 · 特性卡片光晕 */
(function () {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const hero = document.querySelector(".hero");
  if (!hero) return;

  /* ── 1. 英雄多层视差（滚动 + 桌面指针） ── */
  const parallaxLayers = [
    { el: hero.querySelector(".hero__media"), scroll: 0.28, pointer: 14 },
    { el: hero.querySelector(".hero__clouds"), scroll: 0.12, pointer: 8 },
    { el: hero.querySelector(".hero__wind"), scroll: 0.18, pointer: 10 },
    { el: hero.querySelector(".hero__mesh"), scroll: 0.06, pointer: 4 },
  ].filter(function (layer) { return layer.el; });

  let scrollY = 0;
  let pointerX = 0;
  let pointerY = 0;
  let rafId = 0;
  let pointerEnabled = false;

  function applyParallax() {
    rafId = 0;
    parallaxLayers.forEach(function (layer) {
      const sy = scrollY * layer.scroll;
      const px = pointerEnabled ? pointerX * layer.pointer : 0;
      const py = pointerEnabled ? pointerY * layer.pointer : 0;
      layer.el.style.transform =
        "translate3d(" + px + "px, " + (sy + py) + "px, 0)";
    });
  }

  function scheduleParallax() {
    if (rafId) return;
    rafId = window.requestAnimationFrame(applyParallax);
  }

  if (!reduced && parallaxLayers.length) {
    if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
      pointerEnabled = true;
      hero.addEventListener(
        "pointermove",
        function (e) {
          const rect = hero.getBoundingClientRect();
          pointerX = (e.clientX - rect.left) / rect.width - 0.5;
          pointerY = (e.clientY - rect.top) / rect.height - 0.5;
          scheduleParallax();
        },
        { passive: true }
      );
      hero.addEventListener("pointerleave", function () {
        pointerX = 0;
        pointerY = 0;
        scheduleParallax();
      });
    }

    scheduleParallax();
  }

  /* ── 2. 花瓣云雾漂游（轻量 DOM 花瓣） ── */
  const petalHost = hero.querySelector(".hero__petals");
  if (petalHost && !reduced) {
    const palette = ["#f8a8c8", "#ffc8dd", "#a8d4ff", "#b8d4c8"];
    const count = window.matchMedia("(max-width: 767.98px)").matches ? 6 : 10;

    for (let i = 0; i < count; i += 1) {
      const petal = document.createElement("span");
      petal.className = "hero__petal";
      petal.setAttribute("aria-hidden", "true");
      petal.style.setProperty("--petal-left", (8 + Math.random() * 84).toFixed(1) + "%");
      petal.style.setProperty("--petal-size", (6 + Math.random() * 10).toFixed(1) + "px");
      petal.style.setProperty("--petal-drift", (-18 + Math.random() * 36).toFixed(1) + "px");
      petal.style.setProperty("--petal-duration", (14 + Math.random() * 16).toFixed(1) + "s");
      petal.style.setProperty("--petal-delay", (-Math.random() * 20).toFixed(1) + "s");
      petal.style.setProperty("--petal-color", palette[i % palette.length]);
      petalHost.appendChild(petal);
    }
  }

  /* ── 3. 特性卡片入场光晕 + 悬停强化 ── */
  const cards = document.querySelectorAll(".feature-card");
  if (cards.length) {
    if (reduced) {
      cards.forEach(function (card) {
        card.classList.add("is-glow-visible");
      });
      return;
    }

    const glowIo = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-glow-visible");
          glowIo.unobserve(entry.target);
        });
      },
      { threshold: 0.22, rootMargin: "0px 0px -8% 0px" }
    );

    function observeCards(root) {
      if (!root) return;
      root.querySelectorAll(".feature-card:not(.is-glow-visible)").forEach(function (card) {
        glowIo.observe(card);
      });
    }

    observeCards(document.getElementById("features"));

    if (typeof LandingPages !== "undefined") {
      LandingPages.onChange(function (detail) {
        if (detail.slug === "features") observeCards(detail.page);
      });
    }
  }
})();
