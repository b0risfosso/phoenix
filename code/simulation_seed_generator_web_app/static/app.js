const $ = (id) => document.getElementById(id);

let latestRawOutput = "";

function setStatus(el, message, isError = false) {
  el.textContent = message || "";
  el.classList.toggle("error", isError);
}

function renderSeedCards(container, entries) {
  container.innerHTML = "";
  if (!entries || entries.length === 0) {
    return;
  }

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

function renderActions(container, downloadUrl, filename) {
  container.innerHTML = "";
  if (!downloadUrl) return;

  const download = document.createElement("a");
  download.href = downloadUrl;
  download.textContent = `Download JSON${filename ? ` (${filename})` : ""}`;
  container.appendChild(download);
}

async function generateSeeds() {
  const inputPhrase = $("inputPhrase").value.trim();
  const model = $("model").value.trim();
  const temperature = $("temperature").value;
  const saveOutput = $("saveOutput").checked;

  if (!inputPhrase) {
    setStatus($("singleStatus"), "Enter an input word or phrase.", true);
    return;
  }

  $("generateBtn").disabled = true;
  setStatus($("singleStatus"), "Generating simulation seeds...");

  try {
    const response = await fetch("/api/generate-seeds", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        input_phrase: inputPhrase,
        model,
        temperature,
        save_output: saveOutput
      })
    });

    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "Generation failed.");

    latestRawOutput = data.raw_output || "";
    $("rawOutput").textContent = latestRawOutput;
    $("copyRawBtn").disabled = !latestRawOutput;
    renderSeedCards($("seedCards"), data.entries || []);
    renderActions($("resultActions"), data.download_url, data.saved_filename);
    setStatus($("singleStatus"), `Generated ${data.entries?.length || 0} parsed seed entries.`);
  } catch (error) {
    setStatus($("singleStatus"), error.message, true);
  } finally {
    $("generateBtn").disabled = false;
  }
}

async function batchGenerateSeeds() {
  const inputPhrases = $("batchPhrases").value.trim();
  const model = $("model").value.trim();
  const temperature = $("temperature").value;
  const saveOutput = $("saveOutput").checked;

  if (!inputPhrases) {
    setStatus($("batchStatus"), "Enter at least one line.", true);
    return;
  }

  $("batchBtn").disabled = true;
  $("batchResults").innerHTML = "";
  setStatus($("batchStatus"), "Processing batch sequentially...");

  try {
    const response = await fetch("/api/batch-generate-seeds", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        input_phrases: inputPhrases,
        model,
        temperature,
        save_output: saveOutput
      })
    });

    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "Batch generation failed.");

    for (const result of data.results || []) {
      const card = document.createElement("article");
      card.className = "seed-card";

      const title = document.createElement("h3");
      title.textContent = result.input_phrase || "Batch item";

      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = result.ok
        ? `Generated ${result.entries?.length || 0} parsed seed entries.`
        : `Error: ${result.error}`;

      card.append(title, meta);

      if (result.ok && result.download_url) {
        const action = document.createElement("a");
        action.href = result.download_url;
        action.textContent = "Download JSON";
        card.appendChild(action);
      }

      if (result.ok && result.entries?.length) {
        const list = document.createElement("div");
        list.className = "cards";
        renderSeedCards(list, result.entries.slice(0, 3));
        card.appendChild(list);
      }

      $("batchResults").appendChild(card);
    }

    setStatus($("batchStatus"), `Finished ${data.results?.length || 0} batch requests.`);
  } catch (error) {
    setStatus($("batchStatus"), error.message, true);
  } finally {
    $("batchBtn").disabled = false;
  }
}

async function copyRawOutput() {
  if (!latestRawOutput) return;
  await navigator.clipboard.writeText(latestRawOutput);
}

$("generateBtn").addEventListener("click", generateSeeds);
$("batchBtn").addEventListener("click", batchGenerateSeeds);
$("copyRawBtn").addEventListener("click", copyRawOutput);

$("inputPhrase").addEventListener("keydown", (event) => {
  if (event.key === "Enter") generateSeeds();
});
