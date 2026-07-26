import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchIpos } from "../api";
import { useRefreshSignal } from "../hooks/useRefreshSignal";

const STATUS_CLASS = {
  Upcoming: "ipo-status-upcoming",
  Open: "ipo-status-open",
  Closed: "ipo-status-closed",
};

// IPOs with no status yet (GMP not posted, only seen in the subscription
// table) default to "Upcoming" rather than being dropped from every tab.
const TABS = [
  { key: "Open", label: "Ongoing" },
  { key: "Upcoming", label: "Upcoming" },
  { key: "Closed", label: "Closed" },
];

function tabKeyFor(status) {
  return status === "Open" || status === "Closed" ? status : "Upcoming";
}

export default function IpoView({ refreshSignal }) {
  const [ipos, setIpos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("Open");

  const load = useCallback((force = false) => {
    setLoading(true);
    setError(null);
    return fetchIpos(force)
      .then((data) => setIpos(data.ipos))
      .catch((e) => setError(e.message || "Failed to load IPO data"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useRefreshSignal(refreshSignal, load);

  const counts = useMemo(() => {
    const c = { Open: 0, Upcoming: 0, Closed: 0 };
    for (const ipo of ipos) c[tabKeyFor(ipo.status)] += 1;
    return c;
  }, [ipos]);

  const visibleIpos = useMemo(
    () => ipos.filter((ipo) => tabKeyFor(ipo.status) === activeTab),
    [ipos, activeTab]
  );

  return (
    <div className="news-feed">
      <div className="view-intro">
        Grey Market Premium and subscription data for current &amp; recent IPOs, sourced live from
        ipowatch.in. GMP is an unregulated, informal indicator — not investment advice.
      </div>

      <div className="ipo-tab-bar">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={`ipo-tab ${activeTab === tab.key ? "ipo-tab-active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
            <span className="ipo-tab-count">{counts[tab.key]}</span>
          </button>
        ))}
      </div>

      {loading && <div className="status-msg">Loading IPO data…</div>}
      {error && !loading && <div className="status-msg status-error">{error}</div>}
      {!loading && !error && visibleIpos.length === 0 && (
        <div className="status-msg">No {TABS.find((t) => t.key === activeTab)?.label.toLowerCase()} IPOs right now.</div>
      )}
      {!loading &&
        !error &&
        visibleIpos.map((ipo) => (
          <div key={ipo.company} className="ipo-card">
            <div className="ipo-card-top">
              <div className="ipo-company">{ipo.company}</div>
              <div className="ipo-badges">
                {ipo.type && <span className="ipo-type-chip">{ipo.type}</span>}
                {ipo.status && (
                  <span className={`ipo-status-chip ${STATUS_CLASS[ipo.status] || ""}`}>{ipo.status}</span>
                )}
              </div>
            </div>

            {ipo.gmp_amount != null && (
              <div className="ipo-gmp-row">
                <span className="ipo-gmp-label">GMP</span>
                <span className="ipo-gmp-value">
                  {ipo.gmp_trend} ₹{ipo.gmp_amount}
                </span>
                {ipo.price_band && <span className="ipo-price-band">Band: {ipo.price_band}</span>}
                {ipo.est_listing_gain && (
                  <span className="ipo-est-gain">Est. gain: {ipo.est_listing_gain}</span>
                )}
              </div>
            )}

            {ipo.subscription && (
              <div className="ipo-subscription-grid">
                <div>
                  <span className="ipo-sub-label">QIB</span>
                  <span className="ipo-sub-value">{ipo.subscription.qib_times ?? "-"}x</span>
                </div>
                <div>
                  <span className="ipo-sub-label">NII</span>
                  <span className="ipo-sub-value">{ipo.subscription.nii_times ?? "-"}x</span>
                </div>
                <div>
                  <span className="ipo-sub-label">Retail</span>
                  <span className="ipo-sub-value">{ipo.subscription.retail_times ?? "-"}x</span>
                </div>
                <div>
                  <span className="ipo-sub-label">Total</span>
                  <span className="ipo-sub-value ipo-sub-total">{ipo.subscription.total_times ?? "-"}x</span>
                </div>
              </div>
            )}

            <div className="ipo-card-footer">
              {ipo.date_range && <span>{ipo.date_range}</span>}
              {ipo.gmp_last_updated && <span>Updated {ipo.gmp_last_updated}</span>}
            </div>
          </div>
        ))}
    </div>
  );
}
