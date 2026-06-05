/** 2711编辑器 · 本地历史记录（服务端持久化） */
const HistoryPanel = (function () {
  const STYLE_NAMES = {
    xianxia: "古风仙侠",
    urban_romance: "都市言情",
    mystery: "悬疑推理",
    campus: "校园青春",
  };

  let listEl = null;
  let emptyEl = null;
  let loadingEl = null;
  let getStyle = function () { return "urban_romance"; };
  let setStyle = function () {};
  let setText = function () {};
  let onPlay = function () {};
  let onStatus = function () {};
  let onEntryLoaded = function () {};

  function formatDate(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleString("zh-CN", {
        month: "numeric",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  }

  function setPanelStatus(msg, type) {
    if (onStatus) onStatus(msg, type);
  }

  async function refreshList() {
    if (!listEl) return;
    if (loadingEl) loadingEl.hidden = false;
    if (emptyEl) emptyEl.hidden = true;
    try {
      const res = await fetch("/api/history");
      const items = await res.json();
      if (!res.ok) throw new Error(formatDetail(items.detail) || "加载历史失败");
      renderList(Array.isArray(items) ? items : []);
      if (!items.length) {
        const health = await fetch("/api/health").then(function (r) { return r.json(); }).catch(function () { return {}; });
        if (health.history_count > 0) {
          setPanelStatus("历史记录加载异常，请刷新页面重试", "error");
        }
      }
    } catch (err) {
      renderList([]);
      setPanelStatus(err.message || "加载历史失败", "error");
      console.warn("history list", err);
    } finally {
      if (loadingEl) loadingEl.hidden = true;
    }
  }

  function renderList(items) {
    if (!listEl || !emptyEl) return;
    listEl.innerHTML = "";
    if (!items.length) {
      emptyEl.hidden = false;
      return;
    }
    emptyEl.hidden = true;
    items.forEach(function (item) {
      const li = document.createElement("li");
      li.className = "history-item";
      const styleLabel = STYLE_NAMES[item.style] || item.style || "";
      const sub = [
        formatDate(item.updated_at),
        (item.char_count || 0).toLocaleString() + " 字",
        styleLabel,
      ];
      if (item.filename) sub.unshift(item.filename);
      if (item.has_game && (item.node_count || 0) > 0) {
        sub.push(item.node_count + " 场景");
      }
      const main = document.createElement("div");
      main.className = "history-item__main";
      const titleP = document.createElement("p");
      titleP.className = "history-item__title";
      titleP.textContent = item.title || "未命名";
      const metaP = document.createElement("p");
      metaP.className = "history-item__meta";
      metaP.textContent = sub.join(" · ");
      main.appendChild(titleP);
      main.appendChild(metaP);
      const actions = document.createElement("div");
      actions.className = "history-item__actions";
      if (item.has_game) {
        const playBtn = document.createElement("button");
        playBtn.type = "button";
        playBtn.className = "history-btn history-btn--play";
        playBtn.dataset.action = "play";
        playBtn.dataset.id = item.id;
        playBtn.textContent = "直接游玩";
        actions.appendChild(playBtn);
      }
      const loadBtn = document.createElement("button");
      loadBtn.type = "button";
      loadBtn.className = "history-btn";
      loadBtn.dataset.action = "load";
      loadBtn.dataset.id = item.id;
      loadBtn.textContent = "载入文本";
      actions.appendChild(loadBtn);
      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "history-btn history-btn--danger";
      delBtn.dataset.action = "delete";
      delBtn.dataset.id = item.id;
      delBtn.title = "删除";
      delBtn.setAttribute("aria-label", "删除此条历史记录");
      delBtn.textContent = "×";
      actions.appendChild(delBtn);
      li.appendChild(main);
      li.appendChild(actions);
      listEl.appendChild(li);
    });
  }

  function formatDetail(detail) {
    if (detail == null) return "";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map(function (item) {
          if (typeof item === "string") return item;
          if (item && item.msg) return item.msg;
          return String(item);
        })
        .join("；");
    }
    if (typeof detail === "object" && detail.message) return detail.message;
    try {
      return JSON.stringify(detail);
    } catch {
      return "保存历史失败";
    }
  }

  async function saveEntry(opts) {
    const label = opts.game ? "正在保存游戏记录…" : "正在保存历史…";
    setPanelStatus(label, "loading");
    const body = {
      text: opts.text,
      filename: opts.filename || null,
      style: opts.style || getStyle(),
      title: opts.title || null,
      entry_id: opts.entryId || null,
      game: opts.game || null,
    };
    const res = await fetch("/api/history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) {
      throw new Error(formatDetail(data.detail) || "保存历史失败");
    }
    await refreshList();
    const okMsg = opts.game
      ? "已保存 · " + (data.title || "游戏记录") + " · " + (data.node_count || 0) + " 场景"
      : "已保存历史 · " + (data.title || opts.filename || "文本");
    setPanelStatus(okMsg, "ok");
    const historyModal = document.getElementById("history-modal");
    if (historyModal && !historyModal.classList.contains("is-open")) {
      historyModal.hidden = false;
      historyModal.classList.add("is-open");
    }
    return data.id;
  }

  async function loadEntry(id, play) {
    const res = await fetch("/api/history/" + encodeURIComponent(id));
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.detail || "读取历史失败");
    if (data.item && data.item.style) setStyle(data.item.style);
    if (data.text) setText(data.text);
    if (play) {
      if (!data.game || !data.game.nodes) {
        throw new Error("该记录尚未生成游戏，请先点「开始转化」");
      }
      onPlay(data.game, data.text || "");
    }
    if (data.item && data.item.id) onEntryLoaded(data.item.id);
    return data;
  }

  async function deleteEntry(id) {
    const res = await fetch("/api/history/" + encodeURIComponent(id), { method: "DELETE" });
    if (!res.ok) {
      const data = await res.json().catch(function () { return {}; });
      throw new Error(data.detail || "删除失败");
    }
    await refreshList();
  }

  function init(opts) {
    listEl = document.getElementById("history-list");
    emptyEl = document.getElementById("history-empty");
    loadingEl = document.getElementById("history-loading");
    if (opts.getStyle) getStyle = opts.getStyle;
    if (opts.setStyle) setStyle = opts.setStyle;
    if (opts.setText) setText = opts.setText;
    if (opts.onPlay) onPlay = opts.onPlay;
    if (opts.onStatus) onStatus = opts.onStatus;
    if (opts.onEntryLoaded) onEntryLoaded = opts.onEntryLoaded;

    if (listEl) {
      listEl.addEventListener("click", async function (e) {
        const btn = e.target.closest("[data-action]");
        if (!btn) return;
        const id = btn.dataset.id;
        const action = btn.dataset.action;
        if (!id) return;
        try {
          if (action === "load") {
            await loadEntry(id, false);
            setPanelStatus("已载入历史文本 · " + (btn.closest(".history-item")?.querySelector(".history-item__title")?.textContent || ""), "ok");
          } else if (action === "play") {
            await loadEntry(id, true);
          } else if (action === "delete") {
            if (!confirm("确定删除这条历史记录？")) return;
            btn.disabled = true;
            try {
              await deleteEntry(id);
              setPanelStatus("已删除历史记录", "ok");
            } catch (delErr) {
              setPanelStatus(delErr.message || "删除失败", "error");
              btn.disabled = false;
            }
            return;
          }
        } catch (err) {
          setPanelStatus(err.message || "操作失败", "error");
        }
      });
    }
    refreshList();
  }

  return {
    init: init,
    refresh: refreshList,
    save: saveEntry,
    load: loadEntry,
  };
})();
