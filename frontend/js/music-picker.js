/**
 * BgmAuto (MusicPicker) — 按故事风格 / 场景 mood 自动匹配 BGM，可选本地上传
 */

const MusicPicker = (function () {
  const CUSTOM_NAME_KEY = "2711-bgm-custom-name";
  const DISABLED_KEY = "2711-bgm-disabled";
  const AUTO_MATCH_KEY = "2711-bgm-auto-match";

  /** @type {{ url: string, name: string } | null} */
  let customSession = null;

  let currentStyle = "urban_romance";

  /** @type {string | null} 换一首后手动选定的文件名 */
  let manualPick = null;

  let bgmDisabled = false;
  let autoMatchEnabled = true;

  try {
    bgmDisabled = localStorage.getItem(DISABLED_KEY) === "1";
    autoMatchEnabled = localStorage.getItem(AUTO_MATCH_KEY) !== "0";
  } catch (_) { /* noop */ }

  let els = {};

  /** 加载失败 / 审计标记的曲目 — 与 corrupt-file audit 共享 */
  const failedFilenames = new Set();

  let skipInProgress = false;
  let consecutiveFailures = 0;
  const MAX_SKIP_ATTEMPTS = 8;
  const SHUFFLE_DEBOUNCE_MS = 300;

  /** 当前意图播放的 trackId — 用于忽略 superseded 加载错误 */
  let expectedTrackId = null;
  let lastShuffleAt = 0;
  let initDone = false;

  /** 磁盘文件名常量 — 与 frontend/audio/bgm/ 一致（35 首） */
  const FILES = {
    journey: "Journey.mp3",
    loveDeepspace: "Love And Deepspace.mp3",
    dollHouse: "岩崎琢 - 人形の館.mp3",
    kikujiro: "菊次郎的夏天：Summer-Silu+Wang&久石让.mp3",
    littleStory: "Valentin-A Little Story.mp3",
    timeToLove: "OCTOBER - Time to love_20867599.mp3",
    skyChildren: "Choefeker _ Faolan - Sky_Children of the light (feat_ Faolan).ogg",
    ayasaConfession: "Ayasa绚沙 - 告白の夜 (告白之夜) (LIVE!! Ayasa Theater episode 7).ogg",
    reverseAlisa: "Reverse - ALisa.mp3",
    hisTheme: "Toby Fox - His Theme.mp3",
    toTheMoon: "To the moon.mp3",
    easternThought: "Kevin_MacLeod-Eastern_Thought.mp3",
    ishikariLore: "Kevin_MacLeod-Ishikari_Lore.mp3",
    ripplesGuzheng: "Kevin_MacLeod-Ripples_guzheng.mp3",
    nightOnDocks: "Kevin_MacLeod-Night_on_the_Docks.mp3",
    bossaAntigua: "Kevin_MacLeod-Bossa_Antigua.mp3",
    floatingCities: "Kevin_MacLeod-Floating_Cities.mp3",
    mysterySoft: "HoliznaCC0 - Mystery (CC0).mp3",
    atmosphereSoft: "HoliznaCC0 - Atmosphere 1 (CC0).mp3",
    driftingPianoSoft: "HoliznaCC0 - Drifting Piano (CC0).mp3",
    campusSoftPiano: "campus_soft_piano.mp3",
    schoolRomanceAcoustic: "school_romance_acoustic.mp3",
    sliceOfLifeLofi: "slice_of_life_lofi_quiet.mp3",
    xianxiaXiaoMist: "xianxia_xiao_mist.mp3",
    xianxiaGuzhengMist: "xianxia_guzheng_mist.mp3",
    xianxiaPipaAmbient: "xianxia_pipa_ambient.mp3",
    dhakaSoftAsian: "Kevin_MacLeod-Dhaka_soft_asian.mp3",
    pixabayDiziFlute: "Pixabay-Chinese_Dizi_Flute.mp3",
    pixabayCloudsPagoda: "Pixabay-Clouds_Ancient_Pagoda.mp3",
    pixabayGuzhengJourney: "Pixabay-Mystical_Guzheng_Journey.mp3",
    holiznaDriftingPianoNight: "holizna-drifting-piano-night.mp3",
    holiznaShimmerChill: "holizna-shimmer-chill-ambient.mp3",
    holiznaSpringHorizon: "holizna-spring-on-horizon-soft-orchestra.mp3",
    holiznaWaitingCalmStudy: "holizna-waiting-around-calm-study.mp3",
    holiznaYetAgainPeaceful: "holizna-yet-again-peaceful-lofi.mp3",
  };

  /** OGG 主文件 → MP3 回退（Safari / 部分浏览器无 OGG 解码） */
  const OGG_MP3_FALLBACKS = {
    [FILES.skyChildren]: "sky_children.mp3",
    [FILES.ayasaConfession]: "ayasa_confession_night.mp3",
  };

  /** 全部 35 首磁盘曲目（去重） */
  const ALL_FILENAMES = Object.keys(FILES).map(function (k) { return FILES[k]; });

  /**
   * 磁盘文件名 → UI 展示名（极少数自动解析补不上的手工覆盖）。
   * 默认策略：从文件名提取曲名原名，不强制中文化。
   */
  const DISPLAY_NAMES = {};

  /** 偏响曲目 — 仅作风格池轮换尾部，不作 mood / 风格默认 */
  const LOUD = [
    FILES.journey,
    FILES.loveDeepspace,
  ];

  /** 轻柔曲目 — mood 默认与风格池前排均优先从此选取 */
  const GENTLE = [
    FILES.ayasaConfession,
    FILES.littleStory,
    FILES.skyChildren,
    FILES.kikujiro,
    FILES.timeToLove,
    FILES.reverseAlisa,
    FILES.hisTheme,
    FILES.toTheMoon,
    FILES.easternThought,
    FILES.ishikariLore,
    FILES.ripplesGuzheng,
    FILES.nightOnDocks,
    FILES.bossaAntigua,
    FILES.floatingCities,
    FILES.mysterySoft,
    FILES.atmosphereSoft,
    FILES.driftingPianoSoft,
    FILES.campusSoftPiano,
    FILES.schoolRomanceAcoustic,
    FILES.sliceOfLifeLofi,
    FILES.xianxiaXiaoMist,
    FILES.xianxiaGuzhengMist,
    FILES.xianxiaPipaAmbient,
    FILES.dhakaSoftAsian,
    FILES.pixabayDiziFlute,
    FILES.pixabayCloudsPagoda,
    FILES.pixabayGuzhengJourney,
    FILES.holiznaDriftingPianoNight,
    FILES.holiznaShimmerChill,
    FILES.holiznaSpringHorizon,
    FILES.holiznaWaitingCalmStudy,
    FILES.holiznaYetAgainPeaceful,
    FILES.dollHouse,
  ];

  /** 外部别名 → 内部风格键（ancient_fantasy / campus_youth 与工坊 preset 对齐） */
  const STYLE_ALIASES = {
    ancient_fantasy: "xianxia",
    campus_youth: "campus",
  };

  function normalizeStyle(style) {
    return STYLE_ALIASES[style] || style || "urban_romance";
  }

  /** 风格默认曲 — 优先选轻柔、不抢对白 */
  const STYLE_BGM = {
    xianxia: FILES.littleStory,
    ancient_fantasy: FILES.littleStory,
    urban_romance: FILES.timeToLove,
    mystery: FILES.hisTheme,
    campus: FILES.kikujiro,
    campus_youth: FILES.kikujiro,
  };

  const XIANXIA_POOL = [
    FILES.littleStory,
    FILES.ripplesGuzheng,
    FILES.easternThought,
    FILES.ishikariLore,
    FILES.ayasaConfession,
    FILES.skyChildren,
    FILES.xianxiaXiaoMist,
    FILES.xianxiaGuzhengMist,
    FILES.xianxiaPipaAmbient,
    FILES.dhakaSoftAsian,
    FILES.pixabayDiziFlute,
    FILES.pixabayCloudsPagoda,
    FILES.pixabayGuzhengJourney,
    FILES.journey,
  ];

  const URBAN_POOL = [
    FILES.timeToLove,
    FILES.nightOnDocks,
    FILES.bossaAntigua,
    FILES.skyChildren,
    FILES.ayasaConfession,
    FILES.littleStory,
    FILES.holiznaDriftingPianoNight,
    FILES.holiznaYetAgainPeaceful,
    FILES.holiznaWaitingCalmStudy,
    FILES.holiznaShimmerChill,
    FILES.holiznaSpringHorizon,
    FILES.sliceOfLifeLofi,
    FILES.loveDeepspace,
  ];

  const MYSTERY_POOL = [
    FILES.hisTheme,
    FILES.atmosphereSoft,
    FILES.mysterySoft,
    FILES.driftingPianoSoft,
    FILES.holiznaDriftingPianoNight,
    FILES.holiznaShimmerChill,
    FILES.floatingCities,
    FILES.reverseAlisa,
    FILES.ishikariLore,
    FILES.toTheMoon,
    FILES.dollHouse,
  ];

  const CAMPUS_POOL = [
    FILES.kikujiro,
    FILES.timeToLove,
    FILES.ayasaConfession,
    FILES.littleStory,
    FILES.skyChildren,
    FILES.campusSoftPiano,
    FILES.schoolRomanceAcoustic,
    FILES.sliceOfLifeLofi,
    FILES.holiznaWaitingCalmStudy,
    FILES.holiznaYetAgainPeaceful,
    FILES.holiznaSpringHorizon,
  ];

  /** 各风格可轮换曲库（换一首 / 按章节从此池选取；偏响曲目靠后） */
  const STYLE_BGM_POOL = {
    xianxia: XIANXIA_POOL,
    ancient_fantasy: XIANXIA_POOL,
    urban_romance: URBAN_POOL,
    mystery: MYSTERY_POOL,
    campus: CAMPUS_POOL,
    campus_youth: CAMPUS_POOL,
  };

  /** mood 优先于 style；calm/peaceful/romantic/sad/tense/mysterious/dark 一律走 GENTLE */
  const MOOD_BGM = {
    calm: FILES.holiznaDriftingPianoNight,
    peaceful: FILES.holiznaYetAgainPeaceful,
    hopeful: FILES.holiznaSpringHorizon,
    golden_dawn: FILES.holiznaSpringHorizon,
    romantic: FILES.timeToLove,
    sad: FILES.toTheMoon,
    tense: FILES.reverseAlisa,
    mysterious: FILES.driftingPianoSoft,
    dark: FILES.hisTheme,
    dark_mystery: FILES.atmosphereSoft,
    storm_sea: FILES.easternThought,
    neon_rain: FILES.holiznaShimmerChill,
  };

  const STYLE_LABELS = {
    xianxia: "古风仙侠",
    ancient_fantasy: "古风仙侠",
    urban_romance: "都市言情",
    mystery: "悬疑推理",
    campus: "校园青春",
    campus_youth: "校园青春",
  };

  function resolvePlayableFilename(filename) {
    if (!filename) return filename;
    if (/\.ogg$/i.test(filename) && !isOggSupported()) {
      return OGG_MP3_FALLBACKS[filename] || filename;
    }
    return filename;
  }

  function bgmUrl(filename) {
    const resolved = resolvePlayableFilename(filename);
    return "audio/bgm/" + encodeURIComponent(resolved);
  }

  function isOggSupported() {
    const a = document.createElement("audio");
    const can = a.canPlayType('audio/ogg; codecs="vorbis"');
    return can === "probably" || can === "maybe";
  }

  function isPlayableFilename(filename) {
    if (!filename) return false;
    if (failedFilenames.has(filename)) return false;
    if (/\.ogg$/i.test(filename)) {
      if (isOggSupported()) return true;
      const fb = OGG_MP3_FALLBACKS[filename];
      return !!(fb && !failedFilenames.has(fb));
    }
    return true;
  }

  function filterPlayable(filenames) {
    return filenames.filter(isPlayableFilename);
  }

  function pickAlternateFilename(style, mood, exclude) {
    const moodKey = mood && mood !== "neutral" && MOOD_BGM[mood] ? mood : null;
    if (moodKey && MOOD_BGM[moodKey] !== exclude && isPlayableFilename(MOOD_BGM[moodKey])) {
      return MOOD_BGM[moodKey];
    }
    const pool = filterPlayable(buildShufflePool(style));
    const candidates = pool.filter(function (f) { return f !== exclude; });
    if (candidates.length) return candidates[Math.floor(Math.random() * candidates.length)];
    const key = normalizeStyle(style);
    const def = STYLE_BGM[key] || STYLE_BGM.urban_romance;
    if (def && def !== exclude && isPlayableFilename(def)) return def;
    const gentle = filterPlayable(GENTLE);
    return gentle[0] || STYLE_BGM.urban_romance;
  }

  /** trackId 必须包含文件名，否则换一首时 VnAudio / game 会因 id 相同而跳过加载 */
  function buildTrackId(style, moodKey, filename) {
    const key = normalizeStyle(style);
    if (moodKey) return "mood_" + moodKey + "|" + filename;
    if (manualPick) return "manual_" + key + "|" + filename;
    return "style_" + key + "|" + filename;
  }

  const SOURCE_PREFIXES = ["holizna", "pixabay", "holiznacc0"];

  function hasLatin(text) {
    return /[A-Za-z]/.test(text);
  }

  function primaryNonLatin(text) {
    const cjk = (text.match(/[\u3040-\u30ff\u3400-\u9fff]/g) || []).length;
    const latin = (text.match(/[A-Za-z]/g) || []).length;
    return cjk > latin;
  }

  function titleCaseLatin(text) {
    return text.replace(/\b[a-z]/g, function (ch) { return ch.toUpperCase(); });
  }

  function stripExtension(raw) {
    return String(raw).replace(/\.[^.]+$/, "");
  }

  function stripNoiseParens(name) {
    let s = name;
    s = s.replace(/\s*\(CC0\)/gi, "");
    s = s.replace(/\s*\(LIVE!![^)]*\)/gi, "");
    s = s.replace(/\s*\([^)]*episode[^)]*\)/gi, "");
    s = s.replace(/\s*\([^)]*feat[\s._][^)]*\)/gi, "");
    s = s.replace(/\s*\(feat[\s._][^)]*\)/gi, "");
    return s.replace(/\s+/g, " ").trim();
  }

  function stripTrailingIdSuffix(text) {
    return text.replace(/_\d{5,}$/, "").trim();
  }

  /** 去掉曲名末尾的中文译名括号，如 告白の夜 (告白之夜) → 告白の夜 */
  function stripTranslationParen(song) {
    const match = song.match(/^(.+?)\s*\(([^)]+)\)\s*$/);
    if (!match) return song;
    const before = match[1].trim();
    const inner = match[2].trim();
    if (/[ぁ-んァ-ヶ]/.test(before) && /^[一-龥·\s]+$/.test(inner)) {
      return before;
    }
    return song;
  }

  function normalizeSongPart(part) {
    let song = stripTrailingIdSuffix(part);
    song = song.replace(/_/g, " ").replace(/\s+/g, " ").trim();
    song = stripTranslationParen(song);
    return song;
  }

  /** 仅用于全小写/下划线素材名（如 campus_soft_piano、holizna 系列） */
  function humanizeSlugName(name) {
    const spaced = name.replace(/_/g, " ").replace(/-/g, " ").replace(/\s+/g, " ").trim();
    if (/^[a-z0-9\s]+$/.test(spaced)) {
      return titleCaseLatin(spaced);
    }
    return spaced;
  }

  function isSourceArtist(artist) {
    const lower = artist.toLowerCase().replace(/_/g, " ").trim();
    return SOURCE_PREFIXES.some(function (prefix) {
      return lower === prefix || lower.indexOf(prefix) === 0;
    });
  }

  function cleanFilenameLabel(raw) {
    if (!raw) return "未知曲目";

    let name = stripNoiseParens(stripExtension(raw));

    if (/[一-龥]/.test(name) && /[：:]/.test(name)) {
      const beforeColon = name.split(/[：:]/)[0].trim();
      if (beforeColon && /[一-龥]/.test(beforeColon)) return beforeColon;
    }

    const holiznaKebab = name.match(/^holizna[-](.+)$/i);
    if (holiznaKebab) {
      return humanizeSlugName(holiznaKebab[1]);
    }

    const artistSong = name.match(/^(.+?)\s*[-–—]\s*(.+)$/);
    if (artistSong) {
      const artist = artistSong[1].replace(/\s*_\s*/g, " ").replace(/_/g, " ").replace(/\s+/g, " ").trim();
      const song = normalizeSongPart(artistSong[2]);
      if (song) {
        if (isSourceArtist(artist) || /^kevin\s*mac\s*leod$/i.test(artist)) return song;
        if (primaryNonLatin(artist) || primaryNonLatin(song)) return song;
        return song;
      }
    }

    name = stripTrailingIdSuffix(name);
    if (name.indexOf("_") !== -1) {
      name = humanizeSlugName(name);
    } else {
      name = name.replace(/\s+/g, " ").trim();
    }
    return name || raw;
  }

  function displayName(filename) {
    if (!filename) return "无背景音乐";
    if (DISPLAY_NAMES[filename]) return DISPLAY_NAMES[filename];
    return cleanFilenameLabel(filename);
  }

  function pickFilename(style, mood) {
    const moodKey = mood && mood !== "neutral" && MOOD_BGM[mood] ? mood : null;
    let filename;
    if (moodKey) filename = MOOD_BGM[moodKey];
    else if (manualPick) filename = manualPick;
    else {
      const key = normalizeStyle(style);
      filename = STYLE_BGM[key] || STYLE_BGM[style] || STYLE_BGM.urban_romance;
    }
    if (!isPlayableFilename(filename)) {
      filename = pickAlternateFilename(style, moodKey, filename);
    }
    return filename;
  }

  function getCurrentFilename() {
    return pickFilename(currentStyle, null);
  }

  /** GENTLE + 当前风格曲库去重合并，供换一首随机选取 */
  function buildShufflePool(style) {
    const stylePool = STYLE_BGM_POOL[normalizeStyle(style)] || STYLE_BGM_POOL.urban_romance;
    const seen = new Set();
    const pool = [];
    GENTLE.forEach(function (f) {
      if (!seen.has(f)) {
        seen.add(f);
        pool.push(f);
      }
    });
    stylePool.forEach(function (f) {
      if (!seen.has(f)) {
        seen.add(f);
        pool.push(f);
      }
    });
    return pool;
  }

  /** 从 GENTLE ∪ 风格曲库中随机选一首，排除当前正在播放的曲目 */
  function randomTrack(style) {
    const pool = filterPlayable(buildShufflePool(style || currentStyle));
    const current = getCurrentFilename();
    let candidates = pool.filter(function (f) { return f !== current; });
    if (!candidates.length) candidates = pool.slice();
    if (!candidates.length) return STYLE_BGM.urban_romance;
    return candidates[Math.floor(Math.random() * candidates.length)];
  }

  /** 按章节从风格曲库选取固定曲目（同章不切换） */
  function resolveForChapter(style, chapterNum) {
    const resolvedStyle = normalizeStyle(style || currentStyle || "urban_romance");
    const ch = Math.max(1, Number(chapterNum) || 1);

    if (bgmDisabled) {
      return { trackId: "silent", style: resolvedStyle };
    }

    if (customSession && customSession.url) {
      return {
        trackId: "custom",
        customUrl: customSession.url,
        style: resolvedStyle,
      };
    }

    const pool = filterPlayable(STYLE_BGM_POOL[resolvedStyle] || STYLE_BGM_POOL.urban_romance);
    const filename = pool.length
      ? pool[(ch - 1) % pool.length]
      : pickAlternateFilename(resolvedStyle, null, null);
    return {
      trackId: "chapter_" + resolvedStyle + "_" + ch + "|" + filename,
      style: resolvedStyle,
      fileUrl: bgmUrl(filename),
    };
  }

  function resolveForPlay(fallbackStyle, mood) {
    const style = normalizeStyle(fallbackStyle || currentStyle || "urban_romance");

    if (bgmDisabled) {
      return { trackId: "silent", style: style };
    }

    if (customSession && customSession.url) {
      return {
        trackId: "custom",
        customUrl: customSession.url,
        style: style,
      };
    }

    const moodKey = mood && mood !== "neutral" && MOOD_BGM[mood] ? mood : null;
    const filename = pickFilename(style, moodKey);
    return {
      trackId: buildTrackId(style, moodKey, filename),
      style: style,
      mood: moodKey,
      fileUrl: bgmUrl(filename),
    };
  }

  function getAutoTrackLabel(style) {
    const key = STYLE_BGM[normalizeStyle(style)] ? normalizeStyle(style) : "urban_romance";
    if (manualPick) return displayName(manualPick);
    return displayName(STYLE_BGM[key]);
  }

  function getCustomUrl() {
    return customSession ? customSession.url : null;
  }

  function getCustomName() {
    const raw = customSession
      ? customSession.name
      : localStorage.getItem(CUSTOM_NAME_KEY) || "我的音乐";
    return raw === "我的音乐" ? raw : cleanFilenameLabel(raw);
  }

  function isDisabled() {
    return bgmDisabled;
  }

  function isAutoMatchActive() {
    return autoMatchEnabled && !bgmDisabled && !(customSession && customSession.url);
  }

  function persistAutoMatch() {
    try {
      localStorage.setItem(AUTO_MATCH_KEY, autoMatchEnabled ? "1" : "0");
    } catch (_) { /* noop */ }
  }

  function syncAutoToggle() {
    if (!els.autoToggle) return;
    const isCustom = !!(customSession && customSession.url);
    const checked = isAutoMatchActive();
    els.autoToggle.checked = checked;
    els.autoToggle.disabled = bgmDisabled || isCustom;
    if (els.autoToggleWrap) {
      els.autoToggleWrap.classList.toggle("is-off", !checked);
      els.autoToggleWrap.classList.toggle("is-disabled", bgmDisabled || isCustom);
    }
  }

  function showPlaybackError(d) {
    const name = displayName(d.filename) || "曲目";
    let msg;
    if (d.trackId === "custom") {
      msg = "无法播放你上传的音乐，请检查文件是否损坏或格式是否正确。";
    } else if (d.reason === "codec_unsupported") {
      msg = "当前浏览器不支持「" + name + "」的音频格式，正在换一首…";
    } else {
      msg = "无法加载「" + name + "」，正在换一首…";
    }
    if (els.desc) els.desc.textContent = msg;
    if (els.trackLabel) {
      els.trackLabel.textContent = d.trackId === "custom" ? "上传音乐无法播放" : "加载失败 · " + name;
    }
    if (els.trackWaveform) {
      els.trackWaveform.classList.add("is-error");
      els.trackWaveform.classList.remove("is-muted");
    }
  }

  function clearPlaybackError() {
    if (els.trackWaveform) els.trackWaveform.classList.remove("is-error");
  }

  function isStaleLoadError(d) {
    if (!d) return true;
    if (d.reason === "NotAllowedError") return true;
    if (expectedTrackId && d.trackId && d.trackId !== expectedTrackId) return true;

    const activeFilename = customSession && customSession.url
      ? null
      : (manualPick || pickFilename(currentStyle, null));
    if (
      d.filename &&
      activeFilename &&
      d.filename !== activeFilename &&
      d.filename !== resolvePlayableFilename(activeFilename)
    ) {
      return true;
    }
    return false;
  }

  function beginPlayback(resolved) {
    if (!resolved) return;
    expectedTrackId = resolved.trackId || null;
    if (typeof VnAudio !== "undefined" && VnAudio.preview) {
      VnAudio.preview(resolved);
    }
    syncPreviewBtn();
  }

  function handleLoadError(ev) {
    const d = ev && ev.detail;
    if (!d || skipInProgress || isStaleLoadError(d)) return;

    if (d.filename && d.trackId !== "custom") {
      failedFilenames.add(d.filename);
    }

    if (d.trackId === "custom") {
      showPlaybackError(d);
      return;
    }

    showPlaybackError(d);

    consecutiveFailures += 1;
    if (consecutiveFailures >= MAX_SKIP_ATTEMPTS) {
      if (els.desc) {
        els.desc.textContent = "多首曲目无法加载，请检查网络或刷新页面；也可上传本地音乐。";
      }
      if (typeof VnAudio !== "undefined" && VnAudio.stop) VnAudio.stop();
      expectedTrackId = null;
      return;
    }

    skipInProgress = true;
    const style = d.style || currentStyle;
    manualPick = pickAlternateFilename(style, null, d.filename);
    const resolved = resolveForPlay(style);
    expectedTrackId = resolved.trackId || null;

    if (typeof VnAudio !== "undefined" && VnAudio.start) {
      VnAudio.start(resolved);
    }
    skipInProgress = false;
    updateUI(style, { keepError: true });
  }

  /** corrupt-file audit agent: 标记损坏文件，运行时自动跳过 */
  function markFailed(filename) {
    if (filename) failedFilenames.add(filename);
  }

  function getFailedFilenames() {
    return Array.from(failedFilenames);
  }

  function clearFailedFilenames() {
    failedFilenames.clear();
  }

  function updateUI(style, options) {
    const keepError = options && options.keepError;
    if (style) currentStyle = style;
    if (!els.trackLabel && !els.desc) return;

    if (!keepError) clearPlaybackError();

    const isCustom = !!(customSession && customSession.url);

    syncAutoToggle();

    if (bgmDisabled) {
      if (els.desc) {
        els.desc.textContent = "背景音乐已关闭；点击「关闭音乐 ×」可重新启用。";
      }
      if (els.trackLabel) {
        els.trackLabel.textContent = "无背景音乐";
      }
    } else if (isCustom) {
      if (els.desc) {
        els.desc.textContent = "已使用你上传的音乐；游玩时将循环播放此曲目。";
      }
      if (els.trackLabel) {
        els.trackLabel.textContent = getCustomName();
      }
    } else if (manualPick || !autoMatchEnabled) {
      if (els.desc) {
        els.desc.textContent = "当前为手动选曲；开启「自动匹配」可随故事风格切换。";
      }
      if (els.trackLabel) {
        els.trackLabel.textContent = getAutoTrackLabel(currentStyle);
      }
    } else {
      if (els.desc) {
        els.desc.textContent = "将根据故事风格自动切换背景音乐…";
      }
      if (els.trackLabel) {
        els.trackLabel.textContent = getAutoTrackLabel(currentStyle);
      }
    }

    if (els.clearBtn) {
      els.clearBtn.hidden = !isCustom && !manualPick;
    }

    if (els.shuffleBtn) {
      els.shuffleBtn.hidden = isCustom || bgmDisabled;
      els.shuffleBtn.disabled = bgmDisabled;
    }

    if (els.uploadBtn) {
      els.uploadBtn.disabled = bgmDisabled;
    }

    if (els.disableBtn) {
      els.disableBtn.textContent = bgmDisabled ? "开启音乐" : "关闭音乐 ×";
      els.disableBtn.classList.toggle("is-active", bgmDisabled);
    }

    if (els.previewBtn) {
      els.previewBtn.disabled = bgmDisabled;
    }

    if (els.trackWaveform) {
      els.trackWaveform.classList.toggle("is-muted", bgmDisabled);
    }

    syncVolumeWrap();
    syncPreviewBtn();
  }

  function syncVolumeWrap() {
    if (!els.volumeWrap) return;
    els.volumeWrap.classList.toggle("is-muted", bgmDisabled);
    if (els.volumeBtn) {
      els.volumeBtn.setAttribute("aria-disabled", bgmDisabled ? "true" : "false");
    }
  }

  function initVolumeControl() {
    if (!els.volumeWrap || !els.volumePop || !els.volumeRange || typeof VnAudio === "undefined") {
      return;
    }

    let volumePinned = false;

    function setVolumePopOpen(open) {
      els.volumePop.hidden = !open;
      els.volumeWrap.classList.toggle("is-volume-open", open);
      if (els.volumeBtn) {
        els.volumeBtn.setAttribute("aria-expanded", open ? "true" : "false");
      }
    }

    function hideVolumePopUnlessPinned() {
      if (!volumePinned) setVolumePopOpen(false);
    }

    if (typeof VnAudio.getVolume === "function") {
      els.volumeRange.value = String(Math.round(VnAudio.getVolume() * 100));
    }

    els.volumeWrap.addEventListener("mouseenter", function () {
      volumePinned = false;
      setVolumePopOpen(true);
    });
    els.volumeWrap.addEventListener("mouseleave", function () {
      window.setTimeout(hideVolumePopUnlessPinned, 80);
    });
    els.volumeWrap.addEventListener("focusin", function () {
      setVolumePopOpen(true);
    });
    els.volumeWrap.addEventListener("focusout", function (e) {
      if (!volumePinned && !els.volumeWrap.contains(e.relatedTarget)) {
        setVolumePopOpen(false);
      }
    });
    els.volumePop.addEventListener("pointerdown", function () {
      volumePinned = true;
      setVolumePopOpen(true);
    });
    els.volumeRange.addEventListener("input", function () {
      if (typeof VnAudio.setVolume === "function") {
        VnAudio.setVolume(Number(els.volumeRange.value) / 100);
      }
      const gameRange = document.getElementById("bgm-volume");
      if (gameRange) gameRange.value = els.volumeRange.value;
    });
    if (els.volumeBtn) {
      els.volumeBtn.addEventListener("pointerdown", function (e) {
        e.stopPropagation();
      });
      els.volumeBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        const shouldOpen = els.volumePop.hidden;
        if (shouldOpen) {
          volumePinned = true;
          setVolumePopOpen(true);
          els.volumeRange.focus();
        } else {
          volumePinned = false;
          setVolumePopOpen(false);
        }
      });
    }
    document.addEventListener("pointerdown", function (e) {
      if (!volumePinned && !els.volumeWrap.contains(e.target)) {
        setVolumePopOpen(false);
      }
    });
    syncVolumeWrap();
  }

  function syncPreviewBtn() {
    if (!els.previewBtn) return;
    const playing = !bgmDisabled &&
      typeof VnAudio !== "undefined" &&
      VnAudio.isPlaying &&
      VnAudio.isPlaying();
    if (playing && els.trackWaveform && els.trackWaveform.classList.contains("is-error")) {
      consecutiveFailures = 0;
      clearPlaybackError();
      updateUI(currentStyle);
    }
    els.previewBtn.classList.toggle("is-playing", playing);
    if (els.panel) els.panel.classList.toggle("is-playing", playing);
    els.previewBtn.setAttribute("aria-pressed", playing ? "true" : "false");
    const label = playing ? "暂停试听" : "试听当前配乐";
    els.previewBtn.setAttribute("aria-label", label);
    els.previewBtn.title = label;
  }

  function setAutoMatch(enabled) {
    autoMatchEnabled = !!enabled;
    persistAutoMatch();
    if (autoMatchEnabled) {
      manualPick = null;
    } else if (!customSession && !bgmDisabled) {
      manualPick = pickFilename(currentStyle, null);
    }
    if (els.autoToggle) {
      els.autoToggle.checked = isAutoMatchActive();
    }
    updateUI(currentStyle);
  }

  function handleUpload(file) {
    if (!file) return;
    const ok = /\.(mp3|ogg|wav)$/i.test(file.name) || /^audio\//.test(file.type || "");
    if (!ok) {
      alert("请上传 mp3、ogg 或 wav 格式的音频文件。");
      return;
    }
    if (customSession && customSession.url) {
      URL.revokeObjectURL(customSession.url);
    }
    const url = URL.createObjectURL(file);
    customSession = { url: url, name: cleanFilenameLabel(file.name) || file.name };
    manualPick = null;
    autoMatchEnabled = false;
    persistAutoMatch();
    bgmDisabled = false;
    try { localStorage.setItem(DISABLED_KEY, "0"); } catch (_) { /* noop */ }
    try { localStorage.setItem(CUSTOM_NAME_KEY, customSession.name); } catch (_) { /* noop */ }
    clearPlaybackError();
    if (typeof VnAudio !== "undefined" && VnAudio.stop) {
      VnAudio.stop();
    }
    updateUI(currentStyle);
    beginPlayback({ trackId: "custom", customUrl: customSession.url });
    window.setTimeout(syncPreviewBtn, 120);
  }

  function clearCustom() {
    if (customSession && customSession.url) {
      URL.revokeObjectURL(customSession.url);
    }
    customSession = null;
    manualPick = null;
    autoMatchEnabled = true;
    persistAutoMatch();
    if (els.fileInput) els.fileInput.value = "";
    updateUI(currentStyle);
    if (typeof VnAudio !== "undefined" && VnAudio.stop) {
      VnAudio.stop();
    }
  }

  function playCurrentTrack() {
    if (bgmDisabled || typeof VnAudio === "undefined" || !VnAudio.preview) return;
    if (customSession && customSession.url) {
      beginPlayback({ trackId: "custom", customUrl: customSession.url });
    } else {
      beginPlayback(resolveForPlay(currentStyle));
    }
  }

  function shuffleTrack() {
    if (bgmDisabled || (customSession && customSession.url)) return;
    const now = Date.now();
    if (now - lastShuffleAt < SHUFFLE_DEBOUNCE_MS) return;
    lastShuffleAt = now;

    skipInProgress = true;
    consecutiveFailures = 0;
    clearPlaybackError();

    manualPick = randomTrack(currentStyle);
    autoMatchEnabled = false;
    persistAutoMatch();
    updateUI(currentStyle);

    playCurrentTrack();

    window.setTimeout(function () {
      skipInProgress = false;
      syncPreviewBtn();
    }, SHUFFLE_DEBOUNCE_MS);
  }

  function toggleDisabled() {
    bgmDisabled = !bgmDisabled;
    try {
      localStorage.setItem(DISABLED_KEY, bgmDisabled ? "1" : "0");
    } catch (_) { /* noop */ }
    if (!bgmDisabled && !customSession) {
      autoMatchEnabled = true;
      manualPick = null;
      persistAutoMatch();
    }
    updateUI(currentStyle);
    if (typeof VnAudio !== "undefined") {
      if (bgmDisabled) {
        VnAudio.stop();
      } else {
        playCurrentTrack();
      }
    }
  }

  function previewCurrent() {
    if (bgmDisabled) return;
    if (typeof VnAudio === "undefined") return;

    if (VnAudio.isPlaying && VnAudio.isPlaying()) {
      if (VnAudio.pause) VnAudio.pause();
      else if (VnAudio.stop) VnAudio.stop();
      syncPreviewBtn();
      return;
    }

    if (!VnAudio.preview) return;
    if (customSession && customSession.url) {
      beginPlayback({ trackId: "custom", customUrl: customSession.url });
    } else {
      beginPlayback(resolveForPlay(currentStyle));
    }
  }

  function init() {
    if (initDone) return;
    initDone = true;

    els = {
      panel: document.querySelector(".workbench__music.music-panel"),
      autoToggle: document.getElementById("bgm-auto-toggle"),
      autoToggleWrap: document.getElementById("bgm-auto-toggle-wrap"),
      desc: document.getElementById("bgm-auto-desc"),
      trackLabel: document.getElementById("bgm-track-label"),
      trackWaveform: document.getElementById("bgm-track-waveform"),
      uploadBtn: document.getElementById("bgm-upload-btn"),
      clearBtn: document.getElementById("bgm-clear-btn"),
      previewBtn: document.getElementById("bgm-preview-btn"),
      shuffleBtn: document.getElementById("bgm-shuffle-btn"),
      disableBtn: document.getElementById("bgm-disable-btn"),
      fileInput: document.getElementById("bgm-upload-input"),
      volumeWrap: document.getElementById("workbench-bgm-volume-wrap"),
      volumeBtn: document.getElementById("workbench-bgm-volume-btn"),
      volumePop: document.getElementById("workbench-bgm-volume-pop"),
      volumeRange: document.getElementById("workbench-bgm-volume"),
    };

    const studio = document.getElementById("studio");
    if (studio && studio.getAttribute("data-style")) {
      currentStyle = studio.getAttribute("data-style") || currentStyle;
    }

    if (els.autoToggle) {
      els.autoToggle.addEventListener("keydown", function (e) {
        if (e.key !== " " && e.key !== "Enter") return;
        e.preventDefault();
        setAutoMatch(!autoMatchEnabled);
      });
    }

    if (els.autoToggleWrap && els.autoToggle) {
      els.autoToggleWrap.onclick = function () {
        if (els.autoToggle.disabled) return;
        setAutoMatch(!autoMatchEnabled);
      };
    }

    if (els.uploadBtn && els.fileInput) {
      els.uploadBtn.addEventListener("click", function () {
        els.fileInput.click();
      });
      els.fileInput.addEventListener("change", function () {
        const file = els.fileInput.files && els.fileInput.files[0];
        if (file) handleUpload(file);
      });
    }

    if (els.clearBtn) {
      els.clearBtn.addEventListener("click", clearCustom);
    }

    if (els.previewBtn) {
      els.previewBtn.addEventListener("click", previewCurrent);
    }

    if (els.shuffleBtn) {
      els.shuffleBtn.addEventListener("click", shuffleTrack);
    }

    if (els.disableBtn) {
      els.disableBtn.addEventListener("click", toggleDisabled);
    }

    document.addEventListener("vn-bgm-playback-change", function (ev) {
      const playing = ev && ev.detail && ev.detail.playing;
      if (playing) {
        consecutiveFailures = 0;
        clearPlaybackError();
      }
      syncPreviewBtn();
    });
    document.addEventListener("vn-bgm-load-error", handleLoadError);

    initVolumeControl();
    updateUI(currentStyle);
  }

  function suggestForStyle(style) {
    if (autoMatchEnabled && !customSession) {
      manualPick = null;
    }
    updateUI(style);
  }

  return {
    init: init,
    resolveForPlay: resolveForPlay,
    resolveForChapter: resolveForChapter,
    suggestForStyle: suggestForStyle,
    handleUpload: handleUpload,
    clearCustom: clearCustom,
    shuffleTrack: shuffleTrack,
    randomTrack: randomTrack,
    buildShufflePool: buildShufflePool,
    getCurrentFilename: getCurrentFilename,
    toggleDisabled: toggleDisabled,
    setAutoMatch: setAutoMatch,
    isDisabled: isDisabled,
    getCustomUrl: getCustomUrl,
    getCustomName: getCustomName,
    getAutoTrackLabel: getAutoTrackLabel,
    displayName: displayName,
    DISPLAY_NAMES: DISPLAY_NAMES,
    STYLE_BGM: STYLE_BGM,
    STYLE_BGM_POOL: STYLE_BGM_POOL,
    MOOD_BGM: MOOD_BGM,
    STYLE_LABELS: STYLE_LABELS,
    FILES: FILES,
    ALL_FILENAMES: ALL_FILENAMES,
    OGG_MP3_FALLBACKS: OGG_MP3_FALLBACKS,
    resolvePlayableFilename: resolvePlayableFilename,
    GENTLE: GENTLE,
    LOUD: LOUD,
    STYLE_ALIASES: STYLE_ALIASES,
    normalizeStyle: normalizeStyle,
    markFailed: markFailed,
    getFailedFilenames: getFailedFilenames,
    clearFailedFilenames: clearFailedFilenames,
    isOggSupported: isOggSupported,
    isPlayableFilename: isPlayableFilename,
  };
})();
