const TABS = [
  { key: "all", label: "All" },
  { key: "bullish", label: "Bullish" },
  { key: "bearish", label: "Bearish" },
  { key: "neutral", label: "Neutral" },
];

export default function FilterTabs({ active, onChange }) {
  return (
    <div className="filter-tabs" role="tablist">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          role="tab"
          aria-selected={active === tab.key}
          className={`filter-tab ${active === tab.key ? "filter-tab-active" : ""} filter-tab-${tab.key}`}
          onClick={() => onChange(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
