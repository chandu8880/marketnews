// A Kite-style 52-week range bar: a horizontal track from the 52-week low
// to high, with a marker showing where the current price and the average
// sit within that range.
export default function PriceRangeBar({ low, avg, high, price }) {
  if (low == null || high == null || high <= low) return null;

  const pct = (v) => Math.min(100, Math.max(0, ((v - low) / (high - low)) * 100));
  const pricePct = price != null ? pct(price) : null;
  const avgPct = avg != null ? pct(avg) : null;

  return (
    <div className="price-range">
      <div className="price-range-track">
        {avgPct != null && (
          <span className="price-range-avg-marker" style={{ left: `${avgPct}%` }} title={`Avg ₹${avg}`} />
        )}
        {pricePct != null && (
          <span className="price-range-price-marker" style={{ left: `${pricePct}%` }} title={`Price ₹${price}`} />
        )}
      </div>
      <div className="price-range-labels">
        <div className="price-range-label">
          <span className="price-range-label-tag">Low</span>
          <span className="price-range-label-value">₹{low.toLocaleString("en-IN")}</span>
        </div>
        {avg != null && (
          <div className="price-range-label">
            <span className="price-range-label-tag">Avg</span>
            <span className="price-range-label-value">₹{avg.toLocaleString("en-IN")}</span>
          </div>
        )}
        <div className="price-range-label price-range-label-right">
          <span className="price-range-label-tag">High</span>
          <span className="price-range-label-value">₹{high.toLocaleString("en-IN")}</span>
        </div>
      </div>
    </div>
  );
}
