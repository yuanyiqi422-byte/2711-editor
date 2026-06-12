/** 视觉小说 BGM — Web Audio 氛围循环 + 可选 HTML5 本地文件循环 */

const VnAudio = (function () {

  const STORAGE_KEY = "2711-bgm-muted";
  const VOLUME_KEY = "2711-bgm-volume";

  let volumeLevel = 0.65;
  try {
    const saved = localStorage.getItem(VOLUME_KEY);
    if (saved != null) volumeLevel = Math.max(0, Math.min(1, Number(saved) || 0.65));
  } catch (_) { /* noop */ }

  let ctx = null;

  let masterGain = null;

  let nodes = [];

  let htmlAudio = null;

  let currentStyle = null;

  let currentTrackId = null;

  let currentFileUrl = null;

  let muted = localStorage.getItem(STORAGE_KEY) === "1";

  let gestureUnlockBound = false;

  let probeAudio = null;

  /** Monotonic id — ignore error/play callbacks from superseded Audio elements */
  let loadSeq = 0;

  function getProbeAudio() {
    if (!probeAudio && typeof document !== "undefined" && document.createElement) {
      probeAudio = document.createElement("audio");
    }
    return probeAudio;
  }

  function mimeForUrl(url) {
    const ext = (String(url || "").split("?")[0].split(".").pop() || "").toLowerCase();
    if (ext === "ogg" || ext === "oga") return 'audio/ogg; codecs="vorbis"';
    if (ext === "mp3") return "audio/mpeg";
    if (ext === "wav") return "audio/wav";
    return "";
  }

  function canPlayUrl(url) {
    const mime = mimeForUrl(url);
    if (!mime) return true;
    const probe = getProbeAudio();
    if (!probe || !probe.canPlayType) return true;
    const can = probe.canPlayType(mime);
    return can === "probably" || can === "maybe";
  }

  function filenameFromUrl(url) {
    try {
      const path = new URL(url, window.location.href).pathname;
      return decodeURIComponent(path.split("/").pop() || "");
    } catch (_) {
      return url || "";
    }
  }

  function notifyLoadError(detail) {
    try {
      document.dispatchEvent(new CustomEvent("vn-bgm-load-error", { detail: detail }));
    } catch (_) { /* noop */ }
  }

  function isActiveHtmlAudio(audio, seq) {
    return audio === htmlAudio && seq === loadSeq;
  }

  function handleFileFailure(url, trackId, fallbackStyle, reason, retryCount, seq) {
    if (seq != null && seq !== loadSeq) return;
    stopHtml();
    currentTrackId = null;
    notifyPlaybackChange();
    notifyLoadError({
      url: url,
      trackId: trackId,
      style: fallbackStyle || currentStyle,
      filename: filenameFromUrl(url),
      reason: reason,
      retries: retryCount || 0,
      loadSeq: seq,
    });
  }

  function bindGestureUnlock() {
    if (gestureUnlockBound) return;
    gestureUnlockBound = true;
    function tryResumeFromGesture() {
      ensureCtx();
      if (htmlAudio && htmlAudio.paused && currentFileUrl) {
        htmlAudio.play().catch(function () { /* still blocked */ });
      }
    }
    ["click", "keydown", "touchstart"].forEach(function (ev) {
      document.addEventListener(ev, tryResumeFromGesture, { capture: true, passive: true });
    });
  }

  function resolveMediaUrl(url) {
    try {
      return new URL(url, window.location.href).href;
    } catch (_) {
      return url || "";
    }
  }

  function isSameFile(url) {
    if (!htmlAudio || !url) return false;
    const target = resolveMediaUrl(url);
    const src = htmlAudio.src || "";
    return src === target;
  }

  function ensureCtx() {

    if (!ctx) {

      const AC = window.AudioContext || window.webkitAudioContext;

      if (!AC) return null;

      ctx = new AC();

      masterGain = ctx.createGain();

      masterGain.connect(ctx.destination);

    }

    if (ctx.state === "suspended") ctx.resume();

    applyMute();

    bindGestureUnlock();

    return ctx;

  }



  function applyMute() {

    if (masterGain) masterGain.gain.value = muted ? 0 : volumeLevel * 0.35;

    if (htmlAudio) htmlAudio.volume = muted ? 0 : volumeLevel * 0.65;

  }



  function notifyPlaybackChange() {

    try {

      document.dispatchEvent(new CustomEvent("vn-bgm-playback-change", {

        detail: { playing: isPlaying() },

      }));

    } catch (_) { /* noop */ }

  }



  function bindHtmlAudioEvents(audio) {

    ["play", "pause", "ended"].forEach(function (ev) {

      audio.addEventListener(ev, notifyPlaybackChange);

    });

  }



  function isPlaying() {

    if (htmlAudio) return !htmlAudio.paused;

    return nodes.length > 0 && currentTrackId !== "silent" && currentTrackId != null;

  }



  function resumeHtmlIfPaused() {

    if (htmlAudio && htmlAudio.paused) {

      htmlAudio.play().catch(function () { /* autoplay blocked */ });

      return true;

    }

    return false;

  }



  function pause() {

    if (htmlAudio) {

      htmlAudio.pause();

      return;

    }

    if (nodes.length) stop();

  }



  function stopHtml() {

    if (!htmlAudio) return;

    loadSeq += 1;

    const dying = htmlAudio;

    htmlAudio = null;

    currentFileUrl = null;

    try {

      dying.pause();

      dying.removeAttribute("src");

      dying.load();

    } catch (_) { /* noop */ }

  }



  function stop() {

    nodes.forEach(function (n) {

      try {

        if (n.stop) n.stop(0);

        n.disconnect && n.disconnect();

      } catch (_) { /* noop */ }

    });

    nodes = [];

    stopHtml();

    currentStyle = null;

    currentTrackId = null;

    currentFileUrl = null;

    notifyPlaybackChange();

  }



  function playHtmlLoop(url, retryCount) {
    retryCount = retryCount || 0;
    stopHtml();
    loadSeq += 1;
    const seq = loadSeq;

    if (!canPlayUrl(url)) {
      handleFileFailure(url, "custom", currentStyle, "codec_unsupported", retryCount, seq);
      return;
    }

    const audio = new Audio(url);
    audio.loop = true;
    audio.volume = muted ? 0 : volumeLevel * 0.65;
    bindHtmlAudioEvents(audio);

    function onFail(reason) {
      if (!isActiveHtmlAudio(audio, seq)) return;
      if (retryCount < 1) {
        stopHtml();
        window.setTimeout(function () {
          if (seq !== loadSeq) return;
          playHtmlLoop(url, retryCount + 1);
        }, 400);
        return;
      }
      handleFileFailure(url, "custom", currentStyle, reason, retryCount, seq);
    }

    audio.addEventListener("error", function () {
      onFail("load_error");
    }, { once: true });

    function tryPlay() {
      audio.play().catch(function (err) {
        if (!isActiveHtmlAudio(audio, seq)) return;
        if (err && err.name === "NotAllowedError") {
          notifyPlaybackChange();
          return;
        }
        onFail(err && err.name ? err.name : "playback_failed");
      });
    }

    if (String(url).indexOf("blob:") === 0) {
      audio.addEventListener("canplay", tryPlay, { once: true });
      audio.load();
    } else {
      tryPlay();
    }

    htmlAudio = audio;
    currentTrackId = "custom";
    currentFileUrl = url;
    notifyPlaybackChange();
  }



  function noiseBuffer(type) {

    const c = ensureCtx();

    if (!c) return null;

    const len = c.sampleRate * 2;

    const buf = c.createBuffer(1, len, c.sampleRate);

    const data = buf.getChannelData(0);

    let last = 0;

    for (let i = 0; i < len; i++) {

      const white = Math.random() * 2 - 1;

      if (type === "brown") {

        last = (last + 0.02 * white) / 1.02;

        data[i] = last * 3.5;

      } else if (type === "pink") {

        last = 0.98 * last + 0.02 * white;

        data[i] = last * 2;

      } else {

        data[i] = white * 0.4;

      }

    }

    return buf;

  }



  function loopNoise(type, filterFreq, gain) {

    const c = ensureCtx();

    if (!c) return;

    const src = c.createBufferSource();

    src.buffer = noiseBuffer(type);

    src.loop = true;

    const filter = c.createBiquadFilter();

    filter.type = "lowpass";

    filter.frequency.value = filterFreq;

    const g = c.createGain();

    g.gain.value = gain;

    src.connect(filter);

    filter.connect(g);

    g.connect(masterGain);

    src.start(0);

    nodes.push(src);

  }



  function loopTone(freq, type, gain, detune) {

    const c = ensureCtx();

    if (!c) return;

    const osc = c.createOscillator();

    osc.type = type || "sine";

    osc.frequency.value = freq;

    if (detune) osc.detune.value = detune;

    const g = c.createGain();

    g.gain.value = gain;

    osc.connect(g);

    g.connect(masterGain);

    osc.start(0);

    nodes.push(osc);

  }



  function pluckSequence(baseFreq) {

    const c = ensureCtx();

    if (!c) return;

    const freqs = [baseFreq, baseFreq * 1.25, baseFreq * 1.5, baseFreq * 1.125];

    let i = 0;

    function tick() {

      if (currentStyle !== "xianxia") return;

      const osc = c.createOscillator();

      osc.type = "triangle";

      osc.frequency.value = freqs[i % freqs.length];

      const g = c.createGain();

      g.gain.setValueAtTime(0, c.currentTime);

      g.gain.linearRampToValueAtTime(0.06, c.currentTime + 0.02);

      g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + 1.8);

      osc.connect(g);

      g.connect(masterGain);

      osc.start(c.currentTime);

      osc.stop(c.currentTime + 2);

      i += 1;

      nodes.push(osc);

    }

    tick();

    const id = window.setInterval(tick, 4200 + Math.random() * 800);

    nodes.push({ stop: function () { clearInterval(id); } });

  }



  /** 兜底合成音（bgm/ 无对应文件时使用） */
  const BGM_FILES = {
    xianxia: null,
    urban_romance: null,
    mystery: null,
    campus: null,
  };

  const PRESETS = {

    xianxia: function () {

      loopNoise("pink", 420, 0.35);

      pluckSequence(220);

    },

    urban_romance: function () {

      loopNoise("pink", 680, 0.28);

      loopTone(130, "sine", 0.04, 0);

    },

    mystery: function () {

      loopNoise("brown", 320, 0.45);

      loopTone(55, "sine", 0.07, 0);

      loopTone(82, "triangle", 0.03, -8);

    },

    campus: function () {

      loopNoise("pink", 900, 0.22);

      loopTone(440, "sine", 0.025, 0);

      loopTone(554, "sine", 0.018, 5);

    },

  };

  function startPreset(style) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const key = PRESETS[style] ? style : "urban_romance";
    if (currentStyle === key && currentTrackId === "style_" + key && nodes.length) return;
    stop();
    currentStyle = key;
    currentTrackId = "style_" + key;
    ensureCtx();
    const fn = PRESETS[key];
    if (fn) fn();
    notifyPlaybackChange();
  }

  function startHtmlFile(url, trackId, fallbackStyle, retryCount) {
    retryCount = retryCount || 0;
    ensureCtx();
    if (htmlAudio && isSameFile(url) && currentTrackId === trackId) {
      if (resumeHtmlIfPaused()) return;
      if (!htmlAudio.paused) return;
    }

    if (!canPlayUrl(url)) {
      loadSeq += 1;
      handleFileFailure(url, trackId, fallbackStyle, "codec_unsupported", retryCount, loadSeq);
      return;
    }

    stop();
    loadSeq += 1;
    const seq = loadSeq;
    currentStyle = fallbackStyle || currentStyle || "urban_romance";
    currentTrackId = trackId;
    currentFileUrl = url;

    const audio = new Audio();
    audio.loop = true;
    audio.preload = "auto";
    audio.volume = muted ? 0 : volumeLevel * 0.65;
    bindHtmlAudioEvents(audio);

    const mime = mimeForUrl(url);
    const resolved = resolveMediaUrl(url);
    if (mime) {
      const source = document.createElement("source");
      source.src = resolved;
      source.type = mime;
      audio.appendChild(source);
    } else {
      audio.src = resolved;
    }

    function onFail(reason) {
      if (!isActiveHtmlAudio(audio, seq)) return;
      if (retryCount < 1) {
        console.warn("[VnAudio] retry load:", url);
        stopHtml();
        window.setTimeout(function () {
          if (seq !== loadSeq) return;
          startHtmlFile(url, trackId, fallbackStyle, retryCount + 1);
        }, 400);
        return;
      }
      console.warn("[VnAudio] file load failed:", url, reason);
      handleFileFailure(url, trackId, fallbackStyle, reason, retryCount, seq);
    }

    audio.addEventListener("error", function () {
      onFail("load_error");
    }, { once: true });

    htmlAudio = audio;
    audio.load();
    audio.play().catch(function (err) {
      if (!isActiveHtmlAudio(audio, seq)) return;
      if (err && err.name === "NotAllowedError") {
        notifyPlaybackChange();
        return;
      }
      onFail(err && err.name ? err.name : "playback_failed");
    });
    notifyPlaybackChange();
  }

  function startPresetOrFile(style) {
    if (typeof MusicPicker !== "undefined" && MusicPicker.resolveForPlay) {
      const resolved = MusicPicker.resolveForPlay(style);
      if (resolved && resolved.fileUrl) {
        startHtmlFile(resolved.fileUrl, resolved.trackId || "auto", style);
        return;
      }
    }
    console.warn("[VnAudio] no playable file for style:", style);
    currentTrackId = null;
    notifyPlaybackChange();
  }



  /**

   * @param {string|{style?: string, mood?: string, trackId?: string, customUrl?: string, fileUrl?: string}} arg

   */

  function start(arg) {

    let style = "urban_romance";

    let mood = null;

    let trackId = null;

    let customUrl = null;

    let fileUrl = null;



    if (typeof arg === "string") {

      style = arg;

    } else if (arg && typeof arg === "object") {

      style = arg.style || "urban_romance";

      mood = arg.mood || null;

      trackId = arg.trackId || null;

      customUrl = arg.customUrl || null;

      fileUrl = arg.fileUrl || null;

    }



    if (typeof MusicPicker !== "undefined" && !trackId && !customUrl && !fileUrl) {

      const resolved = MusicPicker.resolveForPlay(style, mood);

      trackId = resolved.trackId;

      customUrl = resolved.customUrl || null;

      fileUrl = resolved.fileUrl || null;

      style = resolved.style || style;

      mood = resolved.mood || mood;

    }



    if (trackId === "silent") {

      stop();

      currentTrackId = "silent";

      return;

    }



    if (trackId === "custom" && customUrl) {

      if (currentTrackId === "custom" && htmlAudio && isSameFile(customUrl)) {
        if (resumeHtmlIfPaused()) return;
        if (!htmlAudio.paused) return;
      }

      stop();

      playHtmlLoop(customUrl);

      return;

    }



    if (trackId && trackId.indexOf("style_") === 0) {
      const rest = trackId.slice(6);
      const pipe = rest.indexOf("|");
      style = pipe >= 0 ? rest.slice(0, pipe) : rest;
    }



    if (fileUrl) {

      startHtmlFile(fileUrl, trackId || "auto", style);

      return;

    }



    startPresetOrFile(style);

  }



  function preview(opts) {

    start(opts);

  }



  function toggle() {

    muted = !muted;

    localStorage.setItem(STORAGE_KEY, muted ? "1" : "0");

    applyMute();

    if (!muted) {
      if (htmlAudio) {
        htmlAudio.play().catch(function () {});
      } else if (typeof MusicPicker !== "undefined") {
        start(MusicPicker.resolveForPlay(currentStyle || "urban_romance"));
      } else if (currentStyle) {
        start(currentStyle);
      }
    }

    return muted;

  }



  function isMuted() {

    return muted;

  }



  function setVolume(v) {

    const vol = Math.max(0, Math.min(1, v));

    volumeLevel = vol;

    try { localStorage.setItem(VOLUME_KEY, String(vol)); } catch (_) { /* noop */ }

    if (masterGain) masterGain.gain.value = muted ? 0 : vol * 0.35;

    if (htmlAudio) htmlAudio.volume = muted ? 0 : vol * 0.65;

  }

  function getVolume() {
    return volumeLevel;
  }



  function playClick() {

    if (muted) return;

    const c = ensureCtx();

    if (!c) return;

    const osc = c.createOscillator();

    const g = c.createGain();

    osc.type = "sine";

    osc.frequency.value = 880;

    g.gain.setValueAtTime(0.04, c.currentTime);

    g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + 0.06);

    osc.connect(g);

    g.connect(masterGain);

    osc.start(c.currentTime);

    osc.stop(c.currentTime + 0.07);

  }



  return {

    start: start,

    preview: preview,

    stop: stop,

    pause: pause,

    isPlaying: isPlaying,

    toggle: toggle,

    isMuted: isMuted,

    setVolume: setVolume,

    getVolume: getVolume,

    playClick: playClick,

  };

})();


