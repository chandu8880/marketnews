import { useEffect, useState } from "react";
import { fetchStockUniverse } from "../api";

// The full ~4,900 BSE/NSE-listed company universe, fetched once per
// session, purely to power "search any Indian stock" autocomplete -
// distinct from the much smaller set of stocks currently tracked/mentioned
// in news (useTrackedStocks), which carries live sentiment data.
export function useStockUniverse() {
  const [universe, setUniverse] = useState([]);

  useEffect(() => {
    fetchStockUniverse()
      .then((data) => setUniverse(data.stocks))
      .catch(() => {
        // Silent failure: search just falls back to the smaller tracked
        // list rather than breaking the screen over an autocomplete extra.
      });
  }, []);

  return universe;
}
