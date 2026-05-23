const $ = (id) => document.getElementById(id);

function setStatus(id, message, isError = false) {
  const el = $(id);
  el.textContent = message || "";
  el.classList.toggle("error", isError);
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

function renderScripts(scripts) {
  const list = $("branchScripts");
  list.innerHTML = "";

  if (!scripts || scripts.length === 0) {
    list.textContent = "No scripts attached to this branch yet.";
    return;
  }

  for (const script of scripts) {
    const card = document.createElement("article");
    card.className = "script-card";

    const title = document.createElement("h3");
    title.textContent = script.filename;

    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = `${script.size_bytes} bytes • modified ${script.modified_at || ""} • attached ${script.created_at || ""}`;

    const actions = document.createElement("p");
    actions.className = "actions";
    actions.append(
      createLink(`/script/${encodeURIComponent(script.filename)}`, "Open notes"),
      document.createTextNode(" "),
      createLink(script.download_url, "Download"),
      document.createTextNode(" "),
      createLink(script.run_url, "Open and run", "_blank")
    );

    card.append(title, meta, actions);

    if (script.generation_instruction) {
      const note = document.createElement("p");
      note.className = "meta";
      note.textContent = `Instruction: ${script.generation_instruction}`;
      card.appendChild(note);
    }

    if (script.note) {
      const manualNote = document.createElement("p");
      manualNote.className = "meta";
      manualNote.textContent = `Note: ${script.note}`;
      card.appendChild(manualNote);
    }

    list.appendChild(card);
  }
}

function renderSourceNote(note) {
  const box = $("sourceNote");
  box.innerHTML = "";
  if (!note) {
    box.textContent = "Source note not found.";
    return;
  }

  const badge = document.createElement("div");
  badge.className = "note-type-badge next";
  badge.textContent = "Next sentence note";

  const title = document.createElement("h3");
  title.textContent = note.title || "Source next sentence";

  const text = document.createElement("p");
  text.textContent = note.text || "";

  box.append(badge, title, text);
}

async function loadBranch() {
  try {
    const data = await fetchJson(`/api/branch/${encodeURIComponent(branchId)}`);
    const branch = data.branch;

    $("branchTitle").value = branch.title || "";
    $("coreSentence").value = branch.core_sentence || "";
    $("branchSubtitle").textContent = branch.core_sentence || "Next sentence opened as a core sentence branch.";

    $("branchMeta").innerHTML = "";
    const parent = document.createElement("p");
    parent.textContent = `Parent script: ${branch.parent_script_filename || ""}`;
    const branchLine = document.createElement("p");
    branchLine.textContent = `Branch ID: ${branch.branch_id || ""}`;
    const updated = document.createElement("p");
    updated.textContent = `Updated: ${branch.updated_at || branch.created_at || ""}`;
    $("branchMeta").append(parent, branchLine, updated);

    if (branch.parent_script_filename) {
      $("parentScriptLink").href = `/script/${encodeURIComponent(branch.parent_script_filename)}`;
    }

    renderSourceNote(data.parent_note);
    renderScripts(data.scripts || []);
  } catch (error) {
    setStatus("branchStatus", error.message, true);
  }
}

async function saveBranch() {
  try {
    setStatus("branchStatus", "Saving...");
    const data = await fetchJson(`/api/branch/${encodeURIComponent(branchId)}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        title: $("branchTitle").value.trim(),
        core_sentence: $("coreSentence").value.trim()
      })
    });
    setStatus("branchStatus", "Saved branch core sentence.");
    await loadBranch();
  } catch (error) {
    setStatus("branchStatus", error.message, true);
  }
}

async function saveManualScript() {
  try {
    setStatus("manualScriptStatus", "Saving manual script...");
    $("saveManualScriptBtn").disabled = true;

    const data = await fetchJson(`/api/branch/${encodeURIComponent(branchId)}/manual-script`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        filename: $("manualScriptFilename").value.trim(),
        note: $("manualScriptNote").value.trim(),
        source: $("manualScriptSource").value
      })
    });

    setStatus("manualScriptStatus", `Saved ${data.script.filename}`);
    $("manualScriptFilename").value = "";
    $("manualScriptNote").value = "";
    $("manualScriptSource").value = "";
    await loadBranch();
  } catch (error) {
    setStatus("manualScriptStatus", error.message, true);
  } finally {
    $("saveManualScriptBtn").disabled = false;
  }
}

$("saveBranchBtn").addEventListener("click", saveBranch);
$("saveManualScriptBtn").addEventListener("click", saveManualScript);

loadBranch();
