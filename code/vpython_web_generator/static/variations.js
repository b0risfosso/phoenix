const originalFilename = window.ORIGINAL_SCRIPT_FILENAME;

const originalTitle = document.getElementById("variationOriginalTitle");
const originalMeta = document.getElementById("variationOriginalMeta");
const originalActions = document.getElementById("variationOriginalActions");
const originalCode = document.getElementById("variationOriginalCode");
const variationRequest = document.getElementById("variationRequest");
const variationModel = document.getElementById("variationModel");
const variationTemperature = document.getElementById("variationTemperature");
const generateVariationButton = document.getElementById("generateVariationButton");
const reloadVariationsButton = document.getElementById("reloadVariationsButton");
const variationStatus = document.getElementById("variationStatus");
const variationList = document.getElementById("variationList");
const copyOriginalToManualButton = document.getElementById("copyOriginalToManualButton");
const manualVariationNote = document.getElementById("manualVariationNote");
const manualVariationSource = document.getElementById("manualVariationSource");
const saveManualVariationButton = document.getElementById("saveManualVariationButton");

let originalSource = "";

function setStatus(message, mode = "") {
  variationStatus.textContent = message || "";
  variationStatus.className = `status ${mode}`.trim();
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function outputLink(filename, label) {
  return filename ? `<a href="/outputs/${encodeURIComponent(filename)}">${escapeHTML(label)}</a>` : "";
}

function runLink(runUrl, label = "Open and run") {
  return runUrl ? `<a href="${runUrl}" target="_blank" rel="noopener">${escapeHTML(label)}</a>` : "";
}

function editLink(filename, label = "Edit script") {
  return filename ? `<a href="/script-editor/${encodeURIComponent(filename)}" target="_blank" rel="noopener">${escapeHTML(label)}</a>` : "";
}

function variationsLink(filename, label = "View variations") {
  return filename ? `<a href="/variations/${encodeURIComponent(filename)}">${escapeHTML(label)}</a>` : "";
}

function joinLinks(...links) {
  return links.filter(Boolean).join('<span class="link-separator">•</span>');
}

function bytesToLabel(bytes) {
  if (!Number.isFinite(bytes)) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function requestJSON(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || data.message || `Request failed with status ${response.status}`);
  }
  return data;
}

async function postJSON(url, payload) {
  return requestJSON(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function renderOriginal(original) {
  const metadata = original.metadata || {};
  originalSource = original.source || "";
  originalTitle.textContent = metadata.title || original.filename || originalFilename;
  originalMeta.textContent = `${metadata.filename || original.filename || originalFilename} · ${bytesToLabel(metadata.size_bytes || 0)} · ${metadata.modified_at || ""}`;
  originalCode.textContent = originalSource;
  originalActions.innerHTML = joinLinks(
    outputLink(original.download || metadata.filename, "Download original"),
    runLink(original.run_url),
    editLink(metadata.filename || original.filename),
    variationsLink(metadata.filename || original.filename)
  );
}

function renderVariations(variations) {
  variationList.innerHTML = "";

  if (!variations.length) {
    variationList.innerHTML = '<div class="empty-state small">No variations saved for this original yet.</div>';
    return;
  }

  for (const item of variations) {
    const metadata = item.metadata || {};
    const article = document.createElement("article");
    article.className = "variation-card";
    article.innerHTML = `
      <div class="batch-card-header">
        <div>
          <span class="batch-badge complete">${escapeHTML(item.source || "variation")}</span>
          <h3>${escapeHTML(metadata.title || item.filename)}</h3>
          <p class="detail-meta">${escapeHTML(item.filename)} · ${escapeHTML(item.created_at || metadata.modified_at || "")}</p>
        </div>
        <div class="downloads variation-actions">${joinLinks(
          outputLink(item.download || item.filename, "Download"),
          runLink(item.run_url),
          editLink(item.filename, "Edit"),
          variationsLink(item.filename, "Build from this variation")
        )}</div>
      </div>
      <p><strong>Variation request:</strong> ${escapeHTML(item.request_text || "")}</p>
      <details class="source-preview">
        <summary>Python preview (${item.source_length || 0} characters)</summary>
        <pre>${escapeHTML(item.source_preview || "")}</pre>
      </details>
    `;
    variationList.appendChild(article);
  }
}

async function loadVariations() {
  setStatus("Loading variation page...");
  const data = await requestJSON(`/api/variations/${encodeURIComponent(originalFilename)}`);
  renderOriginal(data.original || {});
  renderVariations(data.variations || []);
  setStatus(`Loaded ${(data.variations || []).length} saved variation${(data.variations || []).length === 1 ? "" : "s"}.`, "success");
}

async function generateVariation() {
  const request = variationRequest.value.trim();
  if (!request) {
    setStatus("Enter a variation request first.", "error");
    return;
  }

  generateVariationButton.disabled = true;
  setStatus("Generating variation script...");

  try {
    const data = await postJSON(`/api/variations/${encodeURIComponent(originalFilename)}`, {
      request,
      model: variationModel.value.trim(),
      temperature: variationTemperature.value,
    });
    renderVariations(data.variations || []);
    manualVariationSource.value = data.source || "";
    setStatus(`Created variation: ${data.filename}`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    generateVariationButton.disabled = false;
  }
}

async function saveManualVariation() {
  const source = manualVariationSource.value.trim();
  if (!source) {
    setStatus("Paste or edit Python source before saving a manual variation.", "error");
    return;
  }

  saveManualVariationButton.disabled = true;
  setStatus("Saving manual variation...");

  try {
    const data = await postJSON(`/api/variations/${encodeURIComponent(originalFilename)}/manual`, {
      source,
      note: manualVariationNote.value.trim(),
    });
    renderVariations(data.variations || []);
    setStatus(`Saved manual variation: ${data.filename}`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    saveManualVariationButton.disabled = false;
  }
}

generateVariationButton.addEventListener("click", generateVariation);
reloadVariationsButton.addEventListener("click", () => loadVariations().catch(error => setStatus(error.message, "error")));
copyOriginalToManualButton.addEventListener("click", () => {
  manualVariationSource.value = originalSource;
  setStatus("Copied original script into the manual variation editor.", "success");
});
saveManualVariationButton.addEventListener("click", saveManualVariation);

loadVariations().catch(error => setStatus(error.message, "error"));
