/** 2711 Editor · API base URL + fetch helper (production / Netlify proxy) */

(function (global) {

  function isLocalDevHost() {
    if (typeof global.location === "undefined") return false;
    var loc = global.location;
    var h = loc.hostname;
    if (h === "localhost" || h === "127.0.0.1" || h === "[::1]" || h === "::1") return true;
    if (loc.protocol === "file:") return true;
    var port = loc.port || (loc.protocol === "https:" ? "443" : "80");
    if (port === "8010") return true;
    if (h && h.slice(-6) === ".local") return true;
    return false;
  }

  function localBackendDownMessage() {
    return "本地后端未响应，请运行 start.bat 或 restart-server.ps1";
  }

  function backendColdStartMessage() {
    return isLocalDevHost()
      ? localBackendDownMessage()
      : "故事解析服务正在唤醒（Render 免费实例冷启动约 30～60 秒）。请稍候再点「开始游戏」重试。";
  }

  function backendUnavailableMessage() {
    return isLocalDevHost()
      ? localBackendDownMessage()
      : "故事解析服务暂时不可用。请稍后重试；若持续失败，请检查 Render 后端是否在线。";
  }

  function backendProxyMisconfigMessage() {
    return isLocalDevHost()
      ? "API 请求返回了网页而非接口数据。请通过 http://127.0.0.1:8010 访问，不要直接双击打开 frontend/index.html。"
      : "API 代理未生效：/api 返回了网页而非接口数据。请确认 Netlify 已设置 API_BACKEND_URL 并重新部署前端。";
  }

  function streamIncompleteMessage() {
    return isLocalDevHost()
      ? "生成流意外结束，未收到完整游戏数据。常见原因：网络中断、AI 接口超时，或本地后端被中断。请刷新后重试；若仍失败，检查 backend/.env 中的 AI_API_KEY。"
      : "生成流意外结束，未收到完整游戏数据。常见原因：网络中断、Netlify 代理截断长连接，或 AI 接口超时。请刷新后重试；若仍失败，稍等 Render 唤醒后再试。";
  }



  function normalizeBase(base) {

    if (!base) return "";

    return String(base).replace(/\/+$/, "");

  }



  var LOCAL_BACKEND_BASE = "http://127.0.0.1:8010";

  function localBackendBase() {
    return LOCAL_BACKEND_BASE;
  }

  function needsLocalBackendBase() {
    if (!isLocalDevHost()) return false;
    if (typeof global.location === "undefined") return false;
    var loc = global.location;
    if (loc.protocol === "file:") return true;
    var port = loc.port || (loc.protocol === "https:" ? "443" : "80");
    return port !== "8010";
  }

  function getBase() {
    // Local dev: same-origin on :8010; otherwise talk to the local FastAPI server.
    if (needsLocalBackendBase()) return normalizeBase(localBackendBase());
    if (isLocalDevHost()) return "";
    return normalizeBase(global.__API_BASE__ || "");
  }



  function apiUrl(path) {

    const p = path && path.charAt(0) === "/" ? path : "/" + (path || "");

    const base = getBase();

    return base ? base + p : p;

  }



  function apiFetch(path, init) {

    return global.fetch(apiUrl(path), init);

  }



  function sleep(ms) {

    return new Promise(function (resolve) { setTimeout(resolve, ms); });

  }



  function isTransientBackendStatus(status) {

    return status === 502 || status === 503 || status === 504;

  }



  function isLikelyHtmlResponse(res) {

    if (!res) return false;

    const ct = ((res.headers && res.headers.get("content-type")) || "").toLowerCase();

    return ct.indexOf("text/html") !== -1 || ct.indexOf("application/xhtml") !== -1;

  }



  function isHtmlBodyText(text) {

    if (!text) return false;

    const trimmed = String(text).trim();

    return trimmed.charAt(0) === "<" && trimmed.indexOf("<html") !== -1;

  }



  function backendUnavailableError(res) {

    if (res && isTransientBackendStatus(res.status)) {

      return new Error(backendColdStartMessage());

    }

    if (res && res.ok) {

      return new Error(backendProxyMisconfigMessage());

    }

    return new Error(backendUnavailableMessage());

  }



  function isRetryableFetchError(err) {

    if (!err) return false;

    if (

      global.ApiErrors &&

      global.ApiErrors.isNetworkFetchError &&

      global.ApiErrors.isNetworkFetchError(err)

    ) {

      return true;

    }

    const m = err.message ? String(err.message) : String(err);

    const lower = m.toLowerCase();

    return (

      lower === "failed to fetch" ||

      lower === "network error" ||

      lower.indexOf("network error") !== -1 ||

      lower.indexOf("networkerror") !== -1 ||

      lower.indexOf("network request failed") !== -1 ||

      lower.indexOf("load failed") !== -1 ||

      (err.name === "TypeError" && lower.indexOf("fetch") !== -1)

    );

  }



  function attachFetchTimeout(userSignal, timeoutMs) {

    if (!timeoutMs || timeoutMs <= 0) return null;

    const controller = new AbortController();

    const state = { timedOut: false };

    const timer = setTimeout(function () {

      state.timedOut = true;

      controller.abort();

    }, timeoutMs);

    function cleanup() {

      clearTimeout(timer);

    }

    if (userSignal) {

      if (userSignal.aborted) {

        cleanup();

        controller.abort(userSignal.reason);

        return { signal: controller.signal, cleanup: cleanup, state: state };

      }

      userSignal.addEventListener("abort", function () {

        cleanup();

        controller.abort(userSignal.reason);

      }, { once: true });

    }

    controller.signal.addEventListener("abort", cleanup, { once: true });

    return { signal: controller.signal, cleanup: cleanup, state: state };

  }



  async function apiFetchWithRetry(path, init, options) {

    const opts = options || {};

    const retries = opts.retries != null ? opts.retries : 2;

    const delayMs = opts.delayMs != null ? opts.delayMs : 12000;

    const timeoutMs = opts.timeoutMs != null ? opts.timeoutMs : 0;

    const retryNetwork = opts.retryNetwork != null ? opts.retryNetwork : true;

    let lastRes = null;

    let lastErr = null;

    for (let attempt = 0; attempt <= retries; attempt++) {

      const timeoutCtx = attachFetchTimeout(init && init.signal, timeoutMs);

      const fetchInit = init ? Object.assign({}, init) : {};

      if (timeoutCtx) fetchInit.signal = timeoutCtx.signal;

      try {

        const res = await apiFetch(path, fetchInit);

        if (timeoutCtx) timeoutCtx.cleanup();

        lastRes = res;

        const transient = isTransientBackendStatus(res.status);

        const html = isLikelyHtmlResponse(res);

        if (attempt < retries && (transient || html)) {

          await sleep(delayMs);

          continue;

        }

        return res;

      } catch (err) {

        if (timeoutCtx) timeoutCtx.cleanup();

        lastErr = err;

        const timedOut = timeoutCtx && timeoutCtx.state.timedOut;

        const network = retryNetwork && isRetryableFetchError(err);

        if (attempt < retries && (network || timedOut)) {

          await sleep(delayMs);

          continue;

        }

        if (timedOut) {

          const timeoutErr = new Error("连接超时，本地后端可能仍在启动");

          timeoutErr.cause = "timeout";

          throw timeoutErr;

        }

        throw err;

      }

    }

    if (lastErr) throw lastErr;

    return lastRes;

  }



  async function readJsonOrApiError(res, fallback) {

    if (isLikelyHtmlResponse(res)) {

      throw backendUnavailableError(res);

    }

    const text = await res.text();

    if (isHtmlBodyText(text)) {

      throw backendUnavailableError(res);

    }

    let data = {};

    if (text) {

      try {

        data = JSON.parse(text);

      } catch (err) {

        if (

          global.ApiErrors &&

          global.ApiErrors.isHtmlJsonParseError &&

          global.ApiErrors.isHtmlJsonParseError(err)

        ) {

          throw backendUnavailableError(res);

        }

        throw new Error(fallback || "服务器返回了无法识别的数据，请稍后重试。");

      }

    }

    if (!res.ok) {

      const detail =

        global.ApiErrors && global.ApiErrors.formatApiDetail

          ? global.ApiErrors.formatApiDetail(data.detail)

          : data.detail;

      throw new Error(detail || fallback || "请求失败");

    }

    return data;

  }



  async function ensureSseResponse(res, fallback) {

    if (!res || !res.ok) {

      return readJsonOrApiError(res, fallback || "生成请求失败");

    }

    const ct = ((res.headers && res.headers.get("content-type")) || "").toLowerCase();

    if (ct.indexOf("text/event-stream") !== -1) return;

    if (isLikelyHtmlResponse(res)) {

      throw backendUnavailableError(res);

    }

    const text = await res.clone().text();

    if (isHtmlBodyText(text)) {

      throw backendUnavailableError(res);

    }

    if (text) {

      try {

        const data = JSON.parse(text);

        const detail =

          global.ApiErrors && global.ApiErrors.formatApiDetail

            ? global.ApiErrors.formatApiDetail(data.detail)

            : data.detail;

        throw new Error(detail || fallback || "生成请求失败");

      } catch (err) {

        if (err instanceof Error && err.message !== fallback) throw err;

        throw new Error(fallback || "生成流响应异常，请稍后重试。");

      }

    }

    throw new Error(fallback || "生成流响应为空，请稍后重试。");

  }



  var nativeFetch = global.fetch && global.fetch.bind(global);

  if (nativeFetch) {

    global.fetch = function patchedFetch(input, init) {

      if (typeof input === "string" && input.indexOf("/api/") === 0) {

        input = apiUrl(input);

      }

      return nativeFetch(input, init);

    };

  }



  global.ApiConfig = {

    getBase: getBase,

    apiUrl: apiUrl,

    apiFetch: apiFetch,

    apiFetchWithRetry: apiFetchWithRetry,

    isLikelyHtmlResponse: isLikelyHtmlResponse,

    isHtmlBodyText: isHtmlBodyText,

    isTransientBackendStatus: isTransientBackendStatus,

    readJsonOrApiError: readJsonOrApiError,

    ensureSseResponse: ensureSseResponse,

    isLocalDev: isLocalDevHost,

    localBackendDownMessage: localBackendDownMessage,

    localBackendBase: localBackendBase,

    needsLocalBackendBase: needsLocalBackendBase,

    backendUnavailableMessage: backendUnavailableMessage,

    backendColdStartMessage: backendColdStartMessage,

    backendProxyMisconfigMessage: backendProxyMisconfigMessage,

    streamIncompleteMessage: streamIncompleteMessage,

  };

})(typeof window !== "undefined" ? window : globalThis);
