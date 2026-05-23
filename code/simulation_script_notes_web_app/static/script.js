const $ = (id) => document.getElementById(id);

let currentNotes = [];
let editingNoteId = null;
let currentSource = "";

function setStatus(message, isError = false) {
  $("noteStatus").textContent = message || "";
  $("noteStatus").classList.toggle("error", isError);
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || "Request failed.");
  return data;
}

function renderTags(tags) {
  const wrap = document.createElement("div");
  if (!Array.isArray(tags)) return wrap;

  for (const tag of tags) {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = tag;
    wrap.appendChild(span);
  }
  return wrap;
}

function fillForm(note) {
  editingNoteId = note.id;
  $("noteType").value = note.note_type || "core_sentence";
  $("noteTitle").value = note.title || "";
  $("noteText").value = note.text || "";
  $("noteTags").value = Array.isArray(note.tags) ? note.tags.join(", ") : "";
  $("saveNoteBtn").textContent = "Save note changes";
  $("cancelEditBtn").hidden = false;
  setStatus("");
}

function clearForm() {
  editingNoteId = null;
  $("noteType").value = "core_sentence";
  $("noteTitle").value = "";
  $("noteText").value = "";
  $("noteTags").value = "";
  $("saveNoteBtn").textContent = "Add note";
  $("cancelEditBtn").hidden = true;
}

function renderNotes(notes) {
  currentNotes = Array.isArray(notes) ? notes : [];
  const list = $("notesList");
  list.innerHTML = "";

  if (!currentNotes.length) {
    list.textContent = "No notes yet.";
    return;
  }

  for (const note of currentNotes.slice().reverse()) {
    const card = document.createElement("article");
    card.className = "note-card";

    const typeBadge = document.createElement("div");
    const noteType = note.note_type || "core_sentence";
    typeBadge.className = `note-type-badge ${noteType === "next_sentence" ? "next" : "core"}`;
    typeBadge.textContent = noteType === "next_sentence" ? "Next sentence note" : "Core sentence note";

    const title = document.createElement("h3");
    title.textContent = note.title || "Untitled note";

    const body = document.createElement("p");
    body.textContent = note.text || "";

    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = `Created ${note.created_at || "unknown"} • Updated ${note.updated_at || "unknown"}`;

    const actions = document.createElement("div");
    actions.className = "actions";

    const editBtn = document.createElement("button");
    editBtn.className = "secondary";
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", () => fillForm(note));

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "danger";
    deleteBtn.textContent = "Delete";
    deleteBtn.addEventListener("click", () => deleteNote(note.id));

    actions.append(editBtn, deleteBtn);

    if ((note.note_type || "core_sentence") === "next_sentence") {
      const branchLink = document.createElement("a");
      branchLink.href = `/branch/from-note/${encodeURIComponent(filename)}/${encodeURIComponent(note.id)}`;
      branchLink.textContent = "Open as branch core sentence";
      branchLink.target = "_blank";
      actions.appendChild(branchLink);
    }
    card.append(typeBadge, title, body, renderTags(note.tags), meta, actions);
    list.appendChild(card);
  }
}

async function loadScript() {
  try {
    const data = await fetchJson(`/api/script/${encodeURIComponent(filename)}`);
    currentSource = data.source || "";
    $("source").textContent = currentSource;
    renderNotes(data.notes || []);
  } catch (error) {
    $("source").textContent = error.message;
  }
}

async function saveNote() {
  const note_type = $("noteType").value;
  const title = $("noteTitle").value.trim();
  const text = $("noteText").value.trim();
  const tags = $("noteTags").value.trim();

  if (!text) {
    setStatus("Note text is required.", true);
    return;
  }

  const url = editingNoteId
    ? `/api/script/${encodeURIComponent(filename)}/notes/${encodeURIComponent(editingNoteId)}`
    : `/api/script/${encodeURIComponent(filename)}/notes`;

  setStatus("Saving note...");

  try {
    const data = await fetchJson(url, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({note_type, title, text, tags})
    });

    renderNotes(data.notes || []);
    clearForm();
    setStatus("Saved.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function deleteNote(noteId) {
  try {
    const data = await fetchJson(`/api/script/${encodeURIComponent(filename)}/notes/${encodeURIComponent(noteId)}`, {
      method: "DELETE"
    });
    renderNotes(data.notes || []);
    setStatus("Deleted.");
    if (editingNoteId === noteId) clearForm();
  } catch (error) {
    setStatus(error.message, true);
  }
}

$("saveNoteBtn").addEventListener("click", saveNote);
$("cancelEditBtn").addEventListener("click", clearForm);
$("copyScriptBtn").addEventListener("click", async () => {
  await navigator.clipboard.writeText(currentSource || "");
});

loadScript();
