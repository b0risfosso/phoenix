const $ = (id) => document.getElementById(id);

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

async function loadDataLocation() {
  try {
    const data = await fetchJson("/api/data-location");
    $("dataLocation").textContent = `Shared scripts folder: ${data.scripts_dir}`;
  } catch (error) {
    $("dataLocation").textContent = error.message;
  }
}

async function loadScripts() {
  const list = $("scriptList");
  const q = encodeURIComponent($("searchBox").value.trim());
  const notes = encodeURIComponent($("noteFilter").value);
  const type = encodeURIComponent($("noteTypeFilter").value);
  list.innerHTML = "Loading scripts...";

  try {
    const data = await fetchJson(`/api/scripts?q=${q}&notes=${notes}&type=${type}`);
    list.innerHTML = "";
    $("countLabel").textContent = `${data.items.length} script${data.items.length === 1 ? "" : "s"}`;

    if (!data.items.length) {
      list.textContent = "No scripts found.";
      return;
    }

    for (const script of data.items) {
      const card = document.createElement("article");
      card.className = "script-card";

      const title = document.createElement("h3");
      title.textContent = script.filename;

      const meta = document.createElement("p");
      meta.className = "meta";
      const coreCount = script.core_sentence_note_count || 0;
      const nextCount = script.next_sentence_note_count || 0;
      meta.textContent = `${script.size_bytes} bytes • modified ${script.modified_at} • ${script.note_count} note${script.note_count === 1 ? "" : "s"} • ${coreCount} core • ${nextCount} next`;

      const actions = document.createElement("p");
      actions.className = "actions";
      actions.append(
        createLink(script.view_url, "Open notes"),
        document.createTextNode(" "),
        createLink(script.download_url, "Download"),
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

let searchTimer = null;
$("searchBox").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadScripts, 250);
});
$("noteFilter").addEventListener("change", loadScripts);
$("noteTypeFilter").addEventListener("change", loadScripts);
$("refreshBtn").addEventListener("click", loadScripts);

loadDataLocation();
loadScripts();
