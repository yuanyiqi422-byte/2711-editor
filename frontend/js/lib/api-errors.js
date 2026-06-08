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

  function classifyLlmError(text) {
    if (!text || typeof text !== "string") return "";
    if (text.indexOf("未配置 AI_API_KEY") !== -1 || text.indexOf("AI_API_KEY") !== -1) {
      return "AI 密钥未配置。请在 Render 环境变量中设置 AI_API_KEY 后重新部署后端。";
    }
    if (text.indexOf("HTTP 401") !== -1 || text.indexOf("HTTP 403") !== -1) {
      return "AI 接口鉴权失败（密钥无效或已过期）。请检查 Render 上的 AI_API_KEY 是否正确。";
    }
    if (text.indexOf("HTTP 404") !== -1 && text.indexOf("model") !== -1) {
      return "AI 模型名称无效。请检查 Render 上的 AI_MODEL 是否与接口提供商一致。";
    }
    if (text.indexOf("HTTP 429") !== -1) {
      return "AI 接口请求过于频繁，请稍后再试。";
    }
    if (text.indexOf("HTTP 5") !== -1 || text.indexOf("AI 接口请求失败") !== -1) {
      return text;
    }
    if (text.indexOf("连接中断") !== -1 || text.indexOf("Timeout") !== -1 || text.indexOf("timeout") !== -1) {
      return "AI 接口响应超时。长故事可能需要数分钟，请稍后重试；若持续失败可缩短文本。";
    }
    if (text.indexOf("JSON") !== -1 || text.indexOf("模型返回") !== -1) {
      return text;
    }
    return "";
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
        const llm = classifyLlmError(m);
        if (llm) return llm;
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
    classifyLlmError: classifyLlmError,
    friendlyValidationMessage: friendlyValidationMessage,
    isHtmlJsonParseError: isHtmlJsonParseError,
    friendlyBackendMessage: friendlyBackendMessage,
  };
})(typeof window !== "undefined" ? window : globalThis);
