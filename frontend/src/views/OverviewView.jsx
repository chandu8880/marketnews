import { useMemo } from "react";
import IndicesTicker from "../components/IndicesTicker";
import { formatDateTime, timeAgo } from "../utils/time";
import { useNewsFeed } from "../hooks/useNewsFeed";
import { useRefreshSignal } from "../hooks/useRefreshSignal";

const WINDOW_MS = 24 * 60 * 60 * 1000; // "today's" news
const CONFIDENCE_THRESHOLD = 0.35; // min |avg sentiment| across a stock's recent news to call it a strong signal
const MIN_CALLS = 10; // always show at least this many, backfilling with weaker signals if needed

// One bullish/bearish call per stock, built from the average sentiment of
// everything published about it in the last 24h - not a single article's
// score, so one outlier headline can't flip the call on its own. The live
// feed underneath keeps polling, so as fresher/stronger news comes in
// (down to the last refresh cycle) these calls update and reorder.
function buildCalls(articles) {
  const cutoff = Date.now() - WINDOW_MS;
  const byTicker = new Map();

  for (const article of articles) {
    if (new Date(article.published).getTime() < cutoff) continue;
    for (const stock of article.related_stocks) {
      const entry = byTicker.get(stock.ticker) || {
        ticker: stock.ticker,
        name: stock.name,
        scores: [],
        latest: article,
      };
      entry.scores.push(article.sentiment_score);
      if (new Date(article.published) > new Date(entry.latest.published)) entry.latest = article;
      byTicker.set(stock.ticker, entry);
    }
  }

  const allCalls = [];
  for (const entry of byTicker.values()) {
    const avg = entry.scores.reduce((a, b) => a + b, 0) / entry.scores.length;
    allCalls.push({
      ticker: entry.ticker,
      name: entry.name,
      direction: avg > 0 ? "bullish" : "bearish",
      confidence: Math.round(Math.abs(avg) * 100),
      strong: Math.abs(avg) >= CONFIDENCE_THRESHOLD,
      mentions: entry.scores.length,
      latest: entry.latest,
    });
  }

  allCalls.sort((a, b) => b.confidence - a.confidence);

  // Show every strong-confidence call, but always at least MIN_CALLS total -
  // backfilling with the next-highest-confidence calls (even below the
  // threshold) rather than leaving the screen sparse when today's news is quiet.
  const strong = allCalls.filter((c) => c.strong);
  if (strong.length >= MIN_CALLS) return strong;
  return allCalls.slice(0, MIN_CALLS);
}

// Needs a broad sample to find enough distinct ticker-tagged stocks to rank -
// most recent articles by source volume alone are unrelated/untagged (NAV
// declarations, generic market wrap-ups, etc.), so the default News-feed
// page size of 60 was leaving too few tagged articles to build a top-10 from.
const ARTICLE_SAMPLE_SIZE = 200;

export default function OverviewView({ refreshSignal }) {
  const { articles, loading, error, pendingCount, showPending, reload } = useNewsFeed(
    "all",
    ARTICLE_SAMPLE_SIZE
  );
  useRefreshSignal(refreshSignal, reload);

  const calls = useMemo(() => buildCalls(articles), [articles]);

  return (
    <>
      <IndicesTicker />
      <div className="news-feed">
        <div className="view-intro">
          Today's bullish/bearish calls, one per stock. Not investment advice.
        </div>

        {pendingCount > 0 && (
          <button className="new-articles-banner" onClick={showPending}>
            {pendingCount} new update{pendingCount > 1 ? "s" : ""} — tap to show
          </button>
        )}

        {loading && <div className="status-msg">Finding today's most confident calls…</div>}
        {error && !loading && <div className="status-msg status-error">{error}</div>}
        {!loading && !error && calls.length === 0 && (
          <div className="status-msg">No confident signal yet — check back soon as news comes in.</div>
        )}
        {!loading &&
          !error &&
          calls.map((call) => (
            <a
              key={call.ticker}
              className={`stock-row-card call-card call-card-${call.direction} ${!call.strong ? "call-card-weak" : ""}`}
              href={call.latest.link}
              target="_blank"
              rel="noreferrer"
            >
              <div className="stock-row-top">
                <div>
                  <span className="stock-row-ticker">{call.ticker}</span>
                  <span className="stock-row-name">{call.name}</span>
                </div>
                <span className={`sentiment-badge badge-${call.direction}`}>
                  {call.direction === "bullish" ? "▲" : "▼"} {call.confidence}%
                  {!call.strong && <span className="call-weak-tag"> · weak</span>}
                </span>
              </div>
              <p className="call-card-headline">{call.latest.title}</p>
              {call.latest.summary && <p className="news-summary">{call.latest.summary}</p>}
              <div className="news-datetime">{formatDateTime(call.latest.published)}</div>
              <div className="stock-row-footer">
                <span>{call.mentions} article{call.mentions > 1 ? "s" : ""} in the last 24h</span>
                <span>{timeAgo(call.latest.published)}</span>
              </div>
            </a>
          ))}
      </div>
    </>
  );
}
