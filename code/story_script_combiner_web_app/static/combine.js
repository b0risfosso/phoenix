const $ = (id) => document.getElementById(id);
let selectedStories = [];

function link(href, text, target = null) {
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

function renderSelectedStories() {
  const box = $("selectedStories");
  const scriptsBox = $("sourceScripts");
  box.innerHTML = "";
  scriptsBox.innerHTML = "";

  if (!selectedStories.length) {
    box.textContent = "No selected stories.";
    return;
  }

  const combinedText = selectedStories.map((story) => story.story || story.sentence || "").join(" ");
  $("combinedStory").value = combinedText;

  for (const story of selectedStories) {
    const card = document.createElement("article");
    card.className = "source-card";
    const title = document.createElement("h3");
    title.textContent = story.title || "Untitled story";
    const sentence = document.createElement("p");
    sentence.textContent = story.sentence || "";
    const full = document.createElement("p");
    full.className = "meta";
    full.textContent = story.story || "";
    card.append(title, sentence, full);
    box.appendChild(card);

    for (const script of story.scripts || []) {
      const s = document.createElement("article");
      s.className = "source-card";
      const h = document.createElement("h3");
      h.textContent = script.filename;
      const p = document.createElement("p");
      p.className = "actions";
      if (!script.missing) {
        p.append(
          link(script.view_url, "Open/edit", "_blank"),
          document.createTextNode(" "),
          link(script.run_url, "Run/CSV", "_blank"),
          document.createTextNode(" "),
          link(script.download_url, "Download")
        );
      } else {
        p.textContent = "Script file missing.";
      }
      s.append(h, p);
      scriptsBox.appendChild(s);
    }
  }

  if (!scriptsBox.childElementCount) {
    scriptsBox.textContent = "No scripts on selected source stories.";
  }
}

async function loadSelectedStories() {
  try {
    const data = await fetchJson("/api/stories-by-ids", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ids: selectedNodeIds})
    });
    selectedStories = data.items || [];
    renderSelectedStories();
  } catch (error) {
    $("selectedStories").textContent = error.message;
  }
}

async function saveCombined() {
  try {
    $("saveCombineBtn").disabled = true;
    $("saveStatus").textContent = "Saving combined story and script...";
    $("saveStatus").classList.remove("error");

    const data = await fetchJson("/api/combine", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        source_ids: selectedNodeIds,
        title: $("combinedTitle").value.trim(),
        combined_story: $("combinedStory").value.trim(),
        script_filename: $("scriptFilename").value.trim(),
        script_note: $("scriptNote").value.trim(),
        script_source: $("combinedScript").value
      })
    });

    $("saveStatus").textContent = "Saved combined story and script.";
    const result = $("saveResult");
    result.innerHTML = "";
    const card = document.createElement("article");
    card.className = "source-card";
    const h = document.createElement("h3");
    h.textContent = data.script.filename;
    const p = document.createElement("p");
    p.className = "actions";
    p.append(
      link(data.script.view_url, "Open/edit script"),
      document.createTextNode(" "),
      link(data.script.run_url, "Run with CSV"),
      document.createTextNode(" "),
      link(data.script.download_url, "Download")
    );
    card.append(h, p);
    result.appendChild(card);
  } catch (error) {
    $("saveStatus").textContent = error.message;
    $("saveStatus").classList.add("error");
  } finally {
    $("saveCombineBtn").disabled = false;
  }
}

$("saveCombineBtn").addEventListener("click", saveCombined);
loadSelectedStories();
