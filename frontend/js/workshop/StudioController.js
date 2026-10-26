/**
 * StudioController — 创作工坊编排入口
 */
(function (global) {
  async function tryFeaturedDeepLink() {
    if (typeof ShareWorld === "undefined" || !ShareWorld.getFeaturedFlagFromUrl) return false;
    if (!ShareWorld.getFeaturedFlagFromUrl()) return false;
    if (typeof FeaturedDemo === "undefined" || !FeaturedDemo.launch) {
      console.warn("featured deep link: FeaturedDemo unavailable");
      return false;
    }
    ShareWorld.clearPlayParam();
    await FeaturedDemo.launch({ forceRestart: true });
    return true;
  }

  async function trySharedPlay() {
    if (typeof ShareWorld === "undefined" || typeof NarrativeGame === "undefined") return false;
    if (await tryFeaturedDeepLink()) return true;
    const token = ShareWorld.getPlayTokenFromUrl();
    if (!token) return false;
    if (token === "featured" || token === "demo") {
      ShareWorld.clearPlayParam();
      if (typeof FeaturedDemo !== "undefined" && FeaturedDemo.launch) {
        await FeaturedDemo.launch({ forceRestart: true });
        return true;
      }
      return false;
    }
    try {
      const data = await ShareWorld.loadSharedGame(token);
      if (!data.game || !data.game.nodes) {
        throw new Error("分享内容不完整");
      }
      ShareWorld.clearPlayParam();
      NarrativeGame.startShared(data.game, data.text || "");
      return true;
    } catch (err) {
      console.warn("shared play", err);
      const errEl = document.getElementById("studio-error");
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = err.message || "分享链接无效";
      }
      return false;
    }
  }

  function initStudio() {
    const studioError = document.getElementById("studio-error");
    let currentHistoryId = null;

    function setError(msg) {
      const { formatApiDetail } = global.ApiErrors;
      const text = typeof msg === "string" ? msg : formatApiDetail(msg) || "";
      if (text) {
        studioError.hidden = false;
        studioError.textContent = text;
      } else {
        studioError.hidden = true;
        studioError.textContent = "";
      }
    }

    async function saveHistory(payload) {
      const entry = Object.assign({}, payload, {
        entryId: payload.entryId != null ? payload.entryId : currentHistoryId,
      });
      currentHistoryId = await HistoryPanel.save(entry);
      return currentHistoryId;
    }

    if (typeof MusicPicker !== "undefined") {
      MusicPicker.init();
    }

    const styles = StylePresets.create({
      initialStyle: "urban_romance",
      onChange: function (style) {
        if (typeof MusicPicker !== "undefined" && MusicPicker.suggestForStyle) {
          MusicPicker.suggestForStyle(style);
        }
      },
    });

    const editor = EditorInput.create({
      inputEl: document.getElementById("story-input"),
      charCountEl: document.getElementById("char-count"),
      fileInputEl: document.getElementById("file-input"),
      uploadStatusEl: document.getElementById("upload-status"),
      uploadProgressEl: document.getElementById("upload-progress"),
      uploadProgressFillEl: document.getElementById("upload-progress-fill"),
      uploadLabelEl: document.querySelector(".workshop-btn--upload"),
      uploadFormatsEl: document.getElementById("upload-formats"),
      uploadLimitsEl: document.getElementById("upload-limits"),
      clearBtnEl: document.getElementById("manuscript-clear-btn"),
      onboardEl: document.getElementById("workshop-onboard"),
      getSelectedStyle: function () { return styles.getStyle(); },
      onHistorySave: saveHistory,
      onError: setError,
    });

    const pipeline = PipelineView.create({
      pipelineEl: document.getElementById("pipeline"),
      fillEl: document.getElementById("pipeline-fill"),
      pctEl: document.getElementById("pipeline-pct"),
      msgEl: document.getElementById("pipeline-msg"),
      elapsedEl: document.getElementById("pipeline-elapsed"),
      studioEl: document.getElementById("studio"),
    });

    CreateFlow.create({
      createBtnEl: document.getElementById("create-btn"),
      demoBtnEl: document.getElementById("nav-demo-btn"),
      heroDemoBtnEl: null,
      editor: editor,
      styles: styles,
      pipeline: pipeline,
      onError: setError,
      onHistorySave: saveHistory,
      onEntryId: function (id) { currentHistoryId = id; },
    });

    NarrativeGame.init({
      onBack: function () {
        if (currentHistoryId) {
          HistoryPanel.touch(currentHistoryId);
        }
        if (typeof UnderTheHood !== "undefined" && UnderTheHood.hide) {
          UnderTheHood.hide();
        }
      },
      onEnter: function () {
        if (typeof UnderTheHood !== "undefined" && UnderTheHood.init) {
          UnderTheHood.init();
        }
      },
    });

    HistoryPanel.init({
      getStyle: function () { return styles.getStyle(); },
      setStyle: function (style) { styles.setStyle(style); },
      setText: function (text) { editor.setText(text); },
      onPlay: function (gamePack, text, id) {
        setError("");
        currentHistoryId = id;
        NarrativeGame.start(gamePack, text || "", { entryId: id });
      },
      onEntryLoaded: function (id) {
        currentHistoryId = id;
      },
      onStatus: function (msg, type) {
        if (type === "error") setError(msg);
        else editor.setUploadStatus(msg, type === "ok" ? "ok" : type);
      },
    });

    trySharedPlay();
  }

  global.StudioController = { init: initStudio };
})(typeof window !== "undefined" ? window : globalThis);
