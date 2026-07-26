export default function StockSentimentBar({ bullish, bearish, neutral }) {
  const total = bullish + bearish + neutral || 1;
  return (
    <div className="stock-sentiment-bar" title={`${bullish} bullish · ${bearish} bearish · ${neutral} neutral`}>
      <span className="ssb-bullish" style={{ width: `${(bullish / total) * 100}%` }} />
      <span className="ssb-neutral" style={{ width: `${(neutral / total) * 100}%` }} />
      <span className="ssb-bearish" style={{ width: `${(bearish / total) * 100}%` }} />
    </div>
  );
}
