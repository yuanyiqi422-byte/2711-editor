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
      : "故事解析服务正在唤醒（Render 免费实例冷启动约 30～90 秒），正在自动重试连接…";
  }

  function backendUnavailableMessage() {
    return isLocalDevHost()
      ? localBackendDownMessage()
      : "故事解析服务暂时不可用。请稍后重试；若持续失败，请检查 Render 后端是否在线。";
  }

  function backendProxyMisconfigMessage() {
    return isLocalDevHost()
      ? "API 请求返回了网页而非接口数据。请通过 http://127.0.0.1:8010 访问，不要直接双击打开 frontend/index.html。"
      : "API 配置异常：/api 返回了网页而非接口数据。请确认 Cloudflare Pages 部署时已注入 API_BACKEND_URL 并重新部署前端。";
  }

  function streamIncompleteMessage() {
    return isLocalDevHost()
      ? "生成流意外结束，未收到完整游戏数据。常见原因：网络中断、AI 接口超时，或本地后端被中断。请刷新后重试；若仍失败，检查 backend/.env 中的 AI_API_KEY。"
      : "生成流意外结束，未收到完整游戏数据。常见原因：网络中断、AI 接口超时，或 Render 实例休眠。请刷新后重试；若仍失败，稍等 Render 唤醒后再试。";
  }

  var backendState = {
    ok: null,
    hasKey: null,
    version: "",
    checkedAt: 0,
    warming: false,
    permanentDown: false,
  };

  var BACKEND_READY_CACHE_MS = 30000;

  function isBackendAvailable() {
    if (backendState.permanentDown) return false;
    if (backendState.warming) return true;
    return backendState.ok !== false;
  }

  function isBackendWarming() {
    return backendState.warming === true;
  }

  function backendStatusMessage() {
    if (backendState.warming) {
      return "正在连接故事解析服务…";
    }
    if (backendState.ok === false && backendState.permanentDown) {
      return backendUnavailableMessage();
    }
    if (backendState.hasKey === false) {
      return "故事解析服务未配置 AI 密钥，暂时无法生成。";
    }
    return "";
  }

  function isTransientProbeFailure(err, res) {
    if (res && isTransientBackendStatus(res.status)) return true;
    if (!err) return false;
    if (err.cause === "timeout") return true;
    if (isRetryableFetchError(err)) return true;
    var m = err.message ? String(err.message) : "";
    if (
      m.indexOf("正在唤醒") !== -1 ||
      m.indexOf("冷启动") !== -1 ||
      m.indexOf("502") !== -1 ||
      m.indexOf("503") !== -1 ||
      m.indexOf("504") !== -1
    ) {
      return true;
    }
    return false;
  }

  function markBackendProbeSuccess(health) {
    backendState.ok = health.ok !== false;
    backendState.hasKey = health.has_key !== false;
    backendState.version = health.version || "";
    backendState.checkedAt = Date.now();
    backendState.warming = false;
    backendState.permanentDown = false;
  }

  function markBackendProbeFailure(err, opts) {
    backendState.checkedAt = Date.now();
    var soft = opts && opts.transientSoftFail;
    if (soft || isTransientProbeFailure(err)) {
      backendState.warming = true;
      backendState.permanentDown = false;
      return;
    }
    backendState.ok = false;
    backendState.hasKey = null;
    backendState.warming = false;
    backendState.permanentDown = true;
  }

  function sleepWithAbort(ms, signal) {
    return new Promise(function (resolve, reject) {
      if (signal && signal.aborted) {
        reject(signal.reason || new DOMException("Aborted", "AbortError"));
        return;
      }
      var timer = setTimeout(resolve, ms);
      if (!signal) return;
      function onAbort() {
        clearTimeout(timer);
        reject(signal.reason || new DOMException("Aborted", "AbortError"));
      }
      signal.addEventListener("abort", onAbort, { once: true });
    });
  }

  function defaultWakeProbeOptions() {
    if (isLocalDevHost()) {
      return { retries: 2, delayMs: 4000, timeoutMs: 15000 };
    }
    return { retries: 5, delayMs: 10000, timeoutMs: 90000 };
  }

  async function probeBackendHealth(options) {
    var opts = options || {};
    var fetchFn = opts.fetchFn || apiFetchWithRetry;
    var probeOpts = defaultWakeProbeOptions();
    try {
      var res = await fetchFn(
        "/api/health",
        undefined,
        {
          retries: opts.retries != null ? opts.retries : probeOpts.retries,
          delayMs: opts.delayMs != null ? opts.delayMs : probeOpts.delayMs,
          timeoutMs: opts.timeoutMs != null ? opts.timeoutMs : probeOpts.timeoutMs,
          retryNetwork: true,
        }
      );
      var health = await readJsonOrApiError(res, "无法连接故事解析服务");
      markBackendProbeSuccess(health);
      return health;
    } catch (err) {
      markBackendProbeFailure(err, opts);
      throw err;
    }
  }

  async function ensureBackendReady(options) {
    var opts = options || {};
    var onProgress = opts.onProgress || function () {};
    var signal = opts.signal;
    var isProd = !isLocalDevHost();

    if (
      backendState.ok === true &&
      backendState.hasKey !== false &&
      Date.now() - backendState.checkedAt < BACKEND_READY_CACHE_MS
    ) {
      return {
        ok: true,
        has_key: backendState.hasKey !== false,
        version: backendState.version,
      };
    }

    var maxAttempts = opts.attempts != null ? opts.attempts : isProd ? 8 : 4;
    var baseDelay = opts.delayMs != null ? opts.delayMs : isProd ? 8000 : 3000;
    var timeoutMs = opts.timeoutMs != null ? opts.timeoutMs : isProd ? 90000 : 20000;
    var lastErr = null;

    backendState.warming = true;

    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
      if (signal && signal.aborted) {
        backendState.warming = false;
        throw signal.reason || new DOMException("Aborted", "AbortError");
      }

      var progressMsg = isProd
        ? "正在连接故事解析服务…（" + attempt + "/" + maxAttempts + "）"
        : "正在检查本地后端…（" + attempt + "/" + maxAttempts + "）";
      if (attempt > 1 && isProd) {
        progressMsg += " · Render 实例唤醒中";
      }
      onProgress(progressMsg, attempt, maxAttempts);

      try {
        var health = await probeBackendHealth({
          retries: 0,
          delayMs: baseDelay,
          timeoutMs: timeoutMs,
          transientSoftFail: true,
          fetchFn: apiFetchWithRetry,
        });
        backendState.warming = false;
        return health;
      } catch (err) {
        lastErr = err;
        if (signal && signal.aborted) {
          backendState.warming = false;
          throw err;
        }
        if (attempt < maxAttempts && isTransientProbeFailure(err)) {
          await sleepWithAbort(Math.min(baseDelay * attempt, 20000), signal);
          continue;
        }
        backendState.warming = false;
        throw err;
      }
    }

    backendState.warming = false;
    throw lastErr || new Error(backendUnavailableMessage());
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

          const timeoutErr = new Error(
            isLocalDevHost()
              ? "连接超时，本地后端可能仍在启动"
              : "连接超时，故事解析服务可能仍在唤醒（Render 冷启动约 30～90 秒）"
          );

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

    isBackendAvailable: isBackendAvailable,

    isBackendWarming: isBackendWarming,

    backendStatusMessage: backendStatusMessage,

    probeBackendHealth: probeBackendHealth,

    ensureBackendReady: ensureBackendReady,

    isTransientProbeFailure: isTransientProbeFailure,

    getBackendState: function () {
      return Object.assign({}, backendState);
    },

  };

  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", function () {
      probeBackendHealth({ transientSoftFail: true }).catch(function () {});
    });
  }

})(typeof window !== "undefined" ? window : globalThis);
