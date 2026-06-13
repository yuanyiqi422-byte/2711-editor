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

    const uploadLimits = options.uploadLimitsEl;

    const clearBtn = options.clearBtnEl;

    const workshopOnboard = options.onboardEl;

    const onTextChange = options.onTextChange || function () {};

    const onHistorySave = options.onHistorySave || function () {};

    const getSelectedStyle = options.getSelectedStyle || function () { return "urban_romance"; };

    const onError = options.onError || function () {};



    let isUploading = false;



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

      charCount.className = "workbench__hint workshop__hint";

      charCount.textContent = "当前字数：" + n.toLocaleString("en-US") + " 字";

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

      isUploading = true;

      if (uploadLabel) uploadLabel.classList.add("is-busy");

      setUploadProgress(true, null);

      setUploadStatus("正在解析「" + file.name + "」… 大文件可能需要 1～3 分钟。", "loading");

      onError("");



      try {

        const form = new FormData();

        form.append("file", file);

        const controller = new AbortController();

        const timeoutMs = file.size > 50 * 1024 * 1024

          ? 600000

          : file.size > 5 * 1024 * 1024

            ? 300000

            : 90000;

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

              "上传解析超时（" + Math.round(timeoutMs / 60000) + " 分钟）。请稍后重试。"

            );

          }

          throw fetchErr;

        } finally {

          clearTimeout(timer);

        }

        const data = global.ApiConfig && global.ApiConfig.readJsonOrApiError

          ? await global.ApiConfig.readJsonOrApiError(res, "上传解析失败")

          : await (async function () {

              const parsed = await res.json().catch(function () { return {}; });

              if (!res.ok) throw new Error(formatApiDetail(parsed.detail) || "上传解析失败");

              return parsed;

            })();



        input.value = data.text || "";

        updateCount();



        const fullChars = data.char_count || (data.text || "").length;

        let msg = "已载入「" + (data.filename || file.name) + "」· " + (data.format || "") +

          " · 全文 " + fullChars.toLocaleString() + " 字";

        if (data.total_pages != null && data.pages_processed != null) {

          msg += " · PDF 共 " + data.total_pages + " 页";

        } else if (data.pages_processed) {

          msg += " · 已处理 " + data.pages_processed + " 页";

        }

        if (data.used_ocr) msg += " · 扫描版 OCR";

        if (data.warnings && data.warnings.length) {

          msg += "\n" + data.warnings.join("\n");

        }

        const hasWarn = !!(data.warnings && data.warnings.length);

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



        onError("");

      } catch (err) {

        setUploadStatus(errorMessage(err, "解析失败"), "error");

      } finally {

        isUploading = false;

        setUploadProgress(false);

        if (uploadLabel) uploadLabel.classList.remove("is-busy");

        fileInput.value = "";

      }

    }



    function clearText() {

      input.value = "";

      updateCount();

      setUploadStatus("");

      onError("");

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



      if (clearBtn) {

        clearBtn.addEventListener("click", function () {

          clearText();

        });

      }

    }



    function loadHealthFormats() {

      fetch("/api/health")

        .then(function (r) {

          if (global.ApiConfig && global.ApiConfig.readJsonOrApiError) {

            return global.ApiConfig.readJsonOrApiError(r, "无法读取服务状态");

          }

          return r.json();

        })

        .catch(function () { return null; })

        .then(function (h) {

          if (!h || !h.upload) return;

          if (uploadFormats && h.upload.formats && h.upload.formats.length) {

            uploadFormats.textContent = "支持 " + h.upload.formats.join("、");

          }

          if (uploadLimits) {

            uploadLimits.textContent = "不限制字数、文件大小与页数";

          }

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

      getMaxCreateChars: function () { return 0; },

      getLlmEffectiveChars: function () { return 0; },

    };

  }



  global.EditorInput = { create: createEditorInput };

})(typeof window !== "undefined" ? window : globalThis);

