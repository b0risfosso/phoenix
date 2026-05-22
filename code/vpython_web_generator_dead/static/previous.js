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
const previousSimulationModel = document.getElementById("previousSimulationModel");
const previousSimulationTemperature = document.getElementById("previousSimulationTemperature");

let allItems = [];
let activeFilter = "all";
let currentSeedFilename = "";

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

function runLink(runUrl, label = "Open and run") {
  return runUrl ? `<a href="${runUrl}" target="_blank" rel="noopener">${label}</a>` : "";
}

function editLink(filename, label = "Edit script") {
  return filename ? `<a href="/script-editor/${encodeURIComponent(filename)}" target="_blank" rel="noopener">${label}</a>` : "";
}

function scriptDetailLink(filename, label = "Open script") {
  return `<button type="button" class="inline-link script-detail-link" data-script-filename="${escapeHTML(filename)}">${escapeHTML(label)}</button>`;
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

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
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

function fullSeedText(seed) {
  return seed.full_text || `${seed.title || ""}: ${seed.description || ""}`.trim();
}

function renderLinkedScripts(seed) {
  const linked = seed.linked_scripts || [];
  if (!linked.length) return "";

  const rows = linked.map(script => `
    <div class="linked-script-row">
      <span>${escapeHTML(script.filename)}</span>
      <span class="downloads">${joinLinks(
        scriptDetailLink(script.filename),
        editLink(script.filename, "Edit"),
        outputLink(script.filename, "Download"),
        runLink(script.run_url)
      )}</span>
    </div>
  `).join("");

  return `<div class="linked-scripts"><strong>Linked script${linked.length === 1 ? "" : "s"}</strong>${rows}</div>`;
}

function renderSeedDetail(metadata, data) {
  showSeedDetail();
  currentSeedFilename = metadata.filename;
  seedTitle.textContent = data.phrase || metadata.title || metadata.filename;
  seedMeta.textContent = `${metadata.filename} · ${metadata.created_at || metadata.modified_at || ""}`;
  seedActions.innerHTML = outputLink(metadata.filename, "Download JSON");

  const rawText = data.raw_text || "";
  seedRawText.innerHTML = rawText ? `<h3>Raw saved seed output</h3><pre>${escapeHTML(rawText)}</pre>` : "";
  seedCards.innerHTML = "";

  const seeds = data.seeds || [];
  if (!seeds.length) {
    seedCards.innerHTML = '<div class="empty-state small">This file has no parsed seed entries.</div>';
    return;
  }

  for (const seed of seeds) {
    const article = document.createElement("article");
    article.className = "seed-card readonly linked-seed-card";
    article.innerHTML = `
      <span class="number">${escapeHTML(seed.number || "")}</span>
      <h3>${escapeHTML(seed.title || "Untitled seed")}</h3>
      <p>${escapeHTML(seed.description || seed.full_text || "")}</p>
      ${renderLinkedScripts(seed)}
      <div class="button-row small-row seed-card-actions">
        <button type="button" class="secondary use-seed-button">Generate script from this seed</button>
      </div>
      <div class="status seed-action-status"></div>
    `;

    const generateButton = article.querySelector(".use-seed-button");
    const actionStatus = article.querySelector(".seed-action-status");
    generateButton.addEventListener("click", () => generateScriptForSeed(seed, generateButton, actionStatus));
    seedCards.appendChild(article);
  }
}

async function generateScriptForSeed(seed, button, actionStatus) {
  const seedText = fullSeedText(seed);
  if (!seedText.trim()) {
    setStatus(actionStatus, "This seed is empty.", "error");
    return;
  }

  button.disabled = true;
  setStatus(actionStatus, "Generating linked VPython script...");

  try {
    const data = await postJSON("/api/simulation", {
      seed: seedText,
      model: previousSimulationModel.value.trim(),
      temperature: previousSimulationTemperature.value,
      save: true,
      seed_source_file: currentSeedFilename,
      seed_number: seed.number || "",
      seed_title: seed.title || "",
    });

    setStatus(actionStatus, "Generated and linked script.", "success");
    await loadItems();
    const detail = await fetchJSON(`/api/previous/${encodeURIComponent(data.script_filename)}`);
    renderScriptDetail(detail.metadata, detail.source || data.source || "", detail.run_url || data.run_url);
  } catch (error) {
    setStatus(actionStatus, error.message, "error");
  } finally {
    button.disabled = false;
  }
}

async function openScriptFromSeed(filename) {
  try {
    const detail = await fetchJSON(`/api/previous/${encodeURIComponent(filename)}`);
    renderScriptDetail(detail.metadata, detail.source || "", detail.run_url || detail.metadata?.run_url);
  } catch (error) {
    setStatus(previousStatus, error.message, "error");
  }
}

function renderScriptDetail(metadata, source, runUrl) {
  showScriptDetail();
  scriptTitle.textContent = metadata.title || metadata.filename;
  scriptMeta.textContent = `${metadata.filename} · ${metadata.created_at || metadata.modified_at || ""}`;
  scriptActions.innerHTML = joinLinks(
    outputLink(metadata.filename, "Download Python script"),
    runLink(runUrl),
    editLink(metadata.filename)
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

document.addEventListener("click", event => {
  const target = event.target.closest(".script-detail-link");
  if (!target) return;
  const filename = target.dataset.scriptFilename;
  if (filename) openScriptFromSeed(filename);
});

loadItems();
