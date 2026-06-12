/** 分享链接 — Web 裂变传播 */
const ShareWorld = (function () {
  function playUrl(token) {
    const base = window.location.origin + window.location.pathname;
    return base + "?play=" + encodeURIComponent(token);
  }

  async function createShareLink(entryId) {
    const res = await fetch("/api/history/" + encodeURIComponent(entryId) + "/share", {
      method: "POST",
    });
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.detail || "生成分享链接失败");
    return {
      token: data.share_token,
      url: playUrl(data.share_token),
    };
  }

  async function loadSharedGame(token) {
    const res = await fetch("/api/share/" + encodeURIComponent(token));
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.detail || "分享链接无效或已过期");
    return data;
  }

  function getPlayTokenFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get("play") || params.get("share") || "";
  }

  function clearPlayParam() {
    const url = new URL(window.location.href);
    url.searchParams.delete("play");
    url.searchParams.delete("share");
    window.history.replaceState({}, "", url.pathname + url.search + url.hash);
  }

  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    }
  }

  return {
    playUrl: playUrl,
    createShareLink: createShareLink,
    loadSharedGame: loadSharedGame,
    getPlayTokenFromUrl: getPlayTokenFromUrl,
    clearPlayParam: clearPlayParam,
    copyToClipboard: copyToClipboard,
  };
})();
