const $=id=>document.getElementById(id);function status(id,msg,err=false){$(id).textContent=msg||"";$(id).classList.toggle("error",err)}function link(h,t,target=null){const a=document.createElement("a");a.href=h;a.textContent=t;if(target)a.target=target;return a}async function fetchJson(u,o={}){const r=await fetch(u,o);const d=await r.json();if(!d.ok)throw new Error(d.error||"Request failed.");return d}

let sourceScripts = [];

async function loadSourceScripts(){
  try{
    const data = await fetchJson(`/api/story/${encodeURIComponent(nodeId)}/available-source-scripts`);
    sourceScripts = data.items || [];
  }catch(error){
    sourceScripts = [];
  }
}

function renderSourceScriptSelect(select){
  select.innerHTML = "";
  if(!sourceScripts.length){
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No ancestor/current source scripts available";
    select.appendChild(option);
    return;
  }
  for(const script of sourceScripts){
    const option = document.createElement("option");
    option.value = script.filename;
    option.textContent = `${script.filename} — ${script.relationship}`;
    select.appendChild(option);
  }
}function renderPath(path){const box=$("storyPath");box.innerHTML="";(path||[]).forEach((item,index)=>{const span=document.createElement("span");span.textContent=item.title||`Sentence ${index+1}`;box.appendChild(span);if(index<path.length-1){const sep=document.createElement("span");sep.textContent=" → ";box.appendChild(sep)}})}function renderScripts(scripts,container){if(!scripts||!scripts.length){const none=document.createElement("p");none.className="meta";none.textContent="No scripts attached.";container.appendChild(none);return}for(const script of scripts){const row=document.createElement("div");row.className="script-card";const h=document.createElement("h3");h.textContent=script.filename;const p=document.createElement("p");p.className="actions";if(!script.missing){p.append(link(script.view_url,"Open/edit"),document.createTextNode(" "),link(script.download_url,"Download"))}else{p.textContent="Script file missing."}row.append(h,p);container.appendChild(row)}}function renderChild(child){const card=document.createElement("article");card.className=`branch-card ${child.script_count>0?"has-scripts":""}`;const title=document.createElement("h3");title.textContent=child.title||"Next sentence";const sentence=document.createElement("p");sentence.textContent=child.sentence||"";const badges=document.createElement("p");const s=document.createElement("span");s.className=`badge ${child.script_count?"green":""}`;s.textContent=`${child.script_count} script${child.script_count===1?"":"s"}`;const source=document.createElement("span");source.className="badge";source.textContent=child.generated_from||"branch";badges.append(s,source);const actions=document.createElement("p");actions.className="actions";actions.append(link(`/story/${encodeURIComponent(child.id)}`,"Open as story"));const scriptList=document.createElement("div");renderScripts(child.scripts||[],scriptList);const form=document.createElement("div");form.className="inline-script-form";const fl=document.createElement("label");fl.textContent="Script filename optional";const fi=document.createElement("input");fi.type="text";const nl=document.createElement("label");nl.textContent="Script note optional";const ni=document.createElement("textarea");ni.rows=2;const sl=document.createElement("label");sl.textContent="Manual Python script source";const si=document.createElement("textarea");si.rows=10;si.className="code-editor";const btn=document.createElement("button");btn.textContent="Attach script to this next sentence";const st=document.createElement("p");st.className="status";btn.addEventListener("click",async()=>{try{st.textContent="Saving script...";st.classList.remove("error");await fetchJson(`/api/story/${encodeURIComponent(child.id)}/script`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filename:fi.value.trim(),note:ni.value.trim(),source:si.value})});fi.value="";ni.value="";si.value="";st.textContent="Script attached.";await loadStory()}catch(error){st.textContent=error.message;st.classList.add("error")}});form.append(fl,fi,nl,ni,sl,si,btn,st);

const modForm=document.createElement("div");
modForm.className="inline-script-form";
const modHeader=document.createElement("h3");
modHeader.textContent="Automated script modification";
const sourceLabel=document.createElement("label");
sourceLabel.textContent="Source script to modify";
const sourceSelect=document.createElement("select");
renderSourceScriptSelect(sourceSelect);
const outputLabel=document.createElement("label");
outputLabel.textContent="Output filename optional";
const outputInput=document.createElement("input");
outputInput.type="text";
outputInput.placeholder="modified-branch-script.py";
const modifierLabel=document.createElement("label");
modifierLabel.textContent="Modifier sentence override optional";
const modifierInput=document.createElement("textarea");
modifierInput.rows=3;
modifierInput.placeholder="Leave blank to use this next sentence.";
const modNoteLabel=document.createElement("label");
modNoteLabel.textContent="Script note optional";
const modNoteInput=document.createElement("textarea");
modNoteInput.rows=2;
const modBtn=document.createElement("button");
modBtn.textContent="Generate modified script for this next sentence";
const modStatus=document.createElement("p");
modStatus.className="status";
modBtn.addEventListener("click",async()=>{
  try{
    if(!sourceSelect.value){
      modStatus.textContent="Select a source script first.";
      modStatus.classList.add("error");
      return;
    }
    modBtn.disabled=true;
    modStatus.textContent="Generating modified script...";
    modStatus.classList.remove("error");
    const data=await fetchJson(`/api/story/${encodeURIComponent(child.id)}/modify-script`,{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        source_filename:sourceSelect.value,
        filename:outputInput.value.trim(),
        note:modNoteInput.value.trim(),
        modifier_sentence:modifierInput.value.trim()
      })
    });
    outputInput.value="";
    modifierInput.value="";
    modNoteInput.value="";
    modStatus.textContent=`Generated and attached ${data.script.filename}`;
    await loadStory();
  }catch(error){
    modStatus.textContent=error.message;
    modStatus.classList.add("error");
  }finally{
    modBtn.disabled=false;
  }
});
modForm.append(modHeader,sourceLabel,sourceSelect,outputLabel,outputInput,modifierLabel,modifierInput,modNoteLabel,modNoteInput,modBtn,modStatus);

card.append(title,badges,sentence,actions,scriptList,form,modForm);return card}async function loadStory(){try{await loadSourceScripts();const data=await fetchJson(`/api/story/${encodeURIComponent(nodeId)}`);$("nodeHeader").textContent=data.node.sentence||"";renderPath(data.story_path||[]);$("storyText").textContent=data.story||data.node.sentence||"";const list=$("childrenList");list.innerHTML="";const children=data.children||[];if(!children.length){list.textContent="No next sentence branches yet.";return}for(const child of children)list.appendChild(renderChild(child))}catch(error){status("generateStatus",error.message,true)}}async function generateNext(){try{$("generateBtn").disabled=true;status("generateStatus","Generating 20 next sentences and adding them as child branches...");const data=await fetchJson(`/api/story/${encodeURIComponent(nodeId)}/generate-next`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({use_full_story:$("useFullStoryCheck").checked,input_text:$("customInput").value.trim()})});status("generateStatus",`Created ${data.created_nodes.length} next sentence branches.`);$("customInput").value="";await loadStory()}catch(error){status("generateStatus",error.message,true)}finally{$("generateBtn").disabled=false}}async function addManualNext(){try{const sentence=$("manualSentence").value.trim();if(!sentence){status("manualStatus","Next sentence is required.",true);return}await fetchJson(`/api/story/${encodeURIComponent(nodeId)}/manual-next`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({title:$("manualTitle").value.trim(),sentence})});$("manualTitle").value="";$("manualSentence").value="";status("manualStatus","Manual branch added.");await loadStory()}catch(error){status("manualStatus",error.message,true)}}$("generateBtn").addEventListener("click",generateNext);$("manualNextBtn").addEventListener("click",addManualNext);loadStory();