import { useCallback, useEffect, useMemo, useState } from "react";
import { analyzeResult, fetchResults } from "../api";
import { timeAgo } from "../utils/time";
import FilterTabs from "../components/FilterTabs";
import { useRefreshSignal } from "../hooks/useRefreshSignal";

const SENTIMENT_META = {
  bullish: { label: "Bullish", cls: "badge-bullish", icon: "▲" },
  bearish: { label: "Bearish", cls: "badge-bearish", icon: "▼" },
  neutral: { label: "Neutral", cls: "badge-neutral", icon: "●" },
};

const ESTIMATE_META = {
  beat: { label: "Beat estimates", cls: "estimate-beat", icon: "✓" },
  miss: { label: "Missed estimates", cls: "estimate-miss", icon: "✗" },
  "in-line": { label: "In line with estimates", cls: "estimate-inline", icon: "≈" },
};

function ResultCard({ r }) {
  const meta = SENTIMENT_META[r.sentiment_label] || SENTIMENT_META.neutral;
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState(null);

  function handleAnalyze() {
    setAnalyzing(true);
    setAnalyzeError(null);
    analyzeResult(r.company)
      .then(setAnalysis)
      .catch((e) => setAnalyzeError(e.message || "Analysis failed"))
      .finally(() => setAnalyzing(false));
  }

  const estimateMeta = analysis?.estimate_status ? ESTIMATE_META[analysis.estimate_status] : null;

  return (
    <div className="result-card">
      <div className="result-card-top">
        <div>
          <div className="result-company">{r.company}</div>
          <div className="result-time">{timeAgo(r.published)}</div>
        </div>
        <span className={`sentiment-badge ${meta.cls}`}>
          {meta.icon} {meta.label}
        </span>
      </div>

      <p className="result-headline">
        {r.link ? (
          <a href={r.link} target="_blank" rel="noreferrer">
            {r.headline}
          </a>
        ) : (
          r.headline
        )}
      </p>

      {r.related_stocks.length > 0 && (
        <div className="stock-chip-row">
          {r.related_stocks.map((s) => (
            <span key={s.ticker} className={`stock-chip stock-chip-${r.sentiment_label}`}>
              <strong>{s.ticker}</strong>
            </span>
          ))}
        </div>
      )}

      {r.related_news.length > 0 && (
        <div className="related-news-block">
          <div className="related-news-label">Related coverage</div>
          {r.related_news.map((n) => (
            <a key={n.id} href={n.link} target="_blank" rel="noreferrer" className="related-news-item">
              {n.title}
              <span className="related-news-source">{n.source}</span>
            </a>
          ))}
        </div>
      )}

      {!analysis && (
        <button className="analyze-btn" onClick={handleAnalyze} disabled={analyzing}>
          {analyzing ? "Analyzing coverage…" : "📊 Profit % & analyst estimates"}
        </button>
      )}

      {analyzeError && <div className="analyze-error">{analyzeError}</div>}

      {analysis && (
        <div className="analysis-block">
          {analysis.profit_change ? (
            <div className={`analysis-pct analysis-pct-${analysis.profit_change.direction}`}>
              {analysis.profit_change.direction === "up" ? "▲" : "▼"}{" "}
              {analysis.profit_change.metric === "profit" ? "Net profit" : "Revenue"}{" "}
              {analysis.profit_change.direction === "up" ? "up" : "down"} {analysis.profit_change.pct}%
            </div>
          ) : (
            <div className="analysis-empty">No profit/revenue % found in current coverage.</div>
          )}

          {estimateMeta ? (
            <div className={`analysis-estimate ${estimateMeta.cls}`}>
              {estimateMeta.icon} {estimateMeta.label}
            </div>
          ) : (
            <div className="analysis-empty">No analyst-estimate comparison found in current coverage.</div>
          )}

          {analysis.supporting_articles.length > 0 && (
            <div className="related-news-block">
              <div className="related-news-label">Based on</div>
              {analysis.supporting_articles.map((n) => (
                <a key={n.id} href={n.link} target="_blank" rel="noreferrer" className="related-news-item">
                  {n.title}
                  <span className="related-news-source">{n.source}</span>
                </a>
              ))}
            </div>
          )}

          <div className="analysis-disclaimer">
            Extracted from news wording, not a formal analyst-estimates feed.
          </div>
        </div>
      )}
    </div>
  );
}

export default function ResultsView({ refreshSignal }) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [sentimentFilter, setSentimentFilter] = useState("all");

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return fetchResults({ days: 4 })
      .then((data) => setResults(data.results))
      .catch((e) => setError(e.message || "Failed to load results"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useRefreshSignal(refreshSignal, load);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return results.filter((r) => {
      if (sentimentFilter !== "all" && r.sentiment_label !== sentimentFilter) return false;
      if (!q) return true;
      return (
        r.company.toLowerCase().includes(q) ||
        r.related_stocks.some((s) => s.ticker.toLowerCase() === q || s.name.toLowerCase().includes(q))
      );
    });
  }, [results, query, sentimentFilter]);

  return (
    <>
      <div className="view-intro">
        Quarterly financial results filed in the last 4 days, sourced live from BSE announcements.
        Bullish/bearish is a quick read of the headline wording, not a substitute for reading the
        actual results. Tap "Profit % &amp; analyst estimates" on a result to pull live coverage and
        extract what it says about the quarter, if anything.
      </div>

      <div className="sticky-toolbar">
        <form className="search-bar" onSubmit={(e) => e.preventDefault()}>
          <span className="search-icon">🔍</span>
          <input
            type="text"
            inputMode="search"
            placeholder="Filter by company, e.g. Tata, Infosys"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button type="button" className="search-clear-btn" onClick={() => setQuery("")}>
              Clear
            </button>
          )}
        </form>

        <FilterTabs active={sentimentFilter} onChange={setSentimentFilter} />
      </div>

      <div className="news-feed">
        {loading && <div className="status-msg">Loading quarterly results…</div>}
        {error && !loading && <div className="status-msg status-error">{error}</div>}
        {!loading && !error && filtered.length === 0 && (
          <div className="status-msg">
            {query ? `No results matching "${query}".` : "No quarterly results filed in the last 4 days yet."}
          </div>
        )}

        {!loading &&
          !error &&
          filtered.map((r, i) => <ResultCard key={`${r.company}-${r.published}-${i}`} r={r} />)}
      </div>
    </>
  );
}
