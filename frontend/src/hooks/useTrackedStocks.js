import { useCallback, useEffect, useState } from "react";
import { fetchStocks } from "../api";

// The ~65 NSE companies/indices tickers.py tags in news, used to power
// search-bar autocomplete so users pick a known spelling instead of typing
// a company name that turns up zero live-search results.
export function useTrackedStocks() {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetches the backend's max (200), not just the 50 shown by default in the
  // "All" tab - the Bullish/Bearish tabs filter this same broader set down
  // to "every currently-bullish/bearish stock", not just whichever of them
  // happened to make the top 50 by mentions.
  const reload = useCallback((force = false) => {
    setLoading(true);
    setError(null);
    return fetchStocks(200, force)
      .then((data) => setStocks(data.stocks))
      .catch((e) => setError(e.message || "Failed to load stocks"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return { stocks, loading, error, reload };
}
