const $ = (id) => document.getElementById(id);

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || "Request failed.");
  return data;
}

function setStatus(message, isError = false) {
  $("status").textContent = message || "";
  $("status").classList.toggle("error", isError);
}

async function loadScript() {
  try {
    const data = await fetchJson(`/api/script/${encodeURIComponent(filename)}`);
    $("sourceEditor").value = data.source || "";
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function saveScript() {
  try {
    setStatus("Saving...");
    await fetchJson(`/api/script/${encodeURIComponent(filename)}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({source: $("sourceEditor").value})
    });
    setStatus("Saved.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

$("saveBtn").addEventListener("click", saveScript);
$("copyBtn").addEventListener("click", async () => {
  await navigator.clipboard.writeText($("sourceEditor").value || "");
  setStatus("Copied.");
});
loadScript();
