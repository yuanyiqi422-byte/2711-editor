/** 视觉小说引擎 — 现代 VN 对话框 / 章节仪式 / BGM / 结局图鉴 */
const NarrativeGame = (function () {
  const els = { landing: null };
  let pack = null;
  let sourceText = "";
  let onBack = null;
  let onEnter = null;
  let nodeId = null;
  let lineIndex = 0;
  let mode = "line";
  let seenChapters = new Set();
  let currentChapterNum = null;
  let activeBgmTrackId = null;
  let pendingNodeId = null;
  let entryId = null;
  let protagonistName = null;
  let shareMode = false;
  let chapterAutoTimer = null;
  let speakerColorMap = Object.create(null);

  const CN_CHAPTER = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"];
  const MAJOR_SPEAKER_PALETTES = ["sky", "sakura", "meadow", "lavender"];
  const MAX_MAJOR_SPEAKERS = 4;
  const SPEAKER_NAME_CLASSES = [
    "vn-name--protagonist",
    "vn-name--sky",
    "vn-name--sakura",
    "vn-name--meadow",
    "vn-name--lavender",
    "vn-name--support",
  ];
  const DIALOGUE_COLOR_CLASSES = [
    "vn-dialogue--protagonist",
    "vn-dialogue--sky",
    "vn-dialogue--sakura",
    "vn-dialogue--meadow",
    "vn-dialogue--lavender",
    "vn-dialogue--support",
    "vn-dialogue--narration",
  ];

  function bindElements() {
    els.root = document.getElementById("game");
    els.landing = document.getElementById("landing-view");
    els.stage = document.getElementById("vn-stage");
    els.sceneBg = document.getElementById("scene-bg");
    els.sceneBgA = document.getElementById("scene-bg-a");
    els.sceneBgB = document.getElementById("scene-bg-b");
    els.style = document.getElementById("game-style");
    els.title = document.getElementById("game-title");
    els.sceneTag = document.getElementById("scene-tag");
    els.speaker = document.getElementById("speaker");
    els.narrative = document.getElementById("narrative");
    els.continueHint = document.getElementById("continue-hint");
    els.choices = document.getElementById("choices");
    els.choicesPanel = document.getElementById("choices-panel");
    els.endingBanner = document.getElementById("ending-banner");
    els.endingType = document.getElementById("ending-type");
    els.endingSubtitle = document.getElementById("ending-subtitle");
    els.endingSynopsis = document.getElementById("ending-synopsis");
    els.restartBtn = document.getElementById("restart-btn");
    els.shareWorldBtn = document.getElementById("share-world-btn");
    els.dialogueBox = document.getElementById("vn-dialogue");
    els.dialogueWrap = document.getElementById("vn-dialogue-wrap");
    els.characterZone = document.getElementById("vn-character-zone");
    els.characterImg = document.getElementById("vn-character-img");
    els.chapterHud = document.getElementById("game-chapter-hud");
    els.chapterHudNum = document.getElementById("chapter-hud-num");
    els.chapterHudText = document.getElementById("chapter-hud-text");
    els.chapterModal = document.getElementById("chapter-modal");
    els.chapterModalNum = document.getElementById("chapter-modal-num");
    els.chapterModalTitle = document.getElementById("chapter-modal-title");
    els.chapterModalBlurb = document.getElementById("chapter-modal-blurb");
    els.chapterModalStart = document.getElementById("chapter-modal-start");
    els.bgmToggle = document.getElementById("bgm-toggle");
    els.shareBrand = document.getElementById("share-brand-bar");
    els.codexBtn = document.getElementById("dock-codex-btn");
    els.codexPanel = document.getElementById("ending-codex");
    els.codexList = document.getElementById("ending-codex-list");
    els.codexClose = document.getElementById("ending-codex-close");
    els.codexProgress = document.getElementById("ending-codex-progress");
    els.codexFromEnd = document.getElementById("ending-codex-from-end");
    els.dockCodexLabel = document.getElementById("dock-codex-label");
  }

  /** 角色立绘区暂关闭：cover/scene 图不适合当立绘。
   *  未来可选：场景内嵌角色、透明 PNG 立绘、或无立绘纯对话框模式。 */
  function updateCharacterArt(_speaker) {
    if (!els.characterZone) return;
    els.characterZone.classList.remove("is-visible");
    els.characterZone.hidden = true;
    els.characterZone.setAttribute("aria-hidden", "true");
    if (els.characterImg) els.characterImg.removeAttribute("src");
  }

  function showStudio() {
    if (typeof VnAudio !== "undefined") VnAudio.stop();
    if (els.landing) {
      els.landing.hidden = false;
      els.landing.removeAttribute("inert");
      els.landing.removeAttribute("aria-hidden");
    }
    if (els.root) els.root.hidden = true;
    document.body.classList.remove("game-active");
    if (els.shareBrand) els.shareBrand.hidden = true;
  }

  function showGameView() {
    if (els.landing) {
      els.landing.hidden = true;
      els.landing.setAttribute("inert", "");
      els.landing.setAttribute("aria-hidden", "true");
    }
    if (els.root) els.root.hidden = false;
    document.body.classList.add("game-active");
    if (els.shareBrand) els.shareBrand.hidden = !shareMode;
  }

  function syncBgmToggle() {
    if (typeof VnAudio === "undefined") return;
    const muted = VnAudio.isMuted();
    document.querySelectorAll("#bgm-toggle").forEach(function (btn) {
      btn.setAttribute("aria-pressed", muted ? "false" : "true");
      btn.classList.toggle("is-muted", muted);
    });
  }

  function persistCheckpoint() {
    if (!entryId || entryId === "demo" || !pack || !nodeId || mode === "ending") return;
    if (typeof ProgressStore === "undefined" || !ProgressStore.saveCheckpoint) return;
    ProgressStore.saveCheckpoint(entryId, {
      nodeId: nodeId,
      lineIndex: lineIndex,
      packTitle: pack.title || "",
      ts: Date.now(),
    });
  }

  function encodeAssetUrl(relPath) {
    if (!relPath) return "";
    const parts = String(relPath).split("/");
    const file = parts.pop();
    return parts.concat([encodeURIComponent(file)]).join("/");
  }

  function startSceneBgm(node) {
    if (!pack || !node || typeof VnAudio === "undefined") return;
    const style = pack.style || "urban_romance";
    const mood = node.mood || "neutral";

    // Featured / curated packs may pin a real local BGM path per node.
    if (node.bgm) {
      const fileUrl = encodeAssetUrl(node.bgm);
      const trackId = "node-bgm:" + node.id + "|" + node.bgm;
      if (activeBgmTrackId === trackId) return;
      activeBgmTrackId = trackId;
      VnAudio.start({
        style: style,
        mood: mood,
        trackId: trackId,
        fileUrl: fileUrl,
      });
      syncBgmToggle();
      return;
    }

    let pick = null;
    if (typeof MusicPicker !== "undefined" && MusicPicker.resolveForPlay) {
      pick = MusicPicker.resolveForPlay(style, mood);
    }
    const trackId = pick && pick.trackId
      ? pick.trackId
      : style + ":" + mood + (pick && pick.fileUrl ? "|" + pick.fileUrl : "");
    if (activeBgmTrackId === trackId) return;
    activeBgmTrackId = trackId;
    if (pick) {
      VnAudio.start(pick);
    } else {
      VnAudio.start(style);
    }
    syncBgmToggle();
  }

  function syncSceneBgm(node) {
    if (!node) return;
    startSceneBgm(node);
  }

  function hideEnding() {
    if (els.endingBanner) {
      els.endingBanner.hidden = true;
      els.endingBanner.classList.remove("is-visible");
    }
    if (els.restartBtn) els.restartBtn.classList.remove("is-visible");
    if (els.dialogueWrap) els.dialogueWrap.hidden = false;
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

  function cnChapterLabel(num) {
    const n = Number(num) || 1;
    return CN_CHAPTER[n] || String(n);
  }

  function getNodeChapter(node) {
    const num = Number(node.chapter) || 1;
    let title = (node.chapter_title || "").trim();
    if (!title) title = "第" + cnChapterLabel(num) + "章";
    let blurb = (node.chapter_blurb || "").trim();
    if (!blurb && node._lines && node._lines[0]) {
      blurb = normalizeDialogueText((node._lines[0].text || "").trim());
    }
    if (blurb) blurb = normalizeDialogueText(blurb);
    if (!blurb && node.narrative) {
      blurb = normalizeDialogueText(node.narrative.trim().slice(0, 48));
    }
    return { num: num, title: title, blurb: blurb };
  }

  function orderedNodeIds(gamePack) {
    const nodes = gamePack.nodes || {};
    const start = resolveStartNode(gamePack);
    if (!start) return Object.keys(nodes);
    const seen = {};
    const order = [];
    const queue = [start];
    while (queue.length) {
      const nid = queue.shift();
      if (seen[nid] || !nodes[nid]) continue;
      seen[nid] = true;
      order.push(nid);
      const node = nodes[nid];
      const nxt = node.after_lines_next;
      if (nxt && nodes[nxt]) queue.push(nxt);
      (node.choices || []).forEach(function (ch) {
        if (ch.next && nodes[ch.next]) queue.push(ch.next);
      });
    }
    Object.keys(nodes).forEach(function (nid) {
      if (!seen[nid]) order.push(nid);
    });
    return order;
  }

  function ensureChapterMetadata(gamePack) {
    if (!gamePack || !gamePack.nodes) return gamePack;
    const nodes = gamePack.nodes;
    const chapters = {};
    Object.keys(nodes).forEach(function (id) {
      const n = nodes[id];
      chapters[n.chapter || 1] = true;
    });
    const hasMeta = Object.keys(chapters).length > 1 ||
      Object.keys(nodes).some(function (id) {
        const n = nodes[id];
        return (n.chapter_title || n.chapter_blurb || "").trim();
      });
    if (hasMeta) return gamePack;

    const order = orderedNodeIds(gamePack);
    const total = order.length;
    const numChapters = total <= 10 ? 3 : total <= 22 ? 4 : 5;
    const chunk = Math.max(1, Math.ceil(total / numChapters));
    const chapterStarts = {};

    order.forEach(function (nid, i) {
      const chNum = Math.min(numChapters, Math.floor(i / chunk) + 1);
      const node = nodes[nid];
      const isFirst = !chapterStarts[chNum];
      if (isFirst) chapterStarts[chNum] = true;
      const label = cnChapterLabel(chNum);
      const titleSeed = node.title || "第" + label + "幕";
      const lines = getLines(node);
      const blurbRaw = isFirst ? ((lines[0] && lines[0].text) || gamePack.synopsis || "").slice(0, 48) : "";
      const blurb = blurbRaw ? normalizeDialogueText(blurbRaw) : "";
      nodes[nid] = Object.assign({}, node, {
        chapter: chNum,
        chapter_title: "第" + label + "章 · " + titleSeed,
        chapter_blurb: blurb,
      });
    });
    return gamePack;
  }

  function formatChapterHudLabel(chapterInfo) {
    const num = Number(chapterInfo.num) || 1;
    const label = cnChapterLabel(num);
    const prefixRe = /^第[一二三四五六七八九十\d]+章\s*(?:[·•]\s*)?/;
    const rawTitle = (chapterInfo.title || "").trim();
    const subtitle = rawTitle.replace(prefixRe, "").trim();
    const base = "第" + label + "章";
    if (subtitle && subtitle !== base && !/^第[一二三四五六七八九十\d]+章$/.test(subtitle)) {
      return base + " · " + subtitle;
    }
    return base;
  }

  function updateChapterHud(chapterInfo) {
    if (!els.chapterHud) return;
    if (!chapterInfo) {
      els.chapterHud.hidden = true;
      return;
    }
    els.chapterHud.hidden = false;
    const hudLabel = formatChapterHudLabel(chapterInfo);
    if (els.chapterHudNum) {
      els.chapterHudNum.textContent = cnChapterLabel(chapterInfo.num);
    }
    if (els.chapterHudText) {
      els.chapterHudText.textContent = hudLabel;
    }
    if (els.chapterHud) {
      els.chapterHud.setAttribute("aria-label", hudLabel);
    }
  }

  function clearChapterAutoTimer() {
    if (chapterAutoTimer) {
      clearTimeout(chapterAutoTimer);
      chapterAutoTimer = null;
    }
  }

  function hideChapterModal() {
    clearChapterAutoTimer();
    if (els.chapterModal) els.chapterModal.hidden = true;
    mode = "line";
  }

  function showChapterModal(chapterInfo, onStart) {
    if (!els.chapterModal) {
      if (onStart) onStart();
      return;
    }
    mode = "chapter";
    if (els.chapterModalNum) {
      els.chapterModalNum.textContent = "Chapter " + chapterInfo.num;
    }
    if (els.chapterModalTitle) {
      const short = chapterInfo.title.replace(/^第[一二三四五六七八九十\d]+章\s*[·•]\s*/, "");
      els.chapterModalTitle.textContent = short || chapterInfo.title;
    }
    if (els.chapterModalBlurb) {
      els.chapterModalBlurb.textContent = normalizeDialogueText(chapterInfo.blurb || "");
    }
    if (els.dialogueWrap) els.dialogueWrap.hidden = true;
    if (els.dialogueBox) els.dialogueBox.hidden = true;
    if (els.continueHint) els.continueHint.hidden = true;
    if (els.choicesPanel) els.choicesPanel.hidden = true;
    els.chapterModal.hidden = false;

    const startHandler = function () {
      hideChapterModal();
      seenChapters.add(chapterInfo.num);
      currentChapterNum = chapterInfo.num;
      updateChapterHud(chapterInfo);
      if (els.chapterModalStart) {
        els.chapterModalStart.removeEventListener("click", startHandler);
      }
      if (onStart) onStart();
    };

    if (els.chapterModalStart) {
      els.chapterModalStart.removeEventListener("click", startHandler);
      els.chapterModalStart.addEventListener("click", startHandler);
      els.chapterModalStart.focus();
    }
  }

  function shouldShowChapterModal(chapterNum) {
    return !seenChapters.has(chapterNum);
  }

  var CJK_CHAR_RE = /[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]/;
  var OPEN_SINGLE_QUOTE_RE = /^[''\u2018\u201a\u201b]/;
  var CLOSE_SINGLE_QUOTE_RE = /^[''\u2019\u201a\u201b]/;
  var OPEN_DOUBLE_QUOTE_RE = /^["\u201c\u201e\u201f]/;
  var CLOSE_DOUBLE_QUOTE_RE = /^["\u201d\u201e\u201f]/;
  var ENGLISH_APOSTROPHE_MARK = "\uE000";

  function protectEnglishApostrophes(text) {
    var saved = [];
    var s = text.replace(/[A-Za-z][''\u2019][A-Za-z]/g, function (m) {
      saved.push(m);
      return ENGLISH_APOSTROPHE_MARK + (saved.length - 1) + ENGLISH_APOSTROPHE_MARK;
    });
    s = s.replace(/[A-Za-z][''\u2019]s\b/g, function (m) {
      saved.push(m);
      return ENGLISH_APOSTROPHE_MARK + (saved.length - 1) + ENGLISH_APOSTROPHE_MARK;
    });
    return { text: s, saved: saved };
  }

  function restoreEnglishApostrophes(text, saved) {
    if (!saved.length) return text;
    return text.replace(
      new RegExp(ENGLISH_APOSTROPHE_MARK + "(\\d+)" + ENGLISH_APOSTROPHE_MARK, "g"),
      function (_, i) {
        return saved[+i];
      }
    );
  }

  function replaceQuotedSegments(text, openRe, closeRe) {
    var out = "";
    var i = 0;
    while (i < text.length) {
      var rest = text.slice(i);
      var openMatch = rest.match(openRe);
      if (!openMatch) {
        out += text.charAt(i);
        i += 1;
        continue;
      }
      var openQuote = openMatch[0];
      var j = i + openQuote.length;
      var inner = "";
      var closed = false;
      while (j < text.length) {
        var ch = text.charAt(j);
        var closeMatch = ch.match(closeRe);
        if (closeMatch) {
          if (CJK_CHAR_RE.test(inner)) {
            out += "\u300c" + inner + "\u300d";
          } else {
            out += openQuote + inner + closeMatch[0];
          }
          j += closeMatch[0].length;
          closed = true;
          break;
        }
        inner += ch;
        j += 1;
      }
      if (closed) {
        i = j;
      } else {
        out += text.charAt(i);
        i += 1;
      }
    }
    return out;
  }

  function normalizeDialogueText(text) {
    if (text == null || text === "") return text;
    var protectedText = protectEnglishApostrophes(String(text));
    var s = protectedText.text;
    s = replaceQuotedSegments(s, OPEN_SINGLE_QUOTE_RE, CLOSE_SINGLE_QUOTE_RE);
    s = replaceQuotedSegments(s, OPEN_DOUBLE_QUOTE_RE, CLOSE_DOUBLE_QUOTE_RE);
    return restoreEnglishApostrophes(s, protectedText.saved);
  }

  function normalizeChoiceText(text) {
    if (text == null || text === "") return "继续";
    var s = String(text).trim();
    if (!s) return "继续";
    var prev;
    do {
      prev = s;
      s = s.replace(/[（(][^）)]*[）)]\s*$/u, "").trim();
    } while (s !== prev && s.length);
    return normalizeDialogueText(s || String(text).trim() || "继续");
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

  function isProtagonistSpeaker(name) {
    if (!name || name === "旁白") return false;
    if (name === "你" || name === "我") return true;
    if (protagonistName && name === protagonistName) return true;
    if (pack && pack.protagonist_name && name === pack.protagonist_name) return true;
    if (pack && pack.characters && pack.characters.length) {
      const lead = pack.characters.find(function (c) {
        return (c.role || "").indexOf("主") >= 0;
      });
      if (lead && name === lead.name) return true;
    }
    return false;
  }

  function isMinorCharacterRole(role) {
    const r = String(role || "");
    return /配|次要|路人|群众|龙套|背景|店|老板|服务员|司机|护士|医生|老师/.test(r);
  }

  function isMajorCharacterRole(role) {
    const r = String(role || "");
    if (!r) return false;
    if (isMinorCharacterRole(r)) return false;
    return /主|核心|重要|关键|反派|男二|女二|女主|男主|对手|挚友|恋人/.test(r);
  }

  function countSpeakerLines(gamePack) {
    const counts = Object.create(null);
    if (!gamePack || !gamePack.nodes) return counts;
    Object.keys(gamePack.nodes).forEach(function (nid) {
      getLines(gamePack.nodes[nid]).forEach(function (line) {
        const sp = String((line && line.speaker) || "").trim();
        if (!sp || sp === "旁白") return;
        counts[sp] = (counts[sp] || 0) + 1;
      });
    });
    return counts;
  }

  function buildSpeakerColorMap(gamePack) {
    speakerColorMap = Object.create(null);
    if (!gamePack) return;

    const reserved = Object.create(null);
    const majorCandidates = [];

    function reserveProtagonist(name) {
      const n = String(name || "").trim();
      if (!n || n === "旁白" || reserved[n]) return;
      reserved[n] = true;
      speakerColorMap[n] = "protagonist";
    }

    reserveProtagonist(protagonistName);
    reserveProtagonist(gamePack.protagonist_name);
    reserveProtagonist("你");
    reserveProtagonist("我");

    (gamePack.characters || []).forEach(function (c) {
      if (!c || !c.name) return;
      if ((c.role || "").indexOf("主") >= 0) reserveProtagonist(c.name);
    });

    (gamePack.characters || []).forEach(function (c) {
      if (!c || !c.name || reserved[c.name]) return;
      if (isMajorCharacterRole(c.role)) {
        majorCandidates.push({ name: c.name, score: 1000 + (c.role || "").length });
        reserved[c.name] = true;
      }
    });

    const lineCounts = countSpeakerLines(gamePack);
    Object.keys(lineCounts)
      .sort(function (a, b) { return lineCounts[b] - lineCounts[a]; })
      .forEach(function (name) {
        if (reserved[name]) return;
        const bibleEntry = (gamePack.characters || []).find(function (c) {
          return c && c.name === name;
        });
        if (bibleEntry && isMinorCharacterRole(bibleEntry.role)) return;
        majorCandidates.push({ name: name, score: lineCounts[name] });
        reserved[name] = true;
      });

    majorCandidates.sort(function (a, b) { return b.score - a.score; });
    majorCandidates.slice(0, MAX_MAJOR_SPEAKERS).forEach(function (entry, idx) {
      speakerColorMap[entry.name] = MAJOR_SPEAKER_PALETTES[idx % MAJOR_SPEAKER_PALETTES.length];
    });
  }

  function resolveSpeakerTone(name, line) {
    const sp = String(name || "").trim();
    if (!sp || sp === "旁白") return "narration";
    if (line && line.role) {
      if (isMinorCharacterRole(line.role)) return "support";
      if ((line.role || "").indexOf("主") >= 0) return "protagonist";
      if (isMajorCharacterRole(line.role) && speakerColorMap[sp]) return speakerColorMap[sp];
    }
    if (speakerColorMap[sp]) return speakerColorMap[sp];
    if (isProtagonistSpeaker(sp)) return "protagonist";
    return "support";
  }

  function applySpeakerAppearance(name, line) {
    const tone = resolveSpeakerTone(name, line);
    if (els.speaker) {
      els.speaker.classList.remove.apply(els.speaker.classList, SPEAKER_NAME_CLASSES);
      if (tone === "protagonist") els.speaker.classList.add("vn-name--protagonist");
      else if (tone === "support") els.speaker.classList.add("vn-name--support");
      else if (MAJOR_SPEAKER_PALETTES.indexOf(tone) >= 0) els.speaker.classList.add("vn-name--" + tone);
    }
    if (els.dialogueBox) {
      els.dialogueBox.classList.remove.apply(els.dialogueBox.classList, DIALOGUE_COLOR_CLASSES);
      els.dialogueBox.classList.add("vn-dialogue--" + tone);
    }
  }

  function endingMeta(type, node) {
    const raw = typeof EndingLabels !== "undefined"
      ? EndingLabels.meta(type, node)
      : { typeLine: "故事至此收束", subtitle: "这一段旅程至此告一段落。", synopsis: "" };
    return {
      typeLine: raw.typeLine,
      subtitle: normalizeDialogueText(raw.subtitle),
      synopsis: normalizeDialogueText(raw.synopsis),
    };
  }

  function renderCodex() {
    if (!els.codexList || !pack || typeof ProgressStore === "undefined") return;
    const gallery = ProgressStore.endingGallery(entryId, pack);
    els.codexList.innerHTML = "";
    gallery.forEach(function (item) {
      const li = document.createElement("li");
      li.className = "ending-codex__item" + (item.unlocked ? " is-unlocked" : " is-locked");
      const mark = item.unlocked ? "✓" : "□";
      li.innerHTML =
        '<span class="ending-codex__mark">' + mark + "</span>" +
        '<span class="ending-codex__label">' + item.label + "</span>";
      els.codexList.appendChild(li);
    });
    if (els.codexBtn) els.codexBtn.hidden = gallery.length === 0;
    const unlocked = gallery.filter(function (g) { return g.unlocked; }).length;
    const total = gallery.length;
    const progressText = total ? "已解锁 " + unlocked + "/" + total : "";
    if (els.codexProgress) els.codexProgress.textContent = progressText;
    if (els.dockCodexLabel) {
      els.dockCodexLabel.textContent = total ? "结局图鉴 " + unlocked + "/" + total : "结局图鉴";
    }
  }

  function applyScene(node, style) {
    try {
      if (typeof MoodBackgrounds !== "undefined" && els.sceneBg) {
        MoodBackgrounds.apply(
          els.sceneBg,
          node.mood || "neutral",
          style || "urban_romance",
          node.image_prompt || "",
          {
            id: node.id,
            nodeId: node.id,
            title: node.title || "",
            scene_type: node.scene_type || "",
            scene_id: node.scene_id || "",
            bg_path: node.bg_path || "",
            lines: node.lines || node._lines || [],
          }
        );
      }
    } catch {
      if (els.sceneBg) els.sceneBg.style.background = "var(--vn-ink, #1a2030)";
    }
    syncSceneBgm(node);
  }

  function setPortraits() { /* 纯场景模式 */ }

  function hideChoices() {
    mode = "line";
    if (els.choicesPanel) els.choicesPanel.hidden = true;
    if (els.choices) els.choices.innerHTML = "";
    if (els.dialogueWrap) els.dialogueWrap.hidden = false;
    if (els.dialogueBox) els.dialogueBox.hidden = false;
    if (els.continueHint) els.continueHint.hidden = false;
  }

  function showChoices(node) {
    mode = "choice";
    if (els.continueHint) els.continueHint.hidden = true;
    if (els.dialogueWrap) els.dialogueWrap.hidden = true;
    if (els.dialogueBox) els.dialogueBox.hidden = true;
    if (els.choicesPanel) els.choicesPanel.hidden = false;
    if (!els.choices) return;
    els.choices.innerHTML = "";

    node.choices.forEach(function (ch) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "vn-choice-btn";

      const textEl = document.createElement("span");
      textEl.className = "vn-choice-text";
      textEl.textContent = normalizeChoiceText(ch.text || "继续");

      btn.appendChild(textEl);
      btn.setAttribute("aria-label", normalizeChoiceText(ch.text || "继续"));
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        handleChoice(node, ch, btn);
      });
      els.choices.appendChild(btn);
    });
  }

  function showEnding(node) {
    mode = "ending";
    if (typeof ProgressStore !== "undefined" && entryId) {
      ProgressStore.recordEnding(entryId, node);
      if (ProgressStore.clearCheckpoint) ProgressStore.clearCheckpoint(entryId);
      ProgressStore.syncServer(entryId);
      renderCodex();
    }
    if (els.continueHint) els.continueHint.hidden = true;
    if (els.choicesPanel) els.choicesPanel.hidden = true;
    if (els.dialogueWrap) els.dialogueWrap.hidden = true;
    if (els.dialogueBox) els.dialogueBox.hidden = true;
    if (els.characterZone) {
      els.characterZone.hidden = true;
      els.characterZone.classList.remove("is-visible");
    }
    if (els.endingBanner) {
      els.endingBanner.hidden = false;
      els.endingBanner.classList.add("is-visible");
    }
    const canonEndingType =
      typeof EndingLabels !== "undefined"
        ? EndingLabels.canonical(node.ending_type) ||
          EndingLabels.canonical(node.title)
        : node.ending_type || "";
    const ending = endingMeta(canonEndingType || node.ending_type, node);
    if (els.endingType) {
      els.endingType.textContent = ending.typeLine;
      els.endingType.dataset.ending = canonEndingType || "unknown";
    }
    if (els.endingSubtitle) els.endingSubtitle.textContent = ending.subtitle;
    if (els.endingSynopsis) {
      els.endingSynopsis.textContent = ending.synopsis || "";
      els.endingSynopsis.hidden = !ending.synopsis;
    }
    if (els.restartBtn) els.restartBtn.classList.add("is-visible");
    if (els.shareWorldBtn) els.shareWorldBtn.hidden = shareMode || !entryId;
    const hudReplay = document.getElementById("game-replay");
    if (hudReplay) hudReplay.hidden = false;
  }

  function showLine(node, lines, idx) {
    const line = lines[idx];
    const sp = (line && line.speaker) || "旁白";
    const text = normalizeDialogueText((line && line.text) || "……");

    if (els.speaker) {
      els.speaker.textContent = sp;
      els.speaker.hidden = !sp || sp === "旁白";
    }
    applySpeakerAppearance(sp, line);
    if (els.narrative) {
      els.narrative.classList.remove("vn-line-enter");
      void els.narrative.offsetWidth;
      els.narrative.textContent = text;
      els.narrative.classList.add("vn-line-enter");
    }
    updateCharacterArt(sp);

    const isLast = idx >= lines.length - 1;
    if (els.continueHint) {
      els.continueHint.hidden = false;
      els.continueHint.textContent = isLast
        ? node.choices && node.choices.length
          ? "点击继续 · 进入抉择"
          : node.is_ending
            ? "点击继续 · 结局"
            : "点击继续 · 下一场景"
        : "点击继续 ▸";
    }
  }

  function enterNode(id, skipChapterGate, resumeLineIndex) {
    if (!pack || !pack.nodes[id]) return;
    nodeId = id;
    lineIndex = typeof resumeLineIndex === "number" ? resumeLineIndex : 0;
    const node = pack.nodes[id];

    showGameView();
    if (els.style) {
      let styleLabel = pack.style_label || "";
      const meta = pack.meta;
      if (meta && meta.ending_count) {
        styleLabel += " · " + meta.ending_count + " 个结局";
      }
      els.style.textContent = styleLabel;
    }
    if (els.title) els.title.textContent = pack.title || "";
    if (els.sceneTag) {
      els.sceneTag.hidden = true;
      els.sceneTag.textContent = "";
    }
    hideEnding();

    if (typeof EngineHud !== "undefined" && EngineHud.update) {
      EngineHud.update(node);
    } else if (typeof updateEngineHud === "function") {
      updateEngineHud(node);
    }

    applyScene(node, pack.style);
    hideChoices();

    const lines = getLines(node);
    node._lines = lines;
    const chapterInfo = getNodeChapter(node);

    if (!skipChapterGate && shouldShowChapterModal(chapterInfo.num)) {
      pendingNodeId = id;
      showChapterModal(chapterInfo, function () {
        pendingNodeId = null;
        mode = "line";
        if (els.dialogueWrap) els.dialogueWrap.hidden = false;
        if (els.dialogueBox) els.dialogueBox.hidden = false;
        showLine(node, lines, lineIndex);
        persistCheckpoint();
      });
      return;
    }

    currentChapterNum = chapterInfo.num;
    seenChapters.add(chapterInfo.num);
    updateChapterHud(chapterInfo);
    mode = "line";
    if (els.dialogueWrap) els.dialogueWrap.hidden = false;
    if (els.dialogueBox) els.dialogueBox.hidden = false;
    showLine(node, lines, lineIndex);
    persistCheckpoint();
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
    showError("本段剧情无法继续，请返回启程台重新开始。");
  }

  function advance() {
    if (!pack || !nodeId) return;
    if (mode === "chapter") return;
    const node = pack.nodes[nodeId];
    const lines = node._lines || getLines(node);

    if (mode === "choice" || mode === "ending") return;

    if (lineIndex < lines.length - 1) {
      lineIndex += 1;
      if (typeof VnAudio !== "undefined") VnAudio.playClick();
      showLine(node, lines, lineIndex);
      persistCheckpoint();
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
    const textEl = btn.querySelector(".vn-choice-text");
    if (textEl) textEl.textContent = "正在生成后续剧情…";
    else btn.textContent = "正在生成后续剧情…";

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
      if (!res.ok) throw new Error(data.detail || "续写失败");
      pack = ensureChapterMetadata(normalizePack(data) || data);
      buildSpeakerColorMap(pack);
      enterNode(pack.nodes[nextId] ? nextId : resolveStartNode(pack));
    } catch (err) {
      btn.disabled = false;
      const restoreEl = btn.querySelector(".vn-choice-text");
      const restored = normalizeChoiceText(choice.text);
      if (restoreEl) restoreEl.textContent = restored;
      else btn.textContent = restored;
      showError(err.message || "续写失败");
    }
  }

  function onStageClick(e) {
    if (e.target.closest(".vn-choice-btn") || e.target.closest(".game__back")) return;
    if (e.target.closest(".vn-dialogue-wrap") || e.target.closest(".vn-dialogue")) {
      if (mode === "line") advance();
      return;
    }
    if (e.target.closest(".ending-codex")) return;
    if (e.target.closest(".game__dock-codex") || e.target.closest(".game__dock-audio")) return;
    if (mode === "chapter") {
      if (els.chapterModalStart) els.chapterModalStart.click();
      return;
    }
    if (mode === "line") advance();
  }

  function onStageKeydown(e) {
    if (!pack || els.root?.hidden) return;
    if (mode === "chapter") {
      if (e.key === " " || e.key === "Enter") {
        if (e.target.closest(".chapter-modal__btn") || document.activeElement === els.chapterModalStart) return;
        e.preventDefault();
        if (els.chapterModalStart) els.chapterModalStart.click();
      }
      return;
    }
    if (e.target.closest("input, textarea, select, button")) return;
    if (e.key === " " || e.key === "Enter") {
      if (mode === "line") {
        e.preventDefault();
        advance();
      }
    } else if (e.key === "Escape") {
      if (els.codexPanel && !els.codexPanel.hidden) {
        els.codexPanel.hidden = true;
        return;
      }
      if (mode !== "ending" && !shareMode && !window.confirm("确定返回启程台？进度已自动保存，下次可继续。")) return;
      hide();
      if (onBack) onBack();
    }
  }

  function enterGame(gamePack, text, opts) {
    bindElements();
    if (onEnter) onEnter();
    opts = opts || {};
    entryId = opts.entryId || entryId;
    protagonistName = opts.protagonistName || gamePack.protagonist_name || null;
    shareMode = Boolean(opts.shareMode);
    pack = ensureChapterMetadata(normalizePack(gamePack));
    buildSpeakerColorMap(pack);
    sourceText = text || "";
    seenChapters = new Set();
    currentChapterNum = null;
    activeBgmTrackId = null;
    pendingNodeId = null;
    hideChapterModal();
    renderCodex();
    if (els.shareWorldBtn && entryId && !shareMode) {
      els.shareWorldBtn.hidden = false;
    }
    const startId = resolveStartNode(pack);
    if (!startId) {
      showError("没有可玩场景。请返回工作室重试。");
      return;
    }
    let resume = null;
    if (!opts.forceRestart && typeof ProgressStore !== "undefined" && ProgressStore.loadCheckpoint) {
      resume = ProgressStore.loadCheckpoint(entryId);
    }
    if (resume && resume.nodeId && pack.nodes[resume.nodeId]) {
      if (resume.packTitle && pack.title && resume.packTitle !== pack.title) {
        resume = null;
      }
    }
    if (resume && !shareMode) {
      const ok = window.confirm("检测到上次游玩进度，是否从断点继续？");
      if (ok) {
        enterNode(resume.nodeId, true, Math.max(0, Number(resume.lineIndex) || 0));
        return;
      }
      if (ProgressStore.clearCheckpoint) ProgressStore.clearCheckpoint(entryId);
    }
    enterNode(startId);
  }

  function start(gamePack, text, opts) {
    enterGame(gamePack, text, opts);
  }

  function startDemo() {
    enterGame(DEMO_GAME_PACK, "", { entryId: "demo" });
  }

  function startFeatured(gamePack, opts) {
    const options = opts || {};
    enterGame(gamePack, "", {
      entryId: options.entryId || "featured",
      forceRestart: !!options.forceRestart,
    });
    if (
      options.underTheHood &&
      typeof UnderTheHood !== "undefined" &&
      UnderTheHood.bindPayload
    ) {
      UnderTheHood.bindPayload(options.underTheHood);
    }
    if (typeof UnderTheHood !== "undefined" && UnderTheHood.init) {
      UnderTheHood.init();
    }
  }

  function startShared(gamePack, text) {
    enterGame(gamePack, text, { shareMode: true });
  }

  function hide() {
    if (typeof VnAudio !== "undefined") VnAudio.stop();
    if (typeof EngineHud !== "undefined" && EngineHud.hide) {
      EngineHud.hide();
    }
    showStudio();
    pack = null;
    nodeId = null;
    lineIndex = 0;
    seenChapters = new Set();
    currentChapterNum = null;
    activeBgmTrackId = null;
    pendingNodeId = null;
    shareMode = false;
    hideChapterModal();
    if (els.chapterHud) els.chapterHud.hidden = true;
    if (els.codexPanel) els.codexPanel.hidden = true;
  }

  function restart() {
    if (!pack) return;
    seenChapters = new Set();
    currentChapterNum = null;
    activeBgmTrackId = null;
    pendingNodeId = null;
    hideChapterModal();
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
        if (shareMode) {
          window.location.href = "/";
          return;
        }
        hide();
        if (onBack) onBack();
      });
    }

    if (els.bgmToggle) {
      els.bgmToggle.addEventListener("click", function (e) {
        e.stopPropagation();
        if (typeof VnAudio !== "undefined") VnAudio.toggle();
        syncBgmToggle();
      });
    }

    document.addEventListener("vn-bgm-load-error", function (ev) {
      const d = ev && ev.detail;
      if (!d) return;
      const name = typeof MusicPicker !== "undefined" && MusicPicker.displayName
        ? MusicPicker.displayName(d.filename)
        : (d.filename || "曲目");
      const tip = d.trackId === "custom"
        ? "自定义音乐无法播放"
        : "背景音乐加载失败：" + name;
      document.querySelectorAll("#bgm-toggle").forEach(function (btn) {
        btn.title = tip;
        btn.setAttribute("aria-label", tip);
      });
    });

    document.addEventListener("vn-bgm-playback-change", function (ev) {
      const playing = ev && ev.detail && ev.detail.playing;
      if (!playing) return;
      document.querySelectorAll("#bgm-toggle").forEach(function (btn) {
        btn.title = "背景音乐";
        btn.setAttribute("aria-label", "背景音乐开关");
      });
    });

    const volumeWrap = document.getElementById("bgm-volume-wrap");
    const volumePop = document.getElementById("bgm-volume-pop");
    const volumeRange = document.getElementById("bgm-volume");
    if (volumeWrap && volumePop && volumeRange && typeof VnAudio !== "undefined") {
      let volumePinned = false;

      function setVolumePopOpen(open) {
        volumePop.hidden = !open;
        volumeWrap.classList.toggle("is-volume-open", open);
      }

      function hideVolumePopUnlessPinned() {
        if (!volumePinned) setVolumePopOpen(false);
      }

      if (typeof VnAudio.getVolume === "function") {
        volumeRange.value = String(Math.round(VnAudio.getVolume() * 100));
      }
      volumeWrap.addEventListener("mouseenter", function () {
        setVolumePopOpen(true);
      });
      volumeWrap.addEventListener("mouseleave", hideVolumePopUnlessPinned);
      volumeWrap.addEventListener("focusin", function () {
        setVolumePopOpen(true);
      });
      volumeWrap.addEventListener("focusout", function (e) {
        if (!volumePinned && !volumeWrap.contains(e.relatedTarget)) setVolumePopOpen(false);
      });
      volumePop.addEventListener("pointerdown", function () {
        volumePinned = true;
        setVolumePopOpen(true);
      });
      volumeRange.addEventListener("input", function () {
        VnAudio.setVolume(Number(volumeRange.value) / 100);
      });
      document.addEventListener("pointerdown", function (e) {
        if (!volumeWrap.contains(e.target)) {
          volumePinned = false;
          setVolumePopOpen(false);
        }
      });
    }
    if (els.codexBtn) {
      els.codexBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        renderCodex();
        if (els.codexPanel) els.codexPanel.hidden = !els.codexPanel.hidden;
      });
    }
    if (els.codexClose) {
      els.codexClose.addEventListener("click", function (e) {
        e.stopPropagation();
        if (els.codexPanel) els.codexPanel.hidden = true;
      });
    }
    if (els.codexFromEnd) {
      els.codexFromEnd.addEventListener("click", function (e) {
        e.stopPropagation();
        renderCodex();
        if (els.codexPanel) els.codexPanel.hidden = false;
      });
    }

    if (els.shareWorldBtn) {
      els.shareWorldBtn.addEventListener("click", async function (e) {
        e.stopPropagation();
        if (!entryId || typeof ShareWorld === "undefined") return;
        try {
          const link = await ShareWorld.createShareLink(entryId);
          await ShareWorld.copyToClipboard(link.url);
          els.shareWorldBtn.textContent = "链接已复制";
        } catch (err) {
          els.shareWorldBtn.textContent = "分享失败";
        }
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

  return { init, start, startDemo, startFeatured, startShared, hide, restart };
})();
