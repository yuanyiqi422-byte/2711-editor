/** 2711 Editor · API 错误格式化 */
(function (global) {
  function formatApiDetail(detail) {
    if (detail == null || detail === "") return "";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map(function (item) {
          if (typeof item === "string") return item;
          if (!item || typeof item !== "object") return String(item);
          const loc = Array.isArray(item.loc)
            ? item.loc.filter(function (x) { return x !== "body"; }).join(".")
            : "";
          const msg = item.msg || item.message || "";
          return loc ? loc + "：" + msg : msg || JSON.stringify(item);
        })
        .filter(Boolean)
        .join("；");
    }
    if (typeof detail === "object") {
      if (typeof detail.message === "string") return detail.message;
      if (detail.detail != null) return formatApiDetail(detail.detail);
      try {
        return JSON.stringify(detail);
      } catch {
        return "请求失败";
      }
    }
    return String(detail);
  }

  function errorMessage(err, fallback) {
    if (err == null) return fallback || "操作失败";
    if (typeof err === "string") return err;
    if (err instanceof Error) {
      const m = err.message;
      if (m && m !== "[object Object]") return m;
    }
    if (err.detail != null) {
      const d = formatApiDetail(err.detail);
      if (d) return d;
    }
    if (typeof err.message === "string" && err.message && err.message !== "[object Object]") {
      return err.message;
    }
    return fallback || "操作失败";
  }

  global.ApiErrors = { formatApiDetail: formatApiDetail, errorMessage: errorMessage };
})(typeof window !== "undefined" ? window : globalThis);
