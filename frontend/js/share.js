/** 分享链接 — Web 裂变传播（历史包走 API；精选 Demo 走静态深链） */
const ShareWorld = (function () {
  function playUrl(token) {
    const base = window.location.origin + window.location.pathname;
    return base + "?play=" + encodeURIComponent(token);
  }

  function featuredPlayUrl() {
    const base = window.location.origin + window.location.pathname;
    return base + "?featured=1";
  }

  function createFeaturedShareLink() {
    return {
      token: "featured",
      url: featuredPlayUrl(),
      kind: "featured",
    };
  }

  async function createShareLink(entryId) {
    if (!entryId || entryId === "featured" || entryId === "demo") {
      return createFeaturedShareLink();
    }
    if (!/^[a-f0-9]{12}$/i.test(String(entryId))) {
      throw new Error("当前世界尚未保存到历史记录，无法生成服务端分享链接。请先完成一次创作并保存。");
    }
    const res = await fetch("/api/history/" + encodeURIComponent(entryId) + "/share", {
      method: "POST",
    });
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) {
      const detail = typeof data.detail === "string"
        ? data.detail
        : (Array.isArray(data.detail) ? data.detail.map(function (d) { return d.msg || d; }).join("; ") : "");
      if (res.status === 404) {
        throw new Error(detail || "历史记录不存在，无法分享。请重新生成并保存后再试。");
      }
      if (res.status === 400) {
        throw new Error(detail || "该记录尚未生成可分享的游戏。");
      }
      throw new Error(detail || ("生成分享链接失败（HTTP " + res.status + "）"));
    }
    if (!data.share_token) {
      throw new Error("服务器未返回分享令牌，请稍后重试。");
    }
    return {
      token: data.share_token,
      url: playUrl(data.share_token),
      kind: "history",
    };
  }

  async function loadSharedGame(token) {
    const res = await fetch("/api/share/" + encodeURIComponent(token));
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "";
      throw new Error(detail || "分享链接无效或已过期");
    }
    return data;
  }

  function getPlayTokenFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get("play") || params.get("share") || "";
  }

  function getFeaturedFlagFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const v = params.get("featured") || params.get("demo");
    if (!v) return false;
    const lower = String(v).toLowerCase();
    return lower === "1" || lower === "true" || lower === "yes" || lower === "featured";
  }

  function clearPlayParam() {
    const url = new URL(window.location.href);
    url.searchParams.delete("play");
    url.searchParams.delete("share");
    url.searchParams.delete("featured");
    url.searchParams.delete("demo");
    window.history.replaceState({}, "", url.pathname + url.search + url.hash);
  }

  async function copyToClipboard(text) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (_) {
      /* fall through */
    }
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return !!ok;
    } catch (_) {
      return false;
    }
  }

  return {
    playUrl: playUrl,
    featuredPlayUrl: featuredPlayUrl,
    createFeaturedShareLink: createFeaturedShareLink,
    createShareLink: createShareLink,
    loadSharedGame: loadSharedGame,
    getPlayTokenFromUrl: getPlayTokenFromUrl,
    getFeaturedFlagFromUrl: getFeaturedFlagFromUrl,
    clearPlayParam: clearPlayParam,
    copyToClipboard: copyToClipboard,
  };
})();
