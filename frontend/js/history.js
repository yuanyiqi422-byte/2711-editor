/** 2711编辑器 · LOAD GAME 存档（服务端持久化 + 本地结局进度） */
const HistoryPanel = (function () {
  const STYLE_NAMES = {
    xianxia: "古风仙侠",
    urban_romance: "都市言情",
    mystery: "悬疑推理",
    campus: "校园青春",
  };

  const STYLE_PILLS = {
    xianxia: "load-game-card__pill--xianxia",
    urban_romance: "load-game-card__pill--urban",
    mystery: "load-game-card__pill--mystery",
    campus: "load-game-card__pill--campus",
  };

  const STYLE_THUMBS = {
    xianxia: "images/workbench/world-xianxia.png?v=12",
    urban_romance: "images/workbench/world-urban-romance.png?v=12",
    mystery: "images/workbench/world-mystery.png?v=12",
    campus: "images/workbench/world-campus.png?v=12",
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
        year: "numeric",
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

  function statsLine(item) {
    const bits = [];
    if (item.char_count) bits.push("字数 " + (item.char_count || 0).toLocaleString());
    if (item.ending_count) {
      let unlocked = typeof item.unlocked_endings === "number" ? item.unlocked_endings : 0;
      if (!unlocked && typeof ProgressStore !== "undefined") {
        unlocked = ProgressStore.unlockedCount(item.id);
      }
      bits.push("结局 " + unlocked + "/" + item.ending_count);
    }
    return bits.join(" · ");
  }

  async function refreshList(options) {
    if (!listEl) return false;
    const silent = options && options.silent;
    if (loadingEl) loadingEl.hidden = silent;
    if (emptyEl) emptyEl.hidden = true;
    try {
      const res = await fetch("/api/history");
      const items =
        typeof ApiConfig !== "undefined" && ApiConfig.readJsonOrApiError
          ? await ApiConfig.readJsonOrApiError(res, "加载存档失败")
          : await res.json();
      if (!res.ok && !(typeof ApiConfig !== "undefined" && ApiConfig.readJsonOrApiError)) {
        throw new Error(formatDetail(items.detail) || "加载存档失败");
      }
      renderList(Array.isArray(items) ? items : []);
    } catch (err) {
      renderList([]);
      setPanelStatus(err.message || "加载存档失败", "error");
      console.warn("history list", err);
    } finally {
      if (loadingEl) loadingEl.hidden = true;
    }
    return true;
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
      li.className = "history-item load-game-card";
      li.dataset.id = item.id;
      li.dataset.hasGame = item.has_game ? "1" : "0";

      const styleKey = item.style || "urban_romance";
      const styleLabel = STYLE_NAMES[styleKey] || styleKey;
      const pillClass = STYLE_PILLS[styleKey] || STYLE_PILLS.urban_romance;
      const thumb = STYLE_THUMBS[styleKey] || STYLE_THUMBS.urban_romance;
      const stats = statsLine(item);
      const title = item.title || "未命名";

      const card = document.createElement("div");
      card.className = "load-game-card__inner";
      card.innerHTML =
        '<div class="load-game-card__media load-game-card__thumb-col">' +
        '<img class="load-game-card__thumb" src="' + thumb + '" alt="" width="76" height="56" loading="lazy" decoding="async" />' +
        '<span class="load-game-card__pill ' + pillClass + '">' + escapeHtml(styleLabel) + "</span>" +
        "</div>" +
        '<div class="load-game-card__copy">' +
        '<div class="load-game-card__head">' +
        '<p class="load-game-card__title">' + escapeHtml(title) + "</p>" +
        "</div>" +
        '<p class="load-game-card__date">' + escapeHtml(formatDate(item.updated_at)) + "</p>" +
        (stats ? '<p class="load-game-card__stats">' + escapeHtml(stats) + "</p>" : "") +
        '<div class="load-game-card__actions-row">' +
        '<button type="button" class="load-game-card__btn load-game-card__btn--secondary" data-action="load-text" data-id="' + item.id + '">载入文本</button>' +
        '<button type="button" class="load-game-card__btn load-game-card__btn--primary" data-action="play" data-id="' + item.id + '"' +
        (item.has_game ? "" : ' disabled title="请先生成游戏"') +
        ">继续游玩</button>" +
        "</div></div>";

      const actions = document.createElement("div");
      actions.className = "history-item__actions";
      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "history-btn history-btn--danger";
      delBtn.dataset.action = "delete";
      delBtn.dataset.id = item.id;
      delBtn.title = "删除";
      delBtn.setAttribute("aria-label", "删除此存档");
      delBtn.textContent = "×";
      actions.appendChild(delBtn);

      li.appendChild(card);
      li.appendChild(actions);
      listEl.appendChild(li);
    });
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
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
      return "保存存档失败";
    }
  }

  async function saveEntry(opts) {
    const label = opts.game ? "正在保存游戏存档…" : "正在保存…";
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
      throw new Error(formatDetail(data.detail) || "保存存档失败");
    }
    await refreshList();
    const endingCount = data.ending_count || 0;
    const branchCount = data.branch_count || 0;
    const okMsg = opts.game
      ? "已存档 · " + (data.title || "游戏") +
        (branchCount > 0 ? " · " + branchCount + " 条命运分支" : "") +
        (endingCount > 0 ? " · " + endingCount + " 种结局" : "")
      : "已保存 · " + (data.title || opts.filename || "文本");
    setPanelStatus(okMsg, "ok");
    return data.id;
  }

  async function loadEntry(id, play) {
    const res = await fetch("/api/history/" + encodeURIComponent(id));
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.detail || "读取存档失败");
    if (data.item && data.item.style) setStyle(data.item.style);
    if (data.text) setText(data.text);
    if (data.item && data.item.id && data.progress && typeof ProgressStore !== "undefined") {
      ProgressStore.mergeProgress(data.item.id, data.progress);
    }
    if (play) {
      if (!data.game || !data.game.nodes) {
        throw new Error("该存档尚未生成游戏，请先点「开始游玩」");
      }
      onPlay(data.game, data.text || "", data.item.id);
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

  async function handleAction(id, action) {
    if (!id) return;
    const play = action === "play";
    try {
      const data = await loadEntry(id, play);
      const title = (data.item && data.item.title) ? data.item.title : "存档";
      if (play) {
        setPanelStatus("正在进入 · " + title, "ok");
      } else {
        setPanelStatus("已载入 · " + title, "ok");
      }
    } catch (err) {
      setPanelStatus(err.message || "操作失败", "error");
    }
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
        e.stopPropagation();
        const id = btn.dataset.id;
        const action = btn.dataset.action;
        if (!id) return;
        if (action === "delete") {
          if (!confirm("确定删除这条存档？")) return;
          btn.disabled = true;
          try {
            await deleteEntry(id);
            setPanelStatus("已删除存档", "ok");
          } catch (delErr) {
            setPanelStatus(delErr.message || "删除失败", "error");
            btn.disabled = false;
          }
          return;
        }
        if (action === "load-text" || action === "play") {
          if (btn.disabled) return;
          await handleAction(id, action);
        }
      });
    }

    if (emptyEl) emptyEl.hidden = true;
    refreshList({ silent: true });
  }

  async function touchEntry(id) {
    if (!id) return;
    try {
      const res = await fetch("/api/history/" + encodeURIComponent(id) + "/touch", {
        method: "POST",
      });
      if (!res.ok) return;
      await refreshList({ silent: true });
    } catch (err) {
      console.warn("history touch", err);
    }
  }

  return {
    init: init,
    refresh: refreshList,
    save: saveEntry,
    load: loadEntry,
    touch: touchEntry,
  };
})();
