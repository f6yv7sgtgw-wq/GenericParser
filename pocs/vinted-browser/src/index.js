const VERSION = "vinted-browser-poc-0.2.0";
const BASE = "https://www.vinted.de";
const MAX_RESULTS = 25;

function json(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
    },
  });
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

function stripTags(value) {
  return String(value || "")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function extractListings(html) {
  const listings = [];
  const seen = new Set();
  const anchorRe = /<a\b[^>]*href=["']([^"']*\/items\/(\d+)[^"']*)["'][^>]*>([\s\S]*?)<\/a>/gi;
  let match;
  while ((match = anchorRe.exec(html)) && listings.length < MAX_RESULTS) {
    const id = match[2];
    if (seen.has(id)) continue;
    seen.add(id);
    const rawHref = match[1].replace(/&amp;/g, "&");
    const block = match[0];
    const text = stripTags(match[3]);
    const titleAttr = block.match(/(?:title|aria-label)=["']([^"']+)["']/i)?.[1];
    const altAttr = block.match(/alt=["']([^"']+)["']/i)?.[1];
    const title = stripTags(titleAttr || altAttr || text.slice(0, 180));
    const priceMatch = text.match(/(\d{1,6}(?:[.,]\d{1,2})?)\s*€/);
    const price = priceMatch ? Number(priceMatch[1].replace(",", ".")) : null;
    const url = new URL(rawHref, BASE).toString();
    listings.push({ id: `vinted:${id}`, title, price, url, source: "vinted" });
  }
  return listings;
}

async function inspectVinted(env, query) {
  const started = Date.now();
  const targetUrl = searchUrl(query);
  const response = await env.BROWSER.quickAction("content", {
    url: targetUrl,
    gotoOptions: { waitUntil: "networkidle2", timeout: 30000 },
    setExtraHTTPHeaders: { "Accept-Language": "de-DE,de;q=0.9,en;q=0.7" },
    cacheTTL: 0,
  });

  const httpStatus = response.status;
  const html = await response.text();
  const textSample = stripTags(html).slice(0, 800);
  const haystack = textSample.toLowerCase();
  const challengeTerms = [
    "human verification",
    "verify you are human",
    "access denied",
    "captcha",
    "datadome",
    "unusual traffic",
  ];
  const challengeDetected = challengeTerms.some((term) => haystack.includes(term));
  const listings = extractListings(html);

  let status = "ok";
  let reason = null;
  if (challengeDetected || [401, 403, 429].includes(httpStatus)) {
    status = "blocked";
    reason = "vinted_browser_access_limited";
  } else if (!listings.length) {
    status = "empty";
    reason = "no_public_item_links_found";
  }

  return {
    poc: VERSION,
    status,
    reason,
    query,
    targetUrl,
    httpStatus,
    elapsedMs: Date.now() - started,
    browser: {
      mode: "browser-run-quick-action-content",
      challengeDetected,
      itemAnchorCount: listings.length,
      browserMsUsed: response.headers.get("x-browser-ms-used"),
    },
    listings,
    bodySample: status === "ok" ? undefined : textSample,
  };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "access-control-allow-origin": "*",
          "access-control-allow-methods": "GET, OPTIONS",
        },
      });
    }
    if (request.method !== "GET") return json({ poc: VERSION, status: "error", reason: "method_not_allowed" }, 405);
    if (url.pathname === "/health" || url.pathname === "/") {
      return json({
        poc: VERSION,
        status: "ok",
        mode: "browser-run-quick-action-content",
        source: "vinted",
        endpoints: ["/health", "/search?q=Evercade"],
      });
    }
    if (url.pathname !== "/search") return json({ poc: VERSION, status: "error", reason: "not_found" }, 404);

    try {
      const query = normalizeQuery(url.searchParams.get("q"));
      const result = await inspectVinted(env, query);
      return json(result, result.status === "ok" ? 200 : 502);
    } catch (error) {
      return json({
        poc: VERSION,
        status: "error",
        reason: "browser_run_quick_action_failed",
        errorType: error?.name || "Error",
        error: String(error?.message || error),
      }, 500);
    }
  },
};
