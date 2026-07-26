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
import { useSearch } from "./hooks/useSearch";
import { useTextSelection } from "./hooks/useTextSelection";
import { useTrackedStocks } from "./hooks/useTrackedStocks";
import DividendsView from "./views/DividendsView";
import IpoView from "./views/IpoView";
import OverviewView from "./views/OverviewView";
import ResultsView from "./views/ResultsView";
import StocksView from "./views/StocksView";

const VIEW_TITLES = {
  overview: "Overview",
  news: "MarketPulse",
  stocks: "Stocks",
  results: "Results",
  dividends: "Dividends",
  ipo: "IPO Watch",
};

function NewsView() {
  const [filter, setFilter] = useState("all");
  const { articles, loading, error, pendingCount, showPending } = useNewsFeed(filter);
  const search = useSearch();
  const { stocks } = useTrackedStocks();

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
  const contentRef = useRef(null);
  const { selection, clear } = useTextSelection(contentRef);
  const auth = useAuth();

  function handleSelectView(key) {
    setView(key);
    setDrawerOpen(false);
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
        <span className="header-spacer" />
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
        {view === "overview" && <OverviewView />}
        {view === "news" && <NewsView />}
        {view === "stocks" && <StocksView />}
        {view === "results" && <ResultsView />}
        {view === "dividends" && <DividendsView />}
        {view === "ipo" && <IpoView />}
      </main>

      <SelectionToolbar selection={selection} onClear={clear} />
    </div>
  );
}

export default App;
