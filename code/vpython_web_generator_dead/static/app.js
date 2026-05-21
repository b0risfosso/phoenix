const phraseInput = document.getElementById("phrase");
const seedModelInput = document.getElementById("seedModel");
const seedTemperatureInput = document.getElementById("seedTemperature");
const saveSeedsInput = document.getElementById("saveSeeds");
const generateSeedsButton = document.getElementById("generateSeedsButton");
const seedStatus = document.getElementById("seedStatus");
const seedDownloads = document.getElementById("seedDownloads");
const seedsContainer = document.getElementById("seeds");

const selectedSeed = document.getElementById("selectedSeed");
const simulationModelInput = document.getElementById("simulationModel");
const simulationTemperatureInput = document.getElementById("simulationTemperature");
const saveSimulationInput = document.getElementById("saveSimulation");
const generateSimulationButton = document.getElementById("generateSimulationButton");
const copyCodeButton = document.getElementById("copyCodeButton");
const simulationStatus = document.getElementById("simulationStatus");
const simulationDownloads = document.getElementById("simulationDownloads");
const pythonCode = document.getElementById("pythonCode");

function setStatus(element, message, mode = "") {
  element.textContent = message;
  element.className = `status ${mode}`.trim();
}

function makeDownloadLink(filename, label) {
  if (!filename) return "";
  const href = `/outputs/${encodeURIComponent(filename)}`;
  return `<a href="${href}">${label}</a>`;
}

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || data.message || `Request failed with status ${response.status}`);
  }
  return data;
}

function renderSeeds(seeds, rawText) {
  seedsContainer.innerHTML = "";

  if (!seeds.length) {
    const fallback = document.createElement("article");
    fallback.className = "seed-card full";
    fallback.innerHTML = `<h3>Raw seed output</h3><pre>${escapeHTML(rawText)}</pre>`;
    seedsContainer.appendChild(fallback);
    return;
  }

  for (const seed of seeds) {
    const card = document.createElement("button");
    card.className = "seed-card";
    card.type = "button";
    card.innerHTML = `
      <span class="number">${seed.number}</span>
      <h3>${escapeHTML(seed.title)}</h3>
      <p>${escapeHTML(seed.description)}</p>
    `;
    card.addEventListener("click", () => {
      selectedSeed.value = seed.full_text;
      document.querySelectorAll(".seed-card.selected").forEach(node => node.classList.remove("selected"));
      card.classList.add("selected");
      selectedSeed.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    seedsContainer.appendChild(card);
  }
}

function escapeHTML(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

generateSeedsButton.addEventListener("click", async () => {
  const phrase = phraseInput.value.trim();
  if (!phrase) {
    setStatus(seedStatus, "Enter a word or phrase first.", "error");
    return;
  }

  generateSeedsButton.disabled = true;
  setStatus(seedStatus, "Generating simulation seeds...");
  seedDownloads.innerHTML = "";
  seedsContainer.innerHTML = "";

  try {
    const data = await postJSON("/api/seeds", {
      phrase,
      model: seedModelInput.value.trim(),
      temperature: seedTemperatureInput.value,
      save: saveSeedsInput.checked,
    });
    renderSeeds(data.seeds || [], data.raw_text || "");
    setStatus(seedStatus, `Generated ${(data.seeds || []).length || "raw"} seed ideas.`, "success");
    seedDownloads.innerHTML = makeDownloadLink(data.download, "Download seeds JSON");
  } catch (error) {
    setStatus(seedStatus, error.message, "error");
  } finally {
    generateSeedsButton.disabled = false;
  }
});

generateSimulationButton.addEventListener("click", async () => {
  const seed = selectedSeed.value.trim();
  if (!seed) {
    setStatus(simulationStatus, "Select or type a simulation seed first.", "error");
    return;
  }

  generateSimulationButton.disabled = true;
  pythonCode.textContent = "";
  simulationDownloads.innerHTML = "";
  setStatus(simulationStatus, "Generating VPython script...");

  try {
    const data = await postJSON("/api/simulation", {
      seed,
      model: simulationModelInput.value.trim(),
      temperature: simulationTemperatureInput.value,
      save: saveSimulationInput.checked,
    });
    pythonCode.textContent = data.source || "";
    setStatus(simulationStatus, "Generated VPython script.", "success");
    simulationDownloads.innerHTML = makeDownloadLink(data.download, "Download Python script");
  } catch (error) {
    setStatus(simulationStatus, error.message, "error");
  } finally {
    generateSimulationButton.disabled = false;
  }
});

copyCodeButton.addEventListener("click", async () => {
  const code = pythonCode.textContent;
  if (!code.trim()) {
    setStatus(simulationStatus, "No code to copy yet.", "error");
    return;
  }
  await navigator.clipboard.writeText(code);
  setStatus(simulationStatus, "Copied code to clipboard.", "success");
});
