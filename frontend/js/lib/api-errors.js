/** 2711 Editor · API 错误格式化 */
(function (global) {
  function isHtmlJsonParseError(err) {
    const m =
      err && err.message
        ? String(err.message)
        : typeof err === "string"
          ? err
          : "";
    return (
      m.indexOf("Unexpected token '<'") !== -1 ||
      m.indexOf("is not valid JSON") !== -1 ||
      (m.indexOf("<html") !== -1 && m.indexOf("JSON") !== -1)
    );
  }

  function friendlyBackendMessage(err) {
    if (!isHtmlJsonParseError(err)) return "";
    return global.ApiConfig && global.ApiConfig.backendUnavailableMessage
      ? global.ApiConfig.backendUnavailableMessage
      : "故事解析服务暂时不可用。Render 冷启动约 30～60 秒，请稍后重试。";
  }

  function isPydanticValidationText(text) {
    return (
      typeof text === "string" &&
      (text.indexOf("validation error") !== -1 ||
        text.indexOf("ValidationError") !== -1 ||
        text.indexOf("string_type") !== -1 ||
        text.indexOf("Input should be") !== -1)
    );
  }

  function friendlyValidationMessage(text) {
    if (!isPydanticValidationText(text)) return "";
    if (text.indexOf("after_lines_next") !== -1) {
      return "故事结构解析失败（场景衔接字段异常），请重试。若多次失败可缩短文本。";
    }
    if (text.indexOf("StoryNode") !== -1) {
      return "故事节点数据格式异常，请重试生成。";
    }
    if (text.indexOf("ChoiceOption") !== -1) {
      return "分支选项数据格式异常，请重试生成。";
    }
    if (text.indexOf("DialogueLine") !== -1) {
      return "对白数据格式异常，请重试生成。";
    }
    return "服务器返回的数据格式有误，请重试生成。";
  }

  function formatApiDetail(detail) {
    if (detail == null || detail === "") return "";
    if (typeof detail === "string") {
      const friendly = friendlyValidationMessage(detail);
      return friendly || detail;
    }
    if (Array.isArray(detail)) {
      const raw = detail
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
      return friendlyValidationMessage(raw) || raw;
    }
    if (typeof detail === "object") {
      if (typeof detail.message === "string") {
        return friendlyValidationMessage(detail.message) || detail.message;
      }
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
    const backendMsg = friendlyBackendMessage(err);
    if (backendMsg) return backendMsg;
    if (typeof err === "string") {
      const backendFromStr = friendlyBackendMessage(err);
      if (backendFromStr) return backendFromStr;
      return friendlyValidationMessage(err) || err;
    }
    if (err instanceof Error) {
      const m = err.message;
      if (m && m !== "[object Object]") {
        return friendlyValidationMessage(m) || m;
      }
    }
    if (err.detail != null) {
      const d = formatApiDetail(err.detail);
      if (d) return d;
    }
    if (typeof err.message === "string" && err.message && err.message !== "[object Object]") {
      return friendlyValidationMessage(err.message) || err.message;
    }
    return fallback || "操作失败";
  }

  global.ApiErrors = {
    formatApiDetail: formatApiDetail,
    errorMessage: errorMessage,
    friendlyValidationMessage: friendlyValidationMessage,
    isHtmlJsonParseError: isHtmlJsonParseError,
    friendlyBackendMessage: friendlyBackendMessage,
  };
})(typeof window !== "undefined" ? window : globalThis);
