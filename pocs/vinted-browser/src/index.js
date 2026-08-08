import puppeteer from "@cloudflare/puppeteer";

const VERSION = "vinted-browser-poc-0.1.0";
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

async function inspectVinted(env, query) {
  const started = Date.now();
  const browser = await puppeteer.launch(env.BROWSER);
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 900 });
    await page.setExtraHTTPHeaders({ "Accept-Language": "de-DE,de;q=0.9,en;q=0.7" });

    const targetUrl = searchUrl(query);
    const response = await page.goto(targetUrl, {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });

    await new Promise((resolve) => setTimeout(resolve, 1500));

    const diagnostic = await page.evaluate((maxResults) => {
      const bodyText = (document.body?.innerText || "").slice(0, 5000);
      const haystack = `${document.title}\n${bodyText}`.toLowerCase();
      const challengeTerms = [
        "human verification",
        "verify you are human",
        "access denied",
        "captcha",
        "datadome",
        "unusual traffic",
      ];
      const challengeDetected = challengeTerms.some((term) => haystack.includes(term));

      const seen = new Set();
      const listings = [];
      for (const anchor of document.querySelectorAll('a[href*="/items/"]')) {
        if (listings.length >= maxResults) break;
        const rawHref = anchor.getAttribute("href") || "";
        const match = rawHref.match(/\/items\/(\d+)/);
        if (!match || seen.has(match[1])) continue;
        seen.add(match[1]);

        const container = anchor.closest('article, li, [data-testid*="item"], [class*="feed-grid"] > div') || anchor.parentElement || anchor;
        const img = container.querySelector?.("img") || anchor.querySelector?.("img");
        const text = (container.innerText || anchor.innerText || "").replace(/\s+/g, " ").trim();
        const title = (
          anchor.getAttribute("title") ||
          anchor.getAttribute("aria-label") ||
          img?.getAttribute("alt") ||
          text.slice(0, 180)
        ).trim();
        const priceMatch = text.match(/(\d{1,6}(?:[.,]\d{1,2})?)\s*€/);
        const price = priceMatch ? Number(priceMatch[1].replace(",", ".")) : null;
        const href = new URL(rawHref, location.origin).toString();
        listings.push({ id: `vinted:${match[1]}`, title, price, url: href, source: "vinted" });
      }

      return {
        title: document.title,
        finalUrl: location.href,
        challengeDetected,
        bodySample: bodyText.slice(0, 600),
        itemAnchorCount: document.querySelectorAll('a[href*="/items/"]').length,
        listings,
      };
    }, MAX_RESULTS);

    const httpStatus = response?.status() ?? null;
    let status = "ok";
    let reason = null;
    if (diagnostic.challengeDetected || [401, 403, 429].includes(httpStatus)) {
      status = "blocked";
      reason = "vinted_browser_access_limited";
    } else if (!diagnostic.listings.length) {
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
        title: diagnostic.title,
        finalUrl: diagnostic.finalUrl,
        challengeDetected: diagnostic.challengeDetected,
        itemAnchorCount: diagnostic.itemAnchorCount,
      },
      listings: diagnostic.listings,
      bodySample: status === "ok" ? undefined : diagnostic.bodySample,
    };
  } finally {
    await browser.close();
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: { "access-control-allow-origin": "*", "access-control-allow-methods": "GET, OPTIONS" } });
    if (request.method !== "GET") return json({ poc: VERSION, status: "error", reason: "method_not_allowed" }, 405);
    if (url.pathname === "/health" || url.pathname === "/") {
      return json({ poc: VERSION, status: "ok", mode: "isolated-browser-run", source: "vinted", endpoints: ["/health", "/search?q=Evercade"] });
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
        reason: "browser_run_failed",
        errorType: error?.name || "Error",
        error: String(error?.message || error),
      }, 500);
    }
  },
};
