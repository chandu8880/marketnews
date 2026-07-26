# MarketPulse

A mobile-first Indian market news app: aggregates finance headlines from
multiple trusted Indian sources (financial media + the official NSE/BSE/SEBI
feeds), tags each article bullish/bearish/neutral and the NSE-listed stocks
it mentions, keeps itself fresh in the background, and lets you select any
sentence to copy or translate it to Telugu.

## Stack

- **Backend:** FastAPI (Python), `feedparser` for RSS, VADER + a finance
  lexicon for sentiment (optionally upgraded per-article by Groq's free
  Llama 3 API, see below), `deep-translator` (free Google Translate) for
  English → Telugu, `APScheduler` for background refresh. No API keys
  required to run — the LLM sentiment upgrade is opt-in.
- **Frontend:** React (Vite), mobile-first CSS, polling-based live updates.

## How it works

1. **News sources** — `backend/app/news_sources.py` lists RSS feeds from:
   - Media: Moneycontrol, Economic Times, LiveMint, The Hindu BusinessLine,
     Google News India (market-keyword search)
   - Official: **NSE** corporate announcements, **BSE** notices, **SEBI**
     press releases — straight from the exchanges/regulator, not just media
     coverage of them
   Add/remove feeds there.
2. **Freshness** — `backend/app/scheduler.py` re-fetches all feeds every 60s
   in a background thread and merges new articles into an in-memory store
   (deduped by article id). The frontend polls `/api/news/latest?since=...`
   every 60s and shows a "N new updates" banner rather than yanking the
   screen out from under you.
3. **Bullish/bearish tagging** — `backend/app/sentiment.py` scores each
   headline+summary with VADER plus a hand-tuned finance lexicon (surge,
   plunge, beats estimates, downgrade, etc.) and classifies it
   bullish/bearish/neutral. If `GROQ_API_KEY` is set (see below),
   `backend/app/llm_sentiment.py` asks Groq's free Llama 3 API to classify
   the same text instead, since an LLM can weigh context VADER's lexicon
   can't; any failure/timeout/rate-limit falls back to the VADER result
   automatically. Each article is only classified once, the first time it's
   fetched — `backend/app/tickers.py` matches ~65 NSE-listed
   companies/indices (Reliance, TCS, Infosys, HDFC Bank, Nifty, Sensex, etc.)
   by name in the text; every ticker found in an article is tagged with that
   article's sentiment.
4. **Translate** — selecting text anywhere in the feed shows a floating
   Copy / Translate toolbar (`frontend/src/components/SelectionToolbar.jsx`).
   Translate calls `POST /api/translate` which uses `deep-translator`.

## Running locally

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health check: http://127.0.0.1:8000/api/health
Interactive API docs: http://127.0.0.1:8000/docs

#### Optional: LLM-upgraded sentiment (free)

By default sentiment is scored locally with VADER, no setup needed. To
upgrade it with Groq's free Llama 3 API:

1. Get a free key at https://console.groq.com -> API Keys.
2. `cp backend/.env.example backend/.env` and paste the key into
   `GROQ_API_KEY=`.
3. Restart the backend. New articles will now be classified by the LLM;
   if the request ever fails, times out, or the key is missing/invalid, it
   silently falls back to VADER, so this is safe to leave partially
   configured.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — resize to a phone width (or use your browser's
device toolbar) for the intended mobile layout; it also works fine on
desktop, capped to a phone-width column.

The frontend reads the API base URL from `frontend/.env`
(`VITE_API_BASE_URL`, defaults to `http://127.0.0.1:8000`).

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/news?limit=&sentiment=&ticker=` | List articles, newest first |
| GET | `/api/news/latest?since=<ISO time>` | Articles fetched after `since` |
| POST | `/api/translate` `{text, target_lang}` | Translate text (default `te`) |
| GET | `/api/health` | Store status |

## Notes / next steps

- Sentiment and ticker-matching are heuristic (no paid data provider), so
  treat bullish/bearish tags as a signal, not investment advice.
- RSS feeds occasionally change URLs or rate-limit; failures on one feed are
  logged and skipped without breaking the others (see `news_sources.py`).
- To swap in a real market-data/sentiment API later, only `ingest.py`,
  `sentiment.py`, and `tickers.py` need to change — the store/API/frontend
  contract stays the same.
# marketnews
