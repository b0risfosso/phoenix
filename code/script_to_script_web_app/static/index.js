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

function renderPath(path) {
  const box = document.createElement("div");
  box.className = "story-path";
  if (!path || !path.length) return box;

  path.forEach((item, index) => {
    const span = document.createElement("span");
    span.textContent = item.title || `Sentence ${index + 1}`;
    box.appendChild(span);

    if (index < path.length - 1) {
      const sep = document.createElement("span");
      sep.textContent = " → ";
      box.appendChild(sep);
    }
  });

  return box;
}

function renderScriptActions(script) {
  const actions = document.createElement("p");
  actions.className = "actions";

  if (script.missing) {
    const missing = document.createElement("span");
    missing.className = "meta";
    missing.textContent = `${script.filename} missing`;
    actions.appendChild(missing);
    return actions;
  }

  actions.append(
    createLink(script.view_url, script.filename),
    document.createTextNode(" "),
    createLink(script.download_url, "Download"),
    document.createTextNode(" "),
    createLink(script.run_url, "Open and run", "_blank")
  );

  return actions;
}

function renderStoryCard(story) {
  const card = document.createElement("article");
  card.className = `story-card ${story.script_count > 0 ? "story-scripted" : "story-unscripted"}`;

  const title = document.createElement("h3");
  title.textContent = story.title || "Untitled story";

  const badge = document.createElement("span");
  badge.className = `badge ${story.script_count > 0 ? "scripted" : "unscripted"}`;
  badge.textContent = story.script_count > 0
    ? `${story.script_count} script${story.script_count === 1 ? "" : "s"}`
    : "no scripts";

  const sentence = document.createElement("p");
  sentence.className = "sentence-snippet";
  sentence.textContent = story.sentence || story.story || "";

  const fullStory = document.createElement("p");
  fullStory.className = "story-preview";
  fullStory.textContent = story.story || story.sentence || "";

  const scriptsBox = document.createElement("div");
  scriptsBox.className = "story-scripts";

  if (story.scripts && story.scripts.length) {
    const scriptHeading = document.createElement("h4");
    scriptHeading.textContent = "Open linked script";
    scriptsBox.appendChild(scriptHeading);

    for (const script of story.scripts) {
      const row = document.createElement("div");
      row.className = "script-row";
      row.appendChild(renderScriptActions(script));

      const meta = document.createElement("p");
      meta.className = "meta";
      meta.textContent = `${script.parent_count || 0} parents • ${script.child_count || 0} children`;
      row.appendChild(meta);

      scriptsBox.appendChild(row);
    }
  } else {
    const none = document.createElement("p");
    none.className = "meta";
    none.textContent = "No scripts linked to this story yet.";
    scriptsBox.appendChild(none);
  }

  card.append(title, badge, sentence, renderPath(story.story_path), fullStory, scriptsBox);

  card.addEventListener("click", (event) => {
    if (event.target.tagName.toLowerCase() === "a") return;
    $("selectedStoryPreview").textContent = story.story || story.sentence || "No story text.";
  });

  return card;
}

async function loadStories() {
  const list = $("storyList");
  const q = encodeURIComponent($("searchBox").value.trim());
  const scriptedOnly = $("scriptedOnlyCheck").checked;
  list.textContent = "Loading stories...";

  try {
    const data = await fetchJson(`/api/stories?q=${q}`);
    let stories = data.items || [];

    if (scriptedOnly) {
      stories = stories.filter(story => story.script_count > 0);
    }

    list.innerHTML = "";
    $("countLabel").textContent = `${stories.length} stor${stories.length === 1 ? "y" : "ies"}`;

    if (!stories.length) {
      list.textContent = "No stories found.";
      return;
    }

    for (const story of stories) {
      list.appendChild(renderStoryCard(story));
    }
  } catch (error) {
    list.textContent = error.message;
  }
}

let searchTimer = null;
$("searchBox").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadStories, 250);
});
$("scriptedOnlyCheck").addEventListener("change", loadStories);
$("refreshBtn").addEventListener("click", loadStories);

loadStories();
