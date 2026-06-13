/**
 * CreateFlow — 故事转化与 SSE 生成流程
 */
(function (global) {
  const { formatApiDetail, errorMessage, friendlyValidationMessage, isTimeoutError, CREATE_PHASE_LABELS } =
    global.ApiErrors;
  const resolvePipelineStep =
    global.PipelineView && global.PipelineView.resolveStep
      ? global.PipelineView.resolveStep
      : function (pct, explicitStep) {
          if (pct > 52 || pct >= 80) return "scene";
          if (pct >= 52) return "branch";
          if (pct >= 32) return "weave";
          return explicitStep || "read";
        };
  const consumeSSE = global.SseClient.consume;

  function reportCreateError(err, context, createContext) {
    const raw =
      (err && err.message) ||
      (err && err.detail != null ? formatApiDetail(err.detail) : "") ||
      String(err || "");
    const friendly = errorMessage(err, "生成失败", createContext);
    if (raw && raw !== friendly) {
      console.error("[CreateFlow] " + (context || "生成失败"), { raw: raw, friendly: friendly });
    } else {
      console.error("[CreateFlow] " + (context || "生成失败"), err);
    }
    return friendly;
  }

  function createCreateFlow(options) {
    const createBtn = options.createBtnEl;
    const demoBtn = options.demoBtnEl;
    const heroDemoBtn = options.heroDemoBtnEl;
    const editor = options.editor;
    const styles = options.styles;
    const pipeline = options.pipeline;
    const onError = options.onError;
    const onHistorySave = options.onHistorySave;
    const onEntryId = options.onEntryId || function () {};

    let isRunning = false;
    let createAbort = null;
    let elapsedTimer = null;
    let lastProgressAt = 0;
    let lastProgressPct = -1;
    let lastProgressMsg = "";
    let lastPipelineStep = "read";
    let lastEntryId = null;
    let createEtaLabel = "";
    let createEtaScale = null;

    function estimateWaitLabel(charCount) {
      if (charCount < 1500) return "约 1–2 分钟";
      if (charCount < 4000) return "约 1–3 分钟";
      if (charCount < 8000) return "约 2–4 分钟";
      if (charCount < 15000) return "约 3–6 分钟";
      return "约 5–8 分钟";
    }

    function resolveEtaLabel(eta) {
      if (!eta) return "";
      if (typeof eta === "object") return eta.label || "";
      return String(eta);
    }

    function applyEtaPayload(eta) {
      if (!eta) return;
      if (typeof eta === "object") {
        createEtaScale = eta;
        createEtaLabel = eta.label || createEtaLabel;
        return;
      }
      createEtaLabel = String(eta);
    }

    function parseEtaRange(label) {
      const m = /(\d+)[–-](\d+)/.exec(label || "");
      if (!m) return null;
      return { min: parseInt(m[1], 10), max: parseInt(m[2], 10) };
    }

    function formatElapsed(sec) {
      if (sec < 60) return sec + " 秒";
      return Math.floor(sec / 60) + " 分 " + (sec % 60) + " 秒";
    }

    function inferPipelineStep(pct, explicitStep) {
      return resolvePipelineStep(pct, explicitStep);
    }

    function markProgressActivity(pct, msg, step) {
      const now = Date.now();
      lastProgressAt = now;
      if (pct !== lastProgressPct) lastProgressPct = pct;
      if (msg && msg !== lastProgressMsg) lastProgressMsg = msg;
      lastPipelineStep = inferPipelineStep(pct, step);
    }

    function setLoading(loading) {
      isRunning = loading;
      createBtn.disabled = loading;
      if (demoBtn) demoBtn.disabled = loading;
      if (heroDemoBtn) heroDemoBtn.disabled = loading;
      createBtn.classList.toggle("is-loading", loading);
      const label = createBtn.querySelector(".new-game__zh") || createBtn.querySelector(".btn__label");
      if (label) label.textContent = loading ? "正在进入世界…" : "开始游戏";
      const spinner = createBtn.querySelector(".btn__spinner");
      if (spinner) spinner.hidden = !loading;
    }

    function clearElapsedTimer() {
      if (elapsedTimer) {
        clearInterval(elapsedTimer);
        elapsedTimer = null;
      }
    }

    function touchStreamActivity() {
      /* keepalive / raw bytes — does not reset progress-idle timer */
    }

    function buildElapsedNote(sec) {
      let note = "已等待 " + formatElapsed(sec);
      const range = parseEtaRange(createEtaLabel);
      if (!range) {
        if (createEtaLabel && sec < 20) note += " · 预计总耗时 " + createEtaLabel;
        return note;
      }
      const elapsedMin = sec / 60;
      if (elapsedMin > range.max + 2) {
        note += " · 略长于预期，仍在生成中";
        return note;
      }
      const remainMin = Math.max(0, Math.ceil(range.min - elapsedMin));
      const remainMax = Math.max(remainMin, Math.ceil(range.max - elapsedMin));
      if (elapsedMin < range.min * 0.3 && sec < 20) {
        note += " · 预计总耗时 " + createEtaLabel;
      } else if (remainMax > 0) {
        note += " · 预计还需 " + remainMin + "–" + remainMax + " 分钟";
      } else {
        note += " · 即将完成";
      }
      return note;
    }

    function startElapsedTimer(charCount) {
      clearElapsedTimer();
      pipeline.setElapsed("");
      const start = Date.now();
      createEtaLabel = estimateWaitLabel(charCount || 0);
      createEtaScale = null;
      lastProgressPct = -1;
      lastProgressMsg = "";
      lastPipelineStep = "read";
      lastProgressAt = Date.now();
      pipeline.setElapsed(buildElapsedNote(0));
      elapsedTimer = setInterval(function () {
        const sec = Math.floor((Date.now() - start) / 1000);
        pipeline.setElapsed(buildElapsedNote(sec));
      }, 1000);
    }

    async function fetchCover(gamePack) {
      try {
        const res = await fetch("/api/game-assets/cover", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: gamePack.title,
            synopsis: gamePack.synopsis,
            style: gamePack.style || styles.getStyle(),
          }),
        });
        const data = await res.json();
        if (res.ok && data.url) {
          gamePack.cover_url = data.url;
          return data.url;
        }
      } catch (e) {
        console.warn("cover", e);
      }
      return null;
    }

    function launchDemo() {
      onError("");
      NarrativeGame.startDemo();
    }

    async function startCreate() {
      if (createAbort) createAbort.abort();
      createAbort = new AbortController();

      if (isRunning || editor.isUploading()) return;
      onError("");

      const text = editor.getText();

      if (text.length < 80) {
        onError("文本太短，请至少输入 80 字。可粘贴故事、上传文件，或试玩 Demo。");
        return;
      }

      if (global.ApiConfig && global.ApiConfig.isBackendAvailable && !global.ApiConfig.isBackendAvailable()) {
        onError(
          (global.ApiConfig.backendStatusMessage && global.ApiConfig.backendStatusMessage()) ||
            "故事解析服务暂时不可用，请稍后再试。"
        );
        return;
      }

      pipeline.reset();
      setLoading(true);
      startElapsedTimer(text.length);
      pipeline.setProgress(2, "正在构筑世界……", {
        step: "read",
        eta: createEtaLabel,
        scale: createEtaScale,
        charCount: text.length,
      });

      let handledTimeout = false;
      try {
        const healthFetch =
          global.ApiConfig && global.ApiConfig.apiFetchWithRetry
            ? global.ApiConfig.apiFetchWithRetry.bind(global.ApiConfig)
            : fetch;
        const healthRes = await healthFetch("/api/health", undefined, {
          retries: 1,
          delayMs: 8000,
          timeoutMs: 25000,
          retryNetwork: true,
        });
        const health = global.ApiConfig && global.ApiConfig.readJsonOrApiError
          ? await global.ApiConfig.readJsonOrApiError(healthRes, "无法连接故事解析服务")
          : await healthRes.json().catch(function () { return {}; });
        if (health.ok === false) {
          throw new Error(
            (health.env_issues && health.env_issues[0]) ||
              "故事解析服务尚未就绪，请稍后再试。"
          );
        }
        if (!health.has_key) {
          throw new Error(
            "未配置 AI_API_KEY。请复制 backend/.env.example 为 backend/.env 并填入密钥，然后重启服务。"
          );
        }

        const createFetch =
          global.ApiConfig && global.ApiConfig.apiFetchWithRetry
            ? global.ApiConfig.apiFetchWithRetry.bind(global.ApiConfig)
            : fetch;
        const res = await createFetch(
          "/api/create/stream",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text, style: styles.getStyle() }),
            signal: createAbort.signal,
          },
          {
            retries: 2,
            delayMs: 10000,
            timeoutMs: 0,
            retryNetwork: true,
          }
        );

        if (global.ApiConfig && global.ApiConfig.ensureSseResponse) {
          await global.ApiConfig.ensureSseResponse(res, "生成请求失败");
        } else if (!res.ok) {
          const err = await res.json().catch(function () { return {}; });
          throw new Error(formatApiDetail(err.detail) || "请求失败 HTTP " + res.status);
        }

        let gamePack = null;
        const sseMeta = await consumeSSE(
          res,
          function (event, data) {
          touchStreamActivity();
          if (event === "status") {
            const pct = data.progress || 0;
            const msg = data.msg || "处理中…";
            markProgressActivity(pct, msg, data.step);
            applyEtaPayload(data.eta);
            pipeline.setProgress(pct, msg, {
              step: inferPipelineStep(pct, data.step),
              branch_count: data.branch_count,
              ending_count: data.ending_count,
              eta: resolveEtaLabel(data.eta) || createEtaLabel,
              scale: createEtaScale,
              charCount: text.length,
            });
          }
          if (event === "done") {
            gamePack = data;
            const meta = data.meta || {};
            pipeline.setProgress(100, "故事成形 · 即将进入世界", { step: "done" });
            pipeline.showAchievement(meta, data.cover_url || null);
          }
          if (event === "error") {
            const detail = data.detail || data;
            const rawDetail = formatApiDetail(detail) || "生成失败";
            const friendly = errorMessage(
              { message: rawDetail },
              "生成失败",
              { phase: lastPipelineStep }
            );
            if (data.debug) {
              console.error("[CreateFlow] SSE error debug:", data.debug);
            } else if (typeof detail === "string" && friendlyValidationMessage(detail)) {
              console.error("[CreateFlow] SSE error raw:", detail);
            }
            throw new Error(friendly);
          }
        },
          createAbort.signal,
          touchStreamActivity
        );

        if (!gamePack) {
          const incompleteMsg =
            (global.ApiConfig && global.ApiConfig.streamIncompleteMessage
              ? global.ApiConfig.streamIncompleteMessage()
              : "") ||
            "生成流意外结束，未收到完整游戏数据。请检查网络是否稳定、AI 接口是否可用后重试。";
          if (sseMeta && sseMeta.eventCount > 0 && !sseMeta.receivedError) {
            console.error("[CreateFlow] SSE ended early", sseMeta);
          }
          throw new Error(incompleteMsg);
        }
        if (!gamePack.nodes || !Object.keys(gamePack.nodes).length) {
          throw new Error("未生成有效场景，请缩短文本后重试。");
        }

        fetchCover(gamePack)
          .then(function (url) {
            if (url) {
              gamePack.cover_url = url;
              pipeline.showAchievement(gamePack.meta, url);
            }
          })
          .catch(function (e) { console.warn("cover", e); });

        try {
          lastEntryId = await onHistorySave({
            text: text,
            style: styles.getStyle(),
            title: gamePack.title,
            game: gamePack,
          });
          onEntryId(lastEntryId);
          if (lastEntryId && pipeline.setShareHandler) {
            pipeline.setShareHandler(async function () {
              try {
                const link = await ShareWorld.createShareLink(lastEntryId);
                await ShareWorld.copyToClipboard(link.url);
                editor.setUploadStatus("分享链接已复制", "ok");
              } catch (err) {
                onError(err.message || "分享失败");
              }
            });
          }
        } catch (saveErr) {
          onError(saveErr.message || "历史保存失败");
          editor.setUploadStatus(saveErr.message || "历史保存失败", "error");
          console.warn("history save", saveErr);
          if (!window.confirm("历史保存失败，仍进入游玩？")) return;
        }

        pipeline.finish();
        NarrativeGame.start(gamePack, text, { entryId: lastEntryId });
      } catch (err) {
        if (err && err.name === "AbortError") {
          onError("已取消生成");
          pipeline.reset();
        } else {
          const createContext = { phase: lastPipelineStep, pct: lastProgressPct };
          const friendly = reportCreateError(err, "生成流程异常", createContext);
          if (isTimeoutError(err, friendly) && pipeline.showTimeoutRetry) {
            handledTimeout = true;
            onError("");
            const phaseLabel = CREATE_PHASE_LABELS[lastPipelineStep] || "";
            const retryMsg = phaseLabel
              ? phaseLabel + "阶段超时。生成超时，可点击重试"
              : "生成超时，可点击重试";
            pipeline.showTimeoutRetry({
              message: retryMsg,
              onRetry: function () {
                onError("");
                startCreate();
              },
            });
          } else {
            onError(friendly);
            pipeline.reset();
          }
        }
      } finally {
        clearElapsedTimer();
        if (!handledTimeout) {
          pipeline.setElapsed("");
        }
        setLoading(false);
      }
    }

    createBtn.addEventListener("click", startCreate);
    if (demoBtn) demoBtn.addEventListener("click", launchDemo);
    if (heroDemoBtn) heroDemoBtn.addEventListener("click", launchDemo);

    return {
      isRunning: function () { return isRunning; },
      launchDemo: launchDemo,
    };
  }

  global.CreateFlow = { create: createCreateFlow };
})(typeof window !== "undefined" ? window : globalThis);
