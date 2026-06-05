/** 2711 Editor · Magic UI 交互 */
(function () {
  const startBtn = document.getElementById("start-btn");
  const loadBtn = document.getElementById("load-btn");
  const storyInput = document.getElementById("story-input");
  const dropzone = document.getElementById("upload-dropzone");
  const fileInput = document.getElementById("file-input");
  const historyModal = document.getElementById("history-modal");
  const historyClose = document.getElementById("history-modal-close");

  function openHistoryModal() {
    if (!historyModal) return;
    historyModal.hidden = false;
    historyModal.classList.add("is-open");
    document.body.style.overflow = "hidden";
    if (typeof HistoryPanel !== "undefined" && HistoryPanel.refresh) {
      HistoryPanel.refresh();
    }
  }

  function closeHistoryModal() {
    if (!historyModal) return;
    historyModal.classList.remove("is-open");
    historyModal.hidden = true;
    document.body.style.overflow = "";
  }

  if (startBtn && storyInput) {
    startBtn.addEventListener("click", function () {
      storyInput.focus({ preventScroll: false });
      storyInput.scrollIntoView({ behavior: "smooth", block: "center" });
      const panel = document.getElementById("studio");
      if (panel) {
        panel.classList.add("is-focused");
        setTimeout(function () { panel.classList.remove("is-focused"); }, 1200);
      }
    });
  }

  if (loadBtn) {
    loadBtn.addEventListener("click", openHistoryModal);
  }

  if (historyClose) {
    historyClose.addEventListener("click", closeHistoryModal);
  }

  if (historyModal) {
    historyModal.addEventListener("click", function (e) {
      if (e.target === historyModal) closeHistoryModal();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && historyModal.classList.contains("is-open")) {
        closeHistoryModal();
      }
    });
  }

  if (dropzone && fileInput) {
    ["dragenter", "dragover"].forEach(function (evt) {
      dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("is-dragover");
      });
    });

    ["dragleave", "drop"].forEach(function (evt) {
      dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("is-dragover");
      });
    });

    dropzone.addEventListener("drop", function (e) {
      const files = e.dataTransfer && e.dataTransfer.files;
      if (!files || !files.length) return;
      const file = files[0];
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
      fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  const historyList = document.getElementById("history-list");
  if (historyList) {
    historyList.addEventListener("click", function (e) {
      const btn = e.target.closest("[data-action='load'], [data-action='play']");
      if (btn) closeHistoryModal();
    });
  }
})();
