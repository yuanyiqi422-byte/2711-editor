/**
 * Engine Telemetry HUD — per-node pipeline metrics for Featured showcase.
 */
(function (global) {
  let visible = false;

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

  function setVisible(show) {
    visible = !!show;
    const e = els();
    if (!e.root) return;
    e.root.hidden = !visible;
    e.root.setAttribute("aria-hidden", visible ? "false" : "true");
    e.root.classList.toggle("is-visible", visible);
  }

  function update(node) {
    const e = els();
    if (!e.root || !node) return;
    const t = node.telemetry;
    if (!t) {
      setVisible(false);
      return;
    }
    setVisible(true);
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
      e.conf.textContent = (Number.isFinite(conf) ? conf.toFixed(2) : "—") + " (Rule+Tag)";
    }
    const pct = Math.round((Number(t.tension_score) || 0) * 100);
    if (e.tensionVal) e.tensionVal.textContent = pct + "%";
    if (e.tensionBar) e.tensionBar.style.width = Math.max(0, Math.min(100, pct)) + "%";
  }

  function hide() {
    setVisible(false);
  }

  function updateEngineHud(node) {
    update(node);
  }

  global.EngineHud = {
    update: update,
    hide: hide,
    setVisible: setVisible,
  };
  global.updateEngineHud = updateEngineHud;
})(typeof window !== "undefined" ? window : globalThis);
