import { useEffect, useMemo, useState } from "react";
import FilterTabs from "../components/FilterTabs";
import NewsCard from "../components/NewsCard";
import SearchBar from "../components/SearchBar";
import StockSentimentBar from "../components/StockSentimentBar";
import { fetchNews } from "../api";
import { useRefreshSignal } from "../hooks/useRefreshSignal";
import { useSearch } from "../hooks/useSearch";
import { useStockUniverse } from "../hooks/useStockUniverse";
import { useTrackedStocks } from "../hooks/useTrackedStocks";

const SENTIMENT_META = {
  bullish: { label: "Bullish", cls: "badge-bullish", icon: "▲" },
  bearish: { label: "Bearish", cls: "badge-bearish", icon: "▼" },
  neutral: { label: "Neutral", cls: "badge-neutral", icon: "●" },
};

const DEFAULT_TOP_N = 50;

// "All" keeps the existing top-50-by-activity ranking; Bullish/Bearish show
// every matching stock (not capped to 50) ordered by confidence - i.e. how
// strongly one-sided its recent coverage has been, not just mention count.
function applyTab(stocks, tab) {
  if (tab === "all") return stocks.slice(0, DEFAULT_TOP_N);
  if (tab === "bullish") {
    return stocks
      .filter((s) => s.overall_sentiment === "bullish")
      .sort((a, b) => b.net_score - a.net_score);
  }
  if (tab === "bearish") {
    return stocks
      .filter((s) => s.overall_sentiment === "bearish")
      .sort((a, b) => a.net_score - b.net_score);
  }
  return stocks.filter((s) => s.overall_sentiment === "neutral");
}

function StockDetail({ stock, onBack }) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchNews({ ticker: stock.ticker, limit: 60 })
      .then((data) => {
        if (!cancelled) setArticles(data.articles);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || "Failed to load news");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [stock.ticker]);

  const meta = SENTIMENT_META[stock.overall_sentiment] || SENTIMENT_META.neutral;

  return (
    <div className="news-feed">
      <button className="back-btn" onClick={onBack}>
        ← All stocks
      </button>

      <div className="stock-detail-header">
        <div>
          <h2 className="stock-detail-ticker">{stock.ticker}</h2>
          <div className="stock-detail-name">{stock.name}</div>
        </div>
        <span className={`sentiment-badge ${meta.cls}`}>
          {meta.icon} {meta.label}
        </span>
      </div>

      <StockSentimentBar
        bullish={stock.bullish_count}
        bearish={stock.bearish_count}
        neutral={stock.neutral_count}
      />
      <div className="stock-detail-counts">
        <span className="count-bullish">{stock.bullish_count} bullish</span>
        <span className="count-bearish">{stock.bearish_count} bearish</span>
        <span className="count-neutral">{stock.neutral_count} neutral</span>
        <span className="count-mentions">{stock.mentions} mentions</span>
      </div>

      {loading && <div className="status-msg">Loading news for {stock.ticker}…</div>}
      {error && !loading && <div className="status-msg status-error">{error}</div>}
      {!loading && !error && articles.map((a) => <NewsCard key={a.id} article={a} />)}
    </div>
  );
}

export default function StocksView({ refreshSignal }) {
  const { stocks, loading, error, reload } = useTrackedStocks();
  const universe = useStockUniverse();
  const [selected, setSelected] = useState(null);
  const [sentimentTab, setSentimentTab] = useState("all");
  const search = useSearch();
  useRefreshSignal(refreshSignal, reload);

  // Autocomplete suggestions cover every listed Indian stock, not just the
  // ones currently trending in news - tracked ones (which carry live
  // sentiment) take priority over the bare universe entry for the same symbol.
  const suggestions = useMemo(() => {
    const bySymbol = new Map();
    for (const s of universe) bySymbol.set(s.symbol, { ticker: s.symbol, name: s.name });
    for (const s of stocks) bySymbol.set(s.ticker, s);
    return Array.from(bySymbol.values());
  }, [universe, stocks]);

  const tabbed = useMemo(() => applyTab(stocks, sentimentTab), [stocks, sentimentTab]);

  const matches = useMemo(() => {
    if (!search.active) return tabbed;
    const q = search.query.trim().toLowerCase();
    return stocks.filter(
      (s) => s.ticker.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)
    );
  }, [stocks, tabbed, search.active, search.query]);

  if (selected) {
    return <StockDetail stock={selected} onBack={() => setSelected(null)} />;
  }

  // A search that doesn't match any tracked stock (e.g. a smaller company
  // not covered by the standing RSS feeds) still gets its latest news via
  // a live search, same as the News tab, rather than a dead end.
  const showNewsFallback = search.active && !loading && matches.length === 0;

  return (
    <>
      <div className="sticky-toolbar">
        <SearchBar
          onSearch={search.runSearch}
          onClear={search.clearSearch}
          active={search.active}
          suggestions={suggestions}
        />
        {!search.active && <FilterTabs active={sentimentTab} onChange={setSentimentTab} />}
      </div>

      <div className="news-feed">
        {!search.active && sentimentTab === "all" && (
          <div className="view-intro">
            Top 50 stocks by news activity today. Search covers every listed Indian stock, not
            just these — pick any company and it'll pull live news even if it isn't trending yet.
          </div>
        )}
        {!search.active && sentimentTab === "bullish" && (
          <div className="view-intro">
            Every currently-bullish stock, most confident first.
          </div>
        )}
        {!search.active && sentimentTab === "bearish" && (
          <div className="view-intro">
            Every currently-bearish stock, most confident first.
          </div>
        )}
        {!search.active && sentimentTab === "neutral" && (
          <div className="view-intro">Stocks with mixed or inconclusive recent coverage.</div>
        )}
        {search.active && !showNewsFallback && (
          <div className="view-intro">
            {matches.length} tracked stock{matches.length === 1 ? "" : "s"} matching "{search.query}"
          </div>
        )}
        {showNewsFallback && (
          <div className="view-intro">
            No tracked stock matches "{search.query}" — showing latest news for it instead.
          </div>
        )}

        {loading && <div className="status-msg">Analyzing stock sentiment…</div>}
        {error && !loading && <div className="status-msg status-error">{error}</div>}
        {!loading && !error && !search.active && stocks.length === 0 && (
          <div className="status-msg">No stock mentions found yet.</div>
        )}
        {!loading && !error && !search.active && stocks.length > 0 && matches.length === 0 && (
          <div className="status-msg">No {sentimentTab} stocks right now.</div>
        )}

        {showNewsFallback && (
          <>
            {search.loading && <div className="status-msg">Searching the web…</div>}
            {search.error && !search.loading && <div className="status-msg status-error">{search.error}</div>}
            {!search.loading && !search.error && search.results.length === 0 && (
              <div className="status-msg">No news found for "{search.query}".</div>
            )}
            {!search.loading &&
              !search.error &&
              search.results.map((article) => <NewsCard key={article.id} article={article} />)}
          </>
        )}

        {!loading &&
          !error &&
          !showNewsFallback &&
          matches.map((stock) => {
            const meta = SENTIMENT_META[stock.overall_sentiment] || SENTIMENT_META.neutral;
            return (
              <button key={stock.ticker} className="stock-row-card" onClick={() => setSelected(stock)}>
                <div className="stock-row-top">
                  <div>
                    <span className="stock-row-ticker">{stock.ticker}</span>
                    <span className="stock-row-name">{stock.name}</span>
                  </div>
                  <span className={`sentiment-badge ${meta.cls}`}>
                    {meta.icon} {meta.label}
                  </span>
                </div>
                <StockSentimentBar
                  bullish={stock.bullish_count}
                  bearish={stock.bearish_count}
                  neutral={stock.neutral_count}
                />
                <div className="stock-row-footer">
                  <span>{stock.mentions} mentions</span>
                  <span>Net score {stock.net_score > 0 ? "+" : ""}{stock.net_score}</span>
                </div>
              </button>
            );
          })}
      </div>
    </>
  );
}
