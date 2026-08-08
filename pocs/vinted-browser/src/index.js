const COMPONENT = "vinted-browser-poc";
const SCHEMA = 2;
const BASE = "https://www.vinted.de";
const MAX_RESULTS = 25;
const DETAIL_BATCH_SIZE = 5;

function json(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "access-control-allow-origin": "*" } });
}
function normalizeQuery(value) {
  const query = String(value || "Evercade").trim().replace(/\s+/g, " ");
  if (!query || query.length > 100) throw new Error("query must contain 1-100 characters");
  return query;
}
function normalizePage(value) {
  const page = Number.parseInt(String(value ?? "0"), 10);
  if (!Number.isFinite(page) || page < 0 || page > 100) throw new Error("page must be between 0 and 100");
  return page;
}
function searchUrl(query, page) {
  const url = new URL("/catalog", BASE);
  url.searchParams.set("search_text", query);
  url.searchParams.set("order", "newest_first");
  if (page > 0) url.searchParams.set("page", String(page + 1));
  return url.toString();
}
function clean(value) { return String(value || "").replace(/\s+/g, " ").trim(); }
function decodeEntities(value) {
  return clean(String(value || "").replace(/&nbsp;/gi, " ").replace(/&amp;/gi, "&").replace(/&quot;/gi, '"').replace(/&#39;/gi, "'").replace(/&lt;/gi, "<").replace(/&gt;/gi, ">"));
}
function stripTags(value) {
  return decodeEntities(String(value || "").replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ").replace(/<[^>]+>/g, " "));
}
function unwrapContent(raw) {
  try { const parsed = JSON.parse(raw); if (parsed && parsed.success && typeof parsed.result === "string") return parsed.result; } catch {}
  return raw;
}
function titleFromSlug(slug) {
  try { return clean(decodeURIComponent(String(slug || "")).replace(/[-_]+/g, " ")); }
  catch { return clean(String(slug || "").replace(/[-_]+/g, " ")); }
}
function absoluteUrl(value) {
  if (!value) return null;
  try { return new URL(String(value), BASE).toString(); } catch { return null; }
}
function metaContent(html, key, value) {
  const escaped = String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re1 = new RegExp(`<meta[^>]+${key}=["']${escaped}["'][^>]+content=["']([^"']+)["'][^>]*>`, "i");
  const re2 = new RegExp(`<meta[^>]+content=["']([^"']+)["'][^>]+${key}=["']${escaped}["'][^>]*>`, "i");
  return decodeEntities(html.match(re1)?.[1] || html.match(re2)?.[1] || "") || null;
}
function walk(value, visitor) {
  if (!value || typeof value !== "object") return null;
  if (visitor(value)) return value;
  const children = Array.isArray(value) ? value : Object.values(value);
  for (const child of children) {
    const found = walk(child, visitor);
    if (found) return found;
  }
  return null;
}
function structuredProduct(html) {
  const re = /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html))) {
    try {
      const data = JSON.parse(m[1]);
      const product = walk(data, value => String(value?.["@type"] || "").toLowerCase() === "product");
      if (product) return product;
    } catch {}
  }
  return null;
}
function money(value) {
  if (value && typeof value === "object") value = value.amount ?? value.value ?? value.price;
  const n = Number(String(value ?? "").replace("€", "").replace(/\s/g, "").replace(",", "."));
  return Number.isFinite(n) ? n : null;
}
function conditionFrom(value) {
  const text = clean(value);
  const match = text.match(/\b(Neu mit Etikett|Neu ohne Etikett|Sehr gut|Gut|Zufriedenstellend|New with tags|New without tags|Very good|Good|Satisfactory)\b/i);
  return match?.[1] || null;
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
    listings.push({ id:`vinted:${id}`, title, condition:conditionFrom(context), price:priceMatch ? Number(priceMatch[1].replace(",", ".")) : null, url:m[0].startsWith("http") ? m[0] : `${BASE}${m[0]}`, source:"vinted", detail_status:"pending", detail_fields:[] });
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
    listings.push({ id:`vinted:text:${listings.length+1}`, title, condition:m[3], price:Number(m[4].replace(",", ".")), url:null, source:"vinted", detail_status:"unavailable", detail_fields:["price","condition"] });
  }
  return listings;
}
function extractListings(content, query) {
  const htmlListings = extractHtmlListings(content);
  if (htmlListings.length) return { strategy:"html-item-links", listings:htmlListings };
  return { strategy:"rendered-text", listings:extractTextListings(content, query) };
}
function parseDetail(content, listing) {
  const html = String(content || "");
  const product = structuredProduct(html) || {};
  const offers = product.offers && typeof product.offers === "object" ? product.offers : {};
  const image = Array.isArray(product.image) ? product.image[0] : product.image;
  const imageFromProduct = image && typeof image === "object" ? image.url : image;
  const imageUrl = absoluteUrl(imageFromProduct || metaContent(html, "property", "og:image") || metaContent(html, "name", "twitter:image"));
  const description = clean(product.description || metaContent(html, "property", "og:description") || metaContent(html, "name", "description") || "") || null;
  let price = money(offers.price ?? product.price);
  if (price == null) {
    const text = stripTags(html).slice(0, 12000);
    const m = text.match(/(\d{1,6}(?:[.,]\d{1,2})?)\s*€/);
    if (m) price = Number(m[1].replace(",", "."));
  }
  const condition = conditionFrom(product.itemCondition || product.condition || stripTags(html).slice(0, 8000)) || listing.condition || null;
  const title = clean(product.name || metaContent(html, "property", "og:title") || listing.title) || listing.title;
  const fields = [];
  if (imageUrl) fields.push("image");
  if (price != null) fields.push("price");
  if (description) fields.push("description");
  if (condition) fields.push("condition");
  return { ...listing, title, image_url:imageUrl || listing.image_url || null, price:price ?? listing.price ?? null, description, condition, detail_status:fields.length ? "ok" : "empty", detail_fields:fields };
}
async function enrichOne(env, listing) {
  if (!listing.url) return listing;
  try {
    const response = await env.BROWSER.quickAction("content", { url:listing.url, gotoOptions:{waitUntil:"networkidle2",timeout:30000}, setExtraHTTPHeaders:{"Accept-Language":"de-DE,de;q=0.9,en;q=0.7"}, cacheTTL:0 });
    if ([401,403,429].includes(response.status)) return { ...listing, detail_status:"blocked", detail_fields:[] };
    const content = unwrapContent(await response.text());
    return parseDetail(content, listing);
  } catch (error) {
    return { ...listing, detail_status:"error", detail_error:String(error?.message || error), detail_fields:[] };
  }
}
async function enrichListings(env, listings) {
  const enriched = [];
  for (let offset = 0; offset < listings.length; offset += DETAIL_BATCH_SIZE) {
    const batch = listings.slice(offset, offset + DETAIL_BATCH_SIZE);
    const rows = await Promise.all(batch.map(item => enrichOne(env, item)));
    enriched.push(...rows);
  }
  const stats = { requested:listings.filter(item => Boolean(item.url)).length, ok:0, partial:0, failed:0, images:0, prices:0, descriptions:0, conditions:0 };
  for (const item of enriched) {
    const fields = Array.isArray(item.detail_fields) ? item.detail_fields : [];
    if (item.detail_status === "ok") {
      if (fields.length >= 3) stats.ok++; else stats.partial++;
    } else if (item.url) stats.failed++;
    if (item.image_url) stats.images++;
    if (item.price != null) stats.prices++;
    if (item.description) stats.descriptions++;
    if (item.condition) stats.conditions++;
  }
  return { listings:enriched, stats };
}
async function inspectVinted(env, query, page) {
  const started = Date.now(), targetUrl = searchUrl(query, page);
  const response = await env.BROWSER.quickAction("content", { url:targetUrl, gotoOptions:{waitUntil:"networkidle2",timeout:30000}, setExtraHTTPHeaders:{"Accept-Language":"de-DE,de;q=0.9,en;q=0.7"}, cacheTTL:0 });
  const httpStatus = response.status, content = unwrapContent(await response.text());
  const sample = clean(content).slice(0,1800), lower = stripTags(content).slice(0,5000).toLowerCase();
  const challengeDetected = ["human verification","verify you are human","access denied","captcha","datadome","unusual traffic"].some(t => lower.includes(t));
  const parsed = extractListings(content, query);
  let listings = parsed.listings;
  let status="ok", reason=null, enrichment={requested:0,ok:0,partial:0,failed:0,images:0,prices:0,descriptions:0,conditions:0};
  if (challengeDetected || [401,403,429].includes(httpStatus)) { status="blocked"; reason="vinted_browser_access_limited"; }
  else if (!listings.length) { status="empty"; reason="no_public_listings_parsed"; }
  else {
    const detail = await enrichListings(env, listings);
    listings = detail.listings;
    enrichment = detail.stats;
  }
  return { component:COMPONENT, schema:SCHEMA, revision:env.REVISION || null, status, reason, query, page, targetUrl, httpStatus, elapsedMs:Date.now()-started, browser:{mode:"browser-run-quick-action-content",parseStrategy:parsed.strategy,challengeDetected,parsedListingCount:listings.length,browserMsUsed:response.headers.get("x-browser-ms-used")}, enrichment, listings, complete:listings.length < MAX_RESULTS, nextPage:listings.length < MAX_RESULTS ? null : page + 1, bodySample:status === "ok" ? undefined : sample };
}
export default { async fetch(request, env) {
  const url = new URL(request.url);
  if (request.method === "OPTIONS") return new Response(null,{status:204,headers:{"access-control-allow-origin":"*","access-control-allow-methods":"GET, OPTIONS"}});
  if (request.method !== "GET") return json({component:COMPONENT,schema:SCHEMA,status:"error",reason:"method_not_allowed"},405);
  if (url.pathname === "/health" || url.pathname === "/") return json({component:COMPONENT,schema:SCHEMA,revision:env.REVISION || null,status:"ok",mode:"browser-run-quick-action-content",detailEnrichment:true,source:"vinted",endpoints:["/health","/search?q=Evercade&page=0"]});
  if (url.pathname !== "/search") return json({component:COMPONENT,schema:SCHEMA,status:"error",reason:"not_found"},404);
  try { const result=await inspectVinted(env,normalizeQuery(url.searchParams.get("q")),normalizePage(url.searchParams.get("page"))); return json(result,result.status === "ok" ? 200 : 502); }
  catch(error){ return json({component:COMPONENT,schema:SCHEMA,status:"error",reason:"browser_run_quick_action_failed",errorType:error?.name||"Error",error:String(error?.message||error)},500); }
}};
