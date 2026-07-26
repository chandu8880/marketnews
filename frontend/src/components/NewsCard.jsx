import { timeAgo } from "../utils/time";

const SENTIMENT_META = {
  bullish: { label: "Bullish", cls: "badge-bullish", icon: "▲" },
  bearish: { label: "Bearish", cls: "badge-bearish", icon: "▼" },
  neutral: { label: "Neutral", cls: "badge-neutral", icon: "●" },
};

export default function NewsCard({ article, isNew }) {
  const meta = SENTIMENT_META[article.sentiment_label] || SENTIMENT_META.neutral;

  return (
    <article className={`news-card ${isNew ? "news-card-new" : ""}`}>
      <div className="news-card-top">
        <span className="news-source">{article.source}</span>
        <span className="news-dot">·</span>
        <span className="news-time">{timeAgo(article.published)}</span>
        <span className={`sentiment-badge ${meta.cls}`}>
          {meta.icon} {meta.label}
        </span>
      </div>

      <h2 className="news-title">
        <a href={article.link} target="_blank" rel="noreferrer">
          {article.title}
        </a>
      </h2>

      {article.summary && <p className="news-summary">{article.summary}</p>}

      {article.related_stocks.length > 0 && (
        <div className="stock-chip-row">
          {article.related_stocks.map((s) => (
            <span key={s.ticker} className={`stock-chip stock-chip-${s.sentiment}`}>
              <strong>{s.ticker}</strong>
              <span className="stock-chip-name">{s.name}</span>
              <span className="stock-chip-arrow">
                {s.sentiment === "bullish" ? "▲" : s.sentiment === "bearish" ? "▼" : "●"}
              </span>
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
