/** 视觉小说引擎 — 点击继续 / 抉择点才选项 */
const NarrativeGame = (function () {
  const els = { landing: null };
  let pack = null;
  let sourceText = "";
  let onBack = null;
  let onEnter = null;
  let nodeId = null;
  let lineIndex = 0;
  let mode = "line";

  function bindElements() {
    els.root = document.getElementById("game");
    els.landing = document.getElementById("landing-view");
    els.stage = document.getElementById("vn-stage");
    els.sceneBg = document.getElementById("scene-bg");
    els.sceneBgA = document.getElementById("scene-bg-a");
    els.sceneBgB = document.getElementById("scene-bg-b");
    els.portraitLeft = document.getElementById("portrait-left");
    els.portraitRight = document.getElementById("portrait-right");
    els.style = document.getElementById("game-style");
    els.title = document.getElementById("game-title");
    els.sceneTag = document.getElementById("scene-tag");
    els.speaker = document.getElementById("speaker");
    els.narrative = document.getElementById("narrative");
    els.continueHint = document.getElementById("continue-hint");
    els.choices = document.getElementById("choices");
    els.choicesPanel = document.getElementById("choices-panel");
    els.endingBanner = document.getElementById("ending-banner");
    els.endingLabel = document.getElementById("ending-label");
    els.restartBtn = document.getElementById("restart-btn");
    els.dialogueBox = document.getElementById("vn-dialogue");
  }

  function showStudio() {
    if (els.landing) {
      els.landing.hidden = false;
      els.landing.removeAttribute("inert");
      els.landing.removeAttribute("aria-hidden");
    }
    if (els.root) els.root.hidden = true;
    document.body.classList.remove("game-active");
  }

  function showGameView() {
    if (els.landing) {
      els.landing.hidden = true;
      els.landing.setAttribute("inert", "");
      els.landing.setAttribute("aria-hidden", "true");
    }
    if (els.root) els.root.hidden = false;
    document.body.classList.add("game-active");
  }

  function hideEnding() {
    if (els.endingBanner) {
      els.endingBanner.hidden = true;
      els.endingBanner.classList.remove("is-visible");
    }
    if (els.restartBtn) els.restartBtn.classList.remove("is-visible");
    if (els.dialogueBox) els.dialogueBox.hidden = false;
    const hudReplay = document.getElementById("game-replay");
    if (hudReplay) hudReplay.hidden = true;
  }

  function resolveStartNode(gamePack) {
    if (!gamePack || !gamePack.nodes) return null;
    const nodes = gamePack.nodes;
    const preferred = gamePack.start_node_id || "start";
    if (nodes[preferred]) return preferred;
    for (const id of ["start", "intro", "opening", "market", "node_1"]) {
      if (nodes[id]) return id;
    }
    return Object.keys(nodes)[0] || null;
  }

  function normalizePack(raw) {
    if (!raw || typeof raw !== "object") return null;
    let nodes = raw.nodes;
    if (!nodes) return null;
    if (Array.isArray(nodes)) {
      const dict = {};
      nodes.forEach(function (n, i) {
        if (n && n.id) dict[n.id] = n;
        else dict["node_" + (i + 1)] = n;
      });
      raw = Object.assign({}, raw, { nodes: dict });
    }
    return raw;
  }

  function getLines(node) {
    if (node.lines && node.lines.length) return node.lines;
    return splitLegacyNarrative(node.narrative || "", node.speaker || "旁白");
  }

  function splitLegacyNarrative(text, speaker) {
    const parts = text.split(/\n+/).filter(Boolean);
    const lines = [];
    parts.forEach(function (p) {
      const t = p.trim();
      if (!t) return;
      if (t.length <= 48) {
        lines.push({ speaker: speaker, text: t, portrait: "none" });
      } else {
        const re = /[^。！？…]+[。！？…]?/g;
        let m;
        while ((m = re.exec(t)) !== null) {
          const s = m[0].trim();
          if (s) lines.push({ speaker: speaker, text: s, portrait: "none" });
        }
      }
    });
    return lines.length ? lines : [{ speaker: "旁白", text: "……", portrait: "none" }];
  }

  function endingLabel(type) {
    const map = { good: "✦ 圆满结局", bad: "✦ 悲剧结局", neutral: "✦ 开放式结局", open: "✦ 故事未完" };
    return map[type] || "✦ 结局";
  }

  function applyScene(node, style) {
    try {
      if (typeof MoodBackgrounds !== "undefined" && els.sceneBg) {
        MoodBackgrounds.apply(
          els.sceneBg,
          node.mood || "neutral",
          style || "urban_romance",
          node.image_prompt || ""
        );
      }
    } catch {
      if (els.sceneBg) els.sceneBg.style.background = "var(--vn-ink, #1a2030)";
    }
  }

  function setPortraits(_portrait, _speaker) {
    /* 立绘已移除 — 纯场景 + 对话框，避免占位块干扰阅读 */
  }

  function hideChoices() {
    mode = "line";
    if (els.choicesPanel) els.choicesPanel.hidden = true;
    if (els.choices) els.choices.innerHTML = "";
    if (els.dialogueBox) els.dialogueBox.hidden = false;
    if (els.continueHint) els.continueHint.hidden = false;
  }

  function showChoices(node) {
    mode = "choice";
    if (els.continueHint) els.continueHint.hidden = true;
    if (els.dialogueBox) els.dialogueBox.hidden = true;
    if (els.choicesPanel) els.choicesPanel.hidden = false;
    if (!els.choices) return;
    els.choices.innerHTML = "";

    node.choices.forEach(function (ch) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "vn-choice-btn";
      btn.textContent = ch.text || "继续";
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        handleChoice(node, ch, btn);
      });
      els.choices.appendChild(btn);
    });
  }

  function showEnding(node) {
    mode = "ending";
    if (els.continueHint) els.continueHint.hidden = true;
    if (els.choicesPanel) els.choicesPanel.hidden = true;
    if (els.dialogueBox) els.dialogueBox.hidden = true;
    if (els.endingBanner) {
      els.endingBanner.hidden = false;
      els.endingBanner.classList.add("is-visible");
    }
    if (els.endingLabel) els.endingLabel.textContent = endingLabel(node.ending_type);
    if (els.restartBtn) els.restartBtn.classList.add("is-visible");
    const hudReplay = document.getElementById("game-replay");
    if (hudReplay) hudReplay.hidden = false;
  }

  function showLine(node, lines, idx) {
    const line = lines[idx];
    const sp = (line && line.speaker) || "旁白";
    const text = (line && line.text) || "……";
    const portrait = (line && line.portrait) || "none";

    if (els.speaker) {
      els.speaker.textContent = sp;
      els.speaker.hidden = !sp || sp === "旁白";
    }
    if (els.narrative) {
      els.narrative.classList.remove("vn-line-enter");
      void els.narrative.offsetWidth;
      els.narrative.textContent = text;
      els.narrative.classList.add("vn-line-enter");
    }
    setPortraits(portrait, sp);

    const isLast = idx >= lines.length - 1;
    if (els.continueHint) {
      els.continueHint.textContent = isLast
        ? node.choices && node.choices.length
          ? "点击继续 · 进入抉择"
          : node.is_ending
            ? "点击继续 · 结局"
            : "点击继续 · 下一场景"
        : "点击继续 ▸";
    }
  }

  function enterNode(id) {
    if (!pack || !pack.nodes[id]) return;
    nodeId = id;
    lineIndex = 0;
    mode = "line";
    const node = pack.nodes[id];

    showGameView();
    if (els.style) {
      let styleLabel = pack.style_label || "";
      const meta = pack.meta;
      if (meta && meta.node_count) {
        styleLabel += " · 共 " + meta.node_count + " 场景";
        if (meta.play_minutes) styleLabel += " · 约 " + meta.play_minutes + " 分钟";
      }
      els.style.textContent = styleLabel;
    }
    if (els.title) els.title.textContent = pack.title || "";
    if (els.sceneTag) els.sceneTag.textContent = node.title || id;
    hideEnding();

    applyScene(node, pack.style);
    hideChoices();

    const lines = getLines(node);
    node._lines = lines;
    showLine(node, lines, 0);
  }

  function afterLinesDone(node) {
    if (node.is_ending) {
      showEnding(node);
      return;
    }
    if (node.choices && node.choices.length) {
      showChoices(node);
      return;
    }
    const nxt = node.after_lines_next;
    if (nxt && pack.nodes[nxt]) {
      enterNode(nxt);
      return;
    }
    showError("本段剧情无法继续，请返回工坊重新转化。");
  }

  function advance() {
    if (!pack || !nodeId) return;
    const node = pack.nodes[nodeId];
    const lines = node._lines || getLines(node);

    if (mode === "choice" || mode === "ending") return;

    if (lineIndex < lines.length - 1) {
      lineIndex += 1;
      showLine(node, lines, lineIndex);
      return;
    }
    afterLinesDone(node);
  }

  function showError(message) {
    showGameView();
    hideEnding();
    hideChoices();
    if (els.speaker) els.speaker.hidden = true;
    if (els.narrative) els.narrative.textContent = message;
    if (els.continueHint) els.continueHint.hidden = true;
    if (els.choices) {
      els.choices.innerHTML = "";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "vn-choice-btn";
      btn.textContent = "返回工作室";
      btn.onclick = function () {
        hide();
        if (onBack) onBack();
      };
      if (els.choicesPanel) {
        els.choicesPanel.hidden = false;
        els.choices.appendChild(btn);
      }
    }
  }

  async function handleChoice(node, choice, btn) {
    const nextId = choice.next;
    if (pack.nodes[nextId]) {
      enterNode(nextId);
      return;
    }

    btn.disabled = true;
    btn.textContent = "正在生成后续剧情…";

    try {
      const res = await fetch("/api/expand", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: sourceText,
          style: pack.style,
          game: pack,
          current_node_id: node.id,
          choice_id: choice.id,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        let msg = "续写失败";
        if (typeof detail === "string") msg = detail;
        else if (Array.isArray(detail)) {
          msg = detail.map(function (i) { return i && i.msg ? i.msg : String(i); }).join("；");
        } else if (detail && typeof detail === "object" && detail.message) {
          msg = detail.message;
        }
        throw new Error(msg);
      }
      pack = normalizePack(data) || data;
      enterNode(pack.nodes[nextId] ? nextId : resolveStartNode(pack));
    } catch (err) {
      btn.disabled = false;
      btn.textContent = choice.text;
      showError(err.message || "续写失败");
    }
  }

  function onStageClick(e) {
    if (e.target.closest(".vn-choice-btn") || e.target.closest(".game__back")) return;
    if (mode === "line") advance();
  }

  function onStageKeydown(e) {
    if (!pack || els.root?.hidden) return;
    if (e.target.closest("input, textarea, select, button")) return;
    if (e.key === " " || e.key === "Enter") {
      if (mode === "line") {
        e.preventDefault();
        advance();
      }
    } else if (e.key === "Escape") {
      if (mode !== "ending" && !window.confirm("确定返回工坊？当前进度未自动保存。")) return;
      hide();
      if (onBack) onBack();
    }
  }

  function enterGame(gamePack, text) {
    bindElements();
    if (onEnter) onEnter();
    pack = normalizePack(gamePack);
    sourceText = text || "";
    const startId = resolveStartNode(pack);
    if (!startId) {
      showError("没有可玩场景。请返回工作室重试。");
      return;
    }
    enterNode(startId);
  }

  function start(gamePack, text) {
    enterGame(gamePack, text);
  }

  function startDemo() {
    enterGame(DEMO_GAME_PACK, "");
  }

  function hide() {
    showStudio();
    pack = null;
    nodeId = null;
    lineIndex = 0;
  }

  function restart() {
    if (!pack) return;
    const startId = resolveStartNode(pack);
    if (startId) enterNode(startId);
  }

  function init(options) {
    onBack = options && options.onBack;
    onEnter = options && options.onEnter;
    bindElements();
    if (els.stage) els.stage.addEventListener("click", onStageClick);
    document.addEventListener("keydown", onStageKeydown);
    const backBtn = document.getElementById("back-studio");
    if (backBtn) {
      backBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        hide();
        if (onBack) onBack();
      });
    }
    const restartBtn = document.getElementById("restart-btn");
    if (restartBtn) restartBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      restart();
    });
    const hudReplay = document.getElementById("game-replay");
    if (hudReplay) hudReplay.addEventListener("click", function (e) {
      e.stopPropagation();
      restart();
    });
  }

  return { init, start, startDemo, hide, restart };
})();
