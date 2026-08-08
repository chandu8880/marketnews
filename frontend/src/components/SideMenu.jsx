const MENU_ITEMS = [
  { key: "overview", label: "Overview", icon: "⭐" },
  { key: "news", label: "News", icon: "📰" },
  { key: "stocks", label: "Stocks", icon: "📊" },
  { key: "top-analysis", label: "Top Analysis", icon: "🧪" },
  { key: "results", label: "Results", icon: "📄" },
  { key: "dividends", label: "Dividends", icon: "💰" },
  { key: "ipo", label: "IPO", icon: "🏦" },
];

export default function SideMenu({ open, activeView, onSelect, onClose, email, onLogout }) {
  return (
    <>
      <div
        className={`side-menu-backdrop ${open ? "side-menu-backdrop-open" : ""}`}
        onClick={onClose}
        aria-hidden={!open}
      />
      <nav className={`side-menu ${open ? "side-menu-open" : ""}`} aria-hidden={!open}>
        <div className="side-menu-header">
          <span className="app-logo">📈</span>
          <span>MarketPulse</span>
        </div>
        <ul className="side-menu-list">
          {MENU_ITEMS.map((item) => (
            <li key={item.key}>
              <button
                className={`side-menu-item ${activeView === item.key ? "side-menu-item-active" : ""}`}
                onClick={() => onSelect(item.key)}
              >
                <span className="side-menu-icon">{item.icon}</span>
                {item.label}
              </button>
            </li>
          ))}
        </ul>

        <div className="side-menu-footer">
          {email && <div className="side-menu-phone">Signed in as {email}</div>}
          <button className="side-menu-item side-menu-logout" onClick={onLogout}>
            <span className="side-menu-icon">🚪</span>
            Logout
          </button>
        </div>
      </nav>
    </>
  );
}
