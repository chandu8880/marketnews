import { useCallback, useEffect, useState } from "react";
import { fetchDividends } from "../api";
import { useRefreshSignal } from "../hooks/useRefreshSignal";

function daysAwayLabel(days) {
  if (days === 0) return "Today";
  if (days === 1) return "Tomorrow";
  return `In ${days} days`;
}

export default function DividendsView({ refreshSignal }) {
  const [dividends, setDividends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback((force = false) => {
    setLoading(true);
    setError(null);
    return fetchDividends(4, force)
      .then((data) => setDividends(data.dividends))
      .catch((e) => setError(e.message || "Failed to load dividends"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useRefreshSignal(refreshSignal, load);

  return (
    <div className="news-feed">
      <div className="view-intro">
        Stocks going ex-dividend in the next 4 days, sourced live from BSE corporate actions.
      </div>
      {loading && <div className="status-msg">Loading dividend calendar…</div>}
      {error && !loading && <div className="status-msg status-error">{error}</div>}
      {!loading && !error && dividends.length === 0 && (
        <div className="status-msg">No dividends going ex-date in the next 4 days.</div>
      )}
      {!loading &&
        !error &&
        dividends.map((d) => (
          <div key={`${d.symbol}-${d.ex_date}`} className="dividend-card">
            <div className="dividend-card-top">
              <div>
                <div className="dividend-symbol">{d.symbol}</div>
                <div className="dividend-company">{d.company}</div>
              </div>
              <span className="dividend-days-chip">{daysAwayLabel(d.days_away)}</span>
            </div>
            <div className="dividend-card-bottom">
              <span className="dividend-type">{d.dividend_type}</span>
              {d.amount != null && <span className="dividend-amount">₹{d.amount.toFixed(2)}/share</span>}
              <span className="dividend-exdate">Ex-date: {d.ex_date}</span>
            </div>
          </div>
        ))}
    </div>
  );
}
