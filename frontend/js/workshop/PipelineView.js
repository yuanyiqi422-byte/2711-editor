/**
 * PipelineView — 生成进度条与故事圣经预览
 */
(function (global) {
  function createPipelineView(options) {
    const pipeline = options.pipelineEl;
    const pipelineFill = options.fillEl;
    const pipelinePct = options.pctEl;
    const pipelineMsg = options.msgEl;
    const pipelineBar = pipeline ? pipeline.querySelector(".pipeline__bar") : null;
    const biblePreview = options.bibleEl;

    function setProgress(pct, msg) {
      if (!pipeline) return;
      pipeline.hidden = false;
      pipelineFill.style.width = pct + "%";
      pipelinePct.textContent = pct + "%";
      pipelineMsg.textContent = msg;
      if (pipelineBar) pipelineBar.setAttribute("aria-valuenow", String(pct));
    }

    function showBible(title, synopsis) {
      if (!biblePreview) return;
      biblePreview.hidden = false;
      biblePreview.replaceChildren();
      const strong = document.createElement("strong");
      strong.textContent = "故事圣经";
      biblePreview.appendChild(strong);
      biblePreview.appendChild(document.createTextNode(" · " + (title || "")));
      biblePreview.appendChild(document.createElement("br"));
      biblePreview.appendChild(document.createTextNode(synopsis || ""));
    }

    function reset() {
      setProgress(0, "等待开始…");
      if (pipelineBar) pipelineBar.setAttribute("aria-valuenow", "0");
      if (biblePreview) {
        biblePreview.hidden = true;
        biblePreview.innerHTML = "";
      }
    }

    return { setProgress: setProgress, showBible: showBible, reset: reset };
  }

  global.PipelineView = { create: createPipelineView };
})(typeof window !== "undefined" ? window : globalThis);
