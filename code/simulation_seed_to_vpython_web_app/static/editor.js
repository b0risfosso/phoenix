const editor = document.getElementById("editor");
const statusEl = document.getElementById("status");

function setStatus(message, isError = false) {
  statusEl.textContent = message || "";
  statusEl.classList.toggle("error", isError);
}

async function loadScript() {
  const res = await fetch(`/api/script/${encodeURIComponent(filename)}`);
  const data = await res.json();
  if (!data.ok) {
    setStatus(data.error || "Failed to load script.", true);
    return;
  }
  editor.value = data.source || "";
}

async function saveScript(saveAsCopy = false) {
  setStatus("Saving...");
  const res = await fetch(`/api/script/${encodeURIComponent(filename)}`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({source: editor.value, save_as_copy: saveAsCopy})
  });
  const data = await res.json();
  if (!data.ok) {
    setStatus(data.error || "Save failed.", true);
    return;
  }
  setStatus(saveAsCopy ? `Saved copy: ${data.script.filename}` : "Saved changes.");
}

document.getElementById("saveBtn").addEventListener("click", () => saveScript(false));
document.getElementById("saveCopyBtn").addEventListener("click", () => saveScript(true));
document.getElementById("copyBtn").addEventListener("click", async () => {
  await navigator.clipboard.writeText(editor.value || "");
  setStatus("Copied.");
});

loadScript();
