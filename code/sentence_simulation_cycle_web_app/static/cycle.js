const $=id=>document.getElementById(id);
let allItems=[],items=[],currentIndex=0,playing=true,deadline=0,lastAutoRunNodeId=null;

function link(h,t,target=null){const a=document.createElement("a");a.href=h;a.textContent=t;if(target)a.target=target;return a}
async function fetchJson(u){const r=await fetch(u);const d=await r.json();if(!d.ok)throw new Error(d.error||"Request failed.");return d}
function secondsPerItem(){return Math.max(1,Number($("secondsInput").value||10))}
function resetTimer(){deadline=Date.now()+secondsPerItem()*1000}

function applyFilter(){
  const scriptsOnly=$("scriptsOnlyCheck").checked;
  items=scriptsOnly ? allItems.filter(item=>(item.scripts||[]).some(script=>!script.missing)) : [...allItems];
  if(currentIndex>=items.length) currentIndex=0;
}

function renderPath(path){
  const box=$("storyPath");
  box.innerHTML="";
  if(!path||!path.length){box.textContent="No path.";return}
  path.forEach((item,index)=>{
    const span=document.createElement("span");
    span.textContent=item.title||`Sentence ${index+1}`;
    box.appendChild(span);
    if(index<path.length-1){
      const sep=document.createElement("span");
      sep.textContent=" → ";
      box.appendChild(sep);
    }
  });
}

async function renderScriptPreview(card,filename){
  if(!$("showSourceCheck").checked)return;
  const pre=document.createElement("pre");
  pre.className="code-preview";
  pre.textContent="Loading preview...";
  card.appendChild(pre);
  try{
    const data=await fetchJson(`/api/script/${encodeURIComponent(filename)}`);
    pre.textContent=data.source||"";
  }catch(e){
    pre.textContent=e.message;
  }
}

function renderScripts(item){
  const box=$("scripts");
  box.innerHTML="";
  if(!item.scripts||!item.scripts.length){
    box.textContent="No scripts tied to this sentence.";
    return;
  }

  item.scripts.forEach(script=>{
    const card=document.createElement("article");
    card.className="script-card";

    const title=document.createElement("h4");
    title.textContent=script.filename+(script.missing?" (missing)":"");

    const meta=document.createElement("p");
    meta.className="meta";
    meta.textContent=script.note||`${script.size_bytes||0} bytes`;

    const actions=document.createElement("p");
    actions.className="script-actions";

    if(!script.missing){
      actions.append(
        link(script.view_url,"Open source","_blank"),
        link(script.download_url,"Download"),
        link(script.run_url,"Open and run","_blank")
      );
    }

    card.append(title,meta,actions);
    box.appendChild(card);
    if(!script.missing)renderScriptPreview(card,script.filename);
  });
}

function renderQueue(){
  const queue=$("queue");
  queue.innerHTML="";

  if(!items.length){
    queue.textContent=$("scriptsOnlyCheck").checked
      ? "No sentence nodes with attached scripts."
      : "No sentence nodes found.";
    return;
  }

  items.forEach((item,index)=>{
    const row=document.createElement("div");
    row.className=`queue-item ${index===currentIndex?"active":""}`;
    row.textContent=`${index+1}. ${item.title||"Untitled"} (${item.script_count} scripts)`;
    row.addEventListener("click",()=>{
      currentIndex=index;
      renderCurrent(true);
    });
    queue.appendChild(row);
  });
}

function renderCurrent(reset=false){
  if(!items.length){
    $("counter").textContent=`0 / 0${$("scriptsOnlyCheck").checked?" • scripts only":""}`;
    $("title").textContent=$("scriptsOnlyCheck").checked ? "No scripted sentences" : "No items";
    $("sentence").textContent=$("scriptsOnlyCheck").checked
      ? "No sentence nodes currently have scripts attached."
      : "No sentence nodes found.";
    $("storyPath").textContent="";
    $("storyText").textContent="";
    $("scripts").textContent="";
    renderQueue();
    return;
  }

  const item=items[currentIndex];
  $("counter").textContent=`${currentIndex+1} / ${items.length}${$("scriptsOnlyCheck").checked?" • scripts only":""}`;
  $("title").textContent=item.title||"Untitled sentence";
  $("sentence").textContent=item.sentence||"";
  $("storyText").textContent=item.story||"";
  renderPath(item.path||[]);
  renderScripts(item);
  renderQueue();

  if($("autoRunCheck").checked&&item.scripts?.length&&item.node_id!==lastAutoRunNodeId){
    const first=item.scripts.find(s=>!s.missing&&s.run_url);
    if(first){
      window.open(first.run_url,"_blank");
      lastAutoRunNodeId=item.node_id;
    }
  }

  if(reset)resetTimer();
}

function nextItem(){
  if(!items.length)return;
  currentIndex=(currentIndex+1)%items.length;
  renderCurrent(true);
}

function prevItem(){
  if(!items.length)return;
  currentIndex=(currentIndex-1+items.length)%items.length;
  renderCurrent(true);
}

function tick(){
  if(playing&&items.length){
    const remaining=Math.max(0,deadline-Date.now());
    $("timerText").textContent=String(Math.ceil(remaining/1000));
    $("progressBar").style.width=`${Math.max(0,Math.min(100,(remaining/(secondsPerItem()*1000))*100))}%`;
    if(remaining<=0)nextItem();
  }
  requestAnimationFrame(tick);
}

async function loadItems(){
  const data=await fetchJson("/api/cycle-items");
  allItems=data.items||[];
  currentIndex=0;
  lastAutoRunNodeId=null;
  applyFilter();
  resetTimer();
  renderCurrent(false);
}

$("playPauseBtn").addEventListener("click",()=>{
  playing=!playing;
  $("playPauseBtn").textContent=playing?"Pause":"Play";
  resetTimer();
});
$("nextBtn").addEventListener("click",nextItem);
$("prevBtn").addEventListener("click",prevItem);
$("reloadBtn").addEventListener("click",loadItems);
$("secondsInput").addEventListener("change",resetTimer);
$("showSourceCheck").addEventListener("change",()=>renderCurrent(false));
$("scriptsOnlyCheck").addEventListener("change",()=>{
  currentIndex=0;
  applyFilter();
  resetTimer();
  renderCurrent(false);
});

loadItems().catch(e=>{
  $("title").textContent="Error";
  $("sentence").textContent=e.message;
});
resetTimer();
tick();
