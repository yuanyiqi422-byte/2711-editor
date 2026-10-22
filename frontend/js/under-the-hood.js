/**
 * Under the Hood — surface long-context architecture next to gameplay.
 */
(function (global) {
  let payload = null;
  let els = null;

  const FALLBACK = {
    title: "Under the Hood",
    subtitle: "14-node Branch & Merge · Victorian Philology Mystery · Instant Featured Pack",
    bullets: [
      {
        label: "Delivery path",
        value:
          "Featured pack loaded from static JSON (offline-capable). Live LLM create remains optional for your own uploads.",
      },
      {
        label: "Narrative topology",
        value:
          "Four acts, 14 nodes, 4 endings with diamond Branch & Merge: dual investigation lines reconverge at the Central Index before climax forks.",
      },
      {
        label: "Immersive pages",
        value:
          "Each node uses multi-page dialogue with choices_trigger_after_page so options appear only after the scene is read.",
      },
      {
        label: "Per-node telemetry",
        value:
          "Engine HUD stays hidden by default. Open Under the Hood to reveal source_span, strategy, scene_tag, confidence, and tension.",
      },
      {
        label: "Featured vs live",
        value:
          "Featured Demo plays a curated static pack instantly. Uploading your own text still uses the live create pipeline when the API is available.",
      },
    ],
    metrics: [
      { label: "Nodes in pack", value: "14" },
      { label: "Endings", value: "4" },
      { label: "Topology", value: "Branch & Merge" },
      { label: "Per-node telemetry", value: "HUD on demand" },
      { label: "Total pages", value: "46" },
      { label: "API at play time", value: "not required" },
    ],
  };

  function bindElements() {
    if (els) return els;
    els = {
      root: document.getElementById("under-the-hood"),
      panel: document.getElementById("uth-panel"),
      openBtn: document.getElementById("uth-open-btn"),
      closeBtn: document.getElementById("uth-close-btn"),
      backdrop: document.getElementById("uth-backdrop"),
      subtitle: document.getElementById("uth-subtitle"),
      list: document.getElementById("uth-bullets"),
      metrics: document.getElementById("uth-metrics"),
    };
    return els;
  }

  function bindPayload(next) {
    payload = next && typeof next === "object" ? next : null;
    render();
  }

  function activePayload() {
    return payload || FALLBACK;
  }

  function render() {
    const e = bindElements();
    const data = activePayload();
    if (e.subtitle) e.subtitle.textContent = data.subtitle || FALLBACK.subtitle;

    if (e.list) {
      e.list.innerHTML = "";
      (data.bullets || FALLBACK.bullets).forEach(function (item) {
        const li = document.createElement("li");
        li.className = "uth__item";
        const label = document.createElement("strong");
        label.className = "uth__label";
        label.textContent = item.label || "";
        const value = document.createElement("p");
        value.className = "uth__value";
        value.textContent = item.value || "";
        li.appendChild(label);
        li.appendChild(value);
        e.list.appendChild(li);
      });
    }

    if (e.metrics) {
      e.metrics.innerHTML = "";
      (data.metrics || FALLBACK.metrics).forEach(function (m) {
        const card = document.createElement("div");
        card.className = "uth__metric";
        const v = document.createElement("span");
        v.className = "uth__metric-value";
        v.textContent = m.value || "";
        const l = document.createElement("span");
        l.className = "uth__metric-label";
        l.textContent = m.label || "";
        card.appendChild(v);
        card.appendChild(l);
        e.metrics.appendChild(card);
      });
    }
  }

  function syncEngineHud(open) {
    if (typeof EngineHud === "undefined") return;
    // Under the Hood reveals / hides the telemetry HUD together with the panel.
    if (EngineHud.setVisible) EngineHud.setVisible(!!open);
    if (open && EngineHud.getLastNode && EngineHud.update) {
      const n = EngineHud.getLastNode();
      if (n) EngineHud.update(n);
    }
  }

  function setOpen(open) {
    const e = bindElements();
    if (!e.root) return;
    e.root.hidden = !open;
    e.root.classList.toggle("is-open", !!open);
    if (e.openBtn) e.openBtn.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) render();
    syncEngineHud(open);
  }

  function show() {
    setOpen(true);
  }

  function hide() {
    setOpen(false);
  }

  function toggle() {
    const e = bindElements();
    const open = !(e.root && !e.root.hidden && e.root.classList.contains("is-open"));
    setOpen(open);
  }

  let inited = false;

  function init() {
    const e = bindElements();
    if (!e.root) return;
    render();
    if (inited) return;
    inited = true;
    if (e.openBtn) {
      e.openBtn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        toggle();
      });
    }
    if (e.closeBtn) {
      e.closeBtn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        hide();
      });
    }
    if (e.backdrop) {
      e.backdrop.addEventListener("click", function (ev) {
        ev.stopPropagation();
        hide();
      });
    }
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && e.root && !e.root.hidden) {
        hide();
      }
    });
  }

  global.UnderTheHood = {
    init: init,
    bindPayload: bindPayload,
    show: show,
    hide: hide,
    toggle: toggle,
  };
})(typeof window !== "undefined" ? window : globalThis);
