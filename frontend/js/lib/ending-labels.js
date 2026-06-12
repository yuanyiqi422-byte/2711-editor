/** 结局展示：内部仍用英文 enum，UI 用文学收束语（非好/坏/普通结局） */

const EndingLabels = (function () {

  const LITERARY_FALLBACKS = {
    good: "尘埃落定，各归其所",
    bad: "风过无痕，徒留怅惘",
    neutral: "潮起潮落，故事至此",
    true: "真相昭然，万事同归",
    hidden: "幽径独行，此中无人知",
    open: "前路未竟，余音袅袅",
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

  function deriveDisplayLabel(type, node) {
    const key = normalize(type) || normalize(node && node.title) || "";
    const sceneTitle = sanitizeEndingTitle(node && node.title, key);
    if (sceneTitle && hasLiteraryChinese(sceneTitle)) {
      return trimToLiteraryLabel(sceneTitle, 16);
    }
    const excerpt = poeticExcerpt(node && node.lines);
    if (excerpt) {
      return trimToLiteraryLabel(excerpt, 16);
    }
    return literaryFallback(key);
  }

  function meta(type, node) {
    const key = normalize(type) || normalize(node && node.title) || "";
    const typeLine = deriveDisplayLabel(key, node);
    const subtitle = tone(key);
    let synopsis = "";
    const sceneTitle = sanitizeEndingTitle(node && node.title, key);
    if (sceneTitle && sceneTitle !== typeLine) {
      synopsis = "\u201c" + sceneTitle + "\u201d";
    }
    const lastLine = node && node.lines && node.lines.length
      ? String(node.lines[node.lines.length - 1].text || "").trim()
      : "";
    if (lastLine && lastLine.length <= 72 && lastLine !== typeLine) {
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
    sanitizeEndingTitle: sanitizeEndingTitle,
    LITERARY_FALLBACKS: LITERARY_FALLBACKS,
  };
})();
