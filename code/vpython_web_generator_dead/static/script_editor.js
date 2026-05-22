const scriptFilename = window.SCRIPT_FILENAME;
const title = document.getElementById("scriptEditorTitle");
const meta = document.getElementById("scriptEditorMeta");
const statusBox = document.getElementById("scriptEditorStatus");
const actions = document.getElementById("scriptEditorActions");
const editor = document.getElementById("scriptSourceEditor");
const reloadButton = document.getElementById("reloadScriptButton");
const copyButton = document.getElementById("copyEditedScriptButton");
const saveButton = document.getElementById("saveScriptButton");
const saveCopyButton = document.getElementById("saveScriptCopyButton");

let currentFilename = scriptFilename;
let dirty = false;

function setStatus(message, mode = "") {
  statusBox.textContent = message || "";
  statusBox.className = `status ${mode}`.trim();
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function joinLinks(...links) {
  return links.filter(Boolean).join('<span class="link-separator">•</span>');
}

function outputLink(filename, label) {
  return `<a href="/outputs/${encodeURIComponent(filename)}">${escapeHTML(label)}</a>`;
}

function runLink(runUrl, label = "Open and run") {
  return runUrl ? `<a href="${runUrl}" target="_blank" rel="noopener">${escapeHTML(label)}</a>` : "";
}

async function requestJSON(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || data.message || `Request failed with status ${response.status}`);
  }
  return data;
}

function renderActions(filename, runUrl) {
  actions.innerHTML = joinLinks(
    outputLink(filename, "Download Python script"),
    runLink(runUrl),
    `<a href="/previous">Back to previous outputs</a>`
  );
}

function renderScript(data) {
  const metadata = data.metadata || {};
  currentFilename = metadata.filename || currentFilename;
  title.textContent = currentFilename;
  meta.textContent = `${metadata.size_bytes || 0} bytes · ${metadata.modified_at || ""}`;
  editor.value = data.source || "";
  dirty = false;
  renderActions(currentFilename, data.run_url || metadata.run_url);
}

async function loadScript() {
  setStatus("Loading script...");
  const data = await requestJSON(`/api/script/${encodeURIComponent(currentFilename)}`);
  renderScript(data);
  setStatus("Loaded script.", "success");
}

async function saveScript(saveAsCopy = false) {
  const source = editor.value;
  if (!source.trim()) {
    setStatus("Script source cannot be empty.", "error");
    return;
  }

  const button = saveAsCopy ? saveCopyButton : saveButton;
  button.disabled = true;
  setStatus(saveAsCopy ? "Saving edited copy..." : "Saving script changes...");

  try {
    const data = await requestJSON(`/api/script/${encodeURIComponent(currentFilename)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, save_as_copy: saveAsCopy }),
    });
    currentFilename = data.filename || currentFilename;
    title.textContent = currentFilename;
    meta.textContent = `${data.metadata?.size_bytes || source.length} bytes · ${data.metadata?.modified_at || ""}`;
    renderActions(currentFilename, data.run_url);
    dirty = false;
    setStatus(data.message || "Saved.", "success");
    if (saveAsCopy) {
      window.history.replaceState({}, "", `/script-editor/${encodeURIComponent(currentFilename)}`);
    }
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    button.disabled = false;
  }
}

editor.addEventListener("input", () => {
  dirty = true;
});

reloadButton.addEventListener("click", async () => {
  if (dirty && !window.confirm("Reload and discard unsaved edits?")) return;
  try {
    await loadScript();
  } catch (error) {
    setStatus(error.message, "error");
  }
});

copyButton.addEventListener("click", async () => {
  await navigator.clipboard.writeText(editor.value || "");
  setStatus("Copied editor contents to clipboard.", "success");
});

saveButton.addEventListener("click", () => saveScript(false));
saveCopyButton.addEventListener("click", () => saveScript(true));

window.addEventListener("beforeunload", (event) => {
  if (!dirty) return;
  event.preventDefault();
  event.returnValue = "";
});

loadScript().catch(error => setStatus(error.message, "error"));
