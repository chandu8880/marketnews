import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchScreener } from "../api";
import { useRefreshSignal } from "../hooks/useRefreshSignal";

const COLUMNS = [
  { key: "name", label: "Stock", type: "text" },
  { key: "rsi", label: "RSI" },
  { key: "stoch_rsi", label: "Stoch RSI" },
  { key: "cci", label: "CCI" },
  { key: "macd", label: "MACD" },
  { key: "macd_signal_line", label: "Signal" },
  { key: "macd_histogram", label: "Histogram" },
  { key: "vwap", label: "VWAP" },
  { key: "plus_di", label: "+DI" },
  { key: "minus_di", label: "-DI" },
  { key: "adx", label: "ADX" },
];

function fmt(v) {
  if (v === null || v === undefined) return "—";
  return v.toFixed(2);
}

export default function ScreenerView({ refreshSignal }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sort, setSort] = useState({ key: "name", dir: "asc" });

  const load = useCallback((force = false) => {
    setLoading(true);
    setError(null);
    return fetchScreener(force)
      .then((data) => setRows(data.rows))
      .catch((e) => setError(e.message || "Failed to load screener data"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useRefreshSignal(refreshSignal, load);

  function handleSort(key) {
    setSort((prev) =>
      prev.key === key ? { key, dir: prev.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }
    );
  }

  const sortedRows = useMemo(() => {
    const col = COLUMNS.find((c) => c.key === sort.key);
    const isText = col?.type === "text";
    const dirMul = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      if (isText) return dirMul * String(av).localeCompare(String(bv));
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      return dirMul * (av - bv);
    });
  }, [rows, sort]);

  return (
    <div className="news-feed">
      <div className="view-intro">
        RSI, Stochastic RSI, CCI, MACD, VWAP, DI and ADX for the top 75 tracked stocks in one table. Tap a column
        header to sort.
      </div>
      {loading && <div className="status-msg">Loading screener…</div>}
      {error && !loading && <div className="status-msg status-error">{error}</div>}
      {!loading && !error && rows.length === 0 && <div className="status-msg">No screener data available yet.</div>}
      {!loading && !error && rows.length > 0 && (
        <div className="shareholding-table-wrap screener-table-wrap">
          <table className="shareholding-table screener-table">
            <thead>
              <tr>
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className="screener-th"
                    onClick={() => handleSort(col.key)}
                    aria-sort={sort.key === col.key ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                  >
                    {col.label}
                    {sort.key === col.key && (
                      <span className="screener-sort-arrow">{sort.dir === "asc" ? " ▲" : " ▼"}</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((r) => (
                <tr key={r.ticker}>
                  <td className="screener-stock-cell">
                    <div className="screener-ticker">{r.ticker}</div>
                    <div className="screener-name">{r.name}</div>
                  </td>
                  <td>{fmt(r.rsi)}</td>
                  <td>{fmt(r.stoch_rsi)}</td>
                  <td>{fmt(r.cci)}</td>
                  <td>{fmt(r.macd)}</td>
                  <td>{fmt(r.macd_signal_line)}</td>
                  <td>{fmt(r.macd_histogram)}</td>
                  <td>{fmt(r.vwap)}</td>
                  <td>{fmt(r.plus_di)}</td>
                  <td>{fmt(r.minus_di)}</td>
                  <td>{fmt(r.adx)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
