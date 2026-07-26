import { useMemo, useState } from "react";

export default function SearchBar({ onSearch, onClear, active, suggestions = [] }) {
  const [value, setValue] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);

  const filtered = useMemo(() => {
    const q = value.trim().toLowerCase();
    if (!q) return [];
    return suggestions
      .filter((s) => s.ticker.toLowerCase().startsWith(q) || s.name.toLowerCase().includes(q))
      .slice(0, 6);
  }, [value, suggestions]);

  function submit(q) {
    const trimmed = q.trim();
    if (!trimmed) return;
    setShowSuggestions(false);
    onSearch(trimmed);
  }

  function handleSubmit(e) {
    e.preventDefault();
    submit(value);
  }

  function handlePick(s) {
    setValue(s.name);
    submit(s.name);
  }

  function handleClear() {
    setValue("");
    setShowSuggestions(false);
    onClear();
  }

  return (
    <div className="search-bar-wrap">
      <form className="search-bar" onSubmit={handleSubmit}>
        <span className="search-icon">🔍</span>
        <input
          type="text"
          inputMode="search"
          placeholder="Search a stock, e.g. Reliance, TCS, HDFC Bank"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setShowSuggestions(true);
          }}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
        />
        {active ? (
          <button type="button" className="search-clear-btn" onClick={handleClear}>
            Clear
          </button>
        ) : (
          <button type="submit" className="search-go-btn">
            Go
          </button>
        )}
      </form>

      {showSuggestions && filtered.length > 0 && (
        <ul className="search-suggestions">
          {filtered.map((s) => (
            <li key={s.ticker}>
              <button type="button" className="search-suggestion-item" onMouseDown={() => handlePick(s)}>
                <span className="search-suggestion-ticker">{s.ticker}</span>
                <span className="search-suggestion-name">{s.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
