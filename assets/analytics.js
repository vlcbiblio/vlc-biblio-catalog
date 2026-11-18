/* Google Analytics 4 with Google Consent Mode v2 and order-funnel tracking. */
(() => {
  if (window.BiblioAnalytics) return;

  // Replace with your real GA4 Measurement ID (e.g. "G-1A2B3C4D5E") before publishing.
  const GA_MEASUREMENT_ID = "G-T701DBZY2R";
  const CONSENT_KEY = "vlc_biblio_analytics_consent_v1";
  const pendingEvents = [];
  let gtagLoaded = false;
  let bannerElement = null;

  const t = (key, fallback) => (window.BiblioI18n ? window.BiblioI18n.t(key, fallback) : fallback);

  function isConfigured() {
    return /^G-[A-Z0-9]{6,}$/i.test(GA_MEASUREMENT_ID) && !/^G-X+$/i.test(GA_MEASUREMENT_ID);
  }

  function readConsent() {
    try {
      const value = localStorage.getItem(CONSENT_KEY);
      return value === "granted" || value === "denied" ? value : null;
    } catch {
      return null;
    }
  }

  function writeConsent(value) {
    try {
      localStorage.setItem(CONSENT_KEY, value);
    } catch {
      /* Storage may be blocked in private browsing; apply for this page view only. */
    }
  }

  window.dataLayer = window.dataLayer || [];
  function gtag() {
    window.dataLayer.push(arguments);
  }
  if (typeof window.gtag !== "function") {
    window.gtag = gtag;
  }

  // Google Consent Mode v2: deny storage by default until explicit user consent.
  window.gtag("consent", "default", {
    analytics_storage: "denied",
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    wait_for_update: 500,
  });

  function loadGtagScript() {
    if (gtagLoaded || !isConfigured()) return;
    gtagLoaded = true;
    window.gtag("js", new Date());
    window.gtag("config", GA_MEASUREMENT_ID, {
      anonymize_ip: true,
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
    });
    const script = document.createElement("script");
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_MEASUREMENT_ID)}`;
    document.head.append(script);
  }

  function flushPendingEvents() {
    while (pendingEvents.length) {
      const { name, params } = pendingEvents.shift();
      window.gtag("event", name, params);
    }
  }

  function applyConsent(status) {
    if (status === "granted") {
      window.gtag("consent", "update", { analytics_storage: "granted" });
      loadGtagScript();
      flushPendingEvents();
    } else {
      window.gtag("consent", "update", { analytics_storage: "denied" });
      pendingEvents.length = 0;
    }
  }

  function track(eventName, params = {}) {
    if (!eventName || typeof eventName !== "string") return;
    const cleanParams = {};
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        cleanParams[key] = value;
      }
    }
    const consent = readConsent();
    if (consent === "denied") return;
    if (consent === "granted") {
      if (isConfigured()) {
        window.gtag("event", eventName, cleanParams);
      }
      return;
    }
    if (pendingEvents.length < 30) {
      pendingEvents.push({ name: eventName, params: cleanParams });
    }
  }

  function ensureStyles() {
    if (document.getElementById("biblio-consent-styles")) return;
    const style = document.createElement("style");
    style.id = "biblio-consent-styles";
    style.textContent = `
      .biblio-consent {
        position: fixed;
        right: 16px;
        bottom: 16px;
        left: 16px;
        z-index: 9999;
        max-width: 560px;
        margin: 0 auto;
        padding: 14px 16px;
        border: 1px solid #ddd4c5;
        border-radius: 8px;
        background: #fffdf8;
        color: #26231f;
        box-shadow: 0 14px 36px rgba(38, 35, 31, 0.16);
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        font-size: 14px;
        line-height: 1.45;
      }
      .biblio-consent p {
        margin: 0 0 12px;
        color: #4d473f;
      }
      .biblio-consent a {
        color: #315f86;
        font-weight: 700;
        text-decoration: none;
      }
      .biblio-consent a:hover {
        text-decoration: underline;
      }
      .biblio-consent-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
      }
      .biblio-consent-btn {
        padding: 8px 14px;
        border: 1px solid #ddd4c5;
        border-radius: 6px;
        background: #f7f4ee;
        color: #26231f;
        font: inherit;
        font-size: 13px;
        font-weight: 700;
        cursor: pointer;
      }
      .biblio-consent-btn:hover,
      .biblio-consent-btn:focus-visible {
        background: #ede7dc;
      }
      .biblio-consent-btn.is-primary {
        border-color: #315f86;
        background: #315f86;
        color: #fffdf8;
      }
      .biblio-consent-btn.is-primary:hover,
      .biblio-consent-btn.is-primary:focus-visible {
        background: #274d6d;
      }
      @media (max-width: 560px) {
        .biblio-consent {
          right: 10px;
          bottom: 10px;
          left: 10px;
          padding: 12px 14px;
        }
      }
    `;
    document.head.append(style);
  }

  function removeBanner() {
    if (bannerElement) {
      bannerElement.remove();
      bannerElement = null;
    }
  }

  function showBanner() {
    if (!document.body || bannerElement) return;
    ensureStyles();
    const aside = document.createElement("aside");
    aside.className = "biblio-consent";
    aside.setAttribute("role", "dialog");
    aside.setAttribute("aria-live", "polite");
    aside.setAttribute("aria-label", t("analytics.banner.aria", "Preferencias de analítica"));

    const text = document.createElement("p");
    text.textContent = t(
      "analytics.banner.text",
      "Usamos Google Analytics para medir visitas diarias y mejorar el proceso de solicitud de libros. Puedes aceptar o rechazar las cookies de analítica. "
    );
    const link = document.createElement("a");
    link.href = "./privacy.html";
    link.textContent = t("analytics.banner.privacy", "Política de privacidad");
    text.append(link);

    const actions = document.createElement("div");
    actions.className = "biblio-consent-actions";

    const accept = document.createElement("button");
    accept.type = "button";
    accept.className = "biblio-consent-btn is-primary";
    accept.textContent = t("analytics.banner.accept", "Aceptar");
    accept.addEventListener("click", () => {
      writeConsent("granted");
      removeBanner();
      applyConsent("granted");
    });

    const reject = document.createElement("button");
    reject.type = "button";
    reject.className = "biblio-consent-btn";
    reject.textContent = t("analytics.banner.reject", "Rechazar");
    reject.addEventListener("click", () => {
      writeConsent("denied");
      removeBanner();
      applyConsent("denied");
    });

    actions.append(accept, reject);
    aside.append(text, actions);
    document.body.append(aside);
    bannerElement = aside;
  }

  function openConsent() {
    removeBanner();
    showBanner();
  }

  function init() {
    const consent = readConsent();
    if (consent === "granted") {
      applyConsent("granted");
    } else if (consent === null) {
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", showBanner, { once: true });
      } else {
        showBanner();
      }
    }
  }

  window.BiblioAnalytics = Object.freeze({
    track,
    openConsent,
    getConsent: readConsent,
    isConfigured,
  });

  init();
})();
