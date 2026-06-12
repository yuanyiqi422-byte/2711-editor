/**
 * PipelineView — 叙事感生成进度 + 成就统计
 */
(function (global) {
  const STEP_ORDER = ["read", "weave", "branch", "scene"];
  const GENERIC_HINT_MSGS = new Set(["等待开始…", "正在构筑世界……", "处理中…", ""]);
  const STATUS_CHILD_IDS = ["pipeline-elapsed", "pipeline-sub", "pipeline-retry-btn"];

  function phaseHint(step, pct) {
    if (pct > 52 || pct >= 80 || step === "scene") {
      return "场景对白生成中，请耐心等待";
    }
    if (pct >= 52 || step === "branch") {
      return "命运分支规划中，请稍候";
    }
    if (step === "weave" || (pct >= 32 && pct < 52)) {
      return "剧情脉络正在编织，请稍候";
    }
    return "故事正在成形，请稍候";
  }

  function resolvePipelineStep(pct, explicitStep) {
    if (pct >= 100) return "done";
    if (pct > 52 || pct >= 80) return "scene";
    if (pct >= 52) return "branch";
    if (pct >= 32) return "weave";
    return explicitStep || "read";
  }

  function stepEtaSubtext(step, pct, extra) {
    extra = extra || {};
    const endingSuffix =
      extra.ending_count && extra.ending_count > 0
        ? " · " + extra.ending_count + " 种结局"
        : "";
    if (pct >= 100) return "世界已就绪";
    return phaseHint(step, pct) + endingSuffix;
  }

  function isProviderSwitchMsg(msg) {
    if (!msg) return false;
    return (
      msg.indexOf("赠送 API") !== -1 ||
      msg.indexOf("已自动切换至 DeepSeek") !== -1 ||
      msg.indexOf("provider_switch") !== -1
    );
  }

  function resolveHint(msg, step, pct, extra) {
    if (pct >= 100) return "世界已就绪";
    const cleaned = normalizeStatusMsg(msg);
    if (isProviderSwitchMsg(cleaned)) {
      return stepEtaSubtext(step, pct, extra);
    }
    if (cleaned && !GENERIC_HINT_MSGS.has(cleaned)) {
      extra = extra || {};
      if (extra.ending_count && extra.ending_count > 0 && cleaned.indexOf("种结局") < 0) {
        return cleaned + " · " + extra.ending_count + " 种结局";
      }
      return cleaned;
    }
    return stepEtaSubtext(step, pct, extra);
  }

  /** Strip elapsed/ETA fragments — pipeline__elapsed owns timing display. */
  function normalizeStatusMsg(msg) {
    if (!msg) return "";
    return msg
      .replace(/[（(][^）)]*已等待[^）)]*[）)]/g, "")
      .replace(/[（(][^）)]*已\s*\d+\s*秒[^）)]*[）)]/g, "")
      .replace(/[（(][^）)]*全程约[^）)]*[）)]/g, "")
      .replace(/[（(][^）)]*预计总耗时[^）)]*[）)]/g, "")
      .replace(/[（(][^）)]*\d+\s*秒\s*\/\s*约[^）)]*[）)]/g, "")
      .replace(/…?\s*已等待\s*\d+\s*秒/g, "")
      .replace(/已等待\s*\d+\s*秒/g, "")
      .replace(/已等待\s*\d+\s*分\s*\d+\s*秒/g, "")
      .replace(/[，,、]\s*已\s*\d+\s*秒/g, "")
      .replace(/已\s*\d+\s*秒/g, "")
      .replace(/\(\s*\d+\s*秒\s*\)/g, "")
      .replace(/（\s*\d+\s*秒\s*）/g, "")
      .replace(/\d+\s*秒\s*\/\s*约/g, "")
      .replace(/\s*[·•]\s*预计总耗时\s*[^（(]+/g, "")
      .replace(/\s*[·•]\s*预计还需\s*[^（(]+/g, "")
      .replace(/[,，]?\s*预计还需\s*[^（(…]+/g, "")
      .replace(/[,，]?\s*全程约\s*[^（(…]+/g, "")
      .replace(/[,，]?\s*可能需\s*[^（(…]+/g, "")
      .replace(/[,，]?\s*通常还需\s*[^（(…]+/g, "")
      .replace(/\s{2,}/g, " ")
      .replace(/\s+([，,。；;])/g, "$1")
      .replace(/[，,]\s*[，,]/g, "，")
      .replace(/…+/g, "…")
      .trim();
  }

  function createPipelineView(options) {
    const pipeline = options.pipelineEl;
    const pipelineFill = options.fillEl;
    const pipelinePct = options.pctEl;
    const pipelineMsg = options.msgEl;
    const pipelineStatus = document.getElementById("pipeline-status");
    const pipelineSteps = document.getElementById("pipeline-steps");
    const pipelineAchievement = document.getElementById("pipeline-achievement");
    const pipelineAchievementStats = document.getElementById("pipeline-achievement-stats");
    const pipelineCover = document.getElementById("pipeline-cover");
    const pipelineCoverImg = document.getElementById("pipeline-cover-img");
    const pipelineShareBtn = document.getElementById("pipeline-share-btn");
    let pipelineRetryBtn = null;
    let pipelineElapsed = options.elapsedEl;
    let pipelineSub = document.getElementById("pipeline-sub");
    const pipelineBar = pipeline ? pipeline.querySelector(".pipeline__bar") : null;
    const studio = options.studioEl;

    let lastMeta = null;
    let lastHint = "";

    function ensureStatusDom() {
      if (!pipelineStatus) return;
      Array.from(pipelineStatus.children).forEach(function (child) {
        if (child.id && STATUS_CHILD_IDS.indexOf(child.id) >= 0) return;
        pipelineStatus.removeChild(child);
      });
      if (!pipelineElapsed || !pipelineStatus.contains(pipelineElapsed)) {
        pipelineElapsed = document.getElementById("pipeline-elapsed");
      }
      if (!pipelineSub || !pipelineStatus.contains(pipelineSub)) {
        pipelineSub = document.getElementById("pipeline-sub");
      }
      if (!pipelineElapsed) {
        pipelineElapsed = document.createElement("p");
        pipelineElapsed.className = "pipeline__elapsed";
        pipelineElapsed.id = "pipeline-elapsed";
        pipelineElapsed.hidden = true;
        pipelineStatus.insertBefore(pipelineElapsed, pipelineStatus.firstChild);
      }
      if (!pipelineSub) {
        pipelineSub = document.createElement("p");
        pipelineSub.className = "pipeline__sub";
        pipelineSub.id = "pipeline-sub";
        pipelineStatus.appendChild(pipelineSub);
      }
    }

    function clearStatusArea() {
      ensureStatusDom();
      if (pipelineElapsed) {
        pipelineElapsed.textContent = "";
        pipelineElapsed.hidden = true;
      }
      if (pipelineSub) {
        pipelineSub.textContent = "";
        pipelineSub.hidden = true;
      }
      if (pipelineMsg) {
        pipelineMsg.textContent = "";
        pipelineMsg.hidden = true;
      }
    }

    function markStep(step) {
      if (!pipelineSteps) return;
      const idx = STEP_ORDER.indexOf(step);
      pipelineSteps.querySelectorAll(".pipeline__step").forEach(function (el, i) {
        el.classList.toggle("is-done", i < idx);
        el.classList.toggle("is-active", i === idx);
      });
    }

    function hide() {
      if (!pipeline) return;
      pipeline.hidden = true;
      if (studio) studio.classList.remove("is-generating");
    }

    function show() {
      if (!pipeline) return;
      pipeline.hidden = false;
      if (studio) studio.classList.add("is-generating");
    }

    function setHint(text) {
      ensureStatusDom();
      lastHint = normalizeStatusMsg(text || "");
      if (!pipelineSub) return;
      if (!lastHint) {
        pipelineSub.textContent = "";
        pipelineSub.hidden = true;
        return;
      }
      pipelineSub.textContent = lastHint;
      pipelineSub.hidden = false;
    }

    function setProgress(pct, msg, extra) {
      if (!pipeline) return;

      show();
      pipelineFill.style.width = pct + "%";
      pipelinePct.textContent = pct + "%";

      if (pipelineBar) pipelineBar.setAttribute("aria-valuenow", String(pct));

      extra = extra || {};
      const step = resolvePipelineStep(pct, extra.step);

      if (step === "done") {
        if (pipelineSteps) {
          pipelineSteps.querySelectorAll(".pipeline__step").forEach(function (el) {
            el.classList.add("is-done");
            el.classList.remove("is-active");
          });
        }
        setHint("世界已就绪");
        return;
      }

      setHint(resolveHint(msg, step, pct, extra));
      markStep(step);
    }

    function ensureRetryButton() {
      ensureStatusDom();
      if (pipelineRetryBtn && pipelineStatus && pipelineStatus.contains(pipelineRetryBtn)) {
        return pipelineRetryBtn;
      }
      pipelineRetryBtn = document.createElement("button");
      pipelineRetryBtn.type = "button";
      pipelineRetryBtn.id = "pipeline-retry-btn";
      pipelineRetryBtn.className = "workshop-btn workshop-btn--outline pipeline__retry-btn";
      pipelineRetryBtn.textContent = "重新生成";
      pipelineRetryBtn.hidden = true;
      if (pipelineStatus) pipelineStatus.appendChild(pipelineRetryBtn);
      return pipelineRetryBtn;
    }

    function showTimeoutRetry(opts) {
      opts = opts || {};
      show();
      const btn = ensureRetryButton();
      setHint(opts.message || "生成超时，可点击重试");
      if (btn) {
        btn.hidden = false;
        btn.onclick = function () {
          btn.hidden = true;
          if (typeof opts.onRetry === "function") opts.onRetry();
        };
      }
    }

    function hideRetryButton() {
      if (pipelineRetryBtn) pipelineRetryBtn.hidden = true;
    }

    function showAchievement(meta, coverUrl) {
      lastMeta = meta || lastMeta;
      if (!pipelineAchievement || !lastMeta) return;

      const branches = lastMeta.branch_count || 0;
      const endings = lastMeta.ending_count || 0;
      pipelineAchievement.hidden = false;

      if (pipelineAchievementStats) {
        pipelineAchievementStats.textContent =
          "AI 共为你生成了 " + branches + " 个命运分支，" + endings + " 种不同结局。";
      }

      if (coverUrl && pipelineCover && pipelineCoverImg) {
        pipelineCover.hidden = false;
        pipelineCoverImg.src = coverUrl;
      }
    }

    function setShareHandler(fn) {
      if (!pipelineShareBtn) return;
      pipelineShareBtn.hidden = false;
      pipelineShareBtn.onclick = fn;
    }

    function setElapsed(text) {
      ensureStatusDom();
      if (!pipelineElapsed) return;
      if (!text) {
        pipelineElapsed.hidden = true;
        pipelineElapsed.textContent = "";
        return;
      }
      pipelineElapsed.textContent = text;
      pipelineElapsed.hidden = false;
    }

    function reset() {
      hide();
      hideRetryButton();
      if (pipelineFill) pipelineFill.style.width = "0%";
      if (pipelinePct) pipelinePct.textContent = "0%";
      clearStatusArea();
      setHint("故事正在成形，请稍候...");
      if (pipelineBar) pipelineBar.setAttribute("aria-valuenow", "0");
      if (pipelineAchievement) pipelineAchievement.hidden = true;
      if (pipelineCover) pipelineCover.hidden = true;
      if (pipelineShareBtn) pipelineShareBtn.hidden = true;
      if (pipelineSteps) {
        pipelineSteps.querySelectorAll(".pipeline__step").forEach(function (el) {
          el.classList.remove("is-done", "is-active");
        });
      }
      lastMeta = null;
      lastHint = "";
    }

    function finish() {
      hide();
    }

    return {
      show: show,
      hide: hide,
      setProgress: setProgress,
      setElapsed: setElapsed,
      reset: reset,
      finish: finish,
      showAchievement: showAchievement,
      setShareHandler: setShareHandler,
      showTimeoutRetry: showTimeoutRetry,
      resolveStep: resolvePipelineStep,
    };
  }

  global.PipelineView = { create: createPipelineView, resolveStep: resolvePipelineStep };
})(typeof window !== "undefined" ? window : globalThis);
