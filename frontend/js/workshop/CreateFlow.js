/**
 * CreateFlow — 故事转化与 SSE 生成流程
 */
(function (global) {
  const { formatApiDetail, errorMessage } = global.ApiErrors;
  const consumeSSE = global.SseClient.consume;

  function createCreateFlow(options) {
    const createBtn = options.createBtnEl;
    const demoBtn = options.demoBtnEl;
    const heroDemoBtn = options.heroDemoBtnEl;
    const editor = options.editor;
    const styles = options.styles;
    const pipeline = options.pipeline;
    const onError = options.onError;
    const onHistorySave = options.onHistorySave;

    let isRunning = false;
    let createAbort = null;

    function setLoading(loading) {
      isRunning = loading;
      createBtn.disabled = loading;
      if (demoBtn) demoBtn.disabled = loading;
      if (heroDemoBtn) heroDemoBtn.disabled = loading;
      createBtn.classList.toggle("is-loading", loading);
      createBtn.querySelector(".btn__label").textContent = loading ? "生成中…" : "一键生成互动游戏";
      createBtn.querySelector(".btn__spinner").hidden = !loading;
    }

    function launchDemo() {
      onError("");
      NarrativeGame.startDemo();
    }

    async function startCreate() {
      pipeline.reset();
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
      if (text.length > maxCreateChars) {
        onError(
          "文本过长（" + text.length.toLocaleString() + " 字）。单次提交上限 " +
          maxCreateChars.toLocaleString() + " 字，请删减或按章节拆分。"
        );
        return;
      }

      setLoading(true);
      const createHint =
        llmEffectiveChars > 0 && text.length > llmEffectiveChars
          ? "全文 " + text.length.toLocaleString() + " 字 · 智能采样 " +
            llmEffectiveChars.toLocaleString() + " 字…"
          : "正在连接 AI，首次约需 1～2 分钟…";
      pipeline.setProgress(2, createHint);

      try {
        const res = await fetch("/api/create/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: text, style: styles.getStyle() }),
        });

        if (!res.ok) {
          const err = await res.json().catch(function () { return {}; });
          throw new Error(formatApiDetail(err.detail) || "请求失败 HTTP " + res.status);
        }

        let gamePack = null;
        await consumeSSE(res, function (event, data) {
          if (event === "status") {
            let msg = data.msg || "处理中…";
            const pct = data.progress || 0;
            if (pct >= 55 && pct < 100) msg += " · 目标 15～25 场景";
            if (data.node_count) msg += " · 已生成 " + data.node_count + " 场景";
            pipeline.setProgress(pct, msg);
          }
          if (event === "bible") {
            pipeline.showBible(data.title, data.synopsis);
            pipeline.setProgress(40, "故事圣经完成 · " + (data.title || "未命名") + " · 正在构建分支…");
          }
          if (event === "done") {
            gamePack = data;
            const meta = data.meta || {};
            const nodes = meta.node_count || Object.keys(data.nodes || {}).length;
            const mins = meta.play_minutes || Math.max(1, Math.round(nodes * 1.5));
            pipeline.setProgress(100, "完成 · 共 " + nodes + " 场景 · 预计游玩 " + mins + " 分钟");
          }
          if (event === "error") {
            throw new Error(formatApiDetail(data.detail) || formatApiDetail(data) || "生成失败");
          }
        }, createAbort.signal);

        if (!gamePack) {
          throw new Error("未收到游戏数据。请检查网络连接与 API 配置后重试。");
        }
        if (!gamePack.nodes || !Object.keys(gamePack.nodes).length) {
          throw new Error("未生成有效场景，请缩短文本后重试。");
        }

        try {
          await onHistorySave({
            text: text,
            style: styles.getStyle(),
            title: gamePack.title,
            game: gamePack,
          });
        } catch (saveErr) {
          onError(saveErr.message || "历史保存失败");
          editor.setUploadStatus(saveErr.message || "历史保存失败", "error");
          console.warn("history save", saveErr);
          if (!window.confirm("历史保存失败，仍进入游玩？")) return;
        }

        NarrativeGame.start(gamePack, text);
      } catch (err) {
        onError(errorMessage(err, "生成失败"));
        pipeline.setProgress(0, "已中断");
      } finally {
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
