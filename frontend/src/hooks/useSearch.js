import { useCallback, useState } from "react";
import { searchNews } from "../api";

export function useSearch() {
  const [query, setQuery] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runSearch = useCallback(async (q) => {
    setQuery(q);
    setLoading(true);
    setError(null);
    try {
      const data = await searchNews(q);
      setResults(data.articles);
    } catch (e) {
      setError(e.message || "Search failed");
    } finally {
      setLoading(false);
    }
  }, []);

  const clearSearch = useCallback(() => {
    setQuery(null);
    setResults([]);
    setError(null);
  }, []);

  return { query, results, loading, error, runSearch, clearSearch, active: query !== null };
}
