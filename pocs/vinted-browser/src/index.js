const COMPONENT = "vinted-browser-poc";
const SCHEMA = 1;
const BASE = "https://www.vinted.de";
const MAX_RESULTS = 25;

function json(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "access-control-allow-origin": "*" } });
}
function normalizeQuery(value) {
  const query = String(value || "Evercade").trim().replace(/\s+/g, " ");
  if (!query || query.length > 100) throw new Error("query must contain 1-100 characters");
  return query;
}
function searchUrl(query) {
  const url = new URL("/catalog", BASE);
  url.searchParams.set("search_text", query);
  url.searchParams.set("order", "newest_first");
  return url.toString();
}
function clean(value) { return String(value || "").replace(/\s+/g, " ").trim(); }
function stripTags(value) {
  return clean(String(value || "").replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ").replace(/<[^>]+>/g, " ").replace(/&nbsp;/gi, " ").replace(/&amp;/gi, "&").replace(/&quot;/gi, '"').replace(/&#39;/gi, "'"));
}
function unwrapContent(raw) {
  try { const parsed = JSON.parse(raw); if (parsed && parsed.success && typeof parsed.result === "string") return parsed.result; } catch {}
  return raw;
}
function titleFromSlug(slug) {
  try { return clean(decodeURIComponent(String(slug || "")).replace(/[-_]+/g, " ")); }
  catch { return clean(String(slug || "").replace(/[-_]+/g, " ")); }
}
function extractHtmlListings(html) {
  const listings = [], seen = new Set();
  const re = /(?:https?:\/\/(?:www\.)?vinted\.de)?\/items\/(\d+)(?:-([^"'?#<\s]+))?/gi;
  let m;
  while ((m = re.exec(html)) && listings.length < MAX_RESULTS) {
    const id = m[1]; if (seen.has(id)) continue; seen.add(id);
    const context = stripTags(html.slice(Math.max(0, m.index - 1200), Math.min(html.length, m.index + 2200)));
    const title = titleFromSlug(m[2] || "") || `Vinted Artikel ${id}`;
    const priceMatch = context.match(/(\d{1,6}(?:[.,]\d{1,2})?)\s*€/);
    const conditionMatch = context.match(/\b(Neu mit Etikett|Neu ohne Etikett|Sehr gut|Gut|Zufriedenstellend)\b/i);
    listings.push({ id:`vinted:${id}`, title, condition:conditionMatch?.[1] || null, price:priceMatch ? Number(priceMatch[1].replace(",", ".")) : null, url:m[0].startsWith("http") ? m[0] : `${BASE}${m[0]}`, source:"vinted" });
  }
  return listings;
}
function extractTextListings(text, query) {
  const normalized = stripTags(text), listings = [], seen = new Set();
  const cardRe = /(?:^|\s)(\d{1,2})?\s*([^€]{3,160}?)\s+(Neu mit Etikett|Neu ohne Etikett|Sehr gut|Gut|Zufriedenstellend)\s+(\d{1,6}(?:[.,]\d{1,2})?)\s*€/gi;
  let m;
  while ((m = cardRe.exec(normalized)) && listings.length < MAX_RESULTS) {
    const title = clean(m[2]).replace(/^Suchergebnisse\s+/i, "").replace(/^Versandkosten.*?hinzu\s+/i, "");
    if (!title || !title.toLowerCase().includes(query.toLowerCase())) continue;
    const key = `${title.toLowerCase()}|${m[4]}`; if (seen.has(key)) continue; seen.add(key);
    listings.push({ id:`vinted:text:${listings.length+1}`, title, condition:m[3], price:Number(m[4].replace(",", ".")), url:null, source:"vinted" });
  }
  return listings;
}
function extractListings(content, query) {
  const htmlListings = extractHtmlListings(content);
  if (htmlListings.length) return { strategy:"html-item-links", listings:htmlListings };
  return { strategy:"rendered-text", listings:extractTextListings(content, query) };
}
async function inspectVinted(env, query) {
  const started = Date.now(), targetUrl = searchUrl(query);
  const response = await env.BROWSER.quickAction("content", { url:targetUrl, gotoOptions:{waitUntil:"networkidle2",timeout:30000}, setExtraHTTPHeaders:{"Accept-Language":"de-DE,de;q=0.9,en;q=0.7"}, cacheTTL:0 });
  const httpStatus = response.status, content = unwrapContent(await response.text());
  const sample = clean(content).slice(0,1800), lower = stripTags(content).slice(0,5000).toLowerCase();
  const challengeDetected = ["human verification","verify you are human","access denied","captcha","datadome","unusual traffic"].some(t => lower.includes(t));
  const parsed = extractListings(content, query), listings = parsed.listings;
  let status="ok", reason=null;
  if (challengeDetected || [401,403,429].includes(httpStatus)) { status="blocked"; reason="vinted_browser_access_limited"; }
  else if (!listings.length) { status="empty"; reason="no_public_listings_parsed"; }
  return { component:COMPONENT, schema:SCHEMA, revision:env.REVISION || null, status, reason, query, targetUrl, httpStatus, elapsedMs:Date.now()-started, browser:{mode:"browser-run-quick-action-content",parseStrategy:parsed.strategy,challengeDetected,parsedListingCount:listings.length,browserMsUsed:response.headers.get("x-browser-ms-used")}, listings, bodySample:status === "ok" ? undefined : sample };
}
export default { async fetch(request, env) {
  const url = new URL(request.url);
  if (request.method === "OPTIONS") return new Response(null,{status:204,headers:{"access-control-allow-origin":"*","access-control-allow-methods":"GET, OPTIONS"}});
  if (request.method !== "GET") return json({component:COMPONENT,schema:SCHEMA,status:"error",reason:"method_not_allowed"},405);
  if (url.pathname === "/health" || url.pathname === "/") return json({component:COMPONENT,schema:SCHEMA,revision:env.REVISION || null,status:"ok",mode:"browser-run-quick-action-content",source:"vinted",endpoints:["/health","/search?q=Evercade"]});
  if (url.pathname !== "/search") return json({component:COMPONENT,schema:SCHEMA,status:"error",reason:"not_found"},404);
  try { const result=await inspectVinted(env,normalizeQuery(url.searchParams.get("q"))); return json(result,result.status === "ok" ? 200 : 502); }
  catch(error){ return json({component:COMPONENT,schema:SCHEMA,status:"error",reason:"browser_run_quick_action_failed",errorType:error?.name||"Error",error:String(error?.message||error)},500); }
}};
