import { useRef, useState } from "react";
import "./App.css";
import FilterTabs from "./components/FilterTabs";
import LoginScreen from "./components/LoginScreen";
import NewsCard from "./components/NewsCard";
import SearchBar from "./components/SearchBar";
import SelectionToolbar from "./components/SelectionToolbar";
import SideMenu from "./components/SideMenu";
import { useAuth } from "./hooks/useAuth";
import { useNewsFeed } from "./hooks/useNewsFeed";
import { useRefreshSignal } from "./hooks/useRefreshSignal";
import { useSearch } from "./hooks/useSearch";
import { useTextSelection } from "./hooks/useTextSelection";
import { useTrackedStocks } from "./hooks/useTrackedStocks";
import DividendsView from "./views/DividendsView";
import IpoView from "./views/IpoView";
import OverviewView from "./views/OverviewView";
import ResultsView from "./views/ResultsView";
import ScreenerView from "./views/ScreenerView";
import StocksView from "./views/StocksView";
import TopAnalysisView from "./views/TopAnalysisView";

const VIEW_TITLES = {
  overview: "Overview",
  news: "MarketPulse",
  stocks: "Stocks",
  "top-analysis": "Top Analysis",
  screener: "Screener",
  results: "Results",
  dividends: "Dividends",
  ipo: "IPO Watch",
};

function NewsView({ refreshSignal }) {
  const [filter, setFilter] = useState("all");
  const { articles, loading, error, pendingCount, showPending, reload } = useNewsFeed(filter);
  const search = useSearch();
  const { stocks } = useTrackedStocks();
  useRefreshSignal(refreshSignal, reload);

  const showingSearch = search.active;
  const list = showingSearch ? search.results : articles;
  const isLoading = showingSearch ? search.loading : loading;
  const isError = showingSearch ? search.error : error;

  return (
    <>
      <div className="sticky-toolbar">
        <SearchBar
          onSearch={search.runSearch}
          onClear={search.clearSearch}
          active={showingSearch}
          suggestions={stocks}
        />
        {!showingSearch && <FilterTabs active={filter} onChange={setFilter} />}
      </div>

      {!showingSearch && pendingCount > 0 && (
        <button className="new-articles-banner" onClick={showPending}>
          {pendingCount} new update{pendingCount > 1 ? "s" : ""} — tap to show
        </button>
      )}

      {showingSearch && (
        <div className="view-intro">
          {isLoading ? "Searching…" : `${list.length} result${list.length === 1 ? "" : "s"} for "${search.query}"`}
        </div>
      )}

      <div className="news-feed">
        {isLoading && <div className="status-msg">{showingSearch ? "Searching the web…" : "Loading market news…"}</div>}
        {isError && !isLoading && <div className="status-msg status-error">{isError}</div>}
        {!isLoading && !isError && list.length === 0 && (
          <div className="status-msg">
            {showingSearch ? "No results found." : "No articles found for this filter yet."}
          </div>
        )}
        {!isLoading && !isError && list.map((article) => <NewsCard key={article.id} article={article} />)}
        {!isLoading && !isError && list.length > 0 && !showingSearch && (
          <div className="feed-end">You're all caught up. News refreshes automatically.</div>
        )}
      </div>
    </>
  );
}

function App() {
  const [view, setView] = useState("overview");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [refreshSignal, setRefreshSignal] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const contentRef = useRef(null);
  const { selection, clear } = useTextSelection(contentRef);
  const auth = useAuth();

  function handleSelectView(key) {
    setView(key);
    setDrawerOpen(false);
  }

  function handleRefresh() {
    setRefreshSignal((s) => s + 1);
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 700);
  }

  function handleLogout() {
    auth.logout();
    setDrawerOpen(false);
    setView("overview");
  }

  if (auth.checking) {
    return <div className="app-shell login-shell login-checking" />;
  }

  if (!auth.isLoggedIn) {
    return <LoginScreen onLogin={auth.login} />;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <button className="menu-toggle-btn" onClick={() => setDrawerOpen(true)} aria-label="Open menu">
          ☰
        </button>
        <div className="app-header-title">{VIEW_TITLES[view]}</div>
        <button
          className={`refresh-btn ${refreshing ? "refresh-btn-spinning" : ""}`}
          onClick={handleRefresh}
          aria-label="Refresh"
        >
          ⟳
        </button>
      </header>

      <SideMenu
        open={drawerOpen}
        activeView={view}
        onSelect={handleSelectView}
        onClose={() => setDrawerOpen(false)}
        email={auth.email}
        onLogout={handleLogout}
      />

      <main ref={contentRef} className="app-content">
        {view === "overview" && <OverviewView refreshSignal={refreshSignal} />}
        {view === "news" && <NewsView refreshSignal={refreshSignal} />}
        {view === "stocks" && <StocksView refreshSignal={refreshSignal} />}
        {view === "top-analysis" && <TopAnalysisView refreshSignal={refreshSignal} />}
        {view === "screener" && <ScreenerView refreshSignal={refreshSignal} />}
        {view === "results" && <ResultsView refreshSignal={refreshSignal} />}
        {view === "dividends" && <DividendsView refreshSignal={refreshSignal} />}
        {view === "ipo" && <IpoView refreshSignal={refreshSignal} />}
      </main>

      <SelectionToolbar selection={selection} onClear={clear} />
    </div>
  );
}

export default App;
