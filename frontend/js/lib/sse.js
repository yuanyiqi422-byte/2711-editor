/** 2711 Editor · Server-Sent Events 消费 */
(function (global) {
  async function consumeSSE(response, onEvent, signal) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      if (signal && signal.aborted) break;
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sep;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const part = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        if (!part.trim()) continue;

        let event = "message";
        let data = "";
        for (const line of part.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data += (data ? "\n" : "") + line.slice(5).trim();
        }
        if (data) {
          try {
            onEvent(event, JSON.parse(data));
          } catch (err) {
            console.error("SSE 解析失败", event, err);
          }
        }
      }
    }
  }

  global.SseClient = { consume: consumeSSE };
})(typeof window !== "undefined" ? window : globalThis);
