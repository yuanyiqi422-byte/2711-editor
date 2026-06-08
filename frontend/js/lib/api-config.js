/** 2711 Editor · API base URL + fetch helper (production / Netlify proxy) */

(function (global) {

  var BACKEND_COLD_START_MSG =
    "故事解析服务正在唤醒（Render 免费实例冷启动约 30～60 秒）。请稍候再试，或刷新页面。";

  var BACKEND_PROXY_MISCONFIG_MSG =
    "API 代理未生效：/api 返回了网页而非接口数据。请确认 Netlify 已设置 API_BACKEND_URL 并重新部署前端。";

  var BACKEND_UNAVAILABLE_MSG =
    "故事解析服务暂时不可用。请稍后重试；若持续失败，请检查 Render 后端是否在线。";



  function normalizeBase(base) {

    if (!base) return "";

    return String(base).replace(/\/+$/, "");

  }



  function getBase() {

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

      return new Error(BACKEND_COLD_START_MSG);

    }

    if (res && res.ok) {

      return new Error(BACKEND_PROXY_MISCONFIG_MSG);

    }

    return new Error(BACKEND_UNAVAILABLE_MSG);

  }



  async function apiFetchWithRetry(path, init, options) {

    const opts = options || {};

    const retries = opts.retries != null ? opts.retries : 2;

    const delayMs = opts.delayMs != null ? opts.delayMs : 12000;

    let lastRes = null;

    for (let attempt = 0; attempt <= retries; attempt++) {

      const res = await apiFetch(path, init);

      lastRes = res;

      const transient = isTransientBackendStatus(res.status);

      const html = isLikelyHtmlResponse(res);

      if (attempt < retries && (transient || html)) {

        await sleep(delayMs);

        continue;

      }

      return res;

    }

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

    backendUnavailableMessage: BACKEND_UNAVAILABLE_MSG,

    backendColdStartMessage: BACKEND_COLD_START_MSG,

    backendProxyMisconfigMessage: BACKEND_PROXY_MISCONFIG_MSG,

  };

})(typeof window !== "undefined" ? window : globalThis);
