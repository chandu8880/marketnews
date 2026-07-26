import { useMarketIndices } from "../hooks/useMarketIndices";

function formatValue(value) {
  return value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

export default function IndicesTicker() {
  const { indices, loading, error } = useMarketIndices();

  if (loading && indices.length === 0) {
    return (
      <div className="indices-ticker">
        <div className="indices-ticker-loading">Loading live indices…</div>
      </div>
    );
  }

  if (error && indices.length === 0) {
    return null; // fail quietly - the rest of Overview still works without it
  }

  return (
    <div className="indices-ticker">
      {indices.map((idx) => {
        const up = (idx.change ?? 0) >= 0;
        return (
          <div key={idx.name} className={`indices-ticker-card ${up ? "indices-up" : "indices-down"}`}>
            <div className="indices-ticker-name">{idx.name}</div>
            <div className="indices-ticker-value">{formatValue(idx.value)}</div>
            {idx.change != null && (
              <div className="indices-ticker-change">
                {up ? "▲" : "▼"} {Math.abs(idx.change).toFixed(2)}
                {idx.change_pct != null && ` (${idx.change_pct > 0 ? "+" : ""}${idx.change_pct.toFixed(2)}%)`}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
