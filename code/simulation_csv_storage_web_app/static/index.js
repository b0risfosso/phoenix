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
  const scriptsBox = document.createElement("div");
  scriptsBox.className = "tree-node-scripts";

  if (!node.scripts || !node.scripts.length) {
    const none = document.createElement("p");
    none.className = "meta";
    none.textContent = "No scripts attached to this sentence.";
    scriptsBox.appendChild(none);
    return scriptsBox;
  }

  for (const script of node.scripts) {
    const row = document.createElement("div");
    row.className = "script-card compact-script-card";

    const h = document.createElement("h3");
    h.textContent = script.filename;

    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = `${script.csv_child_count || 0} CSV child script${script.csv_child_count === 1 ? "" : "s"}`;

    const actions = document.createElement("p");
    actions.className = "actions";
    if (!script.missing) {
      actions.append(
        link(script.view_url, "Open / attach CSV script"),
        document.createTextNode(" "),
        link(script.download_url, "Download")
      );
    } else {
      actions.textContent = "Script file missing.";
    }

    row.append(h, meta, actions);
    scriptsBox.appendChild(row);
  }

  return scriptsBox;
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
  toggle.title = hasChildren(node) ? "Expand/collapse branch" : "No child branches";
  toggle.addEventListener("click", (event) => {
    event.stopPropagation();
    if (collapsed.has(nodeId)) collapsed.delete(nodeId);
    else collapsed.add(nodeId);
    renderTree();
  });

  const heading = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = node.title || (depth === 0 ? "Core sentence" : "Next sentence");
  const type = document.createElement("p");
  type.className = "meta";
  type.textContent = depth === 0 ? "Core sentence" : `Next sentence branch • depth ${depth}`;
  heading.append(title, type);

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
  childBadge.textContent = `${(node.children || []).length} next sentence${(node.children || []).length === 1 ? "" : "s"}`;
  badges.append(scriptBadge, childBadge);

  card.append(top, sentence, renderPath(node.story_path), badges, renderScripts(node));

  card.addEventListener("click", () => {
    $("selectedStory").textContent = node.story || node.sentence || "No story text.";
  });

  wrapper.appendChild(card);

  if (!collapsed.has(nodeId)) {
    const children = document.createElement("div");
    children.className = "tree-children";
    for (const childId of node.children || []) {
      children.appendChild(renderNode(childId, depth + 1));
    }
    wrapper.appendChild(children);
  }

  return wrapper;
}

function renderTree() {
  const tree = $("storyTree");
  tree.innerHTML = "";

  const roots = treeData.root_ids || [];
  const nodes = treeData.nodes || {};
  $("countLabel").textContent =
    `${treeData.node_count || 0} sentence${treeData.node_count === 1 ? "" : "s"} • ${treeData.scripted_node_count || 0} with scripts`;

  if (!roots.length || !Object.keys(nodes).length) {
    tree.textContent = "No story tree found.";
    return;
  }

  for (const rootId of roots) {
    tree.appendChild(renderNode(rootId, 0));
  }
}

async function loadTree() {
  const q = encodeURIComponent($("searchBox").value.trim());
  const scripted = $("scriptedOnlyCheck").checked ? "true" : "false";
  $("storyTree").textContent = "Loading story tree...";

  try {
    treeData = await fetchJson(`/api/story-tree?q=${q}&scripted=${scripted}`);
    // Remove collapsed IDs that are no longer visible after search/filter.
    for (const nodeId of [...collapsed]) {
      if (!treeData.nodes[nodeId]) collapsed.delete(nodeId);
    }
    renderTree();
  } catch (error) {
    $("storyTree").textContent = error.message;
  }
}

function collapseAll() {
  collapsed.clear();
  for (const [nodeId, node] of Object.entries(treeData.nodes || {})) {
    if (hasChildren(node)) collapsed.add(nodeId);
  }
  renderTree();
}

function expandAll() {
  collapsed.clear();
  renderTree();
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

loadTree();
