const $ = (id) => document.getElementById(id);
const state = { installPrompt: null, standaloneFile: window.location.protocol === "file:" };
const apiUrl = (path) => state.standaloneFile ? null : new URL(path.replace(/^\//, ""), window.location.href).toString();
const demo = {
  mode: "demo", generated_urls: ["https://www.kleinanzeigen.de/s-evercade-sunsoft-collection-1/k0?sortingField=SORTING_DATE"],
  diagnostics: [{state:"results",cards_found:3,listings_parsed:2,duplicates_skipped:1,errors:[]}],
  listings: [
    {id:"10001",title:"Evercade Sunsoft Collection 1",url:"https://www.kleinanzeigen.de",price:"29",price_raw:"29 € VB",price_flags:["verhandelbar"],postal_code:"37136",place:"Ebergötzen",posted_at:new Date().toISOString(),description:"Sehr guter Zustand, vollständig.",tags:["Versand möglich"],image_url:null},
    {id:"10002",title:"Sunsoft Collection 1 für Evercade",url:"https://www.kleinanzeigen.de",price:"34",price_raw:"34 €",price_flags:[],postal_code:"37073",place:"Göttingen",posted_at:new Date().toISOString(),description:"Geöffnet und getestet.",tags:[],image_url:null}
  ], summary:{listings:2,cards:3,duplicates:1,card_errors:0,truncated:false}, worker:{version:"0.2.0rc1-demo"}
};

function tokenHeaders(){const token=$("token").value.trim();localStorage.setItem("gp-token",token);return token?{"X-GenericParser-Token":token}:{};}
function numberOrNull(id){const value=$(id).value.trim();return value===""?null:Number(value);}
function message(text,error=false){const box=$("message");box.textContent=String(text??"");box.className=`message${error?" error":""}`;}
function clearMessage(){$("message").className="message hidden";}
function setBusy(value){$("search-button").classList.toggle("busy",value);$("search-button").textContent=value?"Suche läuft …":"Live-Suche starten";}
function metric(value,label){return `<div class="metric"><strong>${value}</strong><span>${label}</span></div>`;}
function escapeHtml(value){return String(value??"").replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));}
function errorText(value){
  if(value==null)return "Unbekannter Fehler";
  if(typeof value==="string")return value;
  if(value instanceof Error)return value.message||value.name||"Unbekannter Fehler";
  if(Array.isArray(value))return value.map(errorText).join("; ");
  if(typeof value==="object"){
    if(typeof value.msg==="string")return value.msg;
    if(typeof value.detail==="string")return value.detail;
    if(value.detail!=null)return errorText(value.detail);
    if(typeof value.message==="string")return value.message;
    try{return JSON.stringify(value);}catch{return "Unbekannter Fehler";}
  }
  return String(value);
}
async function readResponse(response){
  const raw=await response.text();
  let data=null;
  if(raw){try{data=JSON.parse(raw);}catch{data=raw;}}
  if(!response.ok){throw new Error(`HTTP ${response.status}: ${errorText(data)||response.statusText||"Anfrage fehlgeschlagen"}`);}
  return data;
}
function render(payload){clearMessage();$("summary").classList.remove("hidden");$("summary").innerHTML=metric(payload.summary.listings,"Anzeigen")+metric(payload.summary.cards,"Karten")+metric(payload.summary.duplicates,"Duplikate")+metric(payload.summary.card_errors,"Fehler");$("diagnostics-card").classList.remove("hidden");$("worker-version").textContent=payload.worker?.version||"Worker";$("urls").innerHTML=(payload.generated_urls||[]).map(url=>`<code>${escapeHtml(url)}</code>`).join("");$("diagnostics").innerHTML=(payload.diagnostics||[]).map(d=>`<div class="diagnostic"><span>${escapeHtml(d.state)}</span><span>${d.cards_found} Karten</span><span>${d.listings_parsed} geparst</span><span>${d.duplicates_skipped} Duplikate</span></div>`).join("");$("results").innerHTML=(payload.listings||[]).map(item=>`<article class="listing"><div class="listing-image">${item.image_url?`<img src="${escapeHtml(item.image_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">`:"KEIN BILD"}</div><div><h3><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a></h3><div class="price">${item.price!==null?`${escapeHtml(item.price)} €`:escapeHtml(item.price_raw||"Preis offen")}</div><div class="meta">${escapeHtml([item.postal_code,item.place].filter(Boolean).join(" "))} · ID ${escapeHtml(item.id)}</div><p class="description">${escapeHtml(item.description||"Keine Beschreibung in der Ergebnisliste.")}</p><div class="tags">${[...(item.tags||[]),...(item.price_flags||[])].map(t=>`<span class="tag">${escapeHtml(t)}</span>`).join("")}</div></div></article>`).join("");if(!(payload.listings||[]).length)message("Die Suche wurde verarbeitet, aber es wurden keine Anzeigen gefunden.");}

async function liveSearch(){
  if(state.standaloneFile)return message("Live-Suchen benötigen die veröffentlichte Cloudflare-URL.",true);
  setBusy(true);
  clearMessage();
  const postalCode=$("postal-code").value.trim()||null;
  const locationId=numberOrNull("location-id");
  const hasLocation=Boolean(postalCode||locationId);
  const body={
    mode:"live",
    query:$("query").value.trim(),
    postal_code:postalCode,
    location_id:locationId,
    radius_km:hasLocation?numberOrNull("radius-km"):null,
    max_results:numberOrNull("max-results")||12
  };
  try{
    const response=await fetch(apiUrl("api/search"),{method:"POST",headers:{"Content-Type":"application/json",...tokenHeaders()},body:JSON.stringify(body)});
    const data=await readResponse(response);
    render(data);
  }catch(error){message(errorText(error),true);}finally{setBusy(false);}
}
async function extractLocation(){if(state.standaloneFile){const match=$("location-url").value.trim().match(/(?:^|[/?])l(\d+)(?:r\d+)?(?:$|[/?#])/);if(match){$("location-id").value=match[1];return message(`Location-ID ${match[1]} lokal übernommen.`);}return message("Keine Location-ID in der URL gefunden.",true);}const url=$("location-url").value.trim();if(!url)return message("Bitte im Feld zur Ortsbestimmung zuerst eine Kleinanzeigen-URL mit Location-ID einfügen.",true);try{const response=await fetch(apiUrl("api/location-id"),{method:"POST",headers:{"Content-Type":"application/json",...tokenHeaders()},body:JSON.stringify({url})});const data=await readResponse(response);$("location-id").value=data.location_id;message(`Location-ID ${data.location_id} übernommen.`);}catch(error){message(errorText(error),true);}}

$("search-button").addEventListener("click",liveSearch);$("demo-button").addEventListener("click",()=>render(demo));$("extract-location").addEventListener("click",extractLocation);$("token").value=localStorage.getItem("gp-token")||"";
window.addEventListener("online",()=>{$("connection").className="status";$("connection").innerHTML="<span></span> Online";});window.addEventListener("offline",()=>{$("connection").className="status offline";$("connection").innerHTML="<span></span> Offline";});
window.addEventListener("beforeinstallprompt",event=>{event.preventDefault();state.installPrompt=event;$("install-button").classList.remove("hidden");});$("install-button").addEventListener("click",async()=>{if(!state.installPrompt)return;state.installPrompt.prompt();await state.installPrompt.userChoice;state.installPrompt=null;$("install-button").classList.add("hidden");});
if("serviceWorker" in navigator && window.location.protocol.startsWith("http")) navigator.serviceWorker.register("./service-worker.js").catch(()=>{});

function initialiseBrowserMode(){
  const connection=$("connection");
  if(state.standaloneFile){
    connection.className="status offline";
    connection.innerHTML="<span></span> Demo-Datei";
    $("search-button").disabled=true;
    $("search-button").title="Live-Suchen benötigen die veröffentlichte Cloudflare-URL";
    $("health-link").classList.add("hidden");
    const note=$("browser-note");
    note.className="message";
    note.textContent="Diese Datei läuft vollständig lokal im Demo-Modus. Für echte Suchen öffne nach dem Deployment die workers.dev-URL.";
    render(demo);
  }else{
    connection.className=navigator.onLine?"status":"status offline";
    connection.innerHTML=navigator.onLine?"<span></span> Online":"<span></span> Offline";
  }
}
initialiseBrowserMode();
