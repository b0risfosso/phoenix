const $ = (id) => document.getElementById(id);

let treeData = {root_ids: [], nodes: {}};
const collapsed = new Set();

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

function hasChildren(node) {
  return (node.children || []).length > 0;
}

function renderPath(path) {
  const box = document.createElement("div");
  box.className = "story-path";
  (path || []).forEach((item, index) => {
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

function renderScripts(node) {
  const box = document.createElement("div");
  box.className = "tree-node-scripts";

  if (!node.scripts || !node.scripts.length) {
    const none = document.createElement("p");
    none.className = "meta";
    none.textContent = "No scripts attached.";
    box.appendChild(none);
    return box;
  }

  for (const script of node.scripts) {
    const row = document.createElement("div");
    row.className = "script-card compact-script-card";

    const h = document.createElement("h3");
    h.textContent = script.filename;

    const actions = document.createElement("p");
    actions.className = "actions";

    if (!script.missing) {
      actions.append(
        link(script.view_url, "Open/edit"),
        document.createTextNode(" "),
        link(script.download_url, "Download")
      );
    } else {
      actions.textContent = "Script file missing.";
    }

    row.append(h, actions);
    box.appendChild(row);
  }

  return box;
}

function renderNode(nodeId, depth = 0) {
  const node = treeData.nodes[nodeId];
  if (!node) return document.createDocumentFragment();

  const wrapper = document.createElement("div");
  wrapper.className = "tree-node-wrap";
  wrapper.style.setProperty("--depth", depth);

  const card = document.createElement("article");
  card.className = [
    "tree-node-card",
    depth === 0 ? "core-sentence-node" : "next-sentence-node",
    node.script_count > 0 ? "has-script" : "no-script",
  ].join(" ");

  const top = document.createElement("div");
  top.className = "tree-node-top";

  const toggle = document.createElement("button");
  toggle.className = "tree-toggle secondary";
  toggle.textContent = hasChildren(node) ? (collapsed.has(nodeId) ? "▸" : "▾") : "•";
  toggle.disabled = !hasChildren(node);
  toggle.addEventListener("click", (event) => {
    event.stopPropagation();
    if (collapsed.has(nodeId)) collapsed.delete(nodeId);
    else collapsed.add(nodeId);
    renderTree();
  });

  const heading = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = node.title || (depth === 0 ? "Core sentence" : "Next sentence");
  const kind = document.createElement("p");
  kind.className = "meta";
  kind.textContent = depth === 0 ? "Core sentence" : `Next sentence branch • depth ${depth}`;
  heading.append(title, kind);
  top.append(toggle, heading);

  const sentence = document.createElement("p");
  sentence.className = "tree-sentence";
  sentence.textContent = node.sentence || "";

  const badges = document.createElement("p");
  badges.className = "badge-row";
  const scriptBadge = document.createElement("span");
  scriptBadge.className = `badge ${node.script_count ? "green" : ""}`;
  scriptBadge.textContent = node.script_count
    ? `${node.script_count} script${node.script_count === 1 ? "" : "s"}`
    : "no scripts";
  const childBadge = document.createElement("span");
  childBadge.className = "badge";
  childBadge.textContent = `${(node.children || []).length} branch${(node.children || []).length === 1 ? "" : "es"}`;
  badges.append(scriptBadge, childBadge);

  const actions = document.createElement("p");
  actions.className = "actions";
  actions.append(link(`/story/${encodeURIComponent(nodeId)}`, "Select / generate branches"));

  card.append(top, sentence, renderPath(node.story_path), badges, actions, renderScripts(node));
  card.addEventListener("click", (event) => {
    if (event.target.tagName.toLowerCase() === "a" || event.target.tagName.toLowerCase() === "button") return;
    $("selectedStoryPreview").textContent = node.story || node.sentence || "No story text.";
  });
  wrapper.appendChild(card);

  if (!collapsed.has(nodeId)) {
    const childrenBox = document.createElement("div");
    childrenBox.className = "tree-children";
    for (const childId of node.children || []) {
      childrenBox.appendChild(renderNode(childId, depth + 1));
    }
    wrapper.appendChild(childrenBox);
  }

  return wrapper;
}

function renderTree() {
  const tree = $("storyTree");
  tree.innerHTML = "";

  $("countLabel").textContent =
    `${treeData.node_count || 0} sentence${treeData.node_count === 1 ? "" : "s"} • ${treeData.scripted_node_count || 0} with scripts`;

  if (!treeData.root_ids || !treeData.root_ids.length) {
    tree.textContent = "No story tree found.";
    return;
  }

  for (const rootId of treeData.root_ids) {
    tree.appendChild(renderNode(rootId, 0));
  }
}

async function loadTree() {
  const q = encodeURIComponent($("searchBox").value.trim());
  const scripted = $("scriptedOnlyCheck").checked ? "true" : "false";
  $("storyTree").textContent = "Loading story tree...";

  try {
    treeData = await fetchJson(`/api/story-tree?q=${q}&scripted=${scripted}`);
    for (const nodeId of [...collapsed]) {
      if (!treeData.nodes[nodeId]) collapsed.delete(nodeId);
    }
    renderTree();
  } catch (error) {
    $("storyTree").textContent = error.message;
  }
}

function expandAll() {
  collapsed.clear();
  renderTree();
}

function collapseAll() {
  collapsed.clear();
  for (const [nodeId, node] of Object.entries(treeData.nodes || {})) {
    if (hasChildren(node)) collapsed.add(nodeId);
  }
  renderTree();
}

async function loadDataLocation() {
  try {
    const data = await fetchJson("/api/data-location");
    $("dataLocation").textContent = data.tree_file;
  } catch (error) {
    $("dataLocation").textContent = error.message;
  }
}

let timer = null;
$("searchBox").addEventListener("input", () => {
  clearTimeout(timer);
  timer = setTimeout(loadTree, 250);
});
$("scriptedOnlyCheck").addEventListener("change", loadTree);
$("refreshBtn").addEventListener("click", loadTree);
$("expandAllBtn").addEventListener("click", expandAll);
$("collapseAllBtn").addEventListener("click", collapseAll);

loadDataLocation();
loadTree();
