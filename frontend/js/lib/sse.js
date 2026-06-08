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
        global.ApiConfig.backendUnavailableMessage ||
        (global.ApiConfig && global.ApiConfig.backendColdStartMessage) ||
        "故事解析服务正在唤醒，请稍后重试。";
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
            "故事解析服务返回了异常页面，请检查后端是否在线。"
        );
      }
      console.error("SSE JSON 解析失败", event, err);
      return;
    }
    onEvent(event, parsed);
  }

  async function consumeSSE(response, onEvent, signal) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      if (signal && signal.aborted) break;
      const { done, value } = await reader.read();
      if (value) buffer += decoder.decode(value, { stream: true });
      if (done) {
        buffer += decoder.decode();
        break;
      }

      let sep;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const part = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        dispatchBlock(part, onEvent);
      }
    }

    if (buffer.trim()) {
      dispatchBlock(buffer, onEvent);
    }
  }

  global.SseClient = { consume: consumeSSE };
})(typeof window !== "undefined" ? window : globalThis);
