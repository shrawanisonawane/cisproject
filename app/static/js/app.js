document.addEventListener("DOMContentLoaded", function () {
  // 1. Copy Buttons
  document.querySelectorAll(".js-copy").forEach(function (button) {
    button.addEventListener("click", function () {
      var textToCopy = button.getAttribute("data-copy") || "";
      if (!textToCopy) return;

      var originalText = button.textContent;

      function onSuccess() {
        button.textContent = "Copied";
        setTimeout(function () {
          button.textContent = originalText;
        }, 1500);
      }

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(textToCopy).then(onSuccess).catch(function () {
          fallbackCopy(textToCopy, onSuccess);
        });
      } else {
        fallbackCopy(textToCopy, onSuccess);
      }
    });
  });

  function fallbackCopy(text, cb) {
    try {
      var textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.className = "fallback-textarea";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      if (cb) cb();
    } catch (e) {
      // Fail safely
    }
  }

  // 2. Tabs Behaviour
  var tabButtons = document.querySelectorAll("[data-tab]");
  tabButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var targetId = btn.getAttribute("data-tab");
      var parent = btn.closest(".tabs-container") || document;

      // Update button states
      parent.querySelectorAll("[data-tab]").forEach(function (b) {
        b.classList.remove("active");
        b.setAttribute("aria-selected", "false");
      });
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");

      // Toggle tab panels
      parent.querySelectorAll(".tab-panel").forEach(function (panel) {
        if (panel.id === targetId) {
          panel.removeAttribute("hidden");
        } else {
          panel.setAttribute("hidden", "hidden");
        }
      });
    });
  });

  // 3. Dialog Modal Behaviour (Revoke confirm)
  document.querySelectorAll("[data-open-dialog]").forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      var dialogId = trigger.getAttribute("data-open-dialog");
      var dialog = document.getElementById(dialogId);
      if (dialog && typeof dialog.showModal === "function") {
        dialog.showModal();
      }
    });
  });

  document.querySelectorAll("[data-close-dialog]").forEach(function (closeBtn) {
    closeBtn.addEventListener("click", function () {
      var dialogId = closeBtn.getAttribute("data-close-dialog");
      var dialog = document.getElementById(dialogId) || closeBtn.closest("dialog");
      if (dialog && typeof dialog.close === "function") {
        dialog.close();
      }
    });
  });
});
