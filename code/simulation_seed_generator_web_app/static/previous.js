const $ = (id) => document.getElementById(id);

let selectedRawOutput = "";

function renderSeedCards(container, entries) {
  container.innerHTML = "";
  if (!entries || entries.length === 0) return;

  for (const entry of entries) {
    const card = document.createElement("article");
    card.className = "seed-card";

    const title = document.createElement("h3");
    title.textContent = `${entry.number}. ${entry.title || "Untitled seed"}`;

    const desc = document.createElement("p");
    desc.textContent = entry.description || "";

    const seed = document.createElement("p");
    seed.className = "meta";
    seed.textContent = entry.seed || "";

    card.append(title, desc, seed);
    container.appendChild(card);
  }
}

async function loadPreviousSeeds() {
  $("fileList").innerHTML = "";
  const response = await fetch("/api/previous-seeds");
  const data = await response.json();

  if (!data.ok) {
    $("fileList").textContent = data.error || "Failed to load saved seeds.";
    return;
  }

  if (!data.items.length) {
    $("fileList").textContent = "No saved seed files yet.";
    return;
  }

  for (const item of data.items) {
    const card = document.createElement("article");
    card.className = "file-card";

    const title = document.createElement("h3");
    title.textContent = item.input_phrase || item.filename;

    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = `${item.created_at || "Unknown date"} • ${item.entry_count} entries • ${item.model || "model unknown"}`;

    const openBtn = document.createElement("button");
    openBtn.textContent = "Open";
    openBtn.addEventListener("click", () => openSeedFile(item.filename));

    const download = document.createElement("a");
    download.href = item.download_url;
    download.textContent = "Download JSON";

    card.append(title, meta, openBtn, download);
    $("fileList").appendChild(card);
  }
}

async function openSeedFile(filename) {
  const response = await fetch(`/api/seed-file/${encodeURIComponent(filename)}`);
  const data = await response.json();

  if (!data.ok) {
    $("selectedTitle").textContent = "Error";
    $("selectedRaw").textContent = data.error || "Failed to open file.";
    return;
  }

  const seedData = data.data || {};
  $("selectedTitle").textContent = seedData.input_phrase || filename;
  selectedRawOutput = seedData.raw_output || "";
  $("selectedRaw").textContent = selectedRawOutput;
  $("copySelectedBtn").disabled = !selectedRawOutput;

  $("selectedActions").innerHTML = "";
  const download = document.createElement("a");
  download.href = `/outputs/seeds/${encodeURIComponent(filename)}`;
  download.textContent = "Download JSON";
  $("selectedActions").appendChild(download);

  renderSeedCards($("selectedSeedCards"), seedData.entries || []);
}

async function copySelected() {
  if (!selectedRawOutput) return;
  await navigator.clipboard.writeText(selectedRawOutput);
}

$("refreshBtn").addEventListener("click", loadPreviousSeeds);
$("copySelectedBtn").addEventListener("click", copySelected);

loadPreviousSeeds();
