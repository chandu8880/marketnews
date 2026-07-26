const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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

export function fetchNews({ limit = 60, sentiment = null, ticker = null } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (sentiment && sentiment !== "all") params.set("sentiment", sentiment);
  if (ticker) params.set("ticker", ticker);
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

export function fetchStocks(limit = 100) {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiFetch(`/api/stocks?${params.toString()}`);
}

export function fetchDividends(days = 4) {
  const params = new URLSearchParams({ days: String(days) });
  return apiFetch(`/api/dividends/upcoming?${params.toString()}`);
}

export function fetchIpos() {
  return apiFetch("/api/ipo");
}

export function fetchResults({ days = 4, q = null } = {}) {
  const params = new URLSearchParams({ days: String(days) });
  if (q) params.set("q", q);
  return apiFetch(`/api/results?${params.toString()}`);
}

export function analyzeResult(company) {
  const params = new URLSearchParams({ company });
  return apiFetch(`/api/results/analyze?${params.toString()}`);
}

export function requestOtp(phone) {
  return apiPost("/api/auth/request-otp", { phone });
}

export function verifyOtp(phone, code) {
  return apiPost("/api/auth/verify-otp", { phone, code });
}

export function checkSession() {
  return apiFetch("/api/auth/session");
}

export function logoutSession() {
  return apiFetch("/api/auth/logout", { method: "POST" });
}
