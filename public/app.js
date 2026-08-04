const DATA_URL = "./public/data/countries.json";
const WORLD_URL = "./public/data/world.geo.json";

// Equirectangular projection into a 1000x500 canvas. The SVG viewBox crops the
// empty poles / Antarctica so inhabited land fills the frame.
const MAP_WIDTH = 1000;
const MAP_HEIGHT = 500;

const FEED_BATCH = 5; // how many extra signals to reveal per "load more"

const state = {
  countries: [],
  byIso3: new Map(),
  selectedIso2: null,
  activeLayer: "meme",
  world: null,
  // scrollable feed of extra cached candidates for the selected country
  feed: { items: [], shown: 0, loading: false, layer: null, iso2: null },
};

const elements = {
  baseLayer: document.querySelector("#base-layer"),
  hotspotLayer: document.querySelector("#hotspot-layer"),
  markerLayer: document.querySelector("#marker-layer"),
  tooltip: document.querySelector("#tooltip"),
  detailPanel: document.querySelector("#detail-panel-content"),
  countryChips: document.querySelector("#country-chips"),
  statusLine: document.querySelector("#status-line"),
  layerButtons: Array.from(document.querySelectorAll(".layer-button")),
};

function projectCoordinates(lon, lat) {
  return {
    x: ((lon + 180) / 360) * MAP_WIDTH,
    y: ((90 - lat) / 180) * MAP_HEIGHT,
  };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function getCountryByIso2(iso2) {
  return state.countries.find((country) => country.iso2 === iso2) ?? null;
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status}`);
  }
  return response.json();
}

async function loadCountryDetail(iso2) {
  return fetchJson(`./public/data/countries/${iso2}.json`);
}

function currentHeadline(country) {
  return state.activeLayer === "meme" ? country.meme_title : country.news_headline;
}

function createSvgNode(name, attributes = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attributes)) {
    node.setAttribute(key, String(value));
  }
  return node;
}

// --- GeoJSON path helpers -------------------------------------------------

function ringToPath(ring) {
  return ring
    .map(([lon, lat], index) => {
      const { x, y } = projectCoordinates(lon, lat);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .concat("Z")
    .join(" ");
}

function geometryToPath(geometry) {
  if (!geometry) return "";
  if (geometry.type === "Polygon") {
    return geometry.coordinates.map(ringToPath).join(" ");
  }
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates
      .map((polygon) => polygon.map(ringToPath).join(" "))
      .join(" ");
  }
  return "";
}

// --- Rendering ------------------------------------------------------------

function renderBaseMap() {
  elements.baseLayer.innerHTML = "";
  elements.hotspotLayer.innerHTML = "";
  elements.markerLayer.innerHTML = "";

  for (const feature of state.world.features) {
    const iso3 = feature.id;
    const data = state.byIso3.get(iso3);
    const pathData = geometryToPath(feature.geometry);
    if (!pathData) continue;

    const path = createSvgNode("path", {
      class: data ? "country has-data" : "country",
      d: pathData,
    });

    if (data) {
      path.dataset.iso2 = data.iso2;
      path.addEventListener("pointerenter", (event) => renderTooltip(data, event));
      path.addEventListener("pointermove", positionTooltip);
      path.addEventListener("pointerleave", hideTooltip);
      path.addEventListener("click", () => selectCountry(data.iso2));
      elements.hotspotLayer.append(path);
    } else {
      elements.baseLayer.append(path);
    }
  }

  renderMarkers();
  applySelectionClasses();
}

function renderMarkers() {
  elements.markerLayer.innerHTML = "";
  for (const country of state.countries) {
    if (!country.coordinates) continue;
    const { x, y } = projectCoordinates(country.coordinates.lon, country.coordinates.lat);
    const marker = createSvgNode("g", { class: "marker" });
    marker.dataset.iso2 = country.iso2;
    marker.append(
      createSvgNode("circle", { class: "marker-pulse", cx: x, cy: y, r: 9 }),
      createSvgNode("circle", { class: "marker-dot", cx: x, cy: y, r: 3.4 })
    );
    marker.addEventListener("pointerenter", (event) => renderTooltip(country, event));
    marker.addEventListener("pointermove", positionTooltip);
    marker.addEventListener("pointerleave", hideTooltip);
    marker.addEventListener("click", () => selectCountry(country.iso2));
    elements.markerLayer.append(marker);
  }
}

function applySelectionClasses() {
  const has = Boolean(state.selectedIso2);
  for (const node of elements.hotspotLayer.querySelectorAll(".country.has-data")) {
    const selected = node.dataset.iso2 === state.selectedIso2;
    node.classList.toggle("is-selected", selected);
    node.classList.toggle("is-dimmed", has && !selected);
  }
  for (const node of elements.markerLayer.querySelectorAll(".marker")) {
    node.classList.toggle("is-selected", node.dataset.iso2 === state.selectedIso2);
  }
}

function renderTooltip(country, event) {
  const headline = currentHeadline(country) || "No strong signal yet";
  const layerLabel = state.activeLayer === "meme" ? "Trending" : "Top story";
  elements.tooltip.innerHTML = `
    <h3>${escapeHtml(country.flag || "")} ${escapeHtml(country.country_name)}</h3>
    <p class="tooltip-kicker">${escapeHtml(layerLabel)}</p>
    <p>${escapeHtml(headline)}</p>
  `;
  elements.tooltip.hidden = false;
  positionTooltip(event);
}

function hideTooltip() {
  elements.tooltip.hidden = true;
}

function positionTooltip(event) {
  const stage = document.querySelector(".map-stage").getBoundingClientRect();
  const x = event.clientX - stage.left;
  const y = event.clientY - stage.top;
  const flipX = x > stage.width - 260;
  elements.tooltip.classList.toggle("flip-x", flipX);
  elements.tooltip.style.left = `${x}px`;
  elements.tooltip.style.top = `${y}px`;
}

async function selectCountry(iso2) {
  state.selectedIso2 = iso2;
  applySelectionClasses();
  renderCountryChips();
  await renderDetailPanel();
}

function renderCountryChips() {
  elements.countryChips.innerHTML = "";
  for (const country of state.countries) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `country-chip${country.iso2 === state.selectedIso2 ? " is-selected" : ""}`;
    button.innerHTML = `
      <span class="chip-flag">${escapeHtml(country.flag || "")}</span>
      <span class="chip-label">${escapeHtml(country.country_name)}</span>
    `;
    button.addEventListener("click", () => selectCountry(country.iso2));
    elements.countryChips.append(button);
  }
}

function renderEmptyPanel(title, description) {
  elements.detailPanel.innerHTML = `
    <div class="empty-state">
      <p class="section-label">Country Detail</p>
      <h2>${escapeHtml(title)}</h2>
      <p>${escapeHtml(description)}</p>
    </div>
  `;
}

// --- Unified, scrollable card stream -------------------------------------

// The discriminating URL of the primary pick. NOTE: Google Trends gives every
// candidate the same feed source_url, so we key off the unique external link
// (media_url for memes, per-article source_url for news) to avoid mismatches.
function primaryUrls(layer, card) {
  const urls = new Set();
  const item = layer === "meme" ? card.meme : card.top_news;
  if (!item) return urls;
  const key = layer === "meme" ? item.media_url || item.source_url : item.source_url;
  if (key) urls.add(key);
  return urls;
}

// Turn a raw candidate into a uniform card item (short blurb, source links).
function normalizeCandidate(layer, c) {
  if (layer === "meme") {
    const links = [];
    if (c.source_url) links.push({ href: c.source_url, label: "Trend source" });
    if (c.external_url && c.external_url !== c.source_url) {
      links.push({ href: c.external_url, label: "Original link" });
    }
    return {
      title: c.title,
      kicker: c.platform || c.source_label || "trend",
      tone: null,
      explanation: c.short_explanation || c.context || "",
      links,
      // match on the unique external link (source_url is a shared feed URL)
      matchUrls: [c.external_url || c.source_url].filter(Boolean),
    };
  }
  return {
    title: c.title,
    kicker: c.source_name || "news",
    tone: null,
    explanation: c.short_explanation || c.snippet || "",
    links: c.source_url ? [{ href: c.source_url, label: "Read source" }] : [],
    matchUrls: [c.source_url].filter(Boolean),
  };
}

// One uniform, scrollable list of cards. The AI-selected pick leads (with its
// tone + polished title); the rest follow. No separate "primary vs more" split.
function buildCardList(layer, card) {
  const bucket = layer === "meme" ? "trends" : "news";
  const raw = (card.raw_candidates && card.raw_candidates[bucket]) || [];
  const items = raw.map((c) => normalizeCandidate(layer, c)).filter((item) => item.title);

  const primary = layer === "meme" ? card.meme : card.top_news;
  if (!primary) return items;

  const pUrls = primaryUrls(layer, card);
  const idx = items.findIndex((item) => item.matchUrls.some((url) => pUrls.has(url)));
  if (idx >= 0) {
    items[idx].tone = primary.tone || null;
    if (primary.title) items[idx].title = primary.title;
    items[idx].isPrimary = true;
    const [lead] = items.splice(idx, 1);
    items.unshift(lead);
  } else {
    // Selected pick was not in the cached list — lead with it directly.
    items.unshift({
      title: primary.title || primary.headline || "",
      kicker: primary.platform || primary.source_name || (layer === "meme" ? "trend" : "news"),
      tone: primary.tone || null,
      explanation: primary.explanation || primary.summary || "",
      links: [
        primary.source_url && { href: primary.source_url, label: layer === "meme" ? "Trend source" : "Read source" },
        layer === "meme" && primary.media_url && primary.media_url !== primary.source_url
          ? { href: primary.media_url, label: "Original link" }
          : null,
      ].filter(Boolean),
      isPrimary: true,
    });
  }
  return items;
}

function feedItemHtml(item) {
  const kicker = `
    <div class="card-kicker">
      ${item.tone ? `<span class="tone-pill">${escapeHtml(item.tone)}</span>` : ""}
      <span class="source-label">${escapeHtml(item.kicker)}</span>
    </div>`;
  const copy = item.explanation ? `<p class="card-copy">${escapeHtml(item.explanation)}</p>` : "";
  const actions = (item.links || []).length
    ? `<div class="card-actions">${item.links
        .map(
          (link) =>
            `<a class="card-link" href="${escapeHtml(link.href)}" target="_blank" rel="noreferrer">${escapeHtml(link.label)}</a>`
        )
        .join("")}</div>`
    : "";
  return `
    <article class="stream-card${item.isPrimary ? " is-primary" : ""}">
      ${kicker}
      <h3 class="card-title">${escapeHtml(item.title)}</h3>
      ${copy}
      ${actions}
    </article>
  `;
}

function renderFeedBatch(listEl) {
  const { items, shown } = state.feed;
  const next = items.slice(shown, shown + FEED_BATCH);
  const html = next.map(feedItemHtml).join("");
  listEl.insertAdjacentHTML("beforeend", html);
  state.feed.shown += next.length;
  updateFeedFooter();
  maybeAutofill();
}

// If the batch didn't fill the scroll box there's no scrollbar to reach the
// rest, so keep revealing until it overflows or the cache is exhausted.
function maybeAutofill() {
  const scroller = document.querySelector("#feed-scroll");
  if (!scroller) return;
  const { items, shown, loading } = state.feed;
  if (loading || shown >= items.length) return;
  if (scroller.scrollHeight <= scroller.clientHeight + 4) {
    loadMoreFeed();
  }
}

function updateFeedFooter() {
  const footer = document.querySelector("#feed-footer");
  if (!footer) return;
  const { items, shown, loading } = state.feed;
  if (loading) {
    footer.textContent = "Loading more…";
  } else if (shown >= items.length) {
    footer.textContent = items.length
      ? "That's all cached for now. A live backend (Phase 2) would fetch more here."
      : "No extra signals cached for this country yet.";
  } else {
    footer.textContent = `Scroll for more (${items.length - shown} cached)`;
  }
}

// Reveal the next batch when the feed is scrolled near its bottom. This is the
// seam where a real backend fetch would slot in (see Phase 2 in plan.md).
async function loadMoreFeed() {
  const { items, shown, loading } = state.feed;
  if (loading || shown >= items.length) return;
  state.feed.loading = true;
  updateFeedFooter();

  // Cached reveal today; swap for `await fetchMoreCandidates(iso2, layer, shown)`
  // once the API layer exists.
  await new Promise((resolve) => setTimeout(resolve, 180));

  const listEl = document.querySelector("#feed-list");
  state.feed.loading = false;
  if (listEl) renderFeedBatch(listEl);
}

function bindFeedScroll() {
  const scroller = document.querySelector("#feed-scroll");
  if (!scroller) return;
  scroller.addEventListener("scroll", () => {
    const nearBottom =
      scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 48;
    if (nearBottom) loadMoreFeed();
  });
}

async function renderDetailPanel() {
  if (!state.selectedIso2) {
    renderEmptyPanel("Pick a country", "Click a highlighted country to inspect its current card.");
    return;
  }

  const overview = getCountryByIso2(state.selectedIso2);
  if (!overview) {
    renderEmptyPanel("Missing country", "This country is not available in the current data file.");
    return;
  }

  try {
    const card = await loadCountryDetail(state.selectedIso2);
    const keywords = (card.keywords || [])
      .map((keyword) => `<span class="meta-pill">${escapeHtml(keyword)}</span>`)
      .join("");
    const streamLabel =
      state.activeLayer === "meme"
        ? `Trending in ${card.country_name}`
        : `Top stories in ${card.country_name}`;

    elements.detailPanel.innerHTML = `
      <div class="detail-header">
        <div>
          <p class="section-label">Selected Country</p>
          <div class="detail-title">
            <div class="detail-flag">${escapeHtml(card.flag || "")}</div>
            <div>
              <h2>${escapeHtml(card.country_name)}</h2>
              <p class="hero-text">${escapeHtml(overview.region || "Unknown region")}</p>
            </div>
          </div>
          <div class="detail-meta">
            <span class="meta-pill">Layer: ${escapeHtml(state.activeLayer)}</span>
            <span class="meta-pill">Status: ${escapeHtml(card.probe_status || "unknown")}</span>
            ${keywords}
          </div>
        </div>
      </div>
      <section class="stream-section">
        <p class="section-label">${escapeHtml(streamLabel)}</p>
        <div id="feed-scroll" class="feed-scroll">
          <div id="feed-list" class="feed-list"></div>
          <p id="feed-footer" class="feed-footer"></p>
        </div>
      </section>
    `;

    state.feed = {
      items: buildCardList(state.activeLayer, card),
      shown: 0,
      loading: false,
      layer: state.activeLayer,
      iso2: state.selectedIso2,
    };
    const listEl = document.querySelector("#feed-list");
    if (listEl) renderFeedBatch(listEl);
    bindFeedScroll();
  } catch (error) {
    renderEmptyPanel("Failed to load detail", error instanceof Error ? error.message : "Unknown error.");
  }
}

function bindLayerSwitcher() {
  for (const button of elements.layerButtons) {
    button.addEventListener("click", async () => {
      state.activeLayer = button.dataset.layer;
      for (const candidate of elements.layerButtons) {
        const active = candidate === button;
        candidate.classList.toggle("is-active", active);
        candidate.setAttribute("aria-selected", active ? "true" : "false");
      }
      await renderDetailPanel();
    });
  }
}

function bindAboutModal() {
  const modal = document.querySelector("#about-modal");
  const openBtn = document.querySelector("#about-btn");
  const closeBtn = document.querySelector("#about-close");
  if (!modal || !openBtn) return;

  const open = () => {
    modal.hidden = false;
  };
  const close = () => {
    modal.hidden = true;
  };

  openBtn.addEventListener("click", open);
  closeBtn?.addEventListener("click", close);
  modal.addEventListener("click", (event) => {
    if (event.target instanceof HTMLElement && event.target.dataset.close) close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) close();
  });
}

async function bootstrap() {
  bindLayerSwitcher();
  bindAboutModal();

  try {
    const [payload, world] = await Promise.all([fetchJson(DATA_URL), fetchJson(WORLD_URL)]);
    state.countries = payload.countries || [];
    state.world = world;
    state.byIso3 = new Map(
      state.countries.filter((country) => country.iso3).map((country) => [country.iso3, country])
    );
    state.selectedIso2 = state.countries[0]?.iso2 ?? null;

    elements.statusLine.textContent = `${state.countries.length} countries loaded from static JSON`;

    renderBaseMap();
    renderCountryChips();
    await renderDetailPanel();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error.";
    elements.statusLine.textContent = "Failed to load prototype data.";
    renderEmptyPanel("Data load failed", message);
  }
}

bootstrap();
