const previousItems = document.getElementById("previousItems");
const previousStatus = document.getElementById("previousStatus");
const refreshPreviousButton = document.getElementById("refreshPreviousButton");
const detailEmpty = document.getElementById("detailEmpty");
const seedDetail = document.getElementById("seedDetail");
const scriptDetail = document.getElementById("scriptDetail");
const seedTitle = document.getElementById("seedTitle");
const seedMeta = document.getElementById("seedMeta");
const seedActions = document.getElementById("seedActions");
const seedRawText = document.getElementById("seedRawText");
const seedCards = document.getElementById("seedCards");
const scriptTitle = document.getElementById("scriptTitle");
const scriptMeta = document.getElementById("scriptMeta");
const scriptActions = document.getElementById("scriptActions");
const previousPythonCode = document.getElementById("previousPythonCode");
const copyPreviousCodeButton = document.getElementById("copyPreviousCodeButton");

let allItems = [];
let activeFilter = "all";

function setStatus(element, message, mode = "") {
  element.textContent = message;
  element.className = `status ${mode}`.trim();
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bytesToLabel(bytes) {
  if (!Number.isFinite(bytes)) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function outputLink(filename, label) {
  return `<a href="/outputs/${encodeURIComponent(filename)}">${label}</a>`;
}

function runLink(runUrl) {
  return runUrl ? `<a href="${runUrl}" target="_blank" rel="noopener">Open and run</a>` : "";
}

function joinLinks(...links) {
  return links.filter(Boolean).join('<span class="link-separator">•</span>');
}

function hideDetails() {
  detailEmpty.classList.remove("hidden");
  seedDetail.classList.add("hidden");
  scriptDetail.classList.add("hidden");
}

function showSeedDetail() {
  detailEmpty.classList.add("hidden");
  seedDetail.classList.remove("hidden");
  scriptDetail.classList.add("hidden");
}

function showScriptDetail() {
  detailEmpty.classList.add("hidden");
  seedDetail.classList.add("hidden");
  scriptDetail.classList.remove("hidden");
}

function filteredItems() {
  if (activeFilter === "all") return allItems;
  return allItems.filter(item => item.kind === activeFilter);
}

function renderItems() {
  const items = filteredItems();
  previousItems.innerHTML = "";

  if (!items.length) {
    previousItems.innerHTML = `<div class="empty-state small">No saved ${activeFilter === "all" ? "outputs" : activeFilter} found.</div>`;
    return;
  }

  for (const item of items) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "previous-item";
    button.innerHTML = `
      <span class="item-kind ${item.kind}">${item.kind === "seeds" ? "Seeds" : "Script"}</span>
      <strong>${escapeHTML(item.title || item.filename)}</strong>
      <span>${escapeHTML(item.summary || "")}</span>
      <span class="file-line">${escapeHTML(item.filename)} · ${bytesToLabel(item.size_bytes)}</span>
    `;
    button.addEventListener("click", () => loadDetail(item.filename, button));
    previousItems.appendChild(button);
  }
}

async function fetchJSON(url) {
  const response = await fetch(url);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Request failed with status ${response.status}`);
  return data;
}

async function loadItems() {
  setStatus(previousStatus, "Loading saved outputs...");
  hideDetails();
  try {
    const data = await fetchJSON("/api/previous");
    allItems = data.items || [];
    renderItems();
    setStatus(previousStatus, `Found ${allItems.length} saved output file${allItems.length === 1 ? "" : "s"}.`, "success");
  } catch (error) {
    setStatus(previousStatus, error.message, "error");
  }
}

async function loadDetail(filename, selectedButton) {
  document.querySelectorAll(".previous-item.selected").forEach(node => node.classList.remove("selected"));
  selectedButton?.classList.add("selected");

  try {
    const detail = await fetchJSON(`/api/previous/${encodeURIComponent(filename)}`);
    if (detail.metadata?.kind === "seeds") {
      renderSeedDetail(detail.metadata, detail.data || {});
    } else {
      renderScriptDetail(detail.metadata, detail.source || "", detail.run_url || detail.metadata?.run_url);
    }
  } catch (error) {
    setStatus(previousStatus, error.message, "error");
  }
}

function renderSeedDetail(metadata, data) {
  showSeedDetail();
  seedTitle.textContent = data.phrase || metadata.title || metadata.filename;
  seedMeta.textContent = `${metadata.filename} · ${metadata.created_at || metadata.modified_at || ""}`;
  seedActions.innerHTML = outputLink(metadata.filename, "Download JSON");

  const rawText = data.raw_text || "";
  seedRawText.innerHTML = rawText ? `<h3>Raw saved seed output</h3><pre>${escapeHTML(rawText)}</pre>` : "";
  seedCards.innerHTML = "";

  const seeds = data.seeds || [];
  for (const seed of seeds) {
    const article = document.createElement("article");
    article.className = "seed-card readonly";
    article.innerHTML = `
      <span class="number">${escapeHTML(seed.number || "")}</span>
      <h3>${escapeHTML(seed.title || "Untitled seed")}</h3>
      <p>${escapeHTML(seed.description || seed.full_text || "")}</p>
    `;
    seedCards.appendChild(article);
  }
}

function renderScriptDetail(metadata, source, runUrl) {
  showScriptDetail();
  scriptTitle.textContent = metadata.title || metadata.filename;
  scriptMeta.textContent = `${metadata.filename} · ${metadata.created_at || metadata.modified_at || ""}`;
  scriptActions.innerHTML = joinLinks(
    outputLink(metadata.filename, "Download Python script"),
    runLink(runUrl)
  );
  previousPythonCode.textContent = source;
}

refreshPreviousButton.addEventListener("click", loadItems);

for (const button of document.querySelectorAll(".filter-pill")) {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.filter;
    document.querySelectorAll(".filter-pill.active").forEach(node => node.classList.remove("active"));
    button.classList.add("active");
    renderItems();
    hideDetails();
  });
}

copyPreviousCodeButton.addEventListener("click", async () => {
  const code = previousPythonCode.textContent || "";
  if (!code.trim()) return;
  await navigator.clipboard.writeText(code);
  setStatus(previousStatus, "Copied saved Python code to clipboard.", "success");
});

loadItems();
