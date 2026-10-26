/**
 * Featured Demo — load curated story pack from static JSON (no live LLM).
 */
(function (global) {
  const CACHE_URL = "data/featured-demo.json?v=7";
  let cachedPayload = null;
  let inflight = null;

  function normalizePayload(raw) {
    if (!raw || typeof raw !== "object") {
      throw new Error("试玩 Demo 数据无效");
    }
    const game = raw.game || raw.pack || raw;
    if (!game || !game.nodes) {
      throw new Error("试玩 Demo 缺少可玩节点");
    }
    return {
      id: raw.id || "featured",
      label_zh: raw.label_zh || "试玩 Demo",
      label_en: raw.label_en || "Instant Demo",
      tagline_zh: raw.tagline_zh || "",
      tagline_en: raw.tagline_en || "",
      under_the_hood: raw.under_the_hood || null,
      game: game,
    };
  }

  function load() {
    if (cachedPayload) return Promise.resolve(cachedPayload);
    if (inflight) return inflight;
    inflight = fetch(CACHE_URL, { cache: "force-cache" })
      .then(function (res) {
        if (!res.ok) throw new Error("试玩 Demo 加载失败 (" + res.status + ")");
        return res.json();
      })
      .then(function (json) {
        cachedPayload = normalizePayload(json);
        inflight = null;
        return cachedPayload;
      })
      .catch(function (err) {
        inflight = null;
        throw err;
      });
    return inflight;
  }

  function setButtonsBusy(busy) {
    document.querySelectorAll("[data-featured-demo-btn]").forEach(function (btn) {
      btn.disabled = !!busy;
      btn.classList.toggle("is-loading", !!busy);
      if (btn.dataset.busyLabel && busy) {
        if (!btn.dataset.idleLabel) btn.dataset.idleLabel = btn.textContent;
        btn.textContent = btn.dataset.busyLabel;
      } else if (!busy && btn.dataset.idleLabel) {
        btn.textContent = btn.dataset.idleLabel;
      }
    });
  }

  async function launch(options) {
    const opts = options || {};
    const onError = typeof opts.onError === "function" ? opts.onError : function () {};
    setButtonsBusy(true);
    try {
      onError("");
      const payload = await load();
      if (typeof global.UnderTheHood !== "undefined" && global.UnderTheHood.bindPayload) {
        global.UnderTheHood.bindPayload(payload.under_the_hood);
      }
      if (typeof NarrativeGame === "undefined" || !NarrativeGame.startFeatured) {
        throw new Error("游戏引擎未就绪");
      }
      NarrativeGame.startFeatured(payload.game, {
        entryId: "featured",
        underTheHood: payload.under_the_hood,
        forceRestart: !!opts.forceRestart,
        sessionBgm: payload.session_bgm || "audio/bgm/Kevin_MacLeod-Floating_Cities.mp3",
      });
    } catch (err) {
      console.error("[FeaturedDemo]", err);
      onError((err && err.message) || "试玩 Demo 打开失败");
    } finally {
      setButtonsBusy(false);
    }
  }

  function prefetch() {
    load().catch(function () {});
  }

  global.FeaturedDemo = {
    load: load,
    launch: launch,
    prefetch: prefetch,
  };
})(typeof window !== "undefined" ? window : globalThis);
