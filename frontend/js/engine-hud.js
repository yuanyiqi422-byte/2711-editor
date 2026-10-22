/**
 * Engine Telemetry HUD — per-node pipeline metrics for Featured showcase.
 * Hidden by default for immersion; toggled via Under the Hood.
 */
(function (global) {
  let userVisible = false;
  let lastNode = null;

  function els() {
    return {
      root: document.getElementById("engine-hud"),
      act: document.getElementById("hud-act"),
      node: document.getElementById("hud-node"),
      span: document.getElementById("hud-span"),
      strat: document.getElementById("hud-strat"),
      tag: document.getElementById("hud-tag"),
      conf: document.getElementById("hud-conf"),
      tensionVal: document.getElementById("hud-tension-val"),
      tensionBar: document.getElementById("hud-tension-bar"),
    };
  }

  function applyVisibility() {
    const e = els();
    if (!e.root) return;
    const show = !!userVisible && !!lastNode && !!lastNode.telemetry;
    e.root.hidden = !show;
    e.root.style.display = show ? "" : "none";
    e.root.setAttribute("aria-hidden", show ? "false" : "true");
    e.root.classList.toggle("is-visible", show);
  }

  function paint(node) {
    const e = els();
    if (!e.root || !node) return;
    const t = node.telemetry || {};
    if (e.act) {
      const act = String(node.act || "").split("·")[0].trim() || "Act";
      e.act.textContent = act;
    }
    if (e.node) e.node.textContent = node.id || "—";
    if (e.span) e.span.textContent = t.source_span || "—";
    if (e.strat) e.strat.textContent = t.truncate_strategy || "—";
    if (e.tag) e.tag.textContent = t.scene_tag || "—";
    if (e.conf) {
      const conf = Number(t.match_confidence);
      e.conf.textContent = (Number.isFinite(conf) ? conf.toFixed(2) : "—") + " (Tag Match)";
    }
    const pct = Math.round((Number(t.tension_score) || 0) * 100);
    if (e.tensionVal) e.tensionVal.textContent = pct + "%";
    if (e.tensionBar) e.tensionBar.style.width = Math.max(0, Math.min(100, pct)) + "%";
  }

  function setVisible(show) {
    userVisible = !!show;
    applyVisibility();
  }

  function toggle() {
    setVisible(!userVisible);
    return userVisible;
  }

  function isVisible() {
    return !!userVisible;
  }

  function getLastNode() {
    return lastNode;
  }

  function update(node) {
    lastNode = node || null;
    if (lastNode && lastNode.telemetry) {
      paint(lastNode);
    }
    // Never auto-show: refresh internal state always; DOM only if user opened Hood.
    applyVisibility();
  }

  function hide() {
    userVisible = false;
    lastNode = null;
    applyVisibility();
  }

  function updateEngineHud(node) {
    update(node);
  }

  // Ensure hidden on load for immersion.
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        applyVisibility();
      });
    } else {
      applyVisibility();
    }
  }

  global.EngineHud = {
    update: update,
    hide: hide,
    setVisible: setVisible,
    toggle: toggle,
    isVisible: isVisible,
    getLastNode: getLastNode,
  };
  global.updateEngineHud = updateEngineHud;
})(typeof window !== "undefined" ? window : globalThis);
