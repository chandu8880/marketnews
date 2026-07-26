import { useMemo } from "react";
import { timeAgo } from "../utils/time";
import { useNewsFeed } from "../hooks/useNewsFeed";
import { useRefreshSignal } from "../hooks/useRefreshSignal";

const WINDOW_MS = 24 * 60 * 60 * 1000; // "today's" news
const CONFIDENCE_THRESHOLD = 0.35; // min |avg sentiment| across a stock's recent news to call it a signal

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

  const calls = [];
  for (const entry of byTicker.values()) {
    const avg = entry.scores.reduce((a, b) => a + b, 0) / entry.scores.length;
    if (Math.abs(avg) < CONFIDENCE_THRESHOLD) continue;
    calls.push({
      ticker: entry.ticker,
      name: entry.name,
      direction: avg > 0 ? "bullish" : "bearish",
      confidence: Math.round(Math.abs(avg) * 100),
      mentions: entry.scores.length,
      latest: entry.latest,
    });
  }

  calls.sort((a, b) => b.confidence - a.confidence);
  return calls;
}

export default function OverviewView({ refreshSignal }) {
  const { articles, loading, error, pendingCount, showPending, reload } = useNewsFeed("all");
  useRefreshSignal(refreshSignal, reload);

  const calls = useMemo(() => buildCalls(articles), [articles]);

  return (
    <div className="news-feed">
      <div className="view-intro">
        Today's most confident bullish/bearish calls, one per stock — based on the average
        sentiment of everything published about it in the last 24h, not just one headline.
        Higher % means the coverage has been more one-sided, not a guarantee. Not investment advice.
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
            className={`stock-row-card call-card call-card-${call.direction}`}
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
              </span>
            </div>
            <p className="call-card-headline">{call.latest.title}</p>
            <div className="stock-row-footer">
              <span>{call.mentions} article{call.mentions > 1 ? "s" : ""} in the last 24h</span>
              <span>{timeAgo(call.latest.published)}</span>
            </div>
          </a>
        ))}
    </div>
  );
}
