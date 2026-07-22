/* The Bosphorus Brief — client. No frameworks, no trackers, no accounts.
   Reads the JSON the refresh pipeline writes into ./data/ and renders it. */

(() => {
  "use strict";

  const CATEGORY_LABELS = {
    turkiye: "Türkiye",
    region: "Region",
    migration: "Migration & Residency",
    safety: "Safety",
    economy: "Economy",
  };
  // Ownership lenses: [chip label, default explanation]. Codes come from the
  // pipeline's curated source map; unlabeled sources simply get no chip.
  const LENSES = {
    state: ["state", "State-owned or state-funded outlet"],
    progov: ["pro-gov", "Private outlet with pro-government ownership"],
    opposition: ["opposition", "Opposition-leaning or exile-run outlet"],
    independent: ["indep", "Independent newsroom"],
    international: ["intl", "International outlet or wire service"],
    official: ["official", "Government or international body"],
  };
  const LENS_ORDER = [
    "state", "progov", "opposition", "independent", "international",
    "official", "unrated",
  ];
  const BLINDSPOT_NOTES = {
    progov: "In our feed, only state-aligned outlets are covering this story.",
    opposition: "In our feed, only opposition-leaning outlets are covering this story.",
  };
  const REFRESH_MS = 15 * 60 * 1000;
  const STALE_MS = 10 * 60 * 1000;

  const $ = (sel) => document.querySelector(sel);
  const state = {
    news: null,
    digest: null,
    rates: null,
    tab: "top",
    query: "",
    saved: loadSaved(),
    lastLoad: 0,
  };

  // ---------------------------------------------------------- persistence --
  function loadSaved() {
    try {
      return JSON.parse(localStorage.getItem("brief.saved") || "[]");
    } catch {
      return [];
    }
  }
  function persistSaved() {
    localStorage.setItem("brief.saved", JSON.stringify(state.saved.slice(0, 200)));
  }

  // ---------------------------------------------------------------- theme --
  const themeToggle = $("#theme-toggle");
  function applyTheme(theme) {
    if (theme) document.documentElement.dataset.theme = theme;
    else delete document.documentElement.dataset.theme;
  }
  applyTheme(localStorage.getItem("brief.theme") || "");
  themeToggle.addEventListener("click", () => {
    const current = document.documentElement.dataset.theme ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    localStorage.setItem("brief.theme", next);
    applyTheme(next);
  });

  // ------------------------------------------------------- masthead clock --
  function tickMasthead() {
    const now = new Date();
    $("#dateline").textContent = new Intl.DateTimeFormat("en-GB", {
      weekday: "long", day: "numeric", month: "long", year: "numeric",
      timeZone: "Europe/Istanbul",
    }).format(now);
    $("#ist-clock").textContent = "İstanbul " + new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit", minute: "2-digit", timeZone: "Europe/Istanbul",
    }).format(now);
  }
  tickMasthead();
  setInterval(tickMasthead, 30 * 1000);

  // ----------------------------------------------------------- formatting --
  function timeAgo(iso) {
    if (!iso) return null;
    const mins = Math.round((Date.now() - Date.parse(iso)) / 60000);
    if (!Number.isFinite(mins)) return null;
    if (mins < 1) return "just now";
    if (mins < 60) return mins + "m ago";
    const hours = Math.round(mins / 60);
    if (hours < 24) return hours + "h ago";
    const days = Math.round(hours / 24);
    if (days < 14) return days + "d ago";
    return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" })
      .format(new Date(iso));
  }

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (key === "class") node.className = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else if (value !== null && value !== undefined) node.setAttribute(key, value);
    }
    node.append(...children.filter((c) => c !== null && c !== undefined));
    return node;
  }

  function scrollToFeed() {
    const main = document.querySelector(".layout main");
    if (!main) return;
    const top = Math.max(
      0, main.getBoundingClientRect().top + window.pageYOffset - 56
    );
    try {
      window.scrollTo({ top: top, behavior: "smooth" });
    } catch (err) {
      window.scrollTo(0, top);
    }
  }

  // ----------------------------------------------------------------- feed --
  function visibleItems() {
    if (!state.news) return [];
    const items = state.news.items || [];
    let list;
    if (state.tab === "saved") {
      list = state.saved;
    } else if (state.tab === "top") {
      const byId = new Map(items.map((i) => [i.id, i]));
      list = (state.news.top || []).map((id) => byId.get(id)).filter(Boolean);
      if (!list.length) list = items.slice(0, 12);
    } else {
      list = items.filter((i) => i.category === state.tab);
    }
    if (state.query) {
      const q = state.query.toLowerCase();
      list = list.filter((i) =>
        (i.title + " " + (i.summary || "") + " " + i.source).toLowerCase().includes(q));
    }
    return list;
  }

  function isSaved(id) {
    return state.saved.some((s) => s.id === id);
  }

  function toggleSaved(item) {
    if (isSaved(item.id)) {
      state.saved = state.saved.filter((s) => s.id !== item.id);
    } else {
      state.saved = [{ ...item, savedAt: new Date().toISOString() }, ...state.saved];
    }
    persistSaved();
    renderFeed();
    renderSavedCount();
  }

  function renderSavedCount() {
    const badge = $("#saved-count");
    badge.textContent = state.saved.length;
    badge.hidden = state.saved.length === 0;
  }

  async function shareLink(payload, btn) {
    if (navigator.share) {
      try {
        await navigator.share(payload);
      } catch (err) { /* user closed the share sheet — fine */ }
      return;
    }
    try {
      await navigator.clipboard.writeText(payload.url);
      if (btn) {
        const prev = btn.innerHTML;
        btn.classList.add("done");
        btn.innerHTML = "✓";
        setTimeout(() => {
          btn.classList.remove("done");
          btn.innerHTML = prev;
        }, 1300);
      }
    } catch (err) {
      window.prompt("Copy this link:", payload.url);
    }
  }

  function shareIcon() {
    const span = el("span", { class: "share-glyph", "aria-hidden": "true" });
    span.innerHTML = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="M8 6.5 12 3l4 3.5"/><path d="M6 11H5a1.5 1.5 0 0 0-1.5 1.5v7A1.5 1.5 0 0 0 5 21h14a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 19 11h-1"/></svg>';
    return span;
  }

  function lensChip(code, note) {
    const meta = LENSES[code];
    if (!meta) return null;
    return el("span", {
      class: "lens lens-" + code,
      title: note || meta[1],
    }, meta[0]);
  }

  function coverageBlock(item) {
    const cov = item.coverage || [];
    if (cov.length < 2) return null;
    const counts = {};
    cov.forEach((c) => {
      const key = c.lens || "unrated";
      counts[key] = (counts[key] || 0) + 1;
    });
    const bar = el("span", { class: "spectrum", "aria-hidden": "true" },
      ...LENS_ORDER.filter((k) => counts[k]).map((k) =>
        el("span", { class: "seg seg-" + k, style: "flex:" + counts[k] })));
    const list = el("ul", { class: "coverage-list", hidden: "" },
      ...cov.map((c) => el("li", {},
        lensChip(c.lens) || el("span", { class: "lens lens-unrated", title: "Source we haven't classified" }, "—"),
        el("a", { href: c.url, target: "_blank", rel: "noopener" }, c.source),
        el("span", { class: "story-time" }, timeAgo(c.published) || ""))));
    const btn = el("button", {
      class: "coverage-btn",
      "aria-expanded": "false",
      title: "See every outlet reporting this story",
      onclick: () => {
        list.hidden = !list.hidden;
        btn.setAttribute("aria-expanded", String(!list.hidden));
        btn.classList.toggle("open", !list.hidden);
      },
    }, bar, cov.length + " sources", el("span", { class: "chev" }, "▾"));
    return el("div", { class: "coverage" }, btn, list);
  }

  function renderFeed() {
    const list = visibleItems();
    const container = $("#stories");
    container.replaceChildren(...list.map((item) => el("li", { class: "story" },
      el("div", { class: "story-meta" },
        el("span", { class: "story-source" }, item.source),
        lensChip(item.lens, item.lens_note),
        el("span", { class: "story-time" },
          timeAgo(item.published) || "reference"),
        item.blindspot
          ? el("span", { class: "blindspot", title: BLINDSPOT_NOTES[item.blindspot] || "" },
              "one-lens coverage")
          : null,
        state.tab === "top" || state.tab === "saved"
          ? el("span", { class: "story-cat" }, CATEGORY_LABELS[item.category] || "")
          : null,
      ),
      el("h3", {}, el("a", { href: item.url, target: "_blank", rel: "noopener" }, item.title)),
      item.summary ? el("p", { class: "story-summary" }, item.summary) : null,
      coverageBlock(item),
      el("div", { class: "story-actions" },
        el("button", {
          class: "save-btn" + (isSaved(item.id) ? " saved" : ""),
          title: isSaved(item.id) ? "Remove from reading list" : "Save for later",
          "aria-label": "Save story",
          onclick: () => toggleSaved(item),
        }, isSaved(item.id) ? "★" : "☆"),
        el("button", {
          class: "share-btn",
          title: "Share this story",
          "aria-label": "Share story",
          onclick: (ev) => shareLink(
            { title: item.title, url: item.url }, ev.currentTarget),
        }, shareIcon()),
      ),
    )));

    const titles = {
      top: "Top Stories",
      saved: "Saved for later",
      ...CATEGORY_LABELS,
    };
    const sectionTitle = $("#section-title");
    if (sectionTitle) {
      sectionTitle.textContent =
        (titles[state.tab] || "") + " · " + list.length +
        (list.length === 1 ? " story" : " stories");
    }

    const empty = $("#empty-state");
    if (!list.length) {
      empty.textContent = state.tab === "saved"
        ? "Nothing saved yet — tap ☆ on any story to keep it here."
        : state.query
          ? "No stories match that filter."
          : "Nothing here right now — try another section, or refresh.";
      empty.hidden = false;
    } else {
      empty.hidden = true;
    }
  }

  function renderStamp() {
    const stamp = $("#updated-stamp");
    if (state.news && state.news.generated_at) {
      stamp.textContent = "Feed rebuilt " + (timeAgo(state.news.generated_at) || "—");
      stamp.title = "Data generated " + new Date(state.news.generated_at).toLocaleString();
    } else {
      stamp.textContent = "";
    }
    const notice = $("#notice");
    const ageH = state.news && state.news.generated_at
      ? (Date.now() - Date.parse(state.news.generated_at)) / 36e5 : 0;
    if (state.news && state.news.seed) {
      notice.textContent = "You're looking at the Brief's opening edition. Once "
        + "deployed, the feed rebuilds itself every hour with the latest from "
        + "all sources.";
      notice.hidden = false;
    } else if (ageH > 6) {
      notice.textContent = "This edition is more than " + Math.floor(ageH)
        + " hours old — the hourly refresh may be paused. The stories below "
        + "are the most recent available.";
      notice.hidden = false;
    } else {
      notice.hidden = true;
    }
  }

  // --------------------------------------------------------------- digest --
  function renderDigest() {
    const digest = state.digest;
    const card = $("#digest-card");
    if (!digest || !digest.sections) { card.hidden = true; return; }
    card.hidden = false;
    $("#digest-date").textContent = digest.date_label || digest.date || "";
    $("#digest-title").textContent = digest.title || "";
    $("#digest-overview").textContent = digest.overview || "";
    $("#digest-sections").replaceChildren(...digest.sections.map((s) =>
      el("div", { class: "digest-section" },
        el("h4", {}, s.heading), el("p", {}, s.body))));
    $("#digest-closing").textContent = digest.closing || "";
    $("#digest-method").textContent = digest.method === "ai"
      ? "Written each morning by the Brief's AI editor from the sources in the feed. Verify anything critical with the original story."
      : "Automated headline roundup. The AI-written edition appears when a digest key is configured.";
  }

  // ------------------------------------------------------- rates & levels --
  function renderRates() {
    const rates = state.rates;
    const card = $("#rates-card");
    if (!rates || !rates.pairs || !rates.pairs.length) { card.hidden = true; return; }
    card.hidden = false;
    $("#rates-table").replaceChildren(...rates.pairs.map((p) =>
      el("tr", {},
        el("td", { class: "pair" }, p.pair),
        el("td", { class: "rate" }, "₺" + p.rate.toFixed(2)))));
    $("#rates-updated").textContent =
      "As of " + (timeAgo(rates.updated) || "—") + " · " + (rates.source || "");
  }

  function renderAdvisories() {
    const card = $("#advisory-card");
    const advisories = (state.news && state.news.advisories) || [];
    if (!advisories.length) { card.hidden = true; return; }
    card.hidden = false;
    $("#advisory-list").replaceChildren(...advisories.map((a) =>
      el("li", {},
        a.url
          ? el("a", { href: a.url, target: "_blank", rel: "noopener", title: a.title || "" }, a.country)
          : el("span", {}, a.country),
        el("span", { class: "level level-" + a.level, title: a.title || "" },
          "Level " + a.level))));
  }

  // ------------------------------------------------------------- loading --
  async function loadJson(path) {
    const resp = await fetch(path + "?t=" + Date.now(), { cache: "no-store" });
    if (!resp.ok) throw new Error(path + " → " + resp.status);
    return resp.json();
  }

  async function loadAll(showSpinner) {
    const btn = $("#refresh-btn");
    if (showSpinner) btn.classList.add("spinning");
    try {
      const [news, digest, rates] = await Promise.allSettled([
        loadJson("data/news.json"),
        loadJson("data/digest.json"),
        loadJson("data/rates.json"),
      ]);
      if (news.status === "fulfilled") state.news = news.value;
      if (digest.status === "fulfilled") state.digest = digest.value;
      if (rates.status === "fulfilled") state.rates = rates.value;
      state.lastLoad = Date.now();
      renderAll();
    } finally {
      btn.classList.remove("spinning");
    }
  }

  function renderAll() {
    renderFeed();
    renderStamp();
    renderDigest();
    renderRates();
    renderAdvisories();
    renderSavedCount();
  }

  // ---------------------------------------------------------------- wires --
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      state.tab = tab.dataset.tab;
      history.replaceState(null, "", "#" + state.tab);
      renderFeed();
      // On phones the digest sits above the feed, so "top of page" hides the
      // section you just switched to — scroll to the feed itself instead.
      scrollToFeed();
    });
  });
  const hashTab = location.hash.replace("#", "");
  if (hashTab) {
    const target = document.querySelector('.tab[data-tab="' + hashTab + '"]');
    if (target) target.click();
  }

  $("#search").addEventListener("input", (event) => {
    state.query = event.target.value.trim();
    renderFeed();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && document.activeElement !== $("#search")) {
      event.preventDefault();
      $("#search").focus();
    }
  });

  $("#refresh-btn").addEventListener("click", () => loadAll(true));

  $("#share-btn").addEventListener("click", (ev) => shareLink({
    title: "The Bosphorus Brief",
    text: "Two continents. One briefing.",
    url: location.origin + location.pathname,
  }, ev.currentTarget));

  $("#cay-tab").addEventListener("click", () => {
    const card = $("#digest-card");
    if (!card || card.hidden) return;
    const top = Math.max(
      0, card.getBoundingClientRect().top + window.pageYOffset - 56
    );
    try {
      window.scrollTo({ top: top, behavior: "smooth" });
    } catch (err) {
      window.scrollTo(0, top);
    }
    card.classList.remove("glow");
    void card.offsetWidth; // restart the highlight animation
    card.classList.add("glow");
  });

  const infoBtn = $("#digest-info-btn");
  infoBtn.addEventListener("click", () => {
    const about = $("#digest-about");
    about.hidden = !about.hidden;
    infoBtn.setAttribute("aria-expanded", String(!about.hidden));
    infoBtn.classList.toggle("open", !about.hidden);
  });

  const railToggle = $("#rail-toggle");
  railToggle.addEventListener("click", () => {
    const expanded = document.querySelector(".rail").classList.toggle("rail-expanded");
    railToggle.setAttribute("aria-expanded", String(expanded));
    railToggle.textContent = expanded
      ? "Hide rates, advisories & useful doors ▴"
      : "Rates, advisories & useful doors ▾";
  });

  setInterval(() => loadAll(false), REFRESH_MS);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && Date.now() - state.lastLoad > STALE_MS) loadAll(false);
  });

  loadAll(true);
})();
