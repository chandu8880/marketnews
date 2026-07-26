import { useEffect, useRef } from "react";

// Each view already fetches its own data on mount; this just re-runs
// `reload` when the shared header refresh button increments `signal`,
// skipping the very first render so mount doesn't double-fetch. Calls
// `reload(true)` - the `force` flag tells the backend to bypass its own
// cache-staleness check and actually re-check the source site right now,
// since a manual refresh tap means "check for real," not "give me whatever
// you already had."
export function useRefreshSignal(signal, reload) {
  const isFirstRun = useRef(true);

  useEffect(() => {
    if (isFirstRun.current) {
      isFirstRun.current = false;
      return;
    }
    reload(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signal]);
}
