const $ = (id) => document.getElementById(id);

function link(href, text, target = "_blank") {
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

function setStatus(message, isError = false) {
  $("runStatus").textContent = message || "";
  $("runStatus").classList.toggle("error", isError);
}

function renderRunCard(run) {
  const card = document.createElement("article");
  card.className = "run-result-card";

  const h = document.createElement("h3");
  h.textContent = run.run_id || "Run";
  const meta = document.createElement("p");
  meta.className = "meta";
  meta.textContent = `save_csv=${run.save_csv} • run_seconds=${run.run_seconds} • pid=${run.pid || ""} • ${run.started_at || ""}`;
  card.append(h, meta);

  if (run.log_url) {
    const p = document.createElement("p");
    p.appendChild(link(run.log_url, "Open log"));
    card.appendChild(p);
  }

  if (run.run_dir) {
    const p = document.createElement("p");
    p.className = "meta";
    p.textContent = `CSV output directory: ${run.run_dir}`;
    card.appendChild(p);
  }

  if (run.csv_files && run.csv_files.length) {
    for (const csv of run.csv_files) {
      const p = document.createElement("p");
      p.append(
        link(csv.download_url, csv.filename),
        document.createTextNode(` • ${csv.row_count || 0} rows • ${csv.size_bytes || 0} bytes`)
      );
      card.appendChild(p);
    }
  }

  return card;
}

function renderRecent(runs) {
  const box = $("recentRuns");
  box.innerHTML = "";
  if (!runs || !runs.length) {
    box.textContent = "No recent indexed runs.";
    return;
  }
  for (const run of runs) box.appendChild(renderRunCard(run));
}

async function loadRecent() {
  const data = await fetchJson(`/api/runs?script=${encodeURIComponent(filename)}`);
  renderRecent(data.items || []);
}

async function runScript() {
  try {
    setStatus("Starting script process...");
    $("runBtn").disabled = true;

    const data = await fetchJson(`/api/run/${encodeURIComponent(filename)}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        save_csv: $("saveCsvCheck").checked,
        run_seconds: Number($("runSeconds").value || 60)
      })
    });

    $("runResult").innerHTML = "";
    $("runResult").appendChild(renderRunCard(data.run));
    setStatus("Script process started.");
    await loadRecent();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    $("runBtn").disabled = false;
  }
}

$("runBtn").addEventListener("click", runScript);
loadRecent().catch(error => setStatus(error.message, true));
