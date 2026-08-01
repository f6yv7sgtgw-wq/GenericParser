const byId = (id) => document.getElementById(id);
const form = byId("search-form");
const modeInput = byId("mode");
const welcome = byId("welcome");
const resultArea = byId("result-area");
const errorBox = byId("error-box");
const searchButton = byId("search-button");
const spinner = searchButton.querySelector(".spinner");
const buttonLabel = searchButton.querySelector(".button-label");

function setMode(mode) {
  modeInput.value = mode;
  document.querySelectorAll(".mode-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
  });
  document.querySelectorAll(".mode-fields").forEach((section) => {
    section.classList.toggle("hidden", section.dataset.for !== mode);
  });
}

document.querySelectorAll(".mode-button").forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.mode));
});

async function loadFixtures() {
  const response = await fetch("/api/fixtures");
  const payload = await response.json();
  const select = byId("fixture-name");
  select.replaceChildren();
  const labels = {
    "kleinanzeigen_results.html": "Ergebnisse + TOP-Duplikat",
    "kleinanzeigen_no_results.html": "Nulltreffer",
    "kleinanzeigen_layout_changed.html": "Layoutänderung",
    "kleinanzeigen_blocked.html": "Block-/CAPTCHA-Seite",
  };
  payload.fixtures.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = labels[name] || name;
    select.append(option);
  });
}

function requestPayload() {
  const numberOrNull = (id) => {
    const value = byId(id).value.trim();
    return value === "" ? null : Number(value);
  };
  return {
    mode: modeInput.value,
    query: byId("query").value.trim(),
    fixture_name: byId("fixture-name").value || null,
    postal_code: byId("postal-code").value.trim() || null,
    location_id: numberOrNull("location-id"),
    radius_km: numberOrNull("radius-km"),
    max_price: numberOrNull("max-price"),
    category_path: byId("category-path").value.trim() || null,
    save_fixture: byId("save-fixture").checked,
    html: byId("raw-html").value.trim() || null,
  };
}

function setBusy(busy) {
  searchButton.disabled = busy;
  spinner.classList.toggle("hidden", !busy);
  buttonLabel.textContent = busy ? "Parser arbeitet …" : "Testsuche starten";
}

function showError(message, title = "Suche fehlgeschlagen") {
  welcome.classList.add("hidden");
  resultArea.classList.add("hidden");
  errorBox.classList.remove("hidden");
  byId("error-title").textContent = title;
  byId("error-message").textContent = message;
}

function metric(value, label) {
  const node = document.createElement("div");
  node.className = "metric";
  const number = document.createElement("span");
  number.className = "metric-value";
  number.textContent = value;
  const text = document.createElement("span");
  text.className = "metric-label";
  text.textContent = label;
  node.append(number, text);
  return node;
}

function renderUrls(urls) {
  const container = byId("url-list");
  container.replaceChildren();
  if (!urls.length) return;
  urls.forEach((url) => {
    const row = document.createElement("div");
    row.className = "url-item";
    const code = document.createElement("code");
    code.textContent = url;
    const copy = document.createElement("button");
    copy.className = "copy-button";
    copy.type = "button";
    copy.textContent = "Kopieren";
    copy.addEventListener("click", async () => {
      await navigator.clipboard.writeText(url);
      copy.textContent = "Kopiert";
      setTimeout(() => { copy.textContent = "Kopieren"; }, 1200);
    });
    row.append(code, copy);
    container.append(row);
  });
}

function renderDiagnostics(items) {
  const container = byId("diagnostics");
  container.replaceChildren();
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "diagnostic-row";
    const state = document.createElement("span");
    state.className = `state-badge state-${item.state}`;
    state.textContent = item.state.replace("_", " ");
    const values = [
      `Karten ${item.cards_found}`,
      `Geparst ${item.listings_parsed}`,
      `Duplikate ${item.duplicates_skipped}`,
      `Fehler ${item.errors.length}`,
    ];
    row.append(state);
    values.forEach((value) => {
      const span = document.createElement("span");
      span.textContent = value;
      row.append(span);
    });
    container.append(row);
  });
}

function listingCard(item) {
  const card = document.createElement("article");
  card.className = "listing-card";
  const imageBox = document.createElement("div");
  imageBox.className = "listing-image";
  if (item.image_url) {
    const image = document.createElement("img");
    image.src = item.image_url;
    image.alt = "";
    image.loading = "lazy";
    image.referrerPolicy = "no-referrer";
    image.addEventListener("error", () => {
      image.remove();
      const fallback = document.createElement("span");
      fallback.className = "image-placeholder";
      fallback.textContent = "KEIN BILD";
      imageBox.append(fallback);
    });
    imageBox.append(image);
  } else {
    const fallback = document.createElement("span");
    fallback.className = "image-placeholder";
    fallback.textContent = "KEIN BILD";
    imageBox.append(fallback);
  }

  const body = document.createElement("div");
  body.className = "listing-body";
  const top = document.createElement("div");
  top.className = "listing-top";
  const title = document.createElement("h3");
  title.className = "listing-title";
  const link = document.createElement("a");
  link.href = item.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = item.title;
  title.append(link);
  const price = document.createElement("span");
  price.className = "listing-price";
  price.textContent = item.price !== null ? `${item.price} €` : (item.price_raw || "Preis offen");
  top.append(title, price);

  const meta = document.createElement("div");
  meta.className = "listing-meta";
  const location = [item.postal_code, item.place].filter(Boolean).join(" ") || "Ort unbekannt";
  const date = item.posted_at ? new Date(item.posted_at).toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" }) : "Datum unbekannt";
  [location, date, `ID ${item.id}`].forEach((value) => {
    const span = document.createElement("span");
    span.textContent = value;
    meta.append(span);
  });
  const description = document.createElement("p");
  description.className = "listing-description";
  description.textContent = item.description || "Keine Beschreibung in der Ergebnisliste.";
  body.append(top, meta, description);
  if (item.tags.length || item.price_flags.length) {
    const tags = document.createElement("div");
    tags.className = "tags";
    [...item.tags, ...item.price_flags].forEach((value) => {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = value;
      tags.append(tag);
    });
    body.append(tags);
  }
  card.append(imageBox, body);
  return card;
}

function render(payload) {
  welcome.classList.add("hidden");
  errorBox.classList.add("hidden");
  resultArea.classList.remove("hidden");
  byId("result-mode").textContent = payload.mode;
  const summary = payload.summary;
  const metrics = byId("metrics");
  metrics.replaceChildren(
    metric(summary.listings, "Anzeigen"),
    metric(summary.cards, "Karten gefunden"),
    metric(summary.duplicates, "Duplikate"),
    metric(summary.card_errors, "Kartenfehler"),
  );
  renderUrls(payload.generated_urls);
  renderDiagnostics(payload.diagnostics);
  const fixtureBox = byId("saved-fixtures");
  if (payload.saved_fixtures.length) {
    fixtureBox.classList.remove("hidden");
    fixtureBox.textContent = `Gespeichert: ${payload.saved_fixtures.join(", ")}`;
  } else {
    fixtureBox.classList.add("hidden");
  }
  byId("listing-count").textContent = `${payload.listings.length} Treffer`;
  const listings = byId("listings");
  listings.replaceChildren();
  if (!payload.listings.length) {
    const empty = document.createElement("div");
    empty.className = "panel empty-state";
    empty.style.minHeight = "260px";
    const title = document.createElement("h2");
    title.textContent = "Keine Anzeigen gefunden";
    const text = document.createElement("p");
    text.textContent = "Der Parser hat die Seite verarbeitet, aber keine Ergebnisobjekte erzeugt.";
    empty.append(title, text);
    listings.append(empty);
  } else {
    payload.listings.forEach((item) => listings.append(listingCard(item)));
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setBusy(true);
  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestPayload()),
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      throw new Error(detail || `HTTP ${response.status}`);
    }
    render(payload);
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
});

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.example === "evercade") {
      byId("query").value = "evercade sunsoft collection 1";
      byId("max-price").value = "35";
    } else {
      byId("query").value = "zelda link to the past snes pal";
      byId("max-price").value = "70";
    }
  });
});

byId("reset-button").addEventListener("click", () => {
  form.reset();
  setMode("fixture");
  byId("query").value = "evercade sunsoft collection 1";
  welcome.classList.remove("hidden");
  resultArea.classList.add("hidden");
  errorBox.classList.add("hidden");
});

const dialog = byId("location-dialog");
byId("extract-location").addEventListener("click", () => dialog.showModal());
byId("location-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const response = await fetch("/api/location-id", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: byId("location-url").value.trim() }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Location-ID nicht gefunden");
    byId("location-id").value = payload.location_id;
    dialog.close();
  } catch (error) {
    alert(error.message);
  }
});

byId("verify-location").addEventListener("click", async () => {
  const query = byId("query").value.trim();
  const postalCode = byId("postal-code").value.trim();
  const locationId = Number(byId("location-id").value);
  const radius = Number(byId("radius-km").value || 5);
  if (!query || !postalCode || !locationId) {
    showError("Für die Radiusprüfung sind Suchbegriff, PLZ und Location-ID erforderlich.", "Angaben fehlen");
    return;
  }
  setBusy(true);
  try {
    const response = await fetch("/api/verify-location", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, postal_code: postalCode, location_id: locationId, radius_km: radius }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Prüfung fehlgeschlagen");
    const message = payload.radius_effective
      ? `Radius wirkt: lokal ${payload.local_cards}, bundesweit ${payload.nationwide_cards} Karten.`
      : `Noch kein belastbarer Unterschied: lokal und bundesweit jeweils ${payload.local_cards} Karten.`;
    alert(message);
  } catch (error) {
    showError(error.message, "Location-Prüfung fehlgeschlagen");
  } finally {
    setBusy(false);
  }
});

loadFixtures().catch((error) => showError(error.message, "Fixtures konnten nicht geladen werden"));
