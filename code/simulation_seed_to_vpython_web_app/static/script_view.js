const sourceEl = document.getElementById("source");
const copyBtn = document.getElementById("copyBtn");

async function loadScript() {
  const res = await fetch(`/api/script/${encodeURIComponent(filename)}`);
  const data = await res.json();
  if (!data.ok) {
    sourceEl.textContent = data.error || "Failed to load script.";
    return;
  }
  sourceEl.textContent = data.source || "";
}

copyBtn.addEventListener("click", async () => {
  await navigator.clipboard.writeText(sourceEl.textContent || "");
});

loadScript();
