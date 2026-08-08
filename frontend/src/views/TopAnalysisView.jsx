import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchTopAnalysisDetail, fetchTopAnalysisStocks } from "../api";
import { useRefreshSignal } from "../hooks/useRefreshSignal";

const SENTIMENT_META = {
  bullish: { label: "Bullish", cls: "badge-bullish", icon: "▲" },
  bearish: { label: "Bearish", cls: "badge-bearish", icon: "▼" },
  neutral: { label: "Neutral", cls: "badge-neutral", icon: "●" },
};

function IndicatorRow({ label, value, signal }) {
  if (value == null) return null;
  return (
    <div className="indicator-row">
      <span className="indicator-label">{label}</span>
      <span className="indicator-value">
        {value}
        {signal && <span className={`indicator-signal indicator-signal-${signal}`}>{signal}</span>}
      </span>
    </div>
  );
}

function StockAnalysisDetail({ stock, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchTopAnalysisDetail(stock.ticker)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || "Analysis failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [stock.ticker]);

  const ind = data?.indicators;
  const diValue =
    ind && ind.plus_di != null && ind.minus_di != null ? `${ind.plus_di} / ${ind.minus_di}` : null;

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
      </div>

      {loading && (
        <div className="status-msg">
          Running full analysis — indicators, shareholding, news, AI verdict… (~10s)
        </div>
      )}
      {error && !loading && <div className="status-msg status-error">{error}</div>}

      {!loading && !error && data && (
        <>
          {data.verdict ? (
            <div className={`verdict-card verdict-${data.verdict.verdict}`}>
              <div className="verdict-top">
                <span className="verdict-label">
                  {data.verdict.verdict === "bullish" ? "▲" : data.verdict.verdict === "bearish" ? "▼" : "●"}{" "}
                  {data.verdict.verdict.toUpperCase()}
                </span>
                <span className="verdict-confidence">{data.verdict.confidence}% confidence</span>
              </div>
              <p className="verdict-reasoning">{data.verdict.reasoning}</p>
              <div className="verdict-model">
                AI verdict via {data.verdict.model} — analysis of public data, not investment advice.
              </div>
            </div>
          ) : (
            <div className="status-msg">AI verdict unavailable right now — see the raw data below.</div>
          )}

          {ind && (
            <div className="analysis-section">
              <div className="analysis-section-title">Technical Indicators</div>
              <div className="indicator-grid">
                <IndicatorRow label="RSI (14)" value={ind.rsi} signal={ind.rsi_signal} />
                <IndicatorRow label="Stochastic RSI" value={ind.stoch_rsi} />
                <IndicatorRow label="CCI (20)" value={ind.cci} signal={ind.cci_signal} />
                <IndicatorRow label="MFI (14)" value={ind.mfi} signal={ind.mfi_signal} />
                <IndicatorRow label="MACD" value={ind.macd} signal={ind.macd_signal} />
                <IndicatorRow label="MACD Signal Line" value={ind.macd_signal_line} />
                <IndicatorRow label="MACD Histogram" value={ind.macd_histogram} />
                <IndicatorRow label="VWAP" value={ind.vwap != null ? `₹${ind.vwap}` : null} />
                <IndicatorRow label="+DI / −DI" value={diValue} signal={ind.di_signal} />
              </div>
            </div>
          )}

          {data.shareholding && data.shareholding.quarters.length > 0 && (
            <div className="analysis-section">
              <div className="analysis-section-title">Shareholding Pattern (%)</div>
              <div className="shareholding-table-wrap">
                <table className="shareholding-table">
                  <thead>
                    <tr>
                      <th>Quarter</th>
                      <th>Promoter</th>
                      <th>FII</th>
                      <th>DII</th>
                      <th>Public</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.shareholding.quarters.map((q) => (
                      <tr key={q.quarter}>
                        <td>{q.quarter}</td>
                        <td>{q.promoter ?? "—"}</td>
                        <td>{q.fii ?? "—"}</td>
                        <td>{q.dii ?? "—"}</td>
                        <td>{q.public ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {data.news.length > 0 && (
            <div className="analysis-section">
              <div className="analysis-section-title">Top News</div>
              <div className="related-news-block">
                {data.news.map((n) => (
                  <a key={n.id} href={n.link} target="_blank" rel="noreferrer" className="related-news-item">
                    {n.title}
                    <span className="related-news-source">{n.source}</span>
                  </a>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function TopAnalysisView({ refreshSignal }) {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return fetchTopAnalysisStocks()
      .then((d) => setStocks(d.stocks))
      .catch((e) => setError(e.message || "Failed to load stocks"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useRefreshSignal(refreshSignal, load);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return stocks;
    return stocks.filter((s) => s.ticker.toLowerCase().includes(q) || s.name.toLowerCase().includes(q));
  }, [stocks, query]);

  if (selected) {
    return <StockAnalysisDetail stock={selected} onBack={() => setSelected(null)} />;
  }

  return (
    <>
      <div className="view-intro">
        Top 100 tracked NSE stocks. Tap any stock for a full live analysis — technical indicators,
        FII/DII/Promoter shareholding trend, top news, and an AI-generated bullish/bearish verdict.
        Each analysis is computed live (~10s), not pre-cached, so it reflects current data.
      </div>

      <div className="sticky-toolbar">
        <form className="search-bar" onSubmit={(e) => e.preventDefault()}>
          <span className="search-icon">🔍</span>
          <input
            type="text"
            inputMode="search"
            placeholder="Filter by name or ticker"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button type="button" className="search-clear-btn" onClick={() => setQuery("")}>
              Clear
            </button>
          )}
        </form>
      </div>

      <div className="news-feed">
        {loading && <div className="status-msg">Loading stock list…</div>}
        {error && !loading && <div className="status-msg status-error">{error}</div>}
        {!loading &&
          !error &&
          filtered.map((stock) => {
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
                <div className="stock-row-footer">
                  <span>{stock.mentions} recent mentions</span>
                  <span>Tap for full analysis →</span>
                </div>
              </button>
            );
          })}
      </div>
    </>
  );
}
