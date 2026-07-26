import { useCallback, useEffect, useState } from "react";
import { fetchMarketIndices } from "../api";

const POLL_INTERVAL_MS = 60_000; // matches the backend's own refresh cadence

export function useMarketIndices() {
  const [indices, setIndices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback((force = false) => {
    return fetchMarketIndices(force)
      .then((data) => {
        setIndices(data.indices);
        setError(null);
      })
      .catch((e) => setError(e.message || "Failed to load market indices"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(() => load(), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [load]);

  return { indices, loading, error, reload: load };
}
