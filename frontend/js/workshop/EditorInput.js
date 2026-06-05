/**
 * EditorInput — 故事文本输入、字数统计与文件上传
 */
(function (global) {
  const { formatApiDetail, errorMessage } = global.ApiErrors;

  function createEditorInput(options) {
    const input = options.inputEl;
    const charCount = options.charCountEl;
    const fileInput = options.fileInputEl;
    const uploadStatus = options.uploadStatusEl;
    const uploadProgress = options.uploadProgressEl;
    const uploadProgressFill = options.uploadProgressFillEl;
    const uploadLabel = options.uploadLabelEl;
    const uploadFormats = options.uploadFormatsEl;
    const workshopOnboard = options.onboardEl;
    const onTextChange = options.onTextChange || function () {};
    const onHistorySave = options.onHistorySave || function () {};
    const getSelectedStyle = options.getSelectedStyle || function () { return "urban_romance"; };
    const onError = options.onError || function () {};

    let isUploading = false;
    let maxCreateChars = 10000000;
    let llmEffectiveChars = 120000;

    function setUploadProgress(active, pct) {
      if (!uploadProgress || !uploadProgressFill) return;
      if (!active) {
        uploadProgress.hidden = true;
        uploadProgress.classList.remove("is-indeterminate");
        uploadProgressFill.style.width = "0%";
        uploadProgress.setAttribute("aria-valuenow", "0");
        return;
      }
      uploadProgress.hidden = false;
      if (pct == null) {
        uploadProgress.classList.add("is-indeterminate");
        uploadProgressFill.style.width = "40%";
        uploadProgress.setAttribute("aria-valuenow", "0");
      } else {
        uploadProgress.classList.remove("is-indeterminate");
        uploadProgressFill.style.width = Math.min(100, pct) + "%";
        uploadProgress.setAttribute("aria-valuenow", String(Math.min(100, pct)));
      }
    }

    function setUploadStatus(msg, type) {
      if (!uploadStatus) return;
      if (!msg) {
        uploadStatus.hidden = true;
        uploadStatus.textContent = "";
        uploadStatus.className = "workshop__upload-status";
        return;
      }
      uploadStatus.hidden = false;
      uploadStatus.textContent = msg;
      uploadStatus.className = "workshop__upload-status" + (type ? " is-" + type : "");
    }

    function updateOnboard() {
      if (!workshopOnboard || !input) return;
      workshopOnboard.hidden = input.value.trim().length >= 80;
    }

    function updateCount() {
      const n = input.value.length;
      updateOnboard();
      let label = "全文 " + n.toLocaleString() + " 字";
      charCount.className = "workshop__hint";
      if (n > maxCreateChars) {
        charCount.classList.add("is-over");
        label += " · 超出提交上限 " + maxCreateChars.toLocaleString() + " 字";
      } else if (llmEffectiveChars > 0 && n > llmEffectiveChars) {
        charCount.classList.add("is-warn");
        label += " · 生成时将智能采样 " + llmEffectiveChars.toLocaleString() + " 字";
      }
      charCount.textContent = label;
      onTextChange(n);
    }

    function setText(text) {
      input.value = text || "";
      updateCount();
    }

    function getText() {
      return (input.value || "").trim();
    }

    function getRawText() {
      return input.value || "";
    }

    async function uploadStoryFile(file) {
      const maxMb = 50;
      if (file.size > maxMb * 1024 * 1024) {
        setUploadStatus("文件超过 " + maxMb + " MB，请拆分后上传。", "error");
        return;
      }

      isUploading = true;
      if (uploadLabel) uploadLabel.classList.add("is-busy");
      setUploadProgress(true, null);
      setUploadStatus("正在解析「" + file.name + "」… 大文件可能需要 1～3 分钟。", "loading");
      onError("");

      try {
        const form = new FormData();
        form.append("file", file);
        const controller = new AbortController();
        const timeoutMs = file.size > 5 * 1024 * 1024 ? 180000 : 90000;
        const timer = setTimeout(function () { controller.abort(); }, timeoutMs);
        let res;
        try {
          res = await fetch("/api/ingest/file", {
            method: "POST",
            body: form,
            signal: controller.signal,
          });
        } catch (fetchErr) {
          if (fetchErr && fetchErr.name === "AbortError") {
            throw new Error(
              "上传解析超时（" + Math.round(timeoutMs / 60000) + " 分钟）。请稍后重试，或拆分章节上传。"
            );
          }
          throw fetchErr;
        } finally {
          clearTimeout(timer);
        }
        const data = await res.json().catch(function () { return {}; });
        if (!res.ok) throw new Error(formatApiDetail(data.detail) || "上传解析失败");

        input.value = data.text || "";
        updateCount();

        const fullChars = data.char_count || (data.text || "").length;
        let msg = "已载入「" + (data.filename || file.name) + "」· " + (data.format || "") +
          " · 全文 " + fullChars.toLocaleString() + " 字";
        if (data.total_pages != null && data.pages_processed != null) {
          if (data.pages_processed < data.total_pages) {
            msg += " · PDF 已处理 " + data.pages_processed + " / " + data.total_pages + " 页";
          } else {
            msg += " · PDF 共 " + data.total_pages + " 页";
          }
        } else if (data.pages_processed) {
          msg += " · 已处理 " + data.pages_processed + " 页";
        }
        if (data.used_ocr) msg += " · 扫描版 OCR";
        if (data.truncated && data.llm_char_count) {
          msg += " · 生成时将使用 " + data.llm_char_count.toLocaleString() + " 字";
        }
        if (data.warnings && data.warnings.length) {
          msg += "\n" + data.warnings.join("\n");
        }
        const hasWarn = data.truncated || (data.warnings && data.warnings.length) ||
          (data.total_pages && data.pages_processed < data.total_pages);
        setUploadStatus(msg, hasWarn ? "warn" : "ok");

        try {
          await onHistorySave({
            text: data.text || "",
            filename: data.filename || file.name,
            style: getSelectedStyle(),
          });
        } catch (saveErr) {
          onError(saveErr.message || "历史保存失败");
          setUploadStatus(saveErr.message || "历史保存失败", "error");
          console.warn("history save", saveErr);
        }

        if (data.truncated && data.truncate_note) {
          onError(data.truncate_note);
        } else if (data.total_pages && data.pages_processed < data.total_pages) {
          onError(
            "PDF 共 " + data.total_pages + " 页，本次处理 " + data.pages_processed +
            " 页。如需全书提取，请拆分 PDF 后重传，或在 backend/.env 调整 MAX_PDF_PAGES。"
          );
        } else {
          onError("");
        }
      } catch (err) {
        setUploadStatus(errorMessage(err, "解析失败"), "error");
      } finally {
        isUploading = false;
        setUploadProgress(false);
        if (uploadLabel) uploadLabel.classList.remove("is-busy");
        fileInput.value = "";
      }
    }

    function bindEvents() {
      fileInput.addEventListener("change", function () {
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;
        const ext = (file.name.split(".").pop() || "").toLowerCase();
        if (ext === "txt" || ext === "md" || ext === "markdown") {
          const reader = new FileReader();
          reader.onload = async function () {
            input.value = String(reader.result || "");
            updateCount();
            setUploadStatus("已读取本地文本 · " + file.name, "ok");
            fileInput.value = "";
            try {
              await onHistorySave({
                text: input.value,
                filename: file.name,
                style: getSelectedStyle(),
              });
            } catch (saveErr) {
              onError(saveErr.message || "历史保存失败");
              setUploadStatus(saveErr.message || "历史保存失败", "error");
              console.warn("history save", saveErr);
            }
          };
          reader.onerror = function () {
            uploadStoryFile(file);
          };
          reader.readAsText(file, "UTF-8");
          return;
        }
        uploadStoryFile(file);
      });

      input.addEventListener("input", updateCount);
    }

    function loadHealthFormats() {
      fetch("/api/health")
        .then(function (r) { return r.json(); })
        .then(function (h) {
          if (!h.upload || !uploadFormats) return;
          const fmts = (h.upload.formats || []).join(" ").replace(/\./g, "").toUpperCase();
          const ex = h.extract || {};
          let tail = " · 上传后全文载入编辑区";
          maxCreateChars = ex.max_create_chars || ex.max_extract_chars || maxCreateChars;
          llmEffectiveChars = ex.llm_effective_chars || ex.llm_model_safe_chars || llmEffectiveChars;
          updateCount();
          if (llmEffectiveChars > 0) {
            tail += " · 超长文本生成时智能采样至多 " + llmEffectiveChars.toLocaleString() + " 字";
          }
          if (maxCreateChars > 0) {
            tail += " · 提交上限 " + maxCreateChars.toLocaleString() + " 字";
          }
          if (ex.max_pdf_pages > 0) {
            tail += " · PDF 最多 " + ex.max_pdf_pages + " 页";
          } else if (ex.pdf_page_hard_cap) {
            tail += " · PDF 默认全书（上限 " + ex.pdf_page_hard_cap + " 页）";
          }
          uploadFormats.textContent =
            "支持 " + fmts + " · 最大 " + (h.upload.max_mb || 50) + "MB" + tail;
        })
        .catch(function () {});
    }

    bindEvents();
    updateCount();
    loadHealthFormats();

    return {
      getText: getText,
      getRawText: getRawText,
      setText: setText,
      updateCount: updateCount,
      setUploadStatus: setUploadStatus,
      isUploading: function () { return isUploading; },
      getMaxCreateChars: function () { return maxCreateChars; },
      getLlmEffectiveChars: function () { return llmEffectiveChars; },
    };
  }

  global.EditorInput = { create: createEditorInput };
})(typeof window !== "undefined" ? window : globalThis);
