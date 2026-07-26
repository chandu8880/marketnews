import { useCallback, useEffect, useRef, useState } from "react";
import { fetchLatestSince, fetchNews } from "../api";

const POLL_INTERVAL_MS = 60_000;

export function useNewsFeed(filter, limit = 60) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pendingCount, setPendingCount] = useState(0);
  const lastServerTimeRef = useRef(null);
  const pendingArticlesRef = useRef([]);
  const filterRef = useRef(filter);
  filterRef.current = filter;

  const loadInitial = useCallback(async (force = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchNews({ sentiment: filter, limit, force });
      setArticles(data.articles);
      lastServerTimeRef.current = data.server_time;
      pendingArticlesRef.current = [];
      setPendingCount(0);
    } catch (e) {
      setError(e.message || "Failed to load news");
    } finally {
      setLoading(false);
    }
  }, [filter, limit]);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  // Poll for newly-fetched articles without disrupting the user's scroll position;
  // new items are held back until the user taps "show new" (or filter/reload happens).
  useEffect(() => {
    const interval = setInterval(async () => {
      if (!lastServerTimeRef.current) return;
      try {
        const data = await fetchLatestSince(lastServerTimeRef.current);
        lastServerTimeRef.current = data.server_time;
        if (data.articles.length > 0) {
          const currentFilter = filterRef.current;
          const matching = data.articles.filter((a) =>
            currentFilter === "all" ? true : a.sentiment_label === currentFilter
          );
          if (matching.length > 0) {
            const seen = new Set(pendingArticlesRef.current.map((a) => a.id));
            const fresh = matching.filter((a) => !seen.has(a.id));
            pendingArticlesRef.current = [...fresh, ...pendingArticlesRef.current];
            setPendingCount(pendingArticlesRef.current.length);
          }
        }
      } catch {
        // Silent failure on background poll; next tick will retry.
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  const showPending = useCallback(() => {
    setArticles((prev) => {
      const existingIds = new Set(prev.map((a) => a.id));
      const toAdd = pendingArticlesRef.current.filter((a) => !existingIds.has(a.id));
      return [...toAdd, ...prev];
    });
    pendingArticlesRef.current = [];
    setPendingCount(0);
  }, []);

  return { articles, loading, error, pendingCount, showPending, reload: loadInitial };
}
