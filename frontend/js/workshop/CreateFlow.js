/**
 * CreateFlow — 故事转化与 SSE 生成流程
 */
(function (global) {
  const { formatApiDetail, errorMessage, friendlyValidationMessage } = global.ApiErrors;
  const consumeSSE = global.SseClient.consume;

  function reportCreateError(err, context) {
    const raw =
      (err && err.message) ||
      (err && err.detail != null ? formatApiDetail(err.detail) : "") ||
      String(err || "");
    const friendly = errorMessage(err, "生成失败");
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
    let lastEntryId = null;

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

    function startElapsedTimer() {
      clearElapsedTimer();
      const start = Date.now();
      lastProgressAt = start;
      elapsedTimer = setInterval(function () {
        const sec = Math.floor((Date.now() - start) / 1000);
        const idle = Math.floor((Date.now() - lastProgressAt) / 1000);
        let note = "已等待 " + sec + " 秒";
        if (idle >= 45) {
          note += " · 长故事可能需要数分钟，请稍候";
        } else if (idle >= 20) {
          note += " · 命运分支正在编织";
        }
        pipeline.setElapsed(note);
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
      const maxCreateChars = editor.getMaxCreateChars();
      const llmEffectiveChars = editor.getLlmEffectiveChars();

      if (text.length < 80) {
        onError("文本太短，请至少输入 80 字。可粘贴故事、上传文件，或试玩 Demo。");
        return;
      }
      if (maxCreateChars > 0 && text.length > maxCreateChars) {
        onError(
          "文本过长（" + text.length.toLocaleString() + " 字）。单次提交上限 " +
          maxCreateChars.toLocaleString() + " 字，请删减或按章节拆分。"
        );
        return;
      }

      const gate = await ProtagonistGate.show(text);
      if (!gate) return;

      pipeline.reset();
      setLoading(true);
      startElapsedTimer();
      const createHint =
        llmEffectiveChars > 0 && text.length > llmEffectiveChars
          ? "全文 " + text.length.toLocaleString() + " 字 · 智能采样 " +
            llmEffectiveChars.toLocaleString() + " 字…"
          : "正在构筑世界……";
      pipeline.setProgress(2, createHint, { step: "read" });

      try {
        const healthFetch =
          global.ApiConfig && global.ApiConfig.apiFetchWithRetry
            ? global.ApiConfig.apiFetchWithRetry.bind(global.ApiConfig)
            : fetch;
        const healthRes = await healthFetch("/api/health", undefined, { retries: 2, delayMs: 15000 });
        const health = global.ApiConfig && global.ApiConfig.readJsonOrApiError
          ? await global.ApiConfig.readJsonOrApiError(healthRes, "无法连接故事解析服务")
          : await healthRes.json().catch(function () { return {}; });
        if (!health.has_key) {
          throw new Error(
            "未配置 AI_API_KEY。请复制 backend/.env.example 为 backend/.env 并填入密钥，然后重启服务。"
          );
        }

        const res = await fetch("/api/create/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: text, style: styles.getStyle() }),
          signal: createAbort.signal,
        });

        if (global.ApiConfig && global.ApiConfig.ensureSseResponse) {
          await global.ApiConfig.ensureSseResponse(res, "生成请求失败");
        } else if (!res.ok) {
          const err = await res.json().catch(function () { return {}; });
          throw new Error(formatApiDetail(err.detail) || "请求失败 HTTP " + res.status);
        }

        let gamePack = null;
        await consumeSSE(res, function (event, data) {
          if (event === "status") {
            lastProgressAt = Date.now();
            let msg = data.msg || "处理中…";
            let step = data.step || "read";
            if (data.progress >= 55 && !data.step) step = "branch";
            if (data.progress >= 75 && !data.step) step = "scene";
            pipeline.setProgress(data.progress || 0, msg, {
              step: step,
              branch_count: data.branch_count,
              ending_count: data.ending_count,
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
            const friendly = formatApiDetail(detail) || "生成失败";
            if (data.debug) {
              console.error("[CreateFlow] SSE error debug:", data.debug);
            } else if (typeof detail === "string" && friendlyValidationMessage(detail)) {
              console.error("[CreateFlow] SSE error raw:", detail);
            }
            throw new Error(friendly);
          }
        }, createAbort.signal);

        if (!gamePack) {
          throw new Error(
            "生成流意外结束，未收到完整游戏数据。请检查网络是否稳定、AI 接口是否可用后重试。"
          );
        }
        if (!gamePack.nodes || !Object.keys(gamePack.nodes).length) {
          throw new Error("未生成有效场景，请缩短文本后重试。");
        }

        if (gate.originalName && gate.protagonistName) {
          const applied = ProtagonistGate.applyNameToPack(
            gamePack,
            gate.originalName,
            gate.protagonistName
          );
          gamePack = applied.pack;
          gamePack.protagonist_name = applied.protagonistName;
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
        NarrativeGame.start(gamePack, text, {
          entryId: lastEntryId,
          protagonistName: gamePack.protagonist_name,
        });
      } catch (err) {
        if (err && err.name === "AbortError") {
          onError("已取消生成");
        } else {
          onError(reportCreateError(err, "生成流程异常"));
        }
        pipeline.reset();
      } finally {
        clearElapsedTimer();
        pipeline.setElapsed("");
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
