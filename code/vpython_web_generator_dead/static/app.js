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

function makeRunLink(runUrl) {
  if (!runUrl) return "";
  return `<a href="${runUrl}" target="_blank" rel="noopener">Open and run simulation</a>`;
}

function makeEditLink(filename) {
  if (!filename) return "";
  return `<a href="/script-editor/${encodeURIComponent(filename)}" target="_blank" rel="noopener">Edit script</a>`;
}

function joinLinks(...links) {
  return links.filter(Boolean).join('<span class="link-separator">•</span>');
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
    simulationDownloads.innerHTML = joinLinks(
      makeDownloadLink(data.download, "Download Python script"),
      makeRunLink(data.run_url),
      makeEditLink(data.script_filename || data.download)
    );
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

const batchSeedRequestsInput = document.getElementById("batchSeedRequests");
const batchCodeRequestsInput = document.getElementById("batchCodeRequests");
const batchSeedModelInput = document.getElementById("batchSeedModel");
const batchSeedTemperatureInput = document.getElementById("batchSeedTemperature");
const batchSimulationModelInput = document.getElementById("batchSimulationModel");
const batchSimulationTemperatureInput = document.getElementById("batchSimulationTemperature");
const batchSaveSeedsInput = document.getElementById("batchSaveSeeds");
const batchSaveSimulationsInput = document.getElementById("batchSaveSimulations");
const runBatchButton = document.getElementById("runBatchButton");
const clearBatchButton = document.getElementById("clearBatchButton");
const batchStatus = document.getElementById("batchStatus");
const batchResults = document.getElementById("batchResults");

function parseLines(textarea) {
  return textarea.value
    .split("\n")
    .map(line => line.trim())
    .filter(Boolean);
}

function renderBatchResults(results) {
  batchResults.innerHTML = "";

  if (!results.length) {
    batchResults.innerHTML = '<p class="helper-text">No batch results yet.</p>';
    return;
  }

  for (const item of results) {
    const card = document.createElement("article");
    card.className = `batch-card ${item.status === "error" ? "error-card" : ""}`;

    const links = joinLinks(
      makeDownloadLink(item.seed_download, "Download seeds JSON"),
      makeDownloadLink(item.script_download, "Download Python script"),
      makeRunLink(item.run_url),
      makeEditLink(item.script_download)
    );

    const preview = item.source_preview
      ? `<details class="source-preview"><summary>Python preview (${item.source_length || item.source_preview.length} characters)</summary><pre>${escapeHTML(item.source_preview)}</pre></details>`
      : "";

    const seedCountText = item.seed_count
      ? `<p>${item.seed_count} seed ideas generated.</p>`
      : "";

    const errorText = item.error
      ? `<p class="error-text"><strong>Error:</strong> ${escapeHTML(item.error)}</p>`
      : "";

    card.innerHTML = `
      <div class="batch-card-header">
        <h3>${item.index}. ${escapeHTML(item.label || "Untitled request")}</h3>
        <span class="batch-badge ${item.status}">${escapeHTML(item.queue || "batch")}: ${escapeHTML(item.status || "unknown")}</span>
      </div>
      ${seedCountText}
      ${errorText}
      <div class="downloads">${links}</div>
      ${preview}
    `;
    batchResults.appendChild(card);
  }
}

runBatchButton.addEventListener("click", async () => {
  const seedRequests = parseLines(batchSeedRequestsInput);
  const codeRequests = parseLines(batchCodeRequestsInput);
  const totalRequests = seedRequests.length + codeRequests.length;

  if (!totalRequests) {
    setStatus(batchStatus, "Add at least one seed request or code request first.", "error");
    return;
  }

  runBatchButton.disabled = true;
  setStatus(batchStatus, `Processing ${totalRequests} request${totalRequests === 1 ? "" : "s"} sequentially...`);
  batchResults.innerHTML = "";

  try {
    const data = await postJSON("/api/batch", {
      seed_requests: seedRequests,
      code_requests: codeRequests,
      seed_model: batchSeedModelInput.value.trim(),
      seed_temperature: batchSeedTemperatureInput.value,
      simulation_model: batchSimulationModelInput.value.trim(),
      simulation_temperature: batchSimulationTemperatureInput.value,
      save_seeds: batchSaveSeedsInput.checked,
      save_simulations: batchSaveSimulationsInput.checked,
    });

    renderBatchResults(data.results || []);
    const complete = data.complete_count || 0;
    const errors = data.error_count || 0;
    setStatus(batchStatus, `Batch complete: ${complete} completed, ${errors} failed.`, errors ? "error" : "success");
  } catch (error) {
    setStatus(batchStatus, error.message, "error");
  } finally {
    runBatchButton.disabled = false;
  }
});

clearBatchButton.addEventListener("click", () => {
  batchResults.innerHTML = "";
  setStatus(batchStatus, "");
});
