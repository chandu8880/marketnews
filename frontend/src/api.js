// "??" (not "||") so an intentionally-empty VITE_API_BASE_URL (production:
// same-origin relative /api/* calls, proxied by frontend/vercel.json) isn't
// overridden by the localhost fallback - only an unset/undefined value should
// fall back to it.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function handle(res) {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status}): ${body}`);
  }
  return res.json();
}

// Every request carries the HttpOnly session cookie automatically via
// `credentials: "include"` - the token itself is never touched by JS.
function apiFetch(path, options = {}) {
  return fetch(`${API_BASE}${path}`, { ...options, credentials: "include" }).then(handle);
}

function apiPost(path, body) {
  return apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function fetchNews({ limit = 60, sentiment = null, ticker = null, force = false } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (sentiment && sentiment !== "all") params.set("sentiment", sentiment);
  if (ticker) params.set("ticker", ticker);
  if (force) params.set("force", "true");
  return apiFetch(`/api/news?${params.toString()}`);
}

export function fetchLatestSince(sinceIso) {
  const params = new URLSearchParams({ since: sinceIso });
  return apiFetch(`/api/news/latest?${params.toString()}`);
}

export function translateText(text, targetLang = "te") {
  return apiPost("/api/translate", { text, target_lang: targetLang });
}

export function searchNews(q, limit = 40) {
  const params = new URLSearchParams({ q, limit: String(limit) });
  return apiFetch(`/api/news/search?${params.toString()}`);
}

export function fetchStocks(limit = 50, force = false) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (force) params.set("force", "true");
  return apiFetch(`/api/stocks?${params.toString()}`);
}

export function fetchStockUniverse() {
  return apiFetch("/api/stocks/universe");
}

export function fetchMarketIndices(force = false) {
  const params = new URLSearchParams();
  if (force) params.set("force", "true");
  return apiFetch(`/api/market/indices?${params.toString()}`);
}

export function fetchStockPrice(ticker) {
  const params = new URLSearchParams({ ticker });
  return apiFetch(`/api/stocks/price?${params.toString()}`);
}

export function fetchTopAnalysisStocks() {
  return apiFetch("/api/top-analysis/stocks");
}

export function fetchTopAnalysisDetail(ticker) {
  const params = new URLSearchParams({ ticker });
  return apiFetch(`/api/top-analysis/analyze?${params.toString()}`);
}

export function fetchScreener(force = false) {
  const params = new URLSearchParams();
  if (force) params.set("force", "true");
  return apiFetch(`/api/screener?${params.toString()}`);
}

export function fetchDividends(days = 4, force = false) {
  const params = new URLSearchParams({ days: String(days) });
  if (force) params.set("force", "true");
  return apiFetch(`/api/dividends/upcoming?${params.toString()}`);
}

export function fetchIpos(force = false) {
  const params = new URLSearchParams();
  if (force) params.set("force", "true");
  return apiFetch(`/api/ipo?${params.toString()}`);
}

export function fetchResults({ days = 4, q = null, force = false } = {}) {
  const params = new URLSearchParams({ days: String(days) });
  if (q) params.set("q", q);
  if (force) params.set("force", "true");
  return apiFetch(`/api/results?${params.toString()}`);
}

export function analyzeResult(company) {
  const params = new URLSearchParams({ company });
  return apiFetch(`/api/results/analyze?${params.toString()}`);
}

export function requestOtp(email) {
  return apiPost("/api/auth/request-otp", { email });
}

export function verifyOtp(email, code) {
  return apiPost("/api/auth/verify-otp", { email, code });
}

export function checkSession() {
  return apiFetch("/api/auth/session");
}

export function logoutSession() {
  return apiFetch("/api/auth/logout", { method: "POST" });
}
