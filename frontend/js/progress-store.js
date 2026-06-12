/** 游玩进度 — 结局解锁（localStorage + 服务端历史存档同步） */
const ProgressStore = (function () {
  const PREFIX = "2711-progress-";

  function key(entryId) {
    return PREFIX + (entryId || "anonymous");
  }

  function load(entryId) {
    try {
      const raw = localStorage.getItem(key(entryId));
      return raw ? JSON.parse(raw) : { unlocked: [], checkpoint: null };
    } catch {
      return { unlocked: [], checkpoint: null };
    }
  }

  function save(entryId, data) {
    localStorage.setItem(key(entryId), JSON.stringify(data));
  }

  function recordEnding(entryId, node) {
    if (!node || !node.is_ending) return;
    const data = load(entryId);
    const item = {
      nodeId: node.id,
      type: node.ending_type || "unknown",
      title: node.title || "",
      ts: Date.now(),
    };
    const exists = data.unlocked.some(function (u) { return u.nodeId === item.nodeId; });
    if (!exists) data.unlocked.push(item);
    save(entryId, data);
  }

  function unlockedCount(entryId) {
    return load(entryId).unlocked.length;
  }

  function mergeProgress(entryId, serverProgress) {
    if (!entryId || !serverProgress || !Array.isArray(serverProgress.unlocked)) return;
    const local = load(entryId);
    const byId = {};
    local.unlocked.forEach(function (u) { byId[u.nodeId] = u; });
    serverProgress.unlocked.forEach(function (u) {
      if (u && u.nodeId) byId[u.nodeId] = u;
    });
    local.unlocked = Object.keys(byId).map(function (id) { return byId[id]; });
    if (serverProgress.checkpoint && typeof serverProgress.checkpoint === "object") {
      const localTs = local.checkpoint && local.checkpoint.ts ? local.checkpoint.ts : 0;
      const serverTs = serverProgress.checkpoint.ts || 0;
      if (serverTs >= localTs) local.checkpoint = serverProgress.checkpoint;
    }
    save(entryId, local);
  }

  function saveCheckpoint(entryId, checkpoint) {
    if (!entryId || entryId === "demo") return;
    const data = load(entryId);
    data.checkpoint = checkpoint;
    save(entryId, data);
    syncServer(entryId);
  }

  function loadCheckpoint(entryId) {
    const data = load(entryId);
    return data.checkpoint || null;
  }

  function clearCheckpoint(entryId) {
    const data = load(entryId);
    data.checkpoint = null;
    save(entryId, data);
    syncServer(entryId);
  }

  async function syncServer(entryId) {
    if (!entryId || entryId === "demo") return;
    const data = load(entryId);
    try {
      const res = await fetch("/api/history/" + encodeURIComponent(entryId) + "/progress", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ unlocked: data.unlocked, checkpoint: data.checkpoint }),
      });
      if (!res.ok) return;
    } catch (err) {
      console.warn("progress sync", err);
    }
  }

  function collectEndingsFromPack(pack) {
    if (!pack || !pack.nodes) return [];
    return Object.keys(pack.nodes)
      .map(function (id) { return pack.nodes[id]; })
      .filter(function (n) { return n && n.is_ending; });
  }

  function endingGallery(entryId, pack) {
    const all = collectEndingsFromPack(pack);
    const unlocked = load(entryId).unlocked;
    const unlockedIds = new Set(unlocked.map(function (u) { return u.nodeId; }));
    return all.map(function (node) {
      const type =
        typeof EndingLabels !== "undefined"
          ? EndingLabels.canonical(node.ending_type) ||
            EndingLabels.canonical(node.title) ||
            "unknown"
          : node.ending_type || "unknown";
      return {
        nodeId: node.id,
        type: type,
        label: endingTypeLabel(type, node),
        unlocked: unlockedIds.has(node.id),
        hidden: type === "hidden" || (node.title || "").indexOf("隐藏") >= 0,
      };
    });
  }

  function endingTypeLabel(type, node) {
    if (typeof EndingLabels !== "undefined") {
      return EndingLabels.galleryLabel(type, node);
    }
    return "故事至此收束";
  }

  return {
    load: load,
    save: save,
    recordEnding: recordEnding,
    saveCheckpoint: saveCheckpoint,
    loadCheckpoint: loadCheckpoint,
    clearCheckpoint: clearCheckpoint,
    unlockedCount: unlockedCount,
    mergeProgress: mergeProgress,
    syncServer: syncServer,
    endingGallery: endingGallery,
    collectEndingsFromPack: collectEndingsFromPack,
  };
})();
