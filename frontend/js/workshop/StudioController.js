/**
 * StudioController — 创作工坊编排入口
 */
(function (global) {
  function initStudio() {
    const studioError = document.getElementById("studio-error");
    let currentHistoryId = null;
    let workshopScrollY = 0;

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

    const styles = StylePresets.create({
      initialStyle: "urban_romance",
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
      bibleEl: document.getElementById("bible-preview"),
    });

    CreateFlow.create({
      createBtnEl: document.getElementById("create-btn"),
      demoBtnEl: document.getElementById("demo-btn"),
      heroDemoBtnEl: document.getElementById("hero-demo-btn"),
      editor: editor,
      styles: styles,
      pipeline: pipeline,
      onError: setError,
      onHistorySave: saveHistory,
    });

    NarrativeGame.init({
      onBack: function () {
        window.scrollTo({ top: workshopScrollY || 0, behavior: "smooth" });
      },
      onEnter: function () {
        workshopScrollY = window.scrollY;
      },
    });

    HistoryPanel.init({
      getStyle: function () { return styles.getStyle(); },
      setStyle: function (style) { styles.setStyle(style); },
      setText: function (text) { editor.setText(text); },
      onPlay: function (gamePack, text) {
        setError("");
        NarrativeGame.start(gamePack, text || "");
      },
      onEntryLoaded: function (id) {
        currentHistoryId = id;
      },
      onStatus: function (msg, type) {
        if (type === "error") setError(msg);
        else editor.setUploadStatus(msg, type === "ok" ? "ok" : type);
      },
    });
  }

  global.StudioController = { init: initStudio };
})(typeof window !== "undefined" ? window : globalThis);
