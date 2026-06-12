/** 2711 Editor · Server-Sent Events 消费 */
(function (global) {
  function dispatchBlock(part, onEvent) {
    if (!part.trim()) return;

    let event = "message";
    let data = "";
    for (const line of part.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data += (data ? "\n" : "") + line.slice(5).trim();
    }
    if (!data) return;

    if (
      global.ApiConfig &&
      global.ApiConfig.isHtmlBodyText &&
      global.ApiConfig.isHtmlBodyText(data)
    ) {
      const msg =
        (global.ApiConfig && global.ApiConfig.backendUnavailableMessage
          ? global.ApiConfig.backendUnavailableMessage()
          : "") ||
        (global.ApiConfig && global.ApiConfig.backendColdStartMessage
          ? global.ApiConfig.backendColdStartMessage()
          : "") ||
        (global.ApiConfig && global.ApiConfig.isLocalDev && global.ApiConfig.isLocalDev()
          ? global.ApiConfig.localBackendDownMessage
            ? global.ApiConfig.localBackendDownMessage()
            : "本地后端未响应，请运行 start.bat 或 restart-server.ps1"
          : "故事解析服务正在唤醒，请稍后重试。");
      throw new Error(msg);
    }
    let parsed;
    try {
      parsed = JSON.parse(data);
    } catch (err) {
      if (
        global.ApiErrors &&
        global.ApiErrors.isHtmlJsonParseError &&
        global.ApiErrors.isHtmlJsonParseError(err)
      ) {
        throw new Error(
          global.ApiErrors.friendlyBackendMessage(err) ||
            (global.ApiConfig && global.ApiConfig.isLocalDev && global.ApiConfig.isLocalDev()
              ? global.ApiConfig.localBackendDownMessage
                ? global.ApiConfig.localBackendDownMessage()
                : "本地后端未响应，请运行 start.bat 或 restart-server.ps1"
              : "故事解析服务返回了异常页面，请检查后端是否在线。")
        );
      }
      console.error("SSE JSON 解析失败", event, err);
      return;
    }
    onEvent(event, parsed);
  }

  async function consumeSSE(response, onEvent, signal, onActivity) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    const meta = {
      receivedDone: false,
      receivedError: false,
      lastEvent: null,
      eventCount: 0,
      keepaliveCount: 0,
    };

    function notifyActivity() {
      if (typeof onActivity === "function") onActivity();
    }

    while (true) {
      if (signal && signal.aborted) break;
      const { done, value } = await reader.read();
      if (value) {
        buffer += decoder.decode(value, { stream: true });
        notifyActivity();
      }
      if (done) {
        buffer += decoder.decode();
        break;
      }

      let sep;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const part = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        if (part.trim().startsWith(":")) {
          meta.keepaliveCount += 1;
          notifyActivity();
          continue;
        }
        dispatchBlock(part, function (event, data) {
          meta.eventCount += 1;
          meta.lastEvent = event;
          if (event === "done") meta.receivedDone = true;
          if (event === "error") meta.receivedError = true;
          notifyActivity();
          onEvent(event, data);
        });
      }
    }

    if (buffer.trim()) {
      if (buffer.trim().startsWith(":")) {
        meta.keepaliveCount += 1;
        notifyActivity();
      } else {
        dispatchBlock(buffer, function (event, data) {
          meta.eventCount += 1;
          meta.lastEvent = event;
          if (event === "done") meta.receivedDone = true;
          if (event === "error") meta.receivedError = true;
          notifyActivity();
          onEvent(event, data);
        });
      }
    }

    return meta;
  }

  global.SseClient = { consume: consumeSSE };
})(typeof window !== "undefined" ? window : globalThis);
