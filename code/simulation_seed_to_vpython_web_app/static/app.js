const $ = (id) => document.getElementById(id);

let selectedSeedFile = null;

function setText(id, text) {
  $(id).textContent = text || "";
}

function createLink(href, text, target = null) {
  const a = document.createElement("a");
  a.href = href;
  a.textContent = text;
  if (target) a.target = target;
  return a;
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || "Request failed.");
  return data;
}

async function loadSeedFiles() {
  const list = $("seedFileList");
  list.innerHTML = "Loading...";
  try {
    const data = await fetchJson("/api/seeds");
    list.innerHTML = "";

    if (!data.items.length) {
      list.textContent = "No seed JSON files found. Put seed JSON files in outputs/seeds/.";
      return;
    }

    for (const item of data.items) {
      const card = document.createElement("article");
      card.className = "file-card";

      const title = document.createElement("h3");
      title.textContent = item.input_phrase || item.filename;

      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = `${item.entry_count} seeds • ${item.created_at || "unknown date"}`;

      const filename = document.createElement("p");
      filename.className = "meta";
      filename.textContent = item.filename;

      const openBtn = document.createElement("button");
      openBtn.textContent = "Open seed file";
      openBtn.addEventListener("click", () => loadSeedFile(item.filename));

      card.append(title, meta, filename, openBtn);
      list.appendChild(card);
    }
  } catch (error) {
    list.textContent = error.message;
  }
}

async function loadSeedFile(filename) {
  selectedSeedFile = filename;
  const container = $("seedEntries");
  container.innerHTML = "Loading seed entries...";

  try {
    const data = await fetchJson(`/api/seed-file/${encodeURIComponent(filename)}`);
    setText("selectedSeedTitle", data.input_phrase || filename);
    setText("selectedSeedMeta", `${data.entries.length} seeds • ${data.created_at || ""}`);
    container.innerHTML = "";

    for (const entry of data.entries) {
      container.appendChild(renderSeedEntry(filename, entry));
    }
  } catch (error) {
    container.textContent = error.message;
  }
}

function renderSeedEntry(seedFile, entry) {
  const card = document.createElement("article");
  card.className = "seed-card";
  card.dataset.seedFile = seedFile;
  card.dataset.seedNumber = entry.number;
  card.dataset.seedText = entry.seed || "";

  const title = document.createElement("h3");
  title.textContent = `${entry.number}. ${entry.title || "Untitled seed"}`;

  const desc = document.createElement("p");
  desc.textContent = entry.description || entry.seed || "";

  const seedText = document.createElement("p");
  seedText.className = "meta";
  seedText.textContent = entry.seed || "";

  const status = document.createElement("p");
  status.className = "status";

  const generateBtn = document.createElement("button");
  generateBtn.textContent = "Generate VPython script";
  generateBtn.addEventListener("click", () => generateScript(card, status));

  card.append(title, desc, seedText, generateBtn, status);

  const linksBox = renderLinkedScripts(entry.scripts || []);
  card.appendChild(linksBox);

  return card;
}

function renderLinkedScripts(scripts) {
  const box = document.createElement("div");
  box.className = "link-list";

  const heading = document.createElement("h4");
  heading.textContent = scripts.length ? "Linked scripts" : "No linked scripts yet";
  box.appendChild(heading);

  for (const script of scripts) {
    const row = document.createElement("p");
    row.className = "actions";
    row.append(
      createLink(script.open_url, script.filename),
      document.createTextNode(" "),
      createLink(script.download_url, "Download"),
      document.createTextNode(" "),
      createLink(script.edit_url, "Edit"),
      document.createTextNode(" "),
      createLink(script.run_url, "Open and run", "_blank")
    );
    box.appendChild(row);
  }

  return box;
}

async function generateScript(card, statusEl) {
  const seedFile = card.dataset.seedFile;
  const seedNumber = card.dataset.seedNumber;
  const seedText = card.dataset.seedText;
  const model = $("scriptModel").value.trim();
  const temperature = $("scriptTemperature").value.trim();

  statusEl.textContent = "Generating linked VPython script...";
  statusEl.classList.remove("error");

  const button = card.querySelector("button");
  button.disabled = true;

  try {
    const data = await fetchJson("/api/generate-script", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        seed_file: seedFile,
        seed_number: seedNumber,
        seed_text: seedText,
        model,
        temperature
      })
    });

    statusEl.textContent = `Generated ${data.script.filename}`;
    await loadSeedFile(seedFile);
    await loadScripts();
  } catch (error) {
    statusEl.textContent = error.message;
    statusEl.classList.add("error");
  } finally {
    button.disabled = false;
  }
}

async function loadScripts() {
  const list = $("scriptList");
  list.innerHTML = "Loading...";
  try {
    const data = await fetchJson("/api/scripts");
    list.innerHTML = "";

    if (!data.items.length) {
      list.textContent = "No scripts generated yet.";
      return;
    }

    for (const script of data.items) {
      const card = document.createElement("article");
      card.className = "script-card";

      const title = document.createElement("h3");
      title.textContent = script.filename;

      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = `${script.size_bytes} bytes • modified ${script.modified_at}`;

      const actions = document.createElement("p");
      actions.className = "actions";
      actions.append(
        createLink(script.open_url, "Open script"),
        document.createTextNode(" "),
        createLink(script.download_url, "Download"),
        document.createTextNode(" "),
        createLink(script.edit_url, "Edit"),
        document.createTextNode(" "),
        createLink(script.run_url, "Open and run", "_blank")
      );

      card.append(title, meta, actions);
      list.appendChild(card);
    }
  } catch (error) {
    list.textContent = error.message;
  }
}

$("refreshSeedsBtn").addEventListener("click", loadSeedFiles);
$("refreshScriptsBtn").addEventListener("click", loadScripts);

loadSeedFiles();
loadScripts();
