/* Open Telegram links through the Mini App bridge after an explicit click. */
(() => {
  "use strict";

  const webApp = window.Telegram?.WebApp;
  // Keyboard-button Mini Apps may have empty initData, so use the platform.
  if (!webApp?.platform || webApp.platform === "unknown") return;
  webApp.ready();

  document.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest("a[href]");
    if (!link || link.hasAttribute("download")) return;
    const url = new URL(link.href);
    if (url.protocol !== "https:" || url.hostname !== "t.me") return;
    if (typeof webApp.openTelegramLink !== "function" || !webApp.isVersionAtLeast("6.1")) return;

    try {
      webApp.openTelegramLink(link.href);
    } catch {
      // Keep the normal link usable if the Telegram bridge is unavailable.
      return;
    }
    event.preventDefault();
    // Since Bot API 7.0, opening a Telegram link leaves the Mini App open.
    try {
      webApp.close();
    } catch {
      // The link was already handed off; do not open a duplicate browser tab.
    }
  });
})();
