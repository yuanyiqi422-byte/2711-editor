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

  function isNetworkFetchError(err) {
    const m =
      err && err.message
        ? String(err.message)
        : typeof err === "string"
          ? err
          : "";
    const lower = m.toLowerCase();
    return (
      lower === "failed to fetch" ||
      lower === "network error" ||
      lower.indexOf("network error") !== -1 ||
      lower.indexOf("networkerror") !== -1 ||
      lower.indexOf("network request failed") !== -1 ||
      lower.indexOf("load failed") !== -1 ||
      (err && err.name === "TypeError" && lower.indexOf("fetch") !== -1)
    );
  }

  function isLocalDevFallback() {
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

  function isLocalDev() {
    if (global.ApiConfig && global.ApiConfig.isLocalDev) return global.ApiConfig.isLocalDev();
    return isLocalDevFallback();
  }

  function localBackendDownMessage() {
    if (global.ApiConfig && global.ApiConfig.localBackendDownMessage) {
      return global.ApiConfig.localBackendDownMessage();
    }
    return "本地后端未响应，请运行 start.bat 或 restart-server.ps1";
  }

  function isFileProtocolPage() {
    return typeof global.location !== "undefined" && global.location.protocol === "file:";
  }

  function friendlyNetworkMessage() {
    if (isFileProtocolPage()) {
      return global.ApiConfig && global.ApiConfig.backendProxyMisconfigMessage
        ? global.ApiConfig.backendProxyMisconfigMessage()
        : "API 请求返回了网页而非接口数据。请通过 http://127.0.0.1:8010 访问，不要直接双击打开 frontend/index.html。";
    }
    if (isLocalDev()) return localBackendDownMessage();
    if (global.ApiConfig && global.ApiConfig.backendColdStartMessage && !global.ApiConfig.isLocalDev()) {
      return (
        global.ApiConfig.backendColdStartMessage() +
        " 若刚打开页面，请等待约 1 分钟后再次点击「开始游戏」。"
      );
    }
    return global.ApiConfig && global.ApiConfig.backendUnavailableMessage
      ? global.ApiConfig.backendUnavailableMessage()
      : "无法连接故事解析服务。请检查网络后刷新页面重试；Render 免费实例冷启动约需 30～60 秒，稍等后再点「开始游戏」。";
  }

  function friendlyBackendMessage(err) {
    if (isNetworkFetchError(err)) return friendlyNetworkMessage();
    if (!isHtmlJsonParseError(err)) return "";
    if (isLocalDev()) return localBackendDownMessage();
    return global.ApiConfig && global.ApiConfig.backendUnavailableMessage
      ? global.ApiConfig.backendUnavailableMessage()
      : "故事解析服务暂时不可用。请稍后重试；若持续失败，请检查 Render 后端是否在线。";
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

  const CREATE_PHASE_LABELS = {
    read: "读取原文",
    weave: "编织剧情",
    branch: "规划命运分支",
    scene: "生成场景对白",
    done: "收尾",
  };

  function isTimeoutError(err, message) {
    const m =
      message ||
      (err && err.message ? String(err.message) : typeof err === "string" ? err : "");
    if (!m) return false;
    return (
      /timeout/i.test(m) ||
      m.indexOf("连接中断") !== -1 ||
      m.indexOf("超时") !== -1 ||
      m.indexOf("timed out") !== -1
    );
  }

  function isProviderSwitchNoise(text) {
    if (!text || typeof text !== "string") return false;
    return (
      text.indexOf("赠送 API 已用尽") !== -1 ||
      text.indexOf("已自动切换至 DeepSeek") !== -1 ||
      text.indexOf("provider_switch") !== -1
    );
  }

  function classifyLlmError(text, context) {
    if (!text || typeof text !== "string") return "";
    if (isProviderSwitchNoise(text)) return "";
    if (text.indexOf("未配置 AI_API_KEY") !== -1 || text.indexOf("AI_API_KEY") !== -1) {
      return isLocalDev()
        ? "AI 密钥未配置。请复制 backend/.env.example 为 backend/.env，填入 AI_API_KEY 后重启服务。"
        : "AI 密钥未配置。请在 Render 环境变量中设置 AI_API_KEY 后重新部署后端。";
    }
    if (text.indexOf("HTTP 401") !== -1 || text.indexOf("HTTP 403") !== -1) {
      return isLocalDev()
        ? "AI 接口鉴权失败（密钥无效或已过期）。请检查 backend/.env 中的 AI_API_KEY。"
        : "AI 接口鉴权失败（密钥无效或已过期）。请检查 Render 上的 AI_API_KEY 是否正确。";
    }
    if (text.indexOf("HTTP 404") !== -1 && text.indexOf("model") !== -1) {
      return isLocalDev()
        ? "AI 模型名称无效。请检查 backend/.env 中的 AI_MODEL 是否与接口提供商一致。"
        : "AI 模型名称无效。请检查 Render 上的 AI_MODEL 是否与接口提供商一致。";
    }
    if (text.indexOf("HTTP 429") !== -1) {
      return "AI 接口请求过于频繁，请稍后再试。";
    }
    if (text.indexOf("HTTP 402") !== -1 || text.indexOf("余额不足") !== -1) {
      return isLocalDev()
        ? "AI 接口余额不足。请检查 backend/.env 中的 API 密钥与余额。"
        : "AI 接口余额不足。请检查 API 密钥与账户余额。";
    }
    if (text.indexOf("HTTP 5") !== -1 || text.indexOf("AI 接口请求失败") !== -1) {
      return text;
    }
    if (isTimeoutError(null, text)) {
      const phaseKey = context && context.phase;
      const phaseLabel = phaseKey ? CREATE_PHASE_LABELS[phaseKey] || phaseKey : "";
      if (phaseLabel) {
        return (
          phaseLabel +
          "阶段 AI 响应超时。长故事可能需要数分钟，请点击「重新生成」重试；若多次失败可缩短文本。"
        );
      }
      return "AI 接口响应超时。长故事可能需要数分钟，请点击重试；若持续失败可缩短文本。";
    }
    if (
      text.indexOf("JSON") !== -1 ||
      text.indexOf("模型返回") !== -1 ||
      text.indexOf("输出被截断") !== -1 ||
      text.indexOf("输出不完整") !== -1
    ) {
      const phaseKey = context && context.phase;
      const phaseLabel = phaseKey ? CREATE_PHASE_LABELS[phaseKey] || phaseKey : "";
      const prefix = phaseLabel ? phaseLabel + "阶段：" : "";
      if (
        text.indexOf("缩短") !== -1 ||
        text.indexOf("输出不完整") !== -1 ||
        text.indexOf("输出被截断") !== -1 ||
        text.indexOf("JSON 不完整") !== -1
      ) {
        return (
          prefix +
          "AI 输出不完整，服务端会自动重试或拆分批次。请点击「重新生成」重试，无需缩短文本。"
        );
      }
      if (phaseLabel && text.indexOf("阶段") === -1 && text.indexOf(phaseLabel) === -1) {
        return prefix + text;
      }
      return text;
    }
    return "";
  }

  function errorMessage(err, fallback, context) {
    if (err == null) return fallback || "操作失败";
    if (typeof err === "string" && isProviderSwitchNoise(err)) {
      return fallback || "";
    }
    const backendMsg = friendlyBackendMessage(err);
    if (backendMsg) return backendMsg;
    if (typeof err === "string") {
      const backendFromStr = friendlyBackendMessage(err);
      if (backendFromStr) return backendFromStr;
      const llmFromStr = classifyLlmError(err, context);
      if (llmFromStr) return llmFromStr;
      return friendlyValidationMessage(err) || err;
    }
    if (err instanceof Error) {
      const m = err.message;
      if (m && m !== "[object Object]") {
        if (isProviderSwitchNoise(m)) return fallback || "";
        const llm = classifyLlmError(m, context);
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
    isProviderSwitchNoise: isProviderSwitchNoise,
    friendlyValidationMessage: friendlyValidationMessage,
    isHtmlJsonParseError: isHtmlJsonParseError,
    isNetworkFetchError: isNetworkFetchError,
    friendlyBackendMessage: friendlyBackendMessage,
    isTimeoutError: isTimeoutError,
    CREATE_PHASE_LABELS: CREATE_PHASE_LABELS,
  };
})(typeof window !== "undefined" ? window : globalThis);
