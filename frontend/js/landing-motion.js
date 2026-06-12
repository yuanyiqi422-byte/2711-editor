/** 首页动效：英雄视差 · 花瓣漂游 · 预览舞台倾斜 · 特性光晕 · VN 台词 */
(function () {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const hero = document.querySelector(".hero--vn") || document.querySelector(".hero");
  if (!hero) return;

  /* ── 1. 英雄多层视差 ── */
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
    window.addEventListener("scroll", function () {
      scrollY = window.scrollY;
      scheduleParallax();
    }, { passive: true });

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

    scrollY = window.scrollY;
    scheduleParallax();
  }

  /* ── 2. 花瓣漂游 ── */
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

  /* ── 3. 预览舞台轻微倾斜 ── */
  const stage = document.getElementById("hero-preview-stack");
  const stageFrame = stage && stage.querySelector(".hero__stage-frame");
  if (stage && stageFrame && !reduced) {
    if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
      stage.addEventListener(
        "pointermove",
        function (e) {
          const rect = stage.getBoundingClientRect();
          const px = (e.clientX - rect.left) / rect.width - 0.5;
          const py = (e.clientY - rect.top) / rect.height - 0.5;
          stageFrame.style.transform =
            "rotateY(" + (px * -8).toFixed(2) + "deg) rotateX(" + (py * 6).toFixed(2) + "deg)";
        },
        { passive: true }
      );
      stage.addEventListener("pointerleave", function () {
        stageFrame.style.transform = "";
      });
    }
  }

  /* ── 4. 特性卡片光晕 ── */
  const cards = document.querySelectorAll(".feature-card");
  if (cards.length) {
    if (reduced) {
      cards.forEach(function (card) { card.classList.add("is-glow-visible"); });
    } else {
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
      document.querySelectorAll(".feature-card:not(.is-glow-visible)").forEach(function (card) {
        glowIo.observe(card);
      });
    }
  }

  /* ── 5. VN 台词轮播 ── */
  const vnLine = document.getElementById("hero-vn-line");
  if (vnLine && !reduced) {
    const lines = [
      "每一页故事，都在等待被推开……",
      "抉择，将改写命运的走向。",
      "全屏场景、旁白与选项 — 你的小说，此刻可玩。",
    ];
    let lineIdx = 0;
    window.setInterval(function () {
      lineIdx = (lineIdx + 1) % lines.length;
      vnLine.style.opacity = "0";
      window.setTimeout(function () {
        vnLine.textContent = lines[lineIdx];
        vnLine.style.opacity = "1";
      }, 320);
    }, 4800);
    vnLine.style.transition = "opacity 0.32s ease";
  }
})();
