/** 结局展示：内部仍用英文 enum，UI 用文学收束语（非好/坏/普通结局） */

const EndingLabels = (function () {

  const LITERARY_TITLE_POOL = {
    good: [
      "青春就此落款",
      "误会终于冰释",
      "晨曦微照前程",
      "各得其所而安",
      "雨过天晴重逢",
      "前路仍向光明",
    ],
    bad: [
      "风过徒留怅惘",
      "从此山高水长",
      "再无归期",
      "错付的情义",
      "暮色四合归途",
      "天涯一别难追",
    ],
    neutral: [
      "晚风里的秘密",
      "云卷云舒各安",
      "潮起潮落至此",
      "生活回到寻常",
      "平淡收场也罢",
      "各安其所如是",
    ],
    true: [
      "真相终于揭晓",
      "万事同归一处",
      "谜底水落石出",
      "一切尘埃落定",
      "昭然若揭之时",
      "迷雾散尽见真",
    ],
    hidden: [
      "幽径独行无人知",
      "秘而不宣的终章",
      "极少人知的收束",
      "暗线于此闭合",
      "隐秘的另一种可能",
      "无人抵达的彼岸",
    ],
    open: [
      "前路未竟余音在",
      "故事仍将继续",
      "余音袅袅未绝",
      "未完待续的明天",
      "开放式留白",
      "后话尚待书写",
    ],
  };

  const LITERARY_FALLBACKS = {
    good: LITERARY_TITLE_POOL.good[0],
    bad: LITERARY_TITLE_POOL.bad[0],
    neutral: LITERARY_TITLE_POOL.neutral[0],
    true: LITERARY_TITLE_POOL.true[0],
    hidden: LITERARY_TITLE_POOL.hidden[0],
    open: LITERARY_TITLE_POOL.open[0],
  };

  const ALIASES = {
    good: "good",
    好: "good",
    好结局: "good",
    bad: "bad",
    坏: "bad",
    坏结局: "bad",
    be: "bad",
    neutral: "neutral",
    平和: "neutral",
    平和结局: "neutral",
    普通: "neutral",
    普通结局: "neutral",
    true: "true",
    真: "true",
    真结局: "true",
    hidden: "hidden",
    隐藏: "hidden",
    隐藏结局: "hidden",
    open: "open",
    开放: "open",
    开放结局: "open",
  };

  const MORAL_JUDGMENT_TITLES = new Set([
    "好结局",
    "坏结局",
    "普通结局",
    "平和结局",
  ]);

  const TONES = {
    good: "故事在温暖与希望中收束。",
    bad: "命运背道而驰，留下遗憾与回味。",
    neutral: "尘埃落定，生活回到寻常轨道。",
    true: "真相揭晓，一切尘埃落定于最完美的收束。",
    hidden: "极少有人抵达的隐秘收束。",
    open: "前路未竟，故事仍在继续。",
  };

  const DEFAULT_LABEL = "故事至此收束";
  const DEFAULT_TONE = "这一段旅程至此告一段落。";
  const RAW_TYPE_RE = /^(good|bad|neutral|true|hidden|open)(?:[\s_\-·：:]+|(?=结局))(?:结局)?$/i;
  const BROKEN_ENDING_TEMPLATE_RE = /^[\u4e00-\u9fff·…]{1,6}(?:已远，|成空，|落定，|揭晓，|深处，|之后，)(?:平淡收场|徒留怅惘|曙光可期|尘埃落定|秘而不宣|故事仍续)$/;
  const BROKEN_ENDING_SNIP_RE = /^[\u4e00-\u9fff]{2,5}已远/;

  function normalize(type) {
    const key = String(type || "").trim().toLowerCase();
    if (!key) return "";
    if (ALIASES[key]) return ALIASES[key];
    const bare = key.replace(/\s*结局\s*$/, "").trim();
    if (ALIASES[bare]) return ALIASES[bare];
    if (RAW_TYPE_RE.test(key)) return key.match(RAW_TYPE_RE)[1].toLowerCase();
    if (Object.prototype.hasOwnProperty.call(LITERARY_FALLBACKS, key)) return key;
    return "";
  }

  function canonical(type) {
    return normalize(type);
  }

  function literaryFallback(type) {
    return LITERARY_FALLBACKS[normalize(type)] || DEFAULT_LABEL;
  }

  function label(type) {
    return literaryFallback(type);
  }

  function tone(type) {
    return TONES[normalize(type)] || DEFAULT_TONE;
  }

  function isMoralJudgmentTitle(title) {
    const t = String(title || "").trim();
    return MORAL_JUDGMENT_TITLES.has(t);
  }

  function isRawTypeTitle(title, type) {
    const t = String(title || "").trim().toLowerCase();
    const key = normalize(type);
    if (!t) return false;
    if (isMoralJudgmentTitle(String(title || "").trim())) return true;
    if (key && (t === key || t === key + " 结局" || t === key + "结局")) return true;
    const bare = t.replace(/\s*结局\s*$/, "").trim();
    if (Object.prototype.hasOwnProperty.call(LITERARY_FALLBACKS, bare)) return false;
    if (Object.prototype.hasOwnProperty.call(ALIASES, bare)) return true;
    return RAW_TYPE_RE.test(t);
  }

  function sanitizeEndingTitle(title, type) {
    const sceneTitle = String(title || "").trim();
    if (!sceneTitle) return "";
    if (isRawTypeTitle(sceneTitle, type) || isMoralJudgmentTitle(sceneTitle)) return "";
    const stripped = sceneTitle
      .replace(/^(good|bad|neutral|true|hidden|open)(?:[\s_\-·：:]+|(?=结局))/i, "")
      .trim();
    if (!stripped || stripped === "结局" || isRawTypeTitle(stripped, type)) return "";
    if (isMoralJudgmentTitle(stripped)) return "";
    return stripped;
  }

  function hasLiteraryChinese(text) {
    const t = String(text || "").trim();
    if (!t || t.length < 2) return false;
    return /[\u4e00-\u9fff]/.test(t);
  }

  function isBrokenEndingTitle(title) {
    const clean = String(title || "").trim();
    if (!clean || clean.length < 4) return true;
    if (isMoralJudgmentTitle(clean)) return true;
    if (isRawTypeTitle(clean)) return true;
    const compact = clean.replace(/\s+/g, "");
    if (BROKEN_ENDING_TEMPLATE_RE.test(compact)) return true;
    if (BROKEN_ENDING_SNIP_RE.test(compact)) return true;
    return false;
  }

  function isGenericFallback(text, type) {
    const t = String(text || "").trim();
    const key = normalize(type);
    if (!t || t === DEFAULT_LABEL) return true;
    if (LITERARY_FALLBACKS[key] === t) return true;
    const pool = LITERARY_TITLE_POOL[key];
    if (pool && pool.indexOf(t) >= 0) return true;
    return false;
  }

  function trimToLiteraryLabel(text, maxLen) {
    const limit = maxLen || 12;
    const t = String(text || "").trim().replace(/\s+/g, "");
    if (!t) return "";
    if (t.length <= limit) return t;
    const chunk = t.slice(0, limit);
    const punct = chunk.search(/[，。！？、；：…]$/);
    if (punct >= 3) return chunk.slice(0, punct + 1);
    return chunk;
  }

  function trimToSubtitle(text) {
    const t = String(text || "").trim();
    if (!t) return "";
    if (t.length <= 48) return t;
    return t.slice(-48);
  }

  function poeticExcerpt(lines) {
    if (!lines || !lines.length) return "";
    const last = String((lines[lines.length - 1] && lines[lines.length - 1].text) || "").trim();
    if (last && hasLiteraryChinese(last)) return last;
    const texts = [];
    for (let i = Math.max(0, lines.length - 2); i < lines.length; i++) {
      const t = String((lines[i] && lines[i].text) || "").trim();
      if (t) texts.push(t);
    }
    const joined = texts.join("").replace(/\s+/g, "");
    if (!joined || !hasLiteraryChinese(joined)) return "";
    if (joined.length <= 20) return joined;
    return joined.slice(-18);
  }

  function lastDialogueLine(node) {
    if (!node || !node.lines || !node.lines.length) return "";
    return String(node.lines[node.lines.length - 1].text || "").trim();
  }

  function excerptToLabel(excerpt) {
    const t = String(excerpt || "").trim().replace(/\s+/g, "");
    if (!t || !hasLiteraryChinese(t) || isBrokenEndingTitle(t)) return "";
    if (t.length <= 12) return t;
    const parts = t.split(/[，。！？、；：…]/).map(function (p) { return p.trim(); }).filter(Boolean);
    for (let i = parts.length - 1; i >= 0; i--) {
      const p = parts[i];
      if (p.length >= 4 && p.length <= 12 && !isBrokenEndingTitle(p)) return p;
    }
    return "";
  }

  function deriveDisplayLabel(type, node) {
    const key = normalize(type) || normalize(node && node.title) || "";
    const sceneTitle = sanitizeEndingTitle(node && node.title, key);
    if (sceneTitle && hasLiteraryChinese(sceneTitle) && !isBrokenEndingTitle(sceneTitle)) {
      return trimToLiteraryLabel(sceneTitle, 12);
    }
    const excerpt = excerptToLabel(poeticExcerpt(node && node.lines));
    if (excerpt) {
      return excerpt;
    }
    return literaryFallback(key);
  }

  function meta(type, node) {
    const key = normalize(type) || normalize(node && node.title) || "";
    const typeLine = deriveDisplayLabel(key, node);
    const lastLine = lastDialogueLine(node);
    let subtitle = "";
    if (lastLine && lastLine !== typeLine && hasLiteraryChinese(lastLine)) {
      subtitle = trimToSubtitle(lastLine);
    } else if (!isGenericFallback(typeLine, key)) {
      subtitle = tone(key);
    }
    if (subtitle === typeLine) subtitle = "";

    let synopsis = "";
    const sceneTitle = sanitizeEndingTitle(node && node.title, key);
    if (
      sceneTitle &&
      sceneTitle !== typeLine &&
      !isBrokenEndingTitle(sceneTitle)
    ) {
      synopsis = "\u201c" + sceneTitle + "\u201d";
    }
    if (lastLine && lastLine.length <= 72 && lastLine !== typeLine && lastLine !== subtitle) {
      synopsis = synopsis ? synopsis + " · " + lastLine : lastLine;
    }
    return { typeLine: typeLine, subtitle: subtitle, synopsis: synopsis };
  }

  function galleryLabel(type, titleOrNode, maybeNode) {
    const node = titleOrNode && typeof titleOrNode === "object"
      ? titleOrNode
      : (maybeNode || { title: titleOrNode });
    const key = normalize(type) || normalize(node && node.title) || "";
    return deriveDisplayLabel(key, node);
  }

  return {
    canonical: canonical,
    label: label,
    tone: tone,
    meta: meta,
    galleryLabel: galleryLabel,
    deriveDisplayLabel: deriveDisplayLabel,
    literaryFallback: literaryFallback,
    isRawTypeTitle: isRawTypeTitle,
    isBrokenEndingTitle: isBrokenEndingTitle,
    sanitizeEndingTitle: sanitizeEndingTitle,
    LITERARY_FALLBACKS: LITERARY_FALLBACKS,
  };
})();
